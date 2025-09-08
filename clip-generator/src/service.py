import os
import uuid
import logging
from typing import List
from file_service import FileDownloadService
from video_processor import VideoProcessor
from models import ClipMetadata, VideoRequest
from config import settings

logger = logging.getLogger(__name__)

class ClipGeneratorService:
    def __init__(self):
        self.file_service = FileDownloadService()
        self.video_processor = VideoProcessor()
    
    async def generate_clips(self, request: VideoRequest) -> List[ClipMetadata]:
        """Genera clips a partir de un video proporcionado."""
        
        video_id = str(uuid.uuid4())
        temp_video_path = None
        
        try:
            # 1. Descargar el video
            logger.info(f"Descargando video desde: {request.video_url}")
            temp_video_path = await self.file_service.download_video(request.video_url)

            # 2. Detectar los puntos destacados del video
            logger.info("Detectando los puntos destacados del video...")
            highlights = await self.video_processor.detect_highlights(temp_video_path)
            
            if not highlights:
                raise Exception("No se detectaron puntos destacados en el video")

            # 3. Crear clips y guardarlos localmente
            clips_metadata = []
            
            for i, (start_time, end_time) in enumerate(highlights):
                clip_id = f"clip_{video_id}_{i+1}"
                temp_clip_path = os.path.join(settings.temp_dir, f"{clip_id}.mp4")

                # Crear clip
                logger.info(f"Creando clip {i+1}: {start_time:.2f}s - {end_time:.2f}s")
                success = await self.video_processor.create_clip(
                    temp_video_path, start_time, end_time, temp_clip_path
                )
                
                if success and os.path.exists(temp_clip_path):
                    # Guardar clip en almacenamiento persistente
                    clip_url = await self.file_service.save_clip(temp_clip_path, clip_id)

                    # Crear metadatos con información de formato
                    clip_metadata = ClipMetadata(
                        url=clip_url,
                        start=start_time,
                        end=end_time,
                        duration=end_time - start_time,
                        width=settings.clip_width,
                        height=settings.clip_height,
                        format="vertical"
                    )
                    clips_metadata.append(clip_metadata)

                    # Limpiar archivo temporal
                    self.file_service.cleanup_temp_file(temp_clip_path)

                    logger.info(f"Clip creado y guardado correctamente: {clip_url}")
                else:
                    logger.warning(f"No se pudo crear el clip {i+1}")

            return clips_metadata
            
        except Exception as e:
            logger.error(f"Error en la generación de clips: {e}")
            raise
        finally:
            # Limpiar archivo de video temporal
            if temp_video_path:
                self.file_service.cleanup_temp_file(temp_video_path)
