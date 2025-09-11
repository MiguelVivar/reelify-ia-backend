"""
Puntos finales de la API de Kick.com
"""
import os
import tempfile
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.services.kick_service import kick_service
from app.services import SystemVerificationService
from app.services.video_conversion import VideoConversionService
from app.utils.file_utils import generate_file_stream
from app.core.exceptions import VideoNotFoundError, FFmpegNotAvailableError


router = APIRouter()

# Cache para evitar descargas simultáneas del mismo video
_download_locks = {}
_download_cache = {}


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
async def download_clip(clip_id: str, format: str, background_tasks: BackgroundTasks):
    """Descargar un clip en un formato específico (mp4 en 360p o mp3 optimizado con progreso)"""
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
        
        print(f"🎬 Iniciando descarga de clip en {format.upper()} {'360p' if format == 'mp4' else 'optimizado'}")
        print(f"🆔 Clip ID: {clip_id}")
        print(f"📺 Título: {clip_data.get('title', 'Sin título')}")
        
        # Convertir según el formato con calidad optimizada y progreso
        if format == "mp4":
            success = await VideoConversionService.convert_m3u8_to_mp4_360p(clip_data["download_url"], temp_path)
        else:  # mp3 (audio)
            success = await VideoConversionService.convert_m3u8_to_mp3_optimized(clip_data["download_url"], temp_path)
        
        if not success:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise HTTPException(status_code=500, detail=f"Error convirtiendo clip a {format}")
        
        # Configurar cabeceras de descarga
        file_size = os.path.getsize(temp_path)
        quality_suffix = "_360p" if format == "mp4" else "_192kbps"
        filename = f"{clip_data['title'] or 'clip'}_{clip_id}{quality_suffix}.{format}"
        filename = filename.replace("/", "_").replace("\\", "_")  # Limpiar nombre de archivo
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(file_size)
        }
        
        media_type = "video/mp4" if format == "mp4" else "audio/mpeg"
        
        print(f"✅ Clip procesado exitosamente: {filename} ({file_size / (1024*1024):.2f} MB)")
        
        # Función para eliminar el archivo después de la descarga
        def cleanup_file():
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    print(f"🧹 Archivo temporal de clip eliminado: {temp_path}")
            except Exception as e:
                print(f"⚠️ Error eliminando archivo temporal de clip: {e}")
        
        # Agregar tarea de limpieza en segundo plano
        background_tasks.add_task(cleanup_file)
        
        return StreamingResponse(
            generate_file_stream(temp_path),
            media_type=media_type,
            headers=headers
        )
    
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error descargando clip en {format.upper()}: {str(e)}")


