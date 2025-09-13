import cv2
import mediapipe as mp
import numpy as np
import torch

# -------------------------
# 1. Import your model
# -------------------------
from tgcn_model import GCN_muti_att

num_classes = 2000   # matches WLASL
num_points  = 17     # MediaPipe joints
num_person  = 1

model = GCN_muti_att(num_class=num_classes, num_point=num_points, num_person=num_person)
model.load_state_dict(torch.load("your_trained_model.pth", map_location="cpu"))
model.eval()

# -------------------------
# 2. Pose extractor
# -------------------------
mp_pose = mp.solutions.pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    enable_segmentation=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

# -------------------------
# 3. Webcam + buffer
# -------------------------
cap = cv2.VideoCapture(0)
frames_buffer = []
max_frames = 30  # clip length (should match what model was trained on)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)

    # Pose estimation
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = mp_pose.process(rgb)

    # Extract first 17 joints
    joints = np.zeros((17, 2))
    if results.pose_landmarks:
        for i, lm in enumerate(results.pose_landmarks.landmark[:17]):
            joints[i] = [lm.x, lm.y]
            h, w, _ = frame.shape
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 3, (0, 255, 0), -1)

    frames_buffer.append(joints)

    # If we collected enough frames → run model
    if len(frames_buffer) == max_frames:
        skeleton = np.array(frames_buffer)  # (T,V,2)
        skeleton = np.transpose(skeleton, (2,0,1))  # (C,T,V)
        skeleton = skeleton[..., np.newaxis]        # (C,T,V,M)
        skeleton = skeleton[np.newaxis, ...]        # (N,C,T,V,M)

        inp = torch.tensor(skeleton, dtype=torch.float32)
        with torch.no_grad():
            out = model(inp)
            pred = torch.argmax(out, dim=1).item()

        print(f"Predicted class ID: {pred}")

        frames_buffer = []  # reset

    cv2.imshow("Live Pose", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        break

cap.release()
cv2.destroyAllWindows()
