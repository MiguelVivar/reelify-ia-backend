import os
import uuid
import logging
import aiohttp
import aiofiles
from urllib.parse import urlparse
from config import settings

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.clips_input_dir = getattr(settings, 'clips_input_dir', '/app/clips/raw')
        self.clips_output_dir = getattr(settings, 'clips_output_dir', '/app/clips/viral')
        os.makedirs(self.clips_output_dir, exist_ok=True)
        
    async def download_clip(self, clip_url: str) -> str:
        """
        Download clip from URL (either HTTP or local file path)
        Returns local file path
        """
        try:
            # Check if it's a local file path
            if clip_url.startswith('/clips/'):
                # Local file path - construct full path
                filename = os.path.basename(clip_url)
                local_path = os.path.join(self.clips_input_dir, filename)
                
                if os.path.exists(local_path):
                    logger.info(f"Using local clip file: {local_path}")
                    return local_path
                else:
                    raise Exception(f"Local clip file not found: {local_path}")
            
            # HTTP/HTTPS URL - download it
            file_id = str(uuid.uuid4())
            filename = f"clip_{file_id}.mp4"
            local_path = os.path.join(settings.temp_dir, filename)
            
            # Ensure temp directory exists
            os.makedirs(settings.temp_dir, exist_ok=True)
            
            logger.info(f"Downloading clip from: {clip_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(clip_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(local_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        logger.info(f"Clip downloaded successfully to: {local_path}")
                        return local_path
                    else:
                        raise Exception(f"HTTP {response.status}: Failed to download clip")
                        
        except Exception as e:
            logger.error(f"Error downloading clip: {e}")
            raise
    
    async def save_viral_clip(self, clip_path: str, clip_id: str) -> str:
        """
        Save viral clip to persistent storage and return access URL/path
        """
        try:
            # Create clip filename
            clip_filename = f"{clip_id}.mp4"
            output_path = os.path.join(self.clips_output_dir, clip_filename)
            
            # Ensure output directory exists
            os.makedirs(self.clips_output_dir, exist_ok=True)
            
            # Copy file to persistent storage
            async with aiofiles.open(clip_path, 'rb') as src:
                async with aiofiles.open(output_path, 'wb') as dst:
                    async for chunk in src:
                        await dst.write(chunk)
            
            # Return file path (can be converted to URL if needed)
            clip_url = f"/clips/viral/{clip_filename}"
            logger.info(f"Viral clip saved to: {output_path}")
            
            return clip_url
            
        except Exception as e:
            logger.error(f"Error saving viral clip: {e}")
            raise
    
    def cleanup_temp_file(self, file_path: str):
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not clean up {file_path}: {e}")
