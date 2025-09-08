import os
import uuid
import logging
import aiohttp
import aiofiles
from urllib.parse import urlparse
from config import settings

logger = logging.getLogger(__name__)

class FileDownloadService:
    def __init__(self):
        self.clips_output_dir = getattr(settings, 'clips_output_dir', '/app/clips/raw')
        os.makedirs(self.clips_output_dir, exist_ok=True)
        
    async def download_video(self, video_url: str) -> str:
        """
        Descargar video desde una URL y guardarlo en un archivo temporal.
        """
        try:
            # Generar un nombre de archivo único
            file_id = str(uuid.uuid4())
            filename = f"video_{file_id}.mp4"
            local_path = os.path.join(settings.temp_dir, filename)

            # Asegurarse de que el directorio temporal exista
            os.makedirs(settings.temp_dir, exist_ok=True)

            logger.info(f"Descargando video desde: {video_url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(local_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)

                        logger.info(f"Video descargado correctamente en: {local_path}")
                        return local_path
                    else:
                        raise Exception(f"HTTP {response.status}: Falla al descargar video")

        except Exception as e:
            logger.error(f"Error al descargar video: {e}")
            raise
    
    async def save_clip(self, clip_path: str, clip_id: str) -> str:
        """
        Guardar el clip generado en el almacenamiento persistente y devolver la URL o ruta del clip.
        """
        try:
            # Crear el nombre del archivo del clip
            clip_filename = f"{clip_id}.mp4"
            output_path = os.path.join(self.clips_output_dir, clip_filename)

            # Asegurarse de que el directorio de salida exista
            os.makedirs(self.clips_output_dir, exist_ok=True)

            # Copiar el archivo al almacenamiento persistente
            async with aiofiles.open(clip_path, 'rb') as src:
                async with aiofiles.open(output_path, 'wb') as dst:
                    async for chunk in src:
                        await dst.write(chunk)
            
            # Retornar la ruta relativa del clip
            clip_url = f"/clips/raw/{clip_filename}"
            logger.info(f"Clip guardado en: {output_path}")

            return clip_url
            
        except Exception as e:
            logger.error(f"Error al guardar clip: {e}")
            raise
    
    def get_clip_binary_data(self, clip_path: str) -> bytes:
        """
        Obtener los datos binarios de un archivo de clip
        """
        try:
            with open(clip_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error al leer los datos binarios del clip: {e}")
            raise
    
    def cleanup_temp_file(self, file_path: str):
        """Limpiar archivo temporal"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Archivo temporal limpiado: {file_path}")
        except Exception as e:
            logger.warning(f"No se pudo limpiar {file_path}: {e}")
