# app.py
import os
import json
from io import BytesIO
from typing import List, Optional

import numpy as np
import torch
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from pydantic import BaseModel

# Import your existing modules (same as your test script)
from configs import Config
from tgcn_model import GCN_muti_att

# ---------- CONFIG - edit these to your environment ----------
ROOT = "/media/anudisk/github/WLASL"                  # same root as your script
TRAINED_ON = "asl2000"                                # same as before
CHECKPOINT_PATH = os.path.join(ROOT, "code/TGCN/archived", TRAINED_ON, "ckpt.pth")
CONFIG_FILE = os.path.join(ROOT, "code/TGCN/archived", TRAINED_ON, f"{TRAINED_ON}.ini")
LABELS_PATH = os.path.join(ROOT, "data", "labels.json")  # optional: map idx->label
NUM_COPIES = 4
# ------------------------------------------------------------

app = FastAPI(title="TGCN Prediction API")

# Globals (populated at startup)
model = None
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
configs = None
label_map = None


class Prediction(BaseModel):
    class_idx: int
    label: Optional[str] = None
    prob: float


class PredictionResponse(BaseModel):
    top_k: int
    predictions: List[Prediction]


def load_labels(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)  # expected format: {"0": "LABEL_A", "1": "LABEL_B", ...}
    return None


def safe_load_checkpoint(path, map_location):
    ckpt = torch.load(path, map_location=map_location)
    # various checkpoint formats: either state_dict or full checkpoint
    if isinstance(ckpt, dict):
        # common keys: 'state_dict' or the dict itself is the state_dict
        if "state_dict" in ckpt:
            return ckpt["state_dict"]
        elif "model_state_dict" in ckpt:
            return ckpt["model_state_dict"]
        else:
            return ckpt  # assume it's state_dict
    return ckpt


@app.on_event("startup")
def startup_event():
    global model, configs, label_map

    # Load configs
    if not os.path.exists(CONFIG_FILE):
        raise RuntimeError(f"Config file not found at {CONFIG_FILE}")
    configs = Config(CONFIG_FILE)

    # Instantiate model (same constructor as your script)
    input_feature = configs.num_samples * 2
    hidden_size = configs.hidden_size
    drop_p = configs.drop_p
    num_stages = configs.num_stages
    num_class = int(TRAINED_ON[3:])  # retain your convention

    model = GCN_muti_att(input_feature=input_feature,
                         hidden_feature=hidden_size,
                         num_class=num_class,
                         p_dropout=drop_p,
                         num_stage=num_stages).to(device)

    if not os.path.exists(CHECKPOINT_PATH):
        raise RuntimeError(f"Checkpoint not found at {CHECKPOINT_PATH}")

    state_dict = safe_load_checkpoint(CHECKPOINT_PATH, map_location=device)
    try:
        model.load_state_dict(state_dict)
    except Exception as e:
        # try some common wrapping prefixes
        new_state = {}
        for k, v in state_dict.items():
            new_k = k.replace("module.", "")
            new_state[new_k] = v
        model.load_state_dict(new_state)

    model.eval()
    label_map = load_labels(LABELS_PATH)
    print(f"Model loaded on {device}. Labels loaded: {bool(label_map)}")


def preprocess_input_array(arr: np.ndarray, expected_feature_count: int) -> torch.Tensor:
    """
    Accepts a numpy array for one sample and returns a torch tensor shaped (1, feature_count, time)
    Heuristics:
      - If arr.shape == (features, time) => ok
      - If arr.shape == (time, features) => transpose
      - If arr.ndim == 1 and length == features*time => reshape
    """
    if arr.ndim == 1:
        # maybe flattened
        if arr.size == expected_feature_count:
            # single frame? assume time=1
            arr = arr.reshape((expected_feature_count, 1))
        elif arr.size % expected_feature_count == 0:
            time = arr.size // expected_feature_count
            arr = arr.reshape((expected_feature_count, time))
        else:
            raise HTTPException(status_code=400, detail="1D array size incompatible with expected feature count")

    if arr.ndim == 2:
        f0, f1 = arr.shape
        if f0 == expected_feature_count:
            pass  # (features, time) - good
        elif f1 == expected_feature_count:
            arr = arr.T
        else:
            # can't infer; try to assume features are first
            # but if neither matches, raise
            raise HTTPException(status_code=400,
                                detail=f"Array shape {arr.shape} incompatible with expected feature count {expected_feature_count}")
    elif arr.ndim == 3:
        # assume (batch, features, time) -- we will accept first batch only
        arr = arr[0]
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported array ndim={arr.ndim}")

    # final shape (features, time) -> add batch dim
    arr = arr.astype(np.float32)
    tensor = torch.from_numpy(arr).unsqueeze(0)  # (1, features, time)
    return tensor


def model_infer_single(sample_tensor: torch.Tensor, top_k: int = 3):
    """
    Perform the same multi-copy inference as in your test() function.
    sample_tensor: (1, features, time)
    returns top_k indices and probs (cpu numpy)
    """
    global model, device
    X = sample_tensor.to(device)
    num_copies = NUM_COPIES
    stride = X.size(2) // num_copies
    if stride == 0:
        # pad or repeat frames so we have at least num_copies segments
        t = X.size(2)
        needed = num_copies - t
        # tile last frame
        last = X[:, :, -1:].repeat(1, 1, needed)
        X = torch.cat([X, last], dim=2)
        stride = X.size(2) // num_copies

    all_output = []
    with torch.no_grad():
        for i in range(num_copies):
            start = i * stride
            end = (i + 1) * stride
            X_slice = X[:, :, start:end]
            out = model(X_slice)  # shape (1, num_classes)
            all_output.append(out)
        all_output = torch.stack(all_output, dim=1)  # (1, num_copies, num_classes)
        output = torch.mean(all_output, dim=1)      # (1, num_classes)
        probs = torch.softmax(output, dim=1).cpu().numpy()[0]  # (num_classes,)

    # get topk
    best_idx = np.argsort(probs)[-top_k:][::-1]
    best_probs = probs[best_idx]
    return best_idx.tolist(), best_probs.tolist()


@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...), top_k: int = Query(3, ge=1, le=50)):
    """
    Upload a NumPy .npy or .npz file containing a single sample in the same unit your dataset uses:
      - shape (features, time) is expected (features == configs.num_samples * 2)
    Example curl:
      curl -X POST "http://localhost:8000/predict" -F "file=@sample.npy" -F "top_k=5"
    """
    contents = await file.read()
    try:
        arr = np.load(BytesIO(contents), allow_pickle=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load numpy array from uploaded file: {str(e)}")

    expected_features = configs.num_samples * 2
    try:
        sample_tensor = preprocess_input_array(arr, expected_features)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Preprocessing failed: {str(e)}")

    best_idx, best_probs = model_infer_single(sample_tensor, top_k=top_k)
    preds = []
    for idx, prob in zip(best_idx, best_probs):
        label = None
        if label_map:
            # label_map keys may be strings
            label = label_map.get(str(idx), label_map.get(idx, None))
        preds.append(Prediction(class_idx=int(idx), label=label, prob=float(prob)))
    return PredictionResponse(top_k=top_k, predictions=preds)


@app.get("/health")
def health():
    return {"status": "ok", "device": str(device)}
