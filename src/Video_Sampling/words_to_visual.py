import os
import json
import pandas as pd
import subprocess

# ---------------------------
# CONFIG
# ---------------------------
ASLLEX_PATH = "Cleaned ASLLEXR data.csv"
WLASL_PATH = "WLASL_v0.3.json"
OUTPUT_JSON = "gloss_to_video.json"
FILTERED_WLASL_JSON = "filtered_wlasl.json"
SIGN_VIDEO_DIR = "sign_videos"

TOP_N = 400   # how many most frequent signs to keep

# ---------------------------
# STEP 1: Load ASL-LEX and find most frequent signs
# ---------------------------
df = pd.read_csv(ASLLEX_PATH, low_memory=False)
df = df[["EntryID", "ASLFreq"]].dropna(subset=["EntryID"])
df_grouped = df.groupby("EntryID", as_index=False)["ASLFreq"].mean()
df_sorted = df_grouped.sort_values("ASLFreq", ascending=False)
top_glosses = df_sorted["EntryID"].head(TOP_N).tolist()

# ---------------------------
# STEP 2: Load WLASL dataset
# ---------------------------
with open(WLASL_PATH, "r") as f:
    wlasl_data = json.load(f)

# build mapping gloss -> entry (complete JSON object)
wlasl_dict = {entry["gloss"].upper(): entry for entry in wlasl_data}

# ---------------------------
# STEP 3: Match and Download Videos
# ---------------------------
os.makedirs(SIGN_VIDEO_DIR, exist_ok=True)
gloss_to_video = {}
filtered_wlasl = []

for gloss in top_glosses:
    gloss_upper = gloss.upper()
    if gloss_upper not in wlasl_dict:
        continue
    
    entry = wlasl_dict[gloss_upper]
    urls = [inst["url"] for inst in entry["instances"] if "url" in inst]
    if not urls:
        continue

    url = urls[0]  # take first available video
    filename = f"{gloss}.mp4".replace(" ", "_")
    filepath = os.path.join(SIGN_VIDEO_DIR, filename)

    # download video with yt-dlp
    try:
        subprocess.run(
            ["yt-dlp", "-o", filepath, url],
            check=True
        )
        gloss_to_video[gloss] = f"file://{os.path.abspath(filepath)}"
        filtered_wlasl.append(entry)  # add full JSON entry
        print(f"✅ Downloaded {gloss} -> {filepath}")
    except Exception as e:
        print(f"❌ Failed to download {gloss}: {e}")

# ---------------------------
# STEP 4: Save JSON outputs
# ---------------------------
with open(OUTPUT_JSON, "w") as f:
    json.dump(gloss_to_video, f, indent=2)

with open(FILTERED_WLASL_JSON, "w") as f:
    json.dump(filtered_wlasl, f, indent=2)

print(f"\n📂 Saved {len(gloss_to_video)} mappings in {OUTPUT_JSON}")
print(f"📂 Saved {len(filtered_wlasl)} full entries in {FILTERED_WLASL_JSON}")
