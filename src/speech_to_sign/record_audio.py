# save as stream_to_file.py
import subprocess, sys
from datetime import datetime

MODEL="models/ggml-base.en.bin"
OUT="transcript.txt"

with open(OUT, "w", encoding="utf-8") as f:
    cmd=["./stream", "-m", MODEL, "-t", "4", "--no-timestamps", "--print-special", "false"]
    proc=subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1)
    try:
        for line in proc.stdout:
            line=line.strip()
            if not line: continue
            stamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{stamp}] {line}\n")
            f.flush()
            print(line)
    except KeyboardInterrupt:
        proc.terminate()
