from fastapi import FastAPI
import uvicorn
from server.routers import video

app = FastAPI()

# include video router
app.include_router(video.router)

if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
