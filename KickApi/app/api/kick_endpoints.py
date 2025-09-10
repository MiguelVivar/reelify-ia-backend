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
import httpx


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
async def download_video(uuid: str, format: str, force: bool = False):
    """Descargar video usando el microservicio video-downloader con Puppeteer
    
    Args:
        uuid: UUID del video
        format: mp4 o mp3  
        force: Parámetro para compatibilidad
    """
    print(f"🎬 Iniciando descarga automática con Puppeteer: {uuid} en formato {format}")
    
    if format not in ["mp4", "mp3"]:
        raise HTTPException(status_code=400, detail="Formato inválido. Usa 'mp4' o 'mp3'")
    
    try:
        print(f"🔍 Obteniendo datos del video con UUID: {uuid}")
        video_data = await kick_service.get_video_by_uuid(uuid)
        print(f"✅ Datos del video obtenidos: {video_data.get('title', 'Sin título')}")
        
        # Limpiar URL del video
        download_url = video_data["download_url"]
        if download_url:
            cleaned_url = download_url.encode('ascii', errors='ignore').decode('ascii')
            for char in ['\u2060', '\u200B', '\u200C', '\u200D', '\uFEFF', '\u00A0', '\ufffc']:
                cleaned_url = cleaned_url.replace(char, '')
            cleaned_url = ''.join(c for c in cleaned_url if ord(c) >= 32 and ord(c) <= 126)
            cleaned_url = cleaned_url.strip()
            video_data["download_url"] = cleaned_url
        
        # Llamar al microservicio video-downloader
        print(f"🤖 Enviando solicitud al microservicio video-downloader...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post("http://video-downloader:8002/download", json={
                "videoUrl": video_data["download_url"],
                "format": format,
                "title": video_data.get("title", "video")
            })
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Descarga iniciada en microservicio: {result['downloadId']}")
                
                return {
                    "success": True,
                    "message": "Descarga automática iniciada con Puppeteer",
                    "video_info": {
                        "id": uuid,
                        "title": video_data.get('title', 'Sin título'),
                        "duration": video_data.get('duration', 0),
                        "format_requested": format
                    },
                    "download_info": {
                        "download_id": result["downloadId"],
                        "status_url": f"http://localhost:8002{result['statusUrl']}",
                        "download_url": f"http://localhost:8002{result['downloadUrl']}",
                        "progress_check": f"/video/download/status/{result['downloadId']}"
                    },
                    "instructions": {
                        "step_1": "La descarga se está procesando automáticamente",
                        "step_2": "Usa el status_url para verificar el progreso",
                        "step_3": "Cuando esté completa, usa download_url para obtener el archivo"
                    }
                }
            else:
                print(f"❌ Error del microservicio: {response.status_code}")
                error_detail = response.text if response.text else "Error desconocido del microservicio"
                raise HTTPException(status_code=500, detail=f"Error del microservicio de descarga: {error_detail}")
                
    except httpx.TimeoutException:
        print(f"⏰ Timeout conectando con video-downloader")
        raise HTTPException(status_code=503, detail="Microservicio de descarga no disponible (timeout)")
    except httpx.ConnectError:
        print(f"🔌 Error de conexión con video-downloader")
        raise HTTPException(status_code=503, detail="Microservicio de descarga no disponible (conexión)")
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando descarga: {str(e)}")


@router.get("/video/download/status/{download_id}")
async def get_download_status(download_id: str):
    """Verificar el estado de una descarga en el microservicio video-downloader"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://video-downloader:8002/status/{download_id}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="ID de descarga no encontrado")
            else:
                raise HTTPException(status_code=500, detail="Error verificando estado de descarga")
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Microservicio de descarga no disponible (timeout)")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Microservicio de descarga no disponible (conexión)")


@router.get("/video/download/file/{download_id}")
async def get_download_file(download_id: str):
    """Obtener el archivo descargado del microservicio video-downloader"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"http://video-downloader:8002/file/{download_id}")
            
            if response.status_code == 200:
                # Reenviar el archivo desde el microservicio
                return StreamingResponse(
                    content=response.iter_bytes(),
                    media_type=response.headers.get("content-type", "application/octet-stream"),
                    headers={
                        "Content-Disposition": response.headers.get("content-disposition", "attachment"),
                        "Content-Length": response.headers.get("content-length", "")
                    }
                )
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="Archivo no encontrado")
            elif response.status_code == 202:
                result = response.json()
                raise HTTPException(status_code=202, detail=result)
            else:
                raise HTTPException(status_code=500, detail="Error obteniendo archivo")
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Microservicio de descarga no disponible (timeout)")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Microservicio de descarga no disponible (conexión)")


@router.get("/video/{uuid}/direct-link")
async def get_video_direct_link(uuid: str):
    """Obtener el link directo del video sin procesamiento (para videos largos)"""
    print(f"🔗 Obteniendo link directo para video: {uuid}")
    
    try:
        video_data = await kick_service.get_video_by_uuid(uuid)
        
        # Limpiar URL
        download_url = video_data["download_url"]
        if download_url:
            cleaned_url = download_url.encode('ascii', errors='ignore').decode('ascii')
            for char in ['\u2060', '\u200B', '\u200C', '\u200D', '\uFEFF', '\u00A0', '\ufffc']:
                cleaned_url = cleaned_url.replace(char, '')
            cleaned_url = ''.join(c for c in cleaned_url if ord(c) >= 32 and ord(c) <= 126)
            cleaned_url = cleaned_url.strip()
        
        return {
            "video_id": uuid,
            "title": video_data.get('title', 'Sin título'),
            "duration": video_data.get('duration', 0),
            "duration_minutes": round(video_data.get('duration', 0) / 60, 1),
            "direct_download_url": cleaned_url,
            "file_format": "m3u8",
            "note": "Este es el link directo del stream. Para videos largos, usa un downloader que soporte M3U8 como yt-dlp o similar."
        }
        
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo link directo: {str(e)}")


@router.get("/video/{video_id}")
async def get_video_by_id(video_id: str):
    """Obtener información de un video específico por su ID"""
    try:
        return await kick_service.get_video_by_id(video_id)
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo video: {str(e)}")
