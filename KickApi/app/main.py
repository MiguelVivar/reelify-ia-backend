"""
Aplicación principal de FastAPI
"""
from fastapi import FastAPI
from app.core.config import Config
from app.api import system, platforms, video_processing, kick_endpoints, integration
from app.utils.cache import cache_manager


def create_application() -> FastAPI:
    """Crear y configurar la aplicación FastAPI"""
    
    # Crear la app FastAPI
    app = FastAPI(
        title=Config.APP_NAME,
        description=Config.APP_DESCRIPTION,
        version=Config.APP_VERSION
    )
    
    # Incluir enrutadores
    app.include_router(system.router, tags=["System"])
    app.include_router(platforms.router, tags=["Platform Specifications"])
    app.include_router(video_processing.router, tags=["Video Processing"])
    app.include_router(kick_endpoints.router, tags=["Kick.com API"])
    app.include_router(integration.router, prefix="/api/integration", tags=["Microservices Integration"])
    
    # Crear directorios necesarios
    Config.ensure_directories()
    
    # Iniciar hilo de limpieza de caché
    cache_manager.start_cleanup_thread()
    
    return app


# Crear instancia de la app
app = create_application()


@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    print("🚀 KickAPI Ultra Advanced iniciando...")
    print(f"📁 Directorio de videos convertidos: {Config.get_converted_videos_path()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de apagado de la aplicación"""
    print("🛑 KickAPI apagándose...")
    cache_manager.stop_cleanup_thread()
