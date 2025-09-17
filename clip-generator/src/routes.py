from fastapi import APIRouter, HTTPException, status, Response
from fastapi.responses import StreamingResponse, FileResponse
from typing import List
import logging
import os
import io
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
        
        # Generate clips with AI analysis
        clips, analysis_method, video_duration = await service.generate_clips(request)
        
        if not clips:
            return ClipGenerationResponse(
                status="warning",
                clips=[],
                message="No se generaron clips del video proporcionado",
                analysis_method=analysis_method,
                total_video_duration=video_duration
            )

        logger.info(f"Se generaron correctamente {len(clips)} clips usando {analysis_method}")

        return ClipGenerationResponse(
            status="success",
            clips=clips,
            message=f"Se generaron {len(clips)} clips inteligentes usando {analysis_method} (acceso temporal)",
            analysis_method=analysis_method,
            total_video_duration=video_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al generar clips: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/clips/{clip_id}")
async def get_clip(clip_id: str):
    """
    Obtener un clip específico por su ID
    """
    try:
        # Obtener la ruta del clip temporal
        clip_path = service.file_service.get_temp_clip_path(clip_id)
        
        if not clip_path or not os.path.exists(clip_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip no encontrado o ya expirado"
            )
        
        # Servir el archivo de video
        return FileResponse(
            clip_path,
            media_type="video/mp4",
            filename=f"{clip_id}.mp4"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al servir clip {clip_id}: {e}")
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

@router.delete("/clips/cleanup")
async def cleanup_temp_clips():
    """
    Limpiar clips temporales del servidor
    """
    try:
        service.file_service.cleanup_temp_clips()
        return {"message": "Clips temporales limpiados correctamente"}
    except Exception as e:
        logger.error(f"Error al limpiar clips temporales: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al limpiar clips: {str(e)}"
        )


@router.delete("/cache")
async def cleanup_all_cache():
    """
    Endpoint para limpiar toda la cache y archivos temporales del servicio.
    Esto eliminará `settings.temp_dir` completo (videos descargados, clips temporales, etc.).
    """
    try:
        # Limpiar clips temporales en memoria y en disco
        try:
            service.file_service.cleanup_temp_clips()
        except Exception:
            # continuar incluso si falla la limpieza por partes
            pass

        # Limpiar todo el directorio temporal
        report = service.file_service.cleanup_all_cache()

        # Si hay errores reportados, devolver 500 con detalles
        if report.get("errors"):
            logger.error(f"Errores durante limpieza de cache: {report['errors']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Errores eliminando archivos", "report": report}
            )

        # Responder con el informe (incluye removed/skipped)
        return {"message": "Cache limpiada (parcialmente si había recursos ocupados)", "report": report}
    except Exception as e:
        logger.error(f"Error al limpiar toda la cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al limpiar la cache: {str(e)}"
        )
