import os
import uuid
import logging
import aiohttp
import aiofiles
from urllib.parse import urlparse
from config import settings

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.clips_input_dir = getattr(settings, 'clips_input_dir', '/app/clips/raw')
        self.clips_output_dir = getattr(settings, 'clips_output_dir', '/app/clips/viral')
        os.makedirs(self.clips_output_dir, exist_ok=True)
        
    async def download_clip(self, clip_url: str) -> str:
        """
        Descarga un clip desde una URL (HTTP o ruta de archivo local).
        Devuelve la ruta local del archivo.
        """
        try:
            # Verificar si es una ruta de archivo local
            if clip_url.startswith('/clips/'):
                # Ruta de archivo local - construir ruta completa
                filename = os.path.basename(clip_url)
                local_path = os.path.join(self.clips_input_dir, filename)
                
                if os.path.exists(local_path):
                    logger.info(f"Usando archivo local: {local_path}")
                    return local_path
                else:
                    raise Exception(f"Archivo local no encontrado: {local_path}")

            # URL HTTP/HTTPS - descargar el archivo
            file_id = str(uuid.uuid4())
            filename = f"clip_{file_id}.mp4"
            local_path = os.path.join(settings.temp_dir, filename)
            
            # Asegurarse de que exista el directorio temporal
            os.makedirs(settings.temp_dir, exist_ok=True)

            logger.info(f"Descargando: {clip_url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(clip_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(local_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)

                        logger.info(f"Clip descargado: {local_path}")
                        return local_path
                    else:
                        raise Exception(f"HTTP {response.status}: No se pudo descargar el clip desde {clip_url}")
                        
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
    
    async def save_viral_clip(self, clip_path: str, clip_id: str) -> str:
        """
        Guardar el clip viral en almacenamiento persistente y devolver la URL/ruta de acceso.
        """
        try:
            # Crear nombre de archivo para el clip
            clip_filename = f"{clip_id}.mp4"
            output_path = os.path.join(self.clips_output_dir, clip_filename)
            
            # Asegurarse de que exista el directorio de salida
            os.makedirs(self.clips_output_dir, exist_ok=True)
            
            # Copiar el archivo al almacenamiento persistente
            async with aiofiles.open(clip_path, 'rb') as src:
                async with aiofiles.open(output_path, 'wb') as dst:
                    async for chunk in src:
                        await dst.write(chunk)
            
            # Devolver la ruta del archivo (se puede convertir a URL si es necesario)
            clip_url = f"/clips/viral/{clip_filename}"
            logger.info(f"Clip viral guardado en: {output_path}")

            return clip_url
            
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
    
    def cleanup_temp_file(self, file_path: str):
        """Limpiar archivo temporal"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Archivo temporal eliminado: {file_path}")
        except Exception as e:
            logger.warning(f"No se pudo eliminar {file_path}: {e}")
