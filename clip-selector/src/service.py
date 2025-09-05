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
        """Main service method to select viral clips"""
        
        viral_clips = []
        
        for clip_input in request.clips:
            try:
                logger.info(f"Processing clip: {clip_input.url}")
                
                # Generate unique ID for this clip processing
                clip_id = str(uuid.uuid4())
                
                # 1. Download clip (from URL or get local file)
                temp_clip_path = await self.file_service.download_clip(clip_input.url)
                
                # 2. Analyze clip for viral potential
                analysis = await self.viral_analyzer.analyze_clip(temp_clip_path)
                
                # 3. Check if clip meets viral threshold
                if analysis["viral_score"] < settings.min_viral_score:
                    logger.info(f"Clip does not meet viral threshold: {analysis['viral_score']:.3f} < {settings.min_viral_score}")
                    # Clean up if it was downloaded (not a local file)
                    if not clip_input.url.startswith('/clips/'):
                        self.file_service.cleanup_temp_file(temp_clip_path)
                    continue
                
                # 4. Create optimized viral clip
                viral_clip_id = f"viral_{clip_id}"
                temp_viral_path = os.path.join(settings.temp_dir, f"{viral_clip_id}.mp4")
                
                success = await self.viral_analyzer.create_viral_clip(
                    temp_clip_path,
                    analysis["key_moments"],
                    temp_viral_path
                )
                
                if success and os.path.exists(temp_viral_path):
                    # 5. Save viral clip to persistent storage
                    viral_url = await self.file_service.save_viral_clip(temp_viral_path, viral_clip_id)
                    
                    # 6. Create viral clip metadata
                    viral_clip = ViralClip(
                        url=viral_url,
                        keywords=analysis["keywords_found"] + analysis["emotions_found"],
                        duration=analysis["duration"],
                        viral_score=analysis["viral_score"],
                        transcript=analysis["transcription"]["text"]
                    )
                    
                    viral_clips.append(viral_clip)
                    
                    logger.info(f"Successfully created viral clip: {viral_url} (score: {analysis['viral_score']:.3f})")
                    
                    # Clean up temp viral clip
                    self.file_service.cleanup_temp_file(temp_viral_path)
                else:
                    logger.warning(f"Failed to create viral clip for: {clip_input.url}")
                
                # Clean up downloaded clip if it was temporary
                if not clip_input.url.startswith('/clips/'):
                    self.file_service.cleanup_temp_file(temp_clip_path)
                
            except Exception as e:
                logger.error(f"Error processing clip {clip_input.url}: {e}")
                continue
        
        return viral_clips
