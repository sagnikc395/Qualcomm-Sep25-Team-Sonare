# Video Keypoint Extraction System

A real-time video keypoint extraction system built with FastAPI and OpenCV.

## Structure

```
./
├── README.md
├── server/
│   ├── __init__.py        # Package initialization
│   ├── justfile          # Just commands for server management
│   └── main.py           # FastAPI server
└── ui/
    └── capture-video.py  # Video capture and processing
```

## Features

- Real-time video keypoint extraction using OpenCV
- FastAPI REST API for consuming keypoint data
- Queue-based architecture for efficient data processing
- Support for multiple keypoint detectors (ORB, SIFT, SURF)
- Live video display with keypoint visualization
- Thread-safe operations
- Comprehensive logging and error handling

## Installation

```bash
# Install dependencies
pip install fastapi uvicorn opencv-python numpy pydantic requests

# For SURF detector (optional)
pip install opencv-contrib-python
```

## Usage

### 1. Start the Server

```bash
cd server
just dev  # or: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start Video Capture

```bash
cd ui
python capture-video.py

# With options:
python capture-video.py --source 0 --detector ORB --server http://localhost:8000
```

## API Endpoints

- `GET /` - API information and available endpoints
- `GET /keypoints` - Get latest keypoint data
- `GET /keypoints/batch/{count}` - Get multiple keypoint data items
- `GET /stats` - Get processing statistics
- `GET /health` - Health check
- `POST /start` - Start processing notification
- `POST /stop` - Stop processing notification
- `GET /queue/clear` - Clear the keypoint queue

## API Documentation

Once the server is running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Just Commands (Server)

```bash
just install    # Install dependencies
just dev       # Run in development mode
just prod      # Run in production mode
just health    # Check server health
just stats     # Get processing stats
just clear     # Clear keypoint queue
just docs      # Show API documentation URLs
```

## Configuration

### Video Capture Options:

- `--source`: Video source (0 for webcam, or video file path)
- `--detector`: Keypoint detector (ORB, SIFT, SURF)
- `--server`: Server URL (default: http://localhost:8000)

### Server Configuration:

- Port: 8000 (configurable in justfile)
- Queue size: 100 items max
- Workers: 4 (production mode)

## Data Format

Keypoint data includes:

- `timestamp`: Frame capture timestamp
- `frame_id`: Sequential frame number
- `keypoints`: Array of keypoint objects with x, y, size, angle, response, octave, class_id
- `num_keypoints`: Total number of keypoints detected
- `frame_shape`: Dimensions of the video frame

## Examples

### Get Latest Keypoints

```bash
curl http://localhost:8000/keypoints
```

### Get Processing Stats

```bash
curl http://localhost:8000/stats
```

### Batch Processing

```bash
curl http://localhost:8000/keypoints/batch/5
```

## Development

The system is designed for easy extension:

- Add new keypoint detectors in `KeypointExtractor`
- Add new API endpoints in `server/main.py`
- Modify video processing pipeline in `ui/capture-video.py`
- Use the justfile for common development tasks

## Performance

- Real-time processing at 30 FPS
- Efficient queue management with overflow handling
- Thread-safe operations
- Minimal latency between capture and API availability
