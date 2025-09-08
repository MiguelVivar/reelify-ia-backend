"""
Video processing endpoints
"""
import time
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.models import OptimizedVideoRequest, ProcessVideoResponse, VideoStatusResponse
from app.services import SystemVerificationService
from app.services.video_conversion import VideoConversionService
from app.services.video_processing import VideoProcessingService
from app.utils.cache import cache_manager
from app.utils import extract_filename_from_url, validate_quality
from app.utils.file_utils import generate_file_stream
from app.core.exceptions import FFmpegNotAvailableError, InvalidQualityError
import os


router = APIRouter()


@router.post("/process-video", response_model=ProcessVideoResponse)
async def process_video_dynamic(request: OptimizedVideoRequest, background_tasks: BackgroundTasks):
    """
    🚀 DYNAMIC ULTRA ADVANCED ENDPOINT - Process video optimized with AI and professional filters
    
    Convert videos to vertical 9:16 format with ULTRA ADVANCED features:
    
    🎬 AVAILABLE QUALITIES:
    - low: 720x1280, bitrate 1.2Mbps (fast, lower quality)
    - medium: 1080x1920, bitrate 2.8Mbps (perfect balance)
    - high: 1080x1920, bitrate 5Mbps (high quality)
    - ultra: 1080x1920, bitrate 8Mbps (professional quality)
    - tiktok: 1080x1920, optimized for TikTok
    - instagram: 1080x1920, optimized for Instagram/Facebook
    - youtube: 1080x1920, optimized for YouTube Shorts
    
    📱 OPTIMIZED PLATFORMS:
    - TikTok (1080x1920, 30fps, H.264, 2.5Mbps)
    - Instagram Reels (1080x1920, 30fps, H.264, 3.2Mbps)
    - Facebook Reels (uses Instagram configuration)
    - YouTube Shorts (1080x1920, 30fps, H.264, 4Mbps)
    
    🎤 AUTOMATIC AI SUBTITLES:
    - Automatic generation with OpenAI Whisper
    - Multiple language support (es, en, fr, de, etc.)
    - Professional styling with outlines and shadows
    
    🎨 ADVANCED VIDEO FILTERS:
    - Intelligent noise reduction (denoise)
    - Adaptive sharpness enhancement (sharpen)
    - Video stabilization (stabilization)
    - Professional color correction (brightness, contrast, saturation, gamma)
    
    � SPLIT FUNCTIONALITY:
    - Split video mode: Divides video into left/right halves
    - Left half positioned on top (1080x960)
    - Right half positioned on bottom (1080x960)
    - Final output: 1080x1920 without black bars
    
    �🔊 AUDIO ENHANCEMENTS:
    - Professional dynamic compression
    - Audio peak limiting
    - 48kHz professional sample rate
    - Quality-optimized audio bitrates
    
    ⚡ TECHNICAL OPTIMIZATIONS:
    - Lanczos scaling algorithm (best quality)
    - Optimized H.264 profiles with advanced x264 parameters
    - Streaming-optimized GOP size and keyframes
    - Social media optimized metadata
    - Real-time progress monitoring
    
    📊 COMPLETE EXAMPLE WITH ALL FUNCTIONS:
    POST /process-video
    {
        "video_url": "https://storage.asumarket.com/agentetiktok/clip_01K3ZE1Y7MH8CBRQAFR206V4AM",
        "quality": "ultra",
        "platform": "tiktok",
        "split": true,
        "add_subtitles": true,
        "subtitle_language": "es",
        "apply_denoise": true,
        "apply_sharpen": true,
        "sharpen_strength": 0.4,
        "apply_color_correction": true,
        "brightness": 0.1,
        "contrast": 1.2,
        "saturation": 1.1,
        "target_fps": 30,
        "audio_enhancement": true
    }
    
    📦 ENHANCED RESPONSE:
    {
        "success": true,
        "video_id": "clip_01K3ZE1Y7MH8CBRQAFR206V4AM",
        "status": "processing",
        "download_url": "/converted-video/clip_01K3ZE1Y7MH8CBRQAFR206V4AM/download",
        "video_url": "/converted-video/clip_01K3ZE1Y7MH8CBRQAFR206V4AM.mp4",
        "status_url": "/converted-video/clip_01K3ZE1Y7MH8CBRQAFR206V4AM/status",
        "processing_options": {
            "subtitles": true,
            "filters_applied": ["denoise", "sharpen", "color_correction"],
            "audio_enhancement": true,
            "estimated_time": "45-90 seconds"
        }
    }
    """
    try:
        # Verificar que FFmpeg esté disponible
        SystemVerificationService.verify_ffmpeg_or_raise()
        
        # Validar parámetros
        if not validate_quality(request.quality):
            raise InvalidQualityError(f"Invalid quality. Use one of: low, medium, high, ultra, tiktok, instagram, youtube")
        
        # Extraer nombre base desde la URL (será el video_id final)
        base_video_id = extract_filename_from_url(request.video_url)
        
        # Crear una clave de caché que incluya todas las opciones de procesamiento para evitar conflictos
        # pero mantener video_id limpio para las URLs
        cache_key_parts = [base_video_id]
        
        if request.split:
            cache_key_parts.append("split")
        
        # Añadir otras variaciones de procesamiento para evitar conflictos en caché
        if request.apply_denoise:
            cache_key_parts.append("denoise")
        if request.apply_sharpen:
            cache_key_parts.append(f"sharpen{int(request.sharpen_strength*10)}")
        if request.apply_color_correction:
            cache_key_parts.append("color")
        
        # Usar el base_video_id limpio para la respuesta de la API
        video_id = base_video_id
        
        # Crear clave de caché para almacenamiento interno (con todas las opciones)
        cache_key = "_".join(cache_key_parts) if len(cache_key_parts) > 1 else base_video_id
        
        # Optimizar calidad según la plataforma
        optimized_quality = VideoConversionService.optimize_for_platform(request.quality, request.platform)
        
        # Obtener opciones de procesamiento
        processing_options = VideoProcessingService.get_processing_options_from_request(request)
        
        print(f"🎬 Iniciando procesamiento ULTRA AVANZADO para: {video_id}")
        print(f"🔗 URL: {request.video_url}")
        print(f"🎯 Calidad: {request.quality} -> {optimized_quality}")
        print(f"📱 Plataforma: {request.platform}")
        print(f"🔑 Clave de caché: {cache_key}")
        if request.split:
            print(f"🔄 Modo 'split': ACTIVADO (mitades izquierda/derecha, 1080x1920)")
        if request.add_subtitles:
            print(f"🎤 Subtítulos automáticos: {request.subtitle_language}")
        
        # Listar filtros que se aplicarán
        filters_list = []
        if request.apply_denoise:
            filters_list.append("denoise")
        if request.apply_sharpen:
            filters_list.append(f"sharpen({request.sharpen_strength})")
        if request.apply_stabilization:
            filters_list.append("stabilization")
        if request.apply_color_correction:
            filters_list.append("color_correction")
        
        if filters_list:
            print(f"🎨 Filtros aplicados: {', '.join(filters_list)}")
        
        # Verificar si ya existe en caché
        if cache_manager.video_cache.exists(cache_key):
            existing_data = cache_manager.video_cache.get(cache_key)
            return ProcessVideoResponse(
                success=True,
                video_id=video_id,  # Usar video_id limpio
                status=existing_data["status"],
                download_url=f"/converted-video/{video_id}/download",
                video_url=f"/converted-video/{video_id}.mp4",
                status_url=f"/converted-video/{video_id}/status",
                message="Video is already being processed or completed"
            )
        
        # Crear entrada en caché con las nuevas opciones
        cache_manager.video_cache.set(cache_key, {
            "status": "processing",
            "video_url": request.video_url,
            "quality": optimized_quality,
            "platform": request.platform,
            "processing_options": processing_options,
            "filters_applied": filters_list,
            "add_subtitles": request.add_subtitles,
            "created_at": time.time(),
            "file_path": None,
            "file_size": None,
            "conversion_time": None,
            "base_name": video_id,  # Guardar video_id limpio
            "cache_key": cache_key  # Guardar clave de caché para limpieza
        })
        
        # Procesar video en segundo plano con opciones avanzadas
        background_tasks.add_task(
            VideoProcessingService.process_video_background_advanced, 
            cache_key,  # Usar cache_key para procesamiento interno
            video_id,   # Pasar video_id limpio por separado
            request.video_url, 
            optimized_quality, 
            processing_options
        )
        
        # Estimar tiempo según opciones
        estimated_time = "15-30 seconds"
        if request.add_subtitles:
            estimated_time = "45-90 seconds"
        elif len(filters_list) > 2:
            estimated_time = "30-60 seconds"
        
        return ProcessVideoResponse(
            success=True,
            video_id=video_id,
            status="processing",
            download_url=f"/converted-video/{video_id}/download",
            video_url=f"/converted-video/{video_id}.mp4", 
            status_url=f"/converted-video/{video_id}/status",
            estimated_time=estimated_time,
            quality=optimized_quality,
            platform=request.platform,
            processing_options={
                "subtitles": request.add_subtitles,
                "subtitle_language": request.subtitle_language if request.add_subtitles else None,
                "filters_applied": filters_list,
                "audio_enhancement": request.audio_enhancement,
                "target_fps": request.target_fps,
                "custom_bitrate": request.custom_bitrate
            },
            optimizations={
                "format": "MP4 (H.264 Professional)",
                "resolution": "1080x1920" if "1080" in optimized_quality or optimized_quality in ["high", "ultra", "tiktok", "instagram", "youtube"] else "720x1280",
                "fps": str(request.target_fps),
                "audio": f"AAC {processing_options.get('audio_bitrate', '128k')} 48kHz",
                "advanced_features": [
                    "Professional blurred background",
                    "Professional Lanczos scaling",
                    "Optimized x264 parameters",
                    "Dynamic audio compression" if request.audio_enhancement else "Standard audio",
                ] + ([f"Automatic subtitles ({request.subtitle_language})"] if request.add_subtitles else []) + filters_list,
                "compatible_platforms": ["TikTok", "Instagram Reels", "Facebook Reels", "YouTube Shorts", "Twitter", "LinkedIn"]
            },
            message=f"Video ULTRA OPTIMIZED for {request.platform} with {len(filters_list)} advanced filters"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting advanced processing: {str(e)}")


@router.get("/converted-video/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(video_id: str):
    """
    Get the status of a video being processed
    
    Possible states:
    - processing: Video in processing queue
    - downloading: Downloading original video
    - converting: Converting to vertical format
    - completed: Ready for download
    - error: Error in processing
    """
    # Buscar la entrada en caché para este video_id (podría estar almacenada con otra cache_key)
    video_data = None
    cache_key_found = None
    
    # Intentar búsqueda directa primero
    if cache_manager.video_cache.exists(video_id):
        video_data = cache_manager.video_cache.get(video_id)
        cache_key_found = video_id
    else:
        # Buscar entradas en caché con base_name coincidente
        for cache_key in cache_manager.video_cache.keys():
            data = cache_manager.video_cache.get(cache_key)
            if data and data.get("base_name") == video_id:
                video_data = data
                cache_key_found = cache_key
                break
    
    if not video_data:
        raise HTTPException(status_code=404, detail="Video ID not found")
    
    # Preparar respuesta según el estado
    response = VideoStatusResponse(
        video_id=video_id,
        status=video_data["status"],
        quality=video_data.get("quality"),
        created_at=video_data.get("created_at")
    )
    
    if video_data["status"] == "completed":
        response.download_url = f"/converted-video/{video_id}/download"
        response.video_url = f"/converted-video/{video_id}.mp4"
        response.file_size = video_data.get("file_size")
        response.conversion_time = video_data.get("conversion_time")
        response.ready = True
    elif video_data["status"] == "error":
        response.error = video_data.get("error", "Unknown error")
        response.ready = False
    else:
        # processing, downloading, converting
        response.ready = False
        response.message = {
            "processing": "Video in processing queue",
            "downloading": "Downloading original video...",
            "converting": "Converting to vertical format..."
        }.get(video_data["status"], "Processing...")
    
    return response


@router.get("/converted-video/{video_id}/download")
async def download_converted_video(video_id: str):
    """
    Download the converted video using its ID
    
    Example: GET /converted-video/abc123def456/download
    """
    # Buscar la entrada en caché para este video_id
    video_data = None
    
    # Intentar búsqueda directa primero
    if cache_manager.video_cache.exists(video_id):
        video_data = cache_manager.video_cache.get(video_id)
    else:
        # Buscar entradas en caché con base_name coincidente
        for cache_key in cache_manager.video_cache.keys():
            data = cache_manager.video_cache.get(cache_key)
            if data and data.get("base_name") == video_id:
                video_data = data
                break
    
    if not video_data:
        raise HTTPException(status_code=404, detail="Video ID not found")
    
    if video_data["status"] != "completed":
        if video_data["status"] == "error":
            error_msg = video_data.get("error", "Error in processing")
            raise HTTPException(status_code=400, detail=f"Video error: {error_msg}")
        else:
            raise HTTPException(
                status_code=202, 
                detail=f"Video still processing. Current status: {video_data['status']}"
            )
    
    file_path = video_data.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Configurar encabezados para la descarga
    file_size = os.path.getsize(file_path)
    filename = f"vertical_video_{video_id}.mp4"
    
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4"
    }
    
    print(f"📤 Descargando video convertido: {video_id}")
    
    return StreamingResponse(
        generate_file_stream(file_path),
        media_type="video/mp4",
        headers=headers
    )


@router.get("/converted-video/{video_id}.mp4")
async def stream_converted_video(video_id: str):
    """
    🎬 DIRECT ENDPOINT WITH .mp4 URL - Serves video directly as binary file
    
    URL ending in .mp4 for direct browser viewing
    Example: GET /converted-video/abc123def456.mp4
    
    This URL can be used directly in:
    - <video src="http://localhost:8000/converted-video/abc123def456.mp4">
    - Web browser for direct playback
    - Mobile apps expecting video URLs
    - Players requiring .mp4 extension
    """
    # Buscar la entrada en caché para este video_id
    video_data = None
    
    # Intentar búsqueda directa primero
    if cache_manager.video_cache.exists(video_id):
        video_data = cache_manager.video_cache.get(video_id)
    else:
        # Buscar entradas en caché con base_name coincidente
        for cache_key in cache_manager.video_cache.keys():
            data = cache_manager.video_cache.get(cache_key)
            if data and data.get("base_name") == video_id:
                video_data = data
                break
    
    if not video_data:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Solo servir video si está completado
    if video_data["status"] != "completed":
        if video_data["status"] == "error":
            raise HTTPException(status_code=404, detail="Video not available")
        else:
            # Si aún está en procesamiento, devolver 404 en lugar de mensaje de estado
            raise HTTPException(status_code=404, detail="Video not available")
    
    file_path = video_data.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video not available")
    
    # Encabezados para streaming de video (sin forzar descarga)
    file_size = os.path.getsize(file_path)
    
    headers = {
        "Content-Length": str(file_size),
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600"  # Cache por 1 hora
    }
    
    print(f"🎬 Sirviendo video como stream: {video_id}.mp4")
    
    return StreamingResponse(
        generate_file_stream(file_path),
        media_type="video/mp4",
        headers=headers
    )
