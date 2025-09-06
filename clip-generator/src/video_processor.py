import os
import uuid
import logging
import ffmpeg
import subprocess
import json
from typing import List, Tuple
from config import settings

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.temp_dir = settings.temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def detect_highlights(self, video_path: str) -> List[Tuple[float, float]]:
        """
        Detect highlights using FFmpeg analysis (lightweight approach)
        Returns list of (start_time, end_time) tuples
        """
        try:
            # Get video duration using FFprobe
            duration = await self._get_video_duration(video_path)
            
            if duration <= 0:
                logger.warning("Could not determine video duration")
                return []
            
            # Simple segmentation approach: divide video into clips
            highlights = self._create_simple_segments(duration)
            
            logger.info(f"Generated {len(highlights)} segments from video duration: {duration:.2f}s")
            return highlights
            
        except Exception as e:
            logger.error(f"Error detecting highlights: {e}")
            return []
    
    async def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using FFprobe"""
        try:
            cmd = [
                'ffprobe', 
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                logger.error(f"FFprobe error: {result.stderr}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting video duration: {e}")
            return 0.0

    async def _get_video_dimensions(self, video_path: str) -> Tuple[int, int]:
        """Get video width and height using FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=s=x:p=0',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                width, height = map(int, result.stdout.strip().split('x'))
                return width, height
            else:
                logger.error(f"FFprobe error getting dimensions: {result.stderr}")
                return 1920, 1080  # Default dimensions
                
        except Exception as e:
            logger.error(f"Error getting video dimensions: {e}")
            return 1920, 1080  # Default dimensions
    
    def _create_simple_segments(self, duration: float) -> List[Tuple[float, float]]:
        """Create simple time-based segments"""
        
        segments = []
        max_clip_duration = settings.max_clip_duration
        min_clip_duration = settings.min_clip_duration
        
        # If video is shorter than max clip duration, return the whole video
        if duration <= max_clip_duration:
            if duration >= min_clip_duration:
                segments.append((0.0, duration))
            return segments
        
        # Create multiple segments
        segment_duration = min(max_clip_duration, duration / 3)  # Aim for 3 segments
        
        if segment_duration < min_clip_duration:
            segment_duration = min_clip_duration
        
        current_time = 0.0
        
        while current_time < duration:
            end_time = min(current_time + segment_duration, duration)
            
            if end_time - current_time >= min_clip_duration:
                segments.append((current_time, end_time))
            
            current_time += segment_duration * 0.7  # 30% overlap for interesting content
        
        # Ensure we don't have too many segments
        return segments[:5]  # Maximum 5 clips
    
    async def create_clip(self, video_path: str, start_time: float, end_time: float, output_path: str) -> bool:
        """Create a vertical clip (configurable dimensions) from horizontal video with black bars for social media"""
        try:
            duration = end_time - start_time
            
            # Get original video dimensions
            original_width, original_height = await self._get_video_dimensions(video_path)
            
            # Target dimensions from configuration (default: 1080x1920 for TikTok/Instagram Reels)
            target_width = settings.clip_width
            target_height = settings.clip_height
            
            # Calculate scaling to fit the video within the target dimensions while maintaining aspect ratio
            # We want to scale based on width since we're fitting horizontal video into vertical format
            scale_factor = target_width / original_width
            scaled_height = int(original_height * scale_factor)
            
            # If scaled height exceeds our target height, scale based on height instead
            if scaled_height > target_height:
                scale_factor = target_height / original_height
                scaled_width = int(original_width * scale_factor)
                scaled_height = target_height
            else:
                scaled_width = target_width
            
            logger.info(f"Scaling video from {original_width}x{original_height} to {scaled_width}x{scaled_height} "
                       f"for target {target_width}x{target_height}")
            
            # Create vertical video with black background and centered horizontal video
            (
                ffmpeg
                .input(video_path, ss=start_time, t=duration)
                .filter('scale', scaled_width, scaled_height)  # Scale maintaining aspect ratio
                .filter('pad', target_width, target_height, '(ow-iw)/2', '(oh-ih)/2', 'black')  # Center with black bars
                .output(output_path, 
                       vcodec='libx264', 
                       acodec='aac',
                       preset='fast',
                       crf=23,
                       **{
                           'b:a': '128k',
                           'r': '30',  # 30 fps for social media
                           'pix_fmt': 'yuv420p'  # Ensure compatibility
                       })
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Created vertical clip ({target_width}x{target_height}): {output_path} ({start_time:.2f}s - {end_time:.2f}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error creating clip: {e}")
            return False
    
    def cleanup_temp_files(self, *file_paths):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not clean up {file_path}: {e}")
