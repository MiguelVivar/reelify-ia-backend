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
        """Main service method to generate clips from video"""
        
        video_id = str(uuid.uuid4())
        temp_video_path = None
        
        try:
            # 1. Download video from public URL
            logger.info(f"Downloading video from: {request.video_url}")
            temp_video_path = await self.file_service.download_video(request.video_url)
            
            # 2. Detect highlights using auto-highlighter
            logger.info("Detecting video highlights...")
            highlights = await self.video_processor.detect_highlights(temp_video_path)
            
            if not highlights:
                raise Exception("No highlights detected in video")
            
            # 3. Create clips and save locally
            clips_metadata = []
            
            for i, (start_time, end_time) in enumerate(highlights):
                clip_id = f"clip_{video_id}_{i+1}"
                temp_clip_path = os.path.join(settings.temp_dir, f"{clip_id}.mp4")
                
                # Create clip
                logger.info(f"Creating clip {i+1}: {start_time:.2f}s - {end_time:.2f}s")
                success = await self.video_processor.create_clip(
                    temp_video_path, start_time, end_time, temp_clip_path
                )
                
                if success and os.path.exists(temp_clip_path):
                    # Save clip to persistent storage
                    clip_url = await self.file_service.save_clip(temp_clip_path, clip_id)
                    
                    # Create metadata
                    clip_metadata = ClipMetadata(
                        url=clip_url,
                        start=start_time,
                        end=end_time,
                        duration=end_time - start_time
                    )
                    clips_metadata.append(clip_metadata)
                    
                    # Clean up temp clip
                    self.file_service.cleanup_temp_file(temp_clip_path)
                    
                    logger.info(f"Successfully created and saved clip: {clip_url}")
                else:
                    logger.warning(f"Failed to create clip {i+1}")
            
            return clips_metadata
            
        except Exception as e:
            logger.error(f"Error in clip generation: {e}")
            raise
        finally:
            # Clean up temp video file
            if temp_video_path:
                self.file_service.cleanup_temp_file(temp_video_path)
