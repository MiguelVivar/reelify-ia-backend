"""
Endpoints de información del sistema
"""
import os
from fastapi import APIRouter
from app.services import SystemVerificationService


router = APIRouter()


@router.get("/")
async def root():
    """Endpoint raíz"""
    return {"message": "Kick API - Obtén clips y videos de canales de Kick.com"}


@router.get("/health")
async def health_check():
    """Endpoint de verificación de salud para microservicios"""
    try:
        # Comprobaciones básicas de salud
        from app.core.config import Config
        import psutil
        
        # Verificar que los directorios requeridos existan
        Config.ensure_directories()
        
        # Obtener estadísticas del sistema
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "healthy",
            "service": "kick-api",
            "version": Config.APP_VERSION,
            "system": {
                "cpu_usage": f"{cpu_percent}%",
                "memory_usage": f"{memory.percent}%",
                "disk_usage": f"{disk.percent}%"
            },
            "endpoints": [
                "/",
                "/health",
                "/ffmpeg-info",
                "/api/platforms/specifications",
                "/api/video/process",
                "/api/kick/channels",
                "/api/kick/clips"
            ]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "kick-api", 
            "error": str(e)
        }


@router.get("/ffmpeg-info")
async def get_ffmpeg_info():
    """
    🔧 INFORMACIÓN DETALLADA DE FFMPEG - Capacidades y configuración del sistema
    
    Devuelve información detallada sobre las capacidades de FFmpeg instaladas
    """
    info = SystemVerificationService.get_ffmpeg_info()
    recommendations = SystemVerificationService.get_system_recommendations()
    
    # Añadir información del sistema
    info["system_info"] = {
        "os": "Windows" if os.name == 'nt' else "Unix/Linux",
        "cpu_cores": os.cpu_count(),
    }
    
    info["recommendations"] = recommendations
    
    return {
        "status": "ok" if info["ffmpeg_available"] else "warning",
        "system_capabilities": info,
        "features_status": {
            "✅ Vertical 9:16 conversion": info["ffmpeg_available"],
            "✅ Professional blurred background": info.get("capabilities", {}).get("background_blur", False),
            "✅ Automatic AI subtitles": info["whisper_available"],
            "✅ Noise reduction": info.get("capabilities", {}).get("noise_reduction", False),
            "✅ Sharpness enhancement": info.get("capabilities", {}).get("sharpening", False),
            "✅ Color correction": info.get("capabilities", {}).get("color_correction", False),
            "✅ Video stabilization": info.get("capabilities", {}).get("video_stabilization", False),
            "✅ Professional Lanczos scaling": info.get("capabilities", {}).get("professional_scaling", False),
            "✅ Dynamic audio compression": info["ffmpeg_available"],
            "✅ Multi-platform optimization": info["ffmpeg_available"]
        },
        "ready_for_production": info["ffmpeg_available"] and len(recommendations) == 0,
        "setup_recommendations": recommendations
    }
