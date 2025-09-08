"""
Puntos finales de la API de Kick.com
"""
import os
import tempfile
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services.kick_service import kick_service
from app.services import SystemVerificationService
from app.services.video_conversion import VideoConversionService
from app.utils.file_utils import generate_file_stream
from app.core.exceptions import VideoNotFoundError, FFmpegNotAvailableError


router = APIRouter()


@router.get("/channel/{channel_name}/clips")
async def get_channel_clips(channel_name: str, limit: Optional[int] = 20):
    """Obtener clips de un canal específico"""
    try:
        return await kick_service.get_channel_clips(channel_name, limit)
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo clips: {str(e)}")


@router.get("/channel/{channel_name}/videos")
async def get_channel_videos(channel_name: str, limit: Optional[int] = 20):
    """Obtener videos (VODs) de un canal específico"""
    try:
        return await kick_service.get_channel_videos(channel_name, limit)
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo videos: {str(e)}")


@router.get("/clip/{clip_id}")
async def get_clip_by_id(clip_id: str):
    """Obtener información de un clip específico por su ID"""
    try:
        return await kick_service.get_clip_by_id(clip_id)
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo clip: {str(e)}")


@router.get("/clip/{clip_id}/download/{format}")
async def download_clip(clip_id: str, format: str):
    """Descargar un clip en un formato específico (mp4 o mp3)"""
    if format not in ["mp4", "mp3"]:
        raise HTTPException(status_code=400, detail="Formato inválido. Usa 'mp4' o 'mp3'")
    
    try:
        SystemVerificationService.verify_ffmpeg_or_raise()
    except FFmpegNotAvailableError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    try:
        clip_data = await kick_service.get_clip_by_id(clip_id)
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
            temp_path = temp_file.name
        
        # Convertir según el formato
        if format == "mp4":
            success = await VideoConversionService.convert_m3u8_to_mp4(clip_data["download_url"], temp_path)
        else:  # mp3 (audio)
            success = await VideoConversionService.convert_m3u8_to_mp3(clip_data["download_url"], temp_path)
        
        if not success:
            os.unlink(temp_path)
            raise HTTPException(status_code=500, detail=f"Error convirtiendo clip a {format}")
        
        # Configurar cabeceras de descarga
        file_size = os.path.getsize(temp_path)
        filename = f"{clip_data['title'] or 'clip'}_{clip_id}.{format}"
        filename = filename.replace("/", "_").replace("\\", "_")  # Limpiar nombre de archivo
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(file_size)
        }
        
        media_type = "video/mp4" if format == "mp4" else "audio/mpeg"
        
        # Función para eliminar el archivo después de la descarga
        def cleanup():
            try:
                os.unlink(temp_path)
            except:
                pass
        
        return StreamingResponse(
            generate_file_stream(temp_path),
            media_type=media_type,
            headers=headers,
            background=cleanup
        )
    
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error descargando clip en {format.upper()}: {str(e)}")


@router.get("/video/{uuid}/download/{format}")
async def download_video(uuid: str, format: str):
    """Descargar un video en un formato específico (mp4 o mp3)"""
    if format not in ["mp4", "mp3"]:
        raise HTTPException(status_code=400, detail="Formato inválido. Usa 'mp4' o 'mp3'")
    
    try:
        SystemVerificationService.verify_ffmpeg_or_raise()
    except FFmpegNotAvailableError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    try:
        video_data = await kick_service.get_video_by_uuid(uuid)
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
            temp_path = temp_file.name
        
        # Convertir según el formato
        if format == "mp4":
            success = await VideoConversionService.convert_m3u8_to_mp4(video_data["download_url"], temp_path)
        else:  # mp3 (audio)
            success = await VideoConversionService.convert_m3u8_to_mp3(video_data["download_url"], temp_path)
        
        if not success:
            os.unlink(temp_path)
            raise HTTPException(status_code=500, detail=f"Error convirtiendo video a {format}")
        
        # Configurar cabeceras de descarga
        file_size = os.path.getsize(temp_path)
        filename = f"{video_data['title'] or 'video'}_{uuid}.{format}"
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(file_size)
        }
        
        media_type = "video/mp4" if format == "mp4" else "audio/mpeg"
        
        # Función para eliminar el archivo después de la descarga
        def cleanup():
            try:
                os.unlink(temp_path)
            except:
                pass
        
        return StreamingResponse(
            generate_file_stream(temp_path),
            media_type=media_type,
            headers=headers,
            background=cleanup
        )
    
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error descargando video en {format.upper()}: {str(e)}")


@router.get("/video/{video_id}")
async def get_video_by_id(video_id: str):
    """Obtener información de un video específico por su ID"""
    try:
        return await kick_service.get_video_by_id(video_id)
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo video: {str(e)}")
