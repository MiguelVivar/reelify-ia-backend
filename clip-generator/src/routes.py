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
    Genera clips inteligentes analizando todo el video con IA Deepseek.

    - **video_url**: URL pública del video a procesar

    El servicio analiza todo el video usando Deepseek de OpenRouter para identificar
    los momentos más atractivos y virales antes de generar los clips optimizados.
    """
    try:
        logger.info(f"Recibida solicitud de generación de clips con IA para: {request.video_url}")

        # Valida la URL del video
        if not request.video_url or not request.video_url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL de video no válida proporcionada"
            )
        
        # Verificar configuración de API
        analysis_method = "deepseek_ai" if settings.openrouter_api_key else "fallback"
        if not settings.openrouter_api_key:
            logger.warning("API key de OpenRouter no configurada, usando análisis de respaldo")
        
        # Generate clips with AI analysis
        clips = await service.generate_clips(request)
        
        if not clips:
            return ClipGenerationResponse(
                status="warning",
                clips=[],
                message="No se generaron clips del video proporcionado",
                analysis_method=analysis_method
            )

        logger.info(f"Se generaron correctamente {len(clips)} clips usando {analysis_method}")

        return ClipGenerationResponse(
            status="success",
            clips=clips,
            message=f"Se generaron {len(clips)} clips inteligentes usando {analysis_method}",
            analysis_method=analysis_method
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

@router.get("/analysis-info")
async def get_analysis_info():
    """
    Obtiene información sobre el método de análisis disponible
    """
    has_openrouter = bool(settings.openrouter_api_key)
    
    return {
        "analysis_method": "deepseek_ai" if has_openrouter else "fallback",
        "openrouter_configured": has_openrouter,
        "deepseek_model": settings.deepseek_model if has_openrouter else None,
        "analysis_settings": {
            "segment_duration": settings.analysis_segment_duration,
            "max_segments": settings.max_analysis_segments,
            "highlight_threshold": settings.highlight_threshold
        },
        "clip_settings": {
            "max_duration": settings.max_clip_duration,
            "min_duration": settings.min_clip_duration,
            "width": settings.clip_width,
            "height": settings.clip_height
        }
    }
