# server/__init__.py
"""
Video Keypoint Extraction Server Package
"""

__version__ = "1.0.0"

# ===========================
# server/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import asyncio
import queue
import threading
import time
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API responses
class KeypointData(BaseModel):
    x: float
    y: float
    size: float
    angle: float
    response: float
    octave: int
    class_id: int

class FrameData(BaseModel):
    timestamp: float
    frame_id: int
    keypoints: List[KeypointData]
    num_keypoints: int
    frame_shape: List[int]

class StatsResponse(BaseModel):
    frame_count: int
    queue_size: int
    running: bool
    timestamp: float

class HealthResponse(BaseModel):
    status: str
    timestamp: float

# Global queue for keypoint data
keypoint_queue = queue.Queue(maxsize=100)
stats = {
    'frame_count': 0,
    'running': False,
    'start_time': time.time()
}

app = FastAPI(
    title="Video Keypoint Extraction API",
    description="Real-time video keypoint extraction and processing API",
    version="1.0.0"
)

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Video Keypoint Extraction API",
        "version": "1.0.0",
        "endpoints": {
            "keypoints": "/keypoints - Get latest keypoint data",
            "stats": "/stats - Get processing statistics", 
            "health": "/health - Health check",
            "start": "/start - Start video processing",
            "stop": "/stop - Stop video processing"
        }
    }

@app.get("/keypoints", response_model=FrameData)
async def get_keypoints():
    """Get the latest keypoint data from the queue"""
    try:
        # Non-blocking get
        data = keypoint_queue.get_nowait()
        return FrameData(**data)
    except queue.Empty:
        raise HTTPException(status_code=404, detail="No keypoint data available")

@app.get("/keypoints/batch/{count}")
async def get_keypoints_batch(count: int = 10):
    """Get multiple keypoint data items from the queue"""
    if count > 50:
        raise HTTPException(status_code=400, detail="Maximum batch size is 50")
    
    batch_data = []
    try:
        for _ in range(count):
            data = keypoint_queue.get_nowait()
            batch_data.append(data)
    except queue.Empty:
        pass
    
    if not batch_data:
        raise HTTPException(status_code=404, detail="No keypoint data available")
    
    return {
        "count": len(batch_data),
        "data": batch_data
    }

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get processing statistics"""
    return StatsResponse(
        frame_count=stats['frame_count'],
        queue_size=keypoint_queue.qsize(),
        running=stats['running'],
        timestamp=time.time()
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=time.time()
    )

@app.post("/start")
async def start_processing():
    """Start video processing (placeholder - actual start handled by UI)"""
    stats['running'] = True
    return {"message": "Video processing started", "timestamp": time.time()}

@app.post("/stop")
async def stop_processing():
    """Stop video processing (placeholder - actual stop handled by UI)"""
    stats['running'] = False
    return {"message": "Video processing stopped", "timestamp": time.time()}

@app.get("/queue/clear")
async def clear_queue():
    """Clear the keypoint queue"""
    cleared_count = 0
    try:
        while True:
            keypoint_queue.get_nowait()
            cleared_count += 1
    except queue.Empty:
        pass
    
    return {
        "message": f"Cleared {cleared_count} items from queue",
        "timestamp": time.time()
    }

def add_keypoint_data(data: Dict[str, Any]):
    """Add keypoint data to the queue (called by UI component)"""
    global stats
    stats['frame_count'] += 1
    
    try:
        keypoint_queue.put_nowait(data)
    except queue.Full:
        # Remove oldest item if queue is full
        try:
            keypoint_queue.get_nowait()
            keypoint_queue.put_nowait(data)
        except queue.Empty:
            pass

# Make the queue accessible to the UI component
def get_queue():
    return keypoint_queue

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")