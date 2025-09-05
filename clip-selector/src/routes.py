from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
import logging
import os
from models import ClipSelectionRequest, ClipSelectionResponse, ErrorResponse
from service import ClipSelectorService
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
service = ClipSelectorService()

@router.post("/select-viral-clips", response_model=ClipSelectionResponse)
async def select_viral_clips(request: ClipSelectionRequest):
    """
    Select viral clips from input clips using Whisper transcription and viral analysis
    
    - **clips**: List of clip URLs to analyze for viral potential
    
    Returns a list of viral clips with keywords and metadata
    """
    try:
        logger.info(f"Received clip selection request for {len(request.clips)} clips")
        
        # Validate input
        if not request.clips:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No clips provided for analysis"
            )
        
        # Validate URLs (can be HTTP URLs or local paths)
        for clip in request.clips:
            if not clip.url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Empty clip URL provided"
                )
            
            # Allow both HTTP URLs and local paths
            if not (clip.url.startswith(('http://', 'https://')) or clip.url.startswith('/clips/')):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid clip URL format: {clip.url}"
                )
        
        # Process clips
        viral_clips = await service.select_viral_clips(request)
        
        if not viral_clips:
            return ClipSelectionResponse(
                status="warning",
                viral_clips=[],
                message="No clips met the viral criteria"
            )
        
        logger.info(f"Successfully selected {len(viral_clips)} viral clips")
        
        return ClipSelectionResponse(
            status="success",
            viral_clips=viral_clips,
            message=f"Selected {len(viral_clips)} viral clips from {len(request.clips)} input clips"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting viral clips: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/clips/viral/{filename}")
async def get_viral_clip_file(filename: str):
    """
    Serve viral clip files as binary data
    
    - **filename**: Name of the viral clip file to download
    """
    try:
        file_path = os.path.join(settings.clips_output_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Viral clip file not found"
            )
        
        return FileResponse(
            path=file_path,
            media_type='video/mp4',
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving viral clip file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving file: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "clip-selector"}
