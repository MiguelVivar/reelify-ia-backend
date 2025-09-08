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
    Selecciona clips virales de los clips de entrada usando transcripción Whisper y análisis de viralidad

    - **clips**: Lista de URLs de clips para analizar su potencial viral

    Devuelve una lista de clips virales con palabras clave y metadatos
    """
    try:
        logger.info(f"Recibido {len(request.clips)} clips")

        # Validar entrada
        if not request.clips:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere al menos un clip para procesar"
            )
        
        # Validar URLs (pueden ser URLs HTTP o rutas locales)
        for clip in request.clips:
            if not clip.url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Se requiere una URL de clip"
                )
            
            # Permitir tanto URLs HTTP como rutas locales
            if not (clip.url.startswith(('http://', 'https://')) or clip.url.startswith('/clips/')):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"URL de clip no válida: {clip.url}"
                )
        
        # Procesar clips
        viral_clips = await service.select_viral_clips(request)
        
        if not viral_clips:
            return ClipSelectionResponse(
                status="warning",
                viral_clips=[],
                message="No se encontraron clips virales"
            )
        
        logger.info(f"Seleccionados {len(viral_clips)} clips virales")
        
        return ClipSelectionResponse(
            status="success",
            viral_clips=viral_clips,
            message=f"Seleccionados {len(viral_clips)} clips virales de {len(request.clips)} clips de entrada"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al seleccionar clips virales: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/clips/viral/{filename}")
async def get_viral_clip_file(filename: str):
    """
    Servir archivos de clips virales como datos binarios
    
    - **filename**: Nombre del archivo de clip viral a descargar
    """
    try:
        file_path = os.path.join(settings.clips_output_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo de clip viral no encontrado"
            )
        
        return FileResponse(
            path=file_path,
            media_type='video/mp4',
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al servir archivo de clip viral: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al servir archivo: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Endpoint de verificación de estado"""
    return {"status": "saludable", "service": "clip-selector"}
