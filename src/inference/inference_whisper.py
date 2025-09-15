from fastapi import FastAPI, File, UploadFile, Form
import subprocess
import pathlib
import shutil
import tempfile

app = FastAPI()
EXECUTABLE = "faster-whisper-xxl.exe"

@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(..., dscription="Video or audio file to transcribe")
):
    # Save uploaded file to a temporary path
    temp_dir = tempfile.mkdtemp()
    temp_path = pathlib.Path(temp_dir) / file.filename
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Build command
    command = [
        EXECUTABLE,
        str(temp_path),
        "--language", "English",
        "--model", "medium",
        "--output_dir", "C:/Users/QCWorkshop22/Desktop/Qualcomm-Sep25-Team-Sonare/Faster-Whisper-XXL_r245.1_windows/Faster-Whisper-XXL/output-dir",
        "--output_format", "txt",
    ]
    
    try:
        print(command)
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        with open("output-dir/audio.txt", "r") as f:
            transcription = f.read()
        return {
            "status": "success",
            "transcribedText": transcription,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "saved_to": str(temp_path),
            "output_dir": "output",
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "stdout": e.stdout,
            "stderr": e.stderr,
            "returncode": e.returncode
        }

## uvicorn inference_whisper:app --reload --host 127.0.0.1 --port 7777