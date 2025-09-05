import whisper
import os
import logging
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self):
        self.model = None
        self.model_name = settings.whisper_model
        self.device = settings.whisper_device
    
    def _load_model(self):
        """Lazy load Whisper model"""
        if self.model is None:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name, device=self.device)
            logger.info("Whisper model loaded successfully")
    
    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper
        Returns transcription with timestamps and language detection
        """
        try:
            self._load_model()
            
            logger.info(f"Transcribing audio: {audio_path}")
            
            # Transcribe with timestamps
            result = self.model.transcribe(
                audio_path,
                word_timestamps=True,
                language="es"  # Spanish by default, can be auto-detected
            )
            
            # Extract segments with timestamps
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "words": segment.get("words", [])
                })
            
            transcription_result = {
                "text": result["text"].strip(),
                "language": result.get("language", "es"),
                "segments": segments,
                "duration": result.get("duration", 0)
            }
            
            logger.info(f"Transcription completed. Language: {transcription_result['language']}")
            return transcription_result
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {
                "text": "",
                "language": "unknown",
                "segments": [],
                "duration": 0,
                "error": str(e)
            }
