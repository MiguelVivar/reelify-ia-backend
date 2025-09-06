from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import uvicorn
import os
from config import settings
from routes import router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Clip Generator Service",
    description="Microservice for generating video clips using auto-highlighter",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")

# Mount static files for serving clips
if os.path.exists(settings.clips_output_dir):
    app.mount("/clips/raw", StaticFiles(directory=settings.clips_output_dir), name="clips")

@app.get("/")
async def root():
    return {"message": "Clip Generator Service", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
