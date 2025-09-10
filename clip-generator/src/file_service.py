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
        SIN timeout para permitir videos largos, pero CON seguimiento de progreso.
        Usa método robusto para archivos grandes.
        """
        try:
            # Generar un nombre de archivo único
            file_id = str(uuid.uuid4())
            filename = f"video_{file_id}.mp4"
            local_path = os.path.join(settings.temp_dir, filename)

            # Asegurarse de que el directorio temporal exista
            os.makedirs(settings.temp_dir, exist_ok=True)
            
            # Verificar espacio disponible antes de comenzar
            import shutil
            try:
                free_space_gb = shutil.disk_usage(settings.temp_dir).free / (1024 * 1024 * 1024)
                logger.info(f"Espacio libre disponible: {free_space_gb:.2f}GB")
                if free_space_gb < 1:
                    raise Exception(f"Espacio insuficiente en disco: solo {free_space_gb:.2f}GB disponibles. Se requieren al menos 1GB libres.")
            except Exception as space_error:
                logger.warning(f"No se pudo verificar espacio en disco: {space_error}")

            logger.info(f"Descargando video desde: {video_url}")

            # ClientSession SIN timeout para videos largos
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    if response.status == 200:
                        # Obtener información del archivo
                        content_length = response.headers.get('Content-Length')
                        total_size_mb = None
                        
                        if content_length:
                            total_size = int(content_length)
                            total_size_mb = total_size / (1024 * 1024)
                            
                            # Verificar tamaño máximo permitido
                            if total_size_mb > settings.max_video_size_mb:
                                raise Exception(f"Video demasiado grande: {total_size_mb:.1f}MB (máximo permitido: {settings.max_video_size_mb}MB)")
                            
                            logger.info(f"Iniciando descarga de video: {total_size_mb:.1f}MB ({total_size:,} bytes)")
                        else:
                            logger.info("Iniciando descarga de video (tamaño desconocido)")

                        # Descarga con método robusto y seguimiento detallado de progreso
                        downloaded_bytes = 0
                        last_log_mb = 0
                        chunk_size = settings.download_chunk_size
                        
                        logger.info(f"Usando chunks de {chunk_size / 1024 / 1024:.1f}MB para optimizar la descarga")
                        
                        # Usar método síncrono más robusto para archivos grandes
                        with open(local_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(chunk_size):
                                try:
                                    # Escribir chunk de forma síncrona (más estable para archivos grandes)
                                    f.write(chunk)
                                    f.flush()  # Forzar escritura al disco
                                    downloaded_bytes += len(chunk)
                                    downloaded_mb = downloaded_bytes / (1024 * 1024)
                                    
                                    # Log de progreso cada N MB
                                    if downloaded_mb - last_log_mb >= settings.progress_log_interval:
                                        if total_size_mb:
                                            progress_pct = (downloaded_bytes / total_size) * 100
                                            logger.info(f"Progreso descarga: {downloaded_mb:.1f}MB / {total_size_mb:.1f}MB ({progress_pct:.1f}%)")
                                        else:
                                            logger.info(f"Descargado: {downloaded_mb:.1f}MB...")
                                        last_log_mb = downloaded_mb
                                        
                                except IOError as io_err:
                                    logger.error(f"Error de E/O escribiendo chunk en {downloaded_mb:.1f}MB: {io_err}")
                                    raise Exception(f"Error escribiendo archivo en {downloaded_mb:.1f}MB: {str(io_err)}")

                        # Verificar descarga completa
                        final_size = os.path.getsize(local_path)
                        final_size_mb = final_size / (1024 * 1024)
                        
                        if total_size_mb and abs(final_size_mb - total_size_mb) > 1:  # Tolerancia de 1MB
                            logger.warning(f"Posible descarga incompleta: esperado {total_size_mb:.1f}MB, obtenido {final_size_mb:.1f}MB")
                        
                        logger.info(f"✅ Video descargado correctamente: {final_size_mb:.1f}MB en {local_path}")
                        return local_path
                    else:
                        raise Exception(f"HTTP {response.status}: Falla al descargar video desde {video_url}")

        except aiohttp.ClientError as e:
            logger.error(f"Error de conexión HTTP: {e}")
            raise Exception(f"Error de conexión al descargar video: {str(e)}")
        except OSError as e:
            logger.error(f"Error del sistema de archivos: {e}")
            # Verificar espacio en disco
            import shutil
            try:
                free_space = shutil.disk_usage(settings.temp_dir).free / (1024 * 1024 * 1024)  # GB
                logger.error(f"Espacio libre disponible: {free_space:.2f}GB")
                if free_space < 1:
                    raise Exception(f"Espacio insuficiente en disco: solo {free_space:.2f}GB disponibles. Se requieren al menos 1GB libres.")
                else:
                    raise Exception(f"Error escribiendo archivo de video: {str(e)}. Espacio disponible: {free_space:.2f}GB")
            except Exception as space_error:
                logger.error(f"No se pudo verificar espacio en disco: {space_error}")
                raise Exception(f"Error escribiendo archivo de video: {str(e)}")
        except Exception as e:
            logger.error(f"Error al descargar video: {e}")
            # Limpiar archivo parcial si existe
            if 'local_path' in locals() and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    logger.info(f"Archivo parcial limpiado: {local_path}")
                except:
                    pass
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
