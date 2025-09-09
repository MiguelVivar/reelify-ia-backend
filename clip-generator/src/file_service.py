import os
import uuid
import logging
import aiohttp
import aiofiles
import shutil
from urllib.parse import urlparse
from config import settings

logger = logging.getLogger(__name__)

class FileDownloadService:
    def __init__(self):
        # Directorio temporal para clips (se auto-limpia)
        self.temp_clips_dir = os.path.join(settings.temp_dir, "clips")
        os.makedirs(self.temp_clips_dir, exist_ok=True)
        # Diccionario para rastrear clips temporales
        self.temp_clips = {}
        
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
    
    async def save_clip_temporary(self, clip_path: str, clip_id: str) -> str:
        """
        Guardar clip temporalmente y devolver URL de acceso
        """
        try:
            clip_filename = f"{clip_id}.mp4"
            temp_clip_path = os.path.join(self.temp_clips_dir, clip_filename)
            
            # Copiar el archivo al directorio temporal
            shutil.copy2(clip_path, temp_clip_path)
            
            # Registrar en el diccionario temporal
            self.temp_clips[clip_id] = temp_clip_path
            
            # Retornar URL para acceder al clip
            clip_url = f"/api/v1/clips/{clip_id}"
            logger.info(f"Clip guardado temporalmente: {temp_clip_path}")
            
            return clip_url
            
        except Exception as e:
            logger.error(f"Error al guardar clip temporal: {e}")
            raise
    
    def get_temp_clip_path(self, clip_id: str) -> str:
        """
        Obtener la ruta del clip temporal por su ID
        """
        return self.temp_clips.get(clip_id)
    
    async def get_clip_binary_data(self, clip_path: str) -> bytes:
        """
        Obtener los datos binarios de un archivo de clip
        """
        try:
            async with aiofiles.open(clip_path, 'rb') as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Error al leer los datos binarios del clip: {e}")
            raise
    
    def cleanup_temp_clips(self):
        """
        Limpiar clips temporales
        """
        try:
            for clip_id, path in list(self.temp_clips.items()):
                if os.path.exists(path):
                    os.remove(path)
                    logger.debug(f"Clip temporal limpiado: {path}")
                del self.temp_clips[clip_id]
        except Exception as e:
            logger.warning(f"Error al limpiar clips temporales: {e}")
    
    # MÉTODO ELIMINADO: save_clip ya no guarda clips permanentemente
    # Los clips ahora se sirven temporalmente bajo demanda
    
    def cleanup_temp_file(self, file_path: str):
        """Limpiar archivo temporal"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Archivo temporal limpiado: {file_path}")
        except Exception as e:
            logger.warning(f"No se pudo limpiar {file_path}: {e}")
