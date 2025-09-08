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
    Genera clips iniciales a partir de un video proporcionado.

    - **video_url**: URL pública del video a procesar

    Devuelve una lista de clips generados con metadatos.
    """
    try:
        logger.info(f"Recibida solicitud de generación de clip para: {request.video_url}")

        # Valida la URL del video
        if not request.video_url or not request.video_url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL de video no válida proporcionada"
            )
        
        # Generate clips
        clips = await service.generate_clips(request)
        
        if not clips:
            return ClipGenerationResponse(
                status="warning",
                clips=[],
                message="No se generaron clips del video proporcionado"
            )

        logger.info(f"Se generaron correctamente {len(clips)} clips")

        return ClipGenerationResponse(
            status="success",
            clips=clips,
            message=f"Se generaron {len(clips)} clips correctamente"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al generar clips: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "clip-generator"}
