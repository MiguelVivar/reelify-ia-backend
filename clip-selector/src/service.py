import os
import uuid
import logging
from typing import List
from file_service import FileService
from viral_analyzer import ViralClipAnalyzer
from models import ClipSelectionRequest, ViralClip
from config import settings

logger = logging.getLogger(__name__)

class ClipSelectorService:
    def __init__(self):
        self.file_service = FileService()
        self.viral_analyzer = ViralClipAnalyzer()
    
    async def select_viral_clips(self, request: ClipSelectionRequest) -> List[ViralClip]:
        """Método principal del servicio para seleccionar clips virales"""
        
        viral_clips = []
        
        for clip_input in request.clips:
            try:
                logger.info(f"Procesando clip: {clip_input.url}")
                
                # Generar ID único para el procesamiento de este clip
                clip_id = str(uuid.uuid4())
                
                # 1. Descargar clip (desde URL o obtener archivo local)
                temp_clip_path = await self.file_service.download_clip(clip_input.url)
                
                # 2. Analizar clip para potencial viral
                analysis = await self.viral_analyzer.analyze_clip(temp_clip_path)
                
                # 3. Comprobar si el clip cumple el umbral viral
                if analysis["viral_score"] < settings.min_viral_score:
                    logger.info(f"El clip no cumple el umbral viral: {analysis['viral_score']:.3f} < {settings.min_viral_score}")
                    # Limpiar si se descargó (no es un archivo local)
                    if not clip_input.url.startswith('/clips/'):
                        self.file_service.cleanup_temp_file(temp_clip_path)
                    continue
                
                # 4. Crear clip viral optimizado
                viral_clip_id = f"viral_{clip_id}"
                temp_viral_path = os.path.join(settings.temp_dir, f"{viral_clip_id}.mp4")
                
                success = await self.viral_analyzer.create_viral_clip(
                    temp_clip_path,
                    analysis["key_moments"],
                    temp_viral_path
                )
                
                if success and os.path.exists(temp_viral_path):
                    # 5. Guardar clip viral en almacenamiento persistente
                    viral_url = await self.file_service.save_viral_clip(temp_viral_path, viral_clip_id)
                    
                    # 6. Crear metadatos del clip viral
                    viral_clip = ViralClip(
                        url=viral_url,
                        keywords=analysis["keywords_found"] + analysis["emotions_found"],
                        duration=analysis["duration"],
                        viral_score=analysis["viral_score"],
                        transcript=analysis["transcription"]["text"]
                    )
                    
                    viral_clips.append(viral_clip)
                    
                    logger.info(f"Clip viral creado con éxito: {viral_url} (puntuación: {analysis['viral_score']:.3f})")
                    
                    # Limpiar clip viral temporal
                    self.file_service.cleanup_temp_file(temp_viral_path)
                else:
                    logger.warning(f"No se pudo crear el clip viral para: {clip_input.url}")
                
                # Limpiar clip descargado si fue temporal
                if not clip_input.url.startswith('/clips/'):
                    self.file_service.cleanup_temp_file(temp_clip_path)
                
            except Exception as e:
                logger.error(f"Error al procesar el clip {clip_input.url}: {e}")
                continue
        
        return viral_clips
