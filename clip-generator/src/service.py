import os
import uuid
import logging
from typing import List, Tuple
from file_service import FileDownloadService
from video_processor import VideoProcessor
from models import ClipMetadata, VideoRequest
from config import settings

logger = logging.getLogger(__name__)

class ClipGeneratorService:
    def __init__(self):
        self.file_service = FileDownloadService()
        self.video_processor = VideoProcessor()
    
    async def generate_clips(self, request: VideoRequest) -> Tuple[List[ClipMetadata], str, float]:
        """Genera clips a partir de un video analizando todo el contenido con IA."""
        
        video_id = str(uuid.uuid4())
        temp_video_path = None
        
        try:
            # 1. Descargar el video
            logger.info(f"Descargando video desde: {request.video_url}")
            temp_video_path = await self.file_service.download_video(request.video_url)

            # 2. Analizar todo el video con Deepseek IA para detectar los mejores momentos
            logger.info("Analizando video completo con IA para identificar mejores momentos...")
            highlights_data = await self.video_processor.detect_highlights_with_metadata(temp_video_path)
            
            if not highlights_data:
                raise Exception("No se detectaron puntos destacados en el video")

            # 3. Obtener información del análisis para el response
            analysis_method = self.video_processor.get_last_analysis_method()
            video_duration = await self.video_processor._get_video_duration(temp_video_path)

            # 4. Crear clips y guardarlos localmente
            clips_metadata = []
            
            for i, highlight_data in enumerate(highlights_data):
                start_time = highlight_data.get("start", 0.0)
                end_time = highlight_data.get("end", 0.0)
                ai_score = highlight_data.get("score")
                ai_reason = highlight_data.get("reason", f"Momento destacado {i+1} identificado por IA")
                
                # Log para debug
                logger.info(f"Procesando highlight {i+1}: start={start_time:.2f}, end={end_time:.2f}, score={ai_score}, reason={ai_reason[:50]}...")
                
                clip_id = f"clip_{video_id}_{i+1}"
                temp_clip_path = os.path.join(settings.temp_dir, f"{clip_id}.mp4")

                # Crear clip
                logger.info(f"Generando clip {i+1}/{len(highlights_data)}: {start_time:.2f}s - {end_time:.2f}s")
                success = await self.video_processor.create_clip(
                    temp_video_path, start_time, end_time, temp_clip_path
                )
                
                if success and os.path.exists(temp_clip_path):
                    # Guardar clip temporalmente y obtener URL de acceso
                    clip_url = await self.file_service.save_clip_temporary(temp_clip_path, clip_id)
                    
                    # Crear metadatos con URL de acceso temporal
                    clip_metadata = ClipMetadata(
                        clip_id=clip_id,
                        url=clip_url,
                        start=start_time,
                        end=end_time,
                        duration=end_time - start_time,
                        width=settings.clip_width,
                        height=settings.clip_height,
                        format="vertical",
                        ai_score=ai_score,
                        ai_reason=ai_reason
                    )
                    clips_metadata.append(clip_metadata)

                    # Limpiar archivo temporal original (ya está copiado)
                    self.file_service.cleanup_temp_file(temp_clip_path)

                    logger.info(f"Clip {i+1} procesado correctamente: {clip_url}")
                else:
                    logger.warning(f"No se pudo crear el clip {i+1}")

            logger.info(f"Proceso completado: {len(clips_metadata)} clips generados usando {analysis_method} (acceso temporal)")
            
            return clips_metadata, analysis_method, video_duration
            
        except Exception as e:
            logger.error(f"Error en la generación de clips: {e}")
            raise
        finally:
            # Limpiar archivo de video temporal
            if temp_video_path:
                self.file_service.cleanup_temp_file(temp_video_path)
