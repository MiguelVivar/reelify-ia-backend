import os
import logging
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class WhisperService:
    """
    Mock Whisper service for development without heavy dependencies
    Replace with actual Whisper implementation when needed
    """
    
    def __init__(self):
        self.model = None
        self.model_name = getattr(settings, 'whisper_model', 'base')
        self.device = getattr(settings, 'whisper_device', 'cpu')
        logger.info("Initialized Mock Whisper Service")
    
    def _load_model(self):
        """Mock model loading"""
        logger.info(f"Mock loading Whisper model: {self.model_name}")
        self.model = "mock_model"
        logger.info("Mock Whisper model loaded successfully")
    
    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Mock transcription that returns sample data
        """
        try:
            self._load_model()
            
            logger.info(f"Mock transcribing audio: {audio_path}")
            
            # Simulate processing time
            import asyncio
            await asyncio.sleep(0.5)
            
            # Return mock transcription data with viral keywords
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
            
            logger.info(f"Mock transcription completed. Language: {mock_transcription['language']}")
            return mock_transcription
            
        except Exception as e:
            logger.error(f"Error in mock transcription: {e}")
            return {
                "text": "",
                "language": "unknown",
                "segments": [],
                "duration": 0,
                "error": str(e)
            }