@router.get("/video/{uuid}/download/{format}")
async def download_video(uuid: str, format: str, background_tasks: BackgroundTasks, force: bool = False):
    """Descargar video en formato MP4 360p o MP3 optimizado con progreso en consola
    
    Args:
        uuid: UUID del video
        format: mp4 (360p) o mp3 (192kbps)
        background_tasks: Tareas en segundo plano para limpieza
        force: Parámetro para compatibilidad
    """
    print(f"🎬 Iniciando descarga directa: {uuid} en formato {format}")
    
    # Crear clave única para esta descarga
    download_key = f"{uuid}_{format}"
    
    # Verificar si ya hay una descarga en progreso
    if download_key in _download_locks:
        print(f"⏳ Descarga ya en progreso para {download_key}, esperando...")
        await _download_locks[download_key]
        if download_key in _download_cache:
            print(f"✅ Reutilizando descarga completada para {download_key}")
            cached_result = _download_cache[download_key]
            return StreamingResponse(
                generate_file_stream(cached_result["temp_path"]),
                media_type=cached_result["media_type"],
                headers=cached_result["headers"]
            )
    
    # Crear lock para esta descarga
    _download_locks[download_key] = asyncio.Event()
    
    if format not in ["mp4", "mp3"]:
        _download_locks[download_key].set()
        del _download_locks[download_key]
        raise HTTPException(status_code=400, detail="Formato inválido. Usa 'mp4' o 'mp3'")
    
    try:
        SystemVerificationService.verify_ffmpeg_or_raise()
    except FFmpegNotAvailableError as e:
        _download_locks[download_key].set()
        del _download_locks[download_key]
        raise HTTPException(status_code=500, detail=str(e))
    
    try:
        print(f"🔍 Obteniendo datos del video con UUID: {uuid}")
        video_data = await kick_service.get_video_by_uuid(uuid)
        
        # Convertir duración de milisegundos a segundos si es necesario
        duration_raw = video_data.get('duration', 0)
        if duration_raw > 10000:  # Si es mayor a 10k, probablemente está en milisegundos
            duration_seconds = duration_raw / 1000
            duration_minutes = duration_seconds / 60
        else:
            duration_seconds = duration_raw
            duration_minutes = duration_seconds / 60
            
        print(f"✅ Datos del video obtenidos: {video_data.get('title', 'Sin título')}")
        print(f"⏱️ Duración: {duration_seconds:.0f}s ({duration_minutes:.1f} min)")
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
            temp_path = temp_file.name
        
        print(f"🎯 Iniciando conversión a {format.upper()} {'360p' if format == 'mp4' else '192kbps'}")
        print(f"📺 Título: {video_data.get('title', 'Sin título')}")
        print(f"🔗 URL de origen: {video_data.get('download_url', '')[:100]}...")
        
        # Convertir según el formato con calidad optimizada y progreso en consola
        if format == "mp4":
            print(f"🎬 Convirtiendo video a MP4 360p con progreso en tiempo real...")
            success = await VideoConversionService.convert_m3u8_to_mp4_360p(video_data["download_url"], temp_path)
        else:  # mp3 (audio)
            print(f"🎵 Convirtiendo audio a MP3 192kbps con progreso en tiempo real...")
            success = await VideoConversionService.convert_m3u8_to_mp3_optimized(video_data["download_url"], temp_path)
        
        if not success:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            _download_locks[download_key].set()
            del _download_locks[download_key]
            raise HTTPException(status_code=500, detail=f"Error convirtiendo video a {format}")
        
        # Configurar cabeceras de descarga
        file_size = os.path.getsize(temp_path)
        quality_suffix = "_360p" if format == "mp4" else "_192kbps"
        filename = f"{video_data['title'] or 'video'}_{uuid}{quality_suffix}.{format}"
        filename = filename.replace("/", "_").replace("\\", "_").replace(":", "_")  # Limpiar nombre de archivo
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(file_size)
        }
        
        media_type = "video/mp4" if format == "mp4" else "audio/mpeg"
        
        print(f"✅ Video procesado exitosamente: {filename} ({file_size / (1024*1024):.2f} MB)")
        
        # Guardar en caché por 10 minutos
        _download_cache[download_key] = {
            "temp_path": temp_path,
            "media_type": media_type,
            "headers": headers,
            "filename": filename
        }
        
        # Función para eliminar el archivo después de la descarga
        def cleanup_file():
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    print(f"🧹 Archivo temporal eliminado: {temp_path}")
                # Limpiar caché
                if download_key in _download_cache:
                    del _download_cache[download_key]
            except Exception as e:
                print(f"⚠️ Error eliminando archivo temporal: {e}")
        
        # Marcar descarga como completada
        _download_locks[download_key].set()
        
        # Agregar tarea de limpieza en segundo plano (después de 10 minutos)
        async def delayed_cleanup():
            await asyncio.sleep(600)  # 10 minutos
            cleanup_file()
            if download_key in _download_locks:
                del _download_locks[download_key]
        
        background_tasks.add_task(delayed_cleanup)
        
        return StreamingResponse(
            generate_file_stream(temp_path),
            media_type=media_type,
            headers=headers
        )
    
    except VideoNotFoundError as e:
        _download_locks[download_key].set()
        del _download_locks[download_key]
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _download_locks[download_key].set()
        del _download_locks[download_key]
        print(f"❌ Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando descarga: {str(e)}")


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
