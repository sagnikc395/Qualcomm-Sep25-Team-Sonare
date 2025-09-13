#!/usr/bin/env python3
# make_sign_queue.py
# Convert clean_transcript.txt → sign_queue.jsonl using lexicons.json
# - greedy phrase-first matching, then word-level fallbacks
# - optional stopword drop at word level
# - inserts _TWEEN gaps
# - global speed factor to scale clip durations

import json, re, sys
from pathlib import Path

LEX_PATH = Path("lexicons.json")
IN_PATH  = Path("clean_transcript.txt")
OUT_PATH = Path("sign_queue.jsonl")

# ---- knobs ----
TWEEN_MS      = 100          # gap between clips
SPEED_FACTOR  = 1.0          # e.g., 2.0 to play 2x faster (durations halved)
DROP_STOPWORDS= True
STOPWORDS     = {"the","a","an","is","am","are","to","of","in","on","for","and","or","but","be","was","were","do","does","did"}

# normalize: keep letters/numbers/spaces; collapse whitespace
WS_RE   = re.compile(r"\s+")
ALNUM_SP= re.compile(r"[^a-z0-9\s']")   # keep apostrophes for contractions

def norm_text(s: str) -> str:
    s = s.lower().strip()
    s = ALNUM_SP.sub(" ", s)
    s = WS_RE.sub(" ", s)
    return s.strip()

def load_lexicons(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    phrases = {k.strip().lower(): v for k,v in data.get("PHRASES", {}).items()}
    words   = {k.strip().lower(): v for k,v in data.get("WORDS", {}).items()}
    fingerspell = data.get("FINGERSPELL", {}).get("unknown")
    return phrases, words, fingerspell

def scale_ms(ms: int) -> int:
    # speed factor >1.0 means faster playback → shorter dur
    if SPEED_FACTOR <= 0:
        return ms
    return max(1, int(round(ms / SPEED_FACTOR)))

def make_clip(entry):
    return {
        "label": entry["label"],
        "type": "clip",
        "asset": entry["asset"],
        "dur_ms": scale_ms(int(entry.get("dur_ms", 800)))
    }

def tween():
    return {"label": "_TWEEN", "type": "meta", "dur_ms": TWEEN_MS}

def greedy_phrase_first(tokens, phrases_map):
    """
    tokens: list[str]
    return: list[dict] clip entries matched by phrases (greedy longest)
    also returns a mask of consumed indices so words pass only on remaining
    """
    n = len(tokens)
    used = [False]*n
    out  = []

    # build a set of candidate phrase lengths to try (e.g., 4..2)
    max_len = min(6, n)  # cap phrase length search for speed
    lens = list(range(max_len, 1, -1))

    i = 0
    while i < n:
        if used[i]:
            i += 1
            continue
        matched = False
        for L in lens:
            j = i + L
            if j > n: continue
            if any(used[i:k] for k in range(i, j)):  # any consumed
                continue
            phrase = " ".join(tokens[i:j])
            if phrase in phrases_map:
                out.append(("clip", phrases_map[phrase], i, j))
                for k in range(i, j):
                    used[k] = True
                i = j
                matched = True
                break
        if not matched:
            i += 1
    return out, used

def words_on_remaining(tokens, used, words_map):
    out = []
    for i, tok in enumerate(tokens):
        if used[i]:
            continue
        if DROP_STOPWORDS and tok in STOPWORDS:
            continue
        if tok in words_map:
            out.append(("clip", words_map[tok], i, i+1))
        else:
            out.append(("unknown", tok, i, i+1))
    return out

def to_queue(matches, fingerspell_entry):
    """
    matches is a list of tuples: ("clip", entry, i, j) or ("unknown", tok, i, j)
    assemble queue with tweens in-between
    """
    queue = []
    gloss = []

    # sort by original order (start index)
    matches = sorted(matches, key=lambda m: m[2])

    for idx, m in enumerate(matches):
        if m[0] == "clip":
            entry = m[1]
            queue.append(make_clip(entry))
            gloss.append(entry["label"])
        else:
            # unknown token → fingerspell (if provided), else skip
            tok = m[1]
            if fingerspell_entry:
                queue.append(make_clip(fingerspell_entry))
                gloss.append(fingerspell_entry["label"] + f"({tok})")
            else:
                # skip silently or append a placeholder
                continue
        # tween except after last
        if idx != len(matches) - 1:
            queue.append(tween())
    return queue, gloss

def process_line(line, phrases_map, words_map, fingerspell_entry):
    original = line.strip()
    if not original:
        return None

    text = norm_text(original)
    if not text:
        return None

    tokens = text.split()

    # phrase first
    phrase_matches, used_mask = greedy_phrase_first(tokens, phrases_map)
    # words next
    word_matches = words_on_remaining(tokens, used_mask, words_map)
    matches = phrase_matches + word_matches

    queue, gloss = to_queue(matches, fingerspell_entry)
    if not queue:
        return None

    return {
        "input": original,
        "gloss": gloss,
        "queue": queue
    }

def main():
    phrases_map, words_map, fingerspell_entry = load_lexicons(LEX_PATH)

    out_lines = 0
    with open(IN_PATH, "r", encoding="utf-8") as fin, \
         open(OUT_PATH, "w", encoding="utf-8") as fout:
        for line in fin:
            obj = process_line(line, phrases_map, words_map, fingerspell_entry)
            if not obj:
                continue
            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            out_lines += 1

    print(f"[done] wrote {out_lines} entries → {OUT_PATH}")

if __name__ == "__main__":
    main()
