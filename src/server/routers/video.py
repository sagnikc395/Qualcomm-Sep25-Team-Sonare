from fastapi import APIRouter, Request
from queue import Queue
import uuid

router = APIRouter()

# In-memory frame queue
frame_queue = Queue()


@router.post("/get_video")
async def get_video(request: Request):
    """
    Receives a JPEG frame from the frontend camera and pushes it into a queue.
    """
    frame_bytes = await request.body()
    frame_id = str(uuid.uuid4())

    frame_queue.put({
        "id": frame_id,
        "bytes": frame_bytes
    })

    return {"status": "success", "frame_id": frame_id, "queue_size": frame_queue.qsize()}


@router.get("/next_frame")
def next_frame():
    """
    Retrieves the next frame (for debugging/processing).
    """
    if frame_queue.empty():
        return {"status": "empty"}
    
    frame = frame_queue.get()
    return {
        "status": "success",
        "frame_id": frame["id"],
        "frame_size": len(frame["bytes"])
    }
