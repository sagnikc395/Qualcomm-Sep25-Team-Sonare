#!/usr/bin/env python3
import json, os, re, sys, time
import spacy

INFILE  = "/Users/armaansandhu/Desktop/qualcomm-sonare/Qualcomm-Sep25-Team-Sonare/src/speech_to_sign/clean_transcript.txt"
OUTFILE = "/Users/armaansandhu/Desktop/qualcomm-sonare/Qualcomm-Sep25-Team-Sonare/src/speech_to_sign/sign_queue.jsonl"
LEXPATH = "/Users/armaansandhu/Desktop/qualcomm-sonare/Qualcomm-Sep25-Team-Sonare/src/speech_to_sign/lexicons.json"

DEBOUNCE_REPEATS = 1   # emit on first sight
TWEEN_MS = 100
SENTENCE_PAUSE_MS = 250
DROP_POS = {"AUX", "DET", "PART", "ADP", "INTJ"}
KEEP_POS = {"NOUN","VERB","ADJ","ADV","PRON","PROPN","NUM"}
DROP_WORDS = {"uh","um","okay","ok"}

# ---- load ----
try:
    with open(LEXPATH, "r", encoding="utf-8") as f:
        LEX = json.load(f)
except Exception as e:
    sys.exit(f"[error] cannot read lexicon: {LEXPATH}: {e}")

try:
    nlp = spacy.load("en_core_web_sm", exclude=["ner"])
except Exception:
    nlp = spacy.load("en_core_web_sm")

FING = LEX.get("_FINGERSPELL")  # {"type":"fingerspell","asset":"...","per_char_ms":180}

def sp_gloss(text: str):
    t = text.strip()
    if not t or t == "[BLANK_AUDIO]":
        return []

    # simple string fixups
    t = re.sub(r"\bcoming\s+through\b", "come", t, flags=re.I)

    doc = nlp(t)
    raw = []
    i = 0
    while i < len(doc):
        tok = doc[i]
        low = tok.text.lower()
        if tok.is_punct or low in DROP_WORDS:
            i += 1; continue

        # "going to VERB" → VERB (or "gonna VERB")
        if tok.lemma_.lower() == "go":
            nxt = doc[i+1] if i+1 < len(doc) else None
            nxt2 = doc[i+2] if i+2 < len(doc) else None
            if (nxt and (nxt.lower_ == "to" or tok.lower_ == "gonna")) and (nxt2 and nxt2.pos_ == "VERB"):
                raw.append(nxt2.lemma_.upper()); i += 3; continue
            if nxt and nxt.lower_ == "to":
                i += 2; continue

        if tok.pos_ in KEEP_POS and tok.pos_ not in DROP_POS:
            if tok.pos_ == "PROPN":
                raw.append(tok.text.upper())
            elif tok.pos_ == "PRON":
                raw.append(tok.text.upper())
            else:
                raw.append(tok.lemma_.upper())
        i += 1

    # WHAT + UP → WHAT-UP if present
    if len(raw) == 2 and raw[0] == "WHAT" and raw[1] == "UP" and "WHAT-UP" in LEX:
        raw = ["WHAT-UP"]

    # PIPELINE → PROCESS
    raw = ["PROCESS" if g == "PIPELINE" else g for g in raw]

    # dedupe adjacents
    out = []
    for g in raw:
        if not out or out[-1] != g:
            out.append(g)
    return out

def to_queue(gloss_tokens):
    q = []
    for g in gloss_tokens:
        entry = LEX.get(g)
        if entry is None:
            if not FING:
                continue
            label = f"SPELL({g})"
            dur = len(re.sub(r"[^A-Z]", "", g)) * int(FING.get("per_char_ms", 180))
            q.append({"label": label, "type": FING["type"], "asset": FING["asset"], "dur_ms": int(dur)})
        else:
            q.append({"label": g, "type": entry["type"], "asset": entry["asset"], "dur_ms": int(entry.get("dur_ms", 600))})
        q.append({"label": "_TWEEN", "type": "meta", "dur_ms": TWEEN_MS})
    if q: q.pop()
    return q

def emit(outf, line):
    gloss = sp_gloss(line)
    if not gloss:
        sys.stderr.write("[skip] no gloss for line\n"); sys.stderr.flush()
        return
    obj = {
        "input": line.strip(),
        "gloss": gloss,
        "queue": to_queue(gloss),
        "sentence_pause_ms": SENTENCE_PAUSE_MS
    }
    outf.write(json.dumps(obj, ensure_ascii=False) + "\n")
    outf.flush()
    sys.stderr.write(f"[emit] {obj['gloss']}\n"); sys.stderr.flush()

def tail_file(path):
    os.makedirs(os.path.dirname(OUTFILE), exist_ok=True)
    if not os.path.exists(path):
        open(path, "a", encoding="utf-8").close()

    with open(path, "r", encoding="utf-8", errors="ignore") as f, open(OUTFILE, "a", encoding="utf-8") as outf:
        f.seek(0, os.SEEK_END)
        last_seen = ""
        last_emitted = ""
        repeats = 0
        threshold = max(DEBOUNCE_REPEATS, 1)

        sys.stderr.write(f"[watching] {path}\n")
        sys.stderr.write(f"[writing ] {OUTFILE}\n")
        sys.stderr.flush()

        while True:
            line = f.readline()
            if not line:
                time.sleep(0.05)
                continue
            s = line.strip()
            if not s or s == "[BLANK_AUDIO]":
                continue

            sys.stderr.write(f"[line] {s}\n"); sys.stderr.flush()

            if s == last_seen:
                repeats += 1
            else:
                last_seen = s
                repeats = 1

            if repeats >= threshold and s != last_emitted:
                emit(outf, s)
                last_emitted = s

if __name__ == "__main__":
    tail_file(INFILE)
