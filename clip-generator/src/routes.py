from fastapi import APIRouter, HTTPException, status
from typing import List
import logging
import os
from models import VideoRequest, ClipGenerationResponse, ErrorResponse
from service import ClipGeneratorService
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
service = ClipGeneratorService()

@router.post("/generate-initial-clips", response_model=ClipGenerationResponse)
async def generate_initial_clips(request: VideoRequest):
    """
    Generate initial clips from a video using auto-highlighter
    
    - **video_url**: Public URL of the video to process
    
    Returns a list of generated clips with metadata
    """
    try:
        logger.info(f"Received clip generation request for: {request.video_url}")
        
        # Validate video URL
        if not request.video_url or not request.video_url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid video URL provided"
            )
        
        # Generate clips
        clips = await service.generate_clips(request)
        
        if not clips:
            return ClipGenerationResponse(
                status="warning",
                clips=[],
                message="No clips could be generated from the video"
            )
        
        logger.info(f"Successfully generated {len(clips)} clips")
        
        return ClipGenerationResponse(
            status="success",
            clips=clips,
            message=f"Generated {len(clips)} clips successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating clips: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "clip-generator"}
