#!/usr/bin/env bash
# Live mic → whisper.cpp (CMake build) → append transcript to one file

set -euo pipefail

# always run from this script's directory
cd "$(dirname "$0")"

BIN="../../whisper.cpp/build/bin/whisper-stream"
MODEL="../../whisper.cpp/models/ggml-base.en.bin"
OUT_FILE="transcript.txt"

# ---- knobs ----
THREADS="${THREADS:-4}"
STEP_MS="${STEP_MS:-700}"
WIN_MS="${WIN_MS:-7000}"
KEEP_MS="${KEEP_MS:-300}"
VAD_THOLD="${VAD_THOLD:-0.65}"
NO_TIMESTAMPS="${NO_TIMESTAMPS:-true}"   # 'true' or 'false'
PRINT_SPECIAL="${PRINT_SPECIAL:-false}"  # 'true' or 'false'
DEVICE_INDEX="${DEVICE_INDEX:-}"         # set e.g. DEVICE_INDEX=0 to pick a mic

# sanity checks
[[ -x "$BIN" ]] || { echo "[error] binary not found: $BIN"; echo "Build with: cmake -B build -DWHISPER_SDL2=ON && cmake --build build -j"; exit 1; }
[[ -f "$MODEL" ]] || { echo "[error] model not found: $MODEL"; echo "Download with: bash ../../whisper.cpp/models/download-ggml-model.sh base.en"; exit 1; }

# clear transcript once at start
: > "$OUT_FILE"

echo "[info] writing transcript to: $(pwd)/$OUT_FILE"
echo "[info] using model: $MODEL"
echo "[info] to list input devices: $BIN -l"
echo "[info] press Ctrl+C to stop"
echo

# --- safe device flag handling ---
declare -a DEV_FLAG=()
if [[ -n "$DEVICE_INDEX" ]]; then
  DEV_FLAG=(-di "$DEVICE_INDEX")
fi

# run streamer → append to transcript (also prints live)
"$BIN" \
  ${DEV_FLAG[@]+"${DEV_FLAG[@]}"} \
  -m "$MODEL" \
  -t "$THREADS" \
  --step "$STEP_MS" \
  --length "$WIN_MS" \
  --keep "$KEEP_MS" \
  --vad-thold "$VAD_THOLD" \
  --no-timestamps "$NO_TIMESTAMPS" \
  --print-special "$PRINT_SPECIAL" \
  2>/dev/null | tee -a "$OUT_FILE"
