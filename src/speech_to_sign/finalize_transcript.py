#!/usr/bin/env python3
# finalize_transcript_tail.py
# Live-cleaner: tails live_transcript.txt and appends cleaned sentences to clean_transcript.txt

import os, re, sys, time

IN_PATH  = "live_transcript.txt"
OUT_PATH = "clean_transcript.txt"

# --- same heuristics as your batch script ---
TAG_LINE_RE   = re.compile(r"^\s*\[[^\]]+\]\s*$")   # e.g., [BLANK_AUDIO], [MUSIC], [LAUGHTER]
INLINE_TAG_RE = re.compile(r"\[[^\]]+\]")           # strip inline [ ... ]
END_PUNCT_RE  = re.compile(r"[.!?…]$")

COMMIT_ON_PUNCT = True
FORCE_PERIOD    = True
MIN_CHARS       = 8

def clean_text(s: str) -> str:
    s = INLINE_TAG_RE.sub("", s)
    s = " ".join(s.strip().split())
    return s

def finalize_text(s: str) -> str:
    if not s:
        return ""
    # capitalize first letter if alphabetic
    if s and s[0].isalpha():
        s = s[0].upper() + s[1:]
    if FORCE_PERIOD and not END_PUNCT_RE.search(s):
        s += "."
    return s

class CleanerState:
    def __init__(self):
        self.in_burst = False
        self.last_spoken = None     # most recent non-tag line within current burst
        self.last_emitted = None    # last line we actually wrote (to avoid dupes)

    def commit(self, fout, text: str):
        text = clean_text(text)
        if len(text) < MIN_CHARS:
            return
        text = finalize_text(text)
        if not text:
            return
        if text == self.last_emitted:
            return
        fout.write(text + "\n")
        fout.flush()
        self.last_emitted = text
        # reset current burst
        self.in_burst = False
        self.last_spoken = None
        sys.stderr.write(f"[emit] {text}\n"); sys.stderr.flush()

    def feed(self, line: str, fout):
        s = line.rstrip("\n")
        if not s.strip():
            return

        # tag-only line = burst boundary
        if TAG_LINE_RE.match(s):
            if self.in_burst and self.last_spoken:
                self.commit(fout, self.last_spoken)
            else:
                # even if not in burst, make sure state is clean
                self.in_burst = False
                self.last_spoken = None
            return

        # spoken text
        spoken = clean_text(s)
        if not spoken:
            return

        self.in_burst = True
        self.last_spoken = spoken

        # optional early commit on strong end punctuation
        if COMMIT_ON_PUNCT and END_PUNCT_RE.search(spoken):
            self.commit(fout, spoken)

def process_existing(fin, fout, state: CleanerState):
    """Process what's already in the file once, then leave the stream position at EOF."""
    for raw in fin:
        state.feed(raw, fout)

def tail_file():
    # ensure files exist
    if not os.path.exists(IN_PATH):
        open(IN_PATH, "a", encoding="utf-8").close()

    # truncate output once at start (comment out if you prefer append)
    open(OUT_PATH, "w", encoding="utf-8").close()

    state = CleanerState()

    with open(IN_PATH, "r", encoding="utf-8", errors="ignore") as fin, \
         open(OUT_PATH, "a", encoding="utf-8") as fout:
        # first pass over existing content
        process_existing(fin, fout, state)

        # now follow new content
        sys.stderr.write(f"[watching] {os.path.abspath(IN_PATH)}\n")
        sys.stderr.write(f"[writing ] {os.path.abspath(OUT_PATH)}\n")
        sys.stderr.flush()

        # remember position
        pos = fin.tell()

        while True:
            line = fin.readline()
            if not line:
                # detect file truncation/rotation
                try:
                    size = os.stat(IN_PATH).st_size
                except FileNotFoundError:
                    size = 0
                if size < pos:
                    # file was truncated; reopen and restart from beginning
                    sys.stderr.write("[info] input truncated; reopening\n"); sys.stderr.flush()
                    fin.close()
                    fin = open(IN_PATH, "r", encoding="utf-8", errors="ignore")
                    # optionally reprocess all or just set to end; we’ll set to end
                    fin.seek(0, os.SEEK_END)
                    pos = fin.tell()
                else:
                    time.sleep(0.05)
                continue

            pos = fin.tell()
            state.feed(line, fout)

            # if stream ends without boundary, we do NOT force commit;
            # the next [BLANK_AUDIO] or a punctuated line will commit the burst.

if __name__ == "__main__":
    try:
        tail_file()
    except KeyboardInterrupt:
        sys.stderr.write("\n[exit] ctrl-c\n")
