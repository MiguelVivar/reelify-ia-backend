import os
import logging
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class WhisperService:
    """
    Servicio Whisper simulado para desarrollo sin dependencias pesadas.
    Reemplazar con la implementación real de Whisper cuando sea necesario.
    """
    
    def __init__(self):
        self.model = None
        self.model_name = getattr(settings, 'whisper_model', 'base')
        self.device = getattr(settings, 'whisper_device', 'cpu')
        logger.info("Servicio Mock Whisper inicializado")
    
    def _load_model(self):
        """Carga del modelo (simulada)"""
        logger.info(f"Cargando modelo Whisper (simulado): {self.model_name}")
        self.model = "mock_model"
        logger.info("Modelo Whisper (simulado) cargado correctamente")
    
    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcripción simulada que devuelve datos de ejemplo.
        """
        try:
            self._load_model()
            
            logger.info(f"Transcribiendo audio (simulado): {audio_path}")
            
            # Simular tiempo de procesamiento
            import asyncio
            await asyncio.sleep(0.5)
            
            # Devolver datos de transcripción simulada con palabras clave virales
            mock_transcription = {
                "text": "This is an amazing video with incredible content that could go viral. Check this out everyone! This is so funny and awesome.",
                "language": "en",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 3.0,
                        "text": "This is an amazing video with incredible",
                        "words": []
                    },
                    {
                        "start": 3.0,
                        "end": 6.0,
                        "text": "content that could go viral. Check this out",
                        "words": []
                    },
                    {
                        "start": 6.0,
                        "end": 8.0,
                        "text": "everyone! This is so funny and awesome.",
                        "words": []
                    }
                ],
                "duration": 8.0
            }
            
            logger.info(f"Transcripción (simulada) completada. Idioma: {mock_transcription['language']}")
            return mock_transcription
            
        except Exception as e:
            logger.error(f"Error en transcripción simulada: {e}")
            return {
                "text": "",
                "language": "unknown",
                "segments": [],
                "duration": 0,
                "error": str(e)
            }
