#!/usr/bin/env python3
import json
from typing import List, Dict, Any

from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
import uvicorn
import os, subprocess, uuid

import sys 



# ---------------- reuse from your code ----------------

CUSTOM_MAP = {
    "i'm": "I", "im": "I", "i": "I", "me": "I", "my": "MY", "mine": "MY",
    "you": "YOU", "your": "YOUR", "yours": "YOUR", "he": "HE", "she": "SHE",
    "it": "IT", "we": "WE", "they": "THEY", "am": "BE", "is": "BE",
    "are": "BE", "was": "BE", "were": "BE", "hello": "HELLO", "hi": "HI",
    "how": "HOW", "good": "GOOD", "morning": "MORNING", "afternoon": "AFTERNOON",
    "evening": "EVENING", "do": "DO", "doing": "DO", "today": "TODAY",
    "what": "WHAT", "why": "WHY", "where": "WHERE", "when": "WHEN",
    "which": "WHICH", "please": "PLEASE", "thanks": "THANK-YOU", "thank": "THANK-YOU",
    "yes": "YES", "no": "NO"
}

DROP = {"THE","A","AN","OF","TO","IN","ON","AT","FOR","AND","OR","BUT","WITH","BE"}

def normalize_token(tok: str) -> str:
    return tok.lower().replace("’", "'").replace("`", "'")

def basic_lemma(tok: str) -> str:
    if tok.endswith("'s"):
        tok = tok[:-2]
    for suf in ("ing", "ed", "es", "s"):
        if tok.endswith(suf) and len(tok) > len(suf) + 1:
            return tok[: -len(suf)]
    return tok

def sent_to_gloss_basic(text: str) -> List[str]:
    import re
    WORD_RE = re.compile(r"[A-Za-z0-9']+")
    toks = [normalize_token(t) for t in WORD_RE.findall(text)]
    glosses: List[str] = []
    for t in toks:
        if t in CUSTOM_MAP:
            glosses.append(CUSTOM_MAP[t])
        else:
            glosses.append(basic_lemma(t).upper())
    glosses = [g for g in glosses if g not in DROP]
    dedup: List[str] = []
    for g in glosses:
        if not dedup or dedup[-1] != g:
            dedup.append(g)
    return dedup

def map_gloss_to_queue(gloss: List[str], lex: Dict[str, Dict[str, Any]], tween_ms: int = 100, rate: float = 1.0) -> List[Dict[str, Any]]:
    # super simplified — just fake assets
    queue: List[Dict[str, Any]] = []
    for i, g in enumerate(gloss):
        key = g.lower()  # your lexicons.json keys look lowercase in your example
        entry = lex.get(key)
        if not entry:
            # try direct uppercase key or stripped variants
            entry = lex.get(g) or lex.get(g.lower())
        if entry:
            dur = int(round(entry.get("dur_ms", 1000) / max(rate, 0.01)))
            queue.append({
                "label": entry.get("label", g),
                "type": "clip",
                "asset": entry.get("asset"),
                "dur_ms": dur
            })
            if tween_ms and i < len(gloss) - 1:
                queue.append({"label": "_TWEEN", "type": "meta", "dur_ms": tween_ms})
        # silently skip OOV tokens
    return queue

def load_lexicons(path: str) -> Dict[str, Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------- FastAPI app ----------------

app = FastAPI()
from fastapi.staticfiles import StaticFiles
app.mount("/generated", StaticFiles(directory="generated"), name="generated")

@app.post("/inference")
def inference(
    text: str = Body(..., embed=True),
    tween_ms: int = 100,
    sentence_pause_ms: int = 250,
    rate: float = 1.0
):
    
    gloss = sent_to_gloss_basic(text)
    print("the generated gloss is", gloss)
    lex = load_lexicons("lexicons.json")
    queue = map_gloss_to_queue(gloss, lex, tween_ms=tween_ms, rate=rate)
    print("the generated queue is", queue)
# Filter out only clip assets
    clip_paths = [q["asset"] for q in queue if q["type"] == "clip"]
    # ## add /videos before final filename for each clip_path
    # clip_paths = [u.split("\\")[0] + "/videos/" + u.split("\\")[-1] for u in clip_paths]
    # clip_paths = [u for u in clip_paths if os.path.exists(u)]
    # Create file list for ffmpeg concat
    os.makedirs("generated", exist_ok=True)
    uuid_str = str(uuid.uuid4())
    list_file = f"generated/{uuid_str}.txt"
    with open(list_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    # Output stitched file
    output_file = f"generated/{uuid_str}.mp4"
    ffmpeg_exe = "C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe"

    cmd = [
        ffmpeg_exe, "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", output_file
    ]
    #subprocess.run(" ".join(cmd),shell=True, check=True, executable="/bin/bash")
    print(" ".join(cmd))
    subprocess.run(" ".join(cmd),shell=True, check=True)

    obj = {
        "input": text,
        "gloss": gloss,
        "queue": queue,
        "sentence_pause_ms": sentence_pause_ms,
        "stitched_video": output_file
    }

    return JSONResponse(obj)

if __name__ == "__main__":
    uvicorn.run("inference_basic:app", host="0.0.0.0", port=8000, reload=True)
