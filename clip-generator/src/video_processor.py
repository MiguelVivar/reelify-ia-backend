import os
import uuid
import logging
import ffmpeg
import numpy as np
from typing import List, Tuple
from moviepy.editor import VideoFileClip
import librosa
from sklearn.cluster import KMeans
from config import settings

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.temp_dir = settings.temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def detect_highlights(self, video_path: str) -> List[Tuple[float, float]]:
        """
        Detect highlights using audio and visual analysis
        Returns list of (start_time, end_time) tuples
        """
        try:
            # Load video
            video = VideoFileClip(video_path)
            duration = video.duration
            
            # Audio analysis for highlights
            audio_highlights = await self._analyze_audio_energy(video_path)
            
            # Visual analysis for scene changes
            visual_highlights = await self._analyze_visual_changes(video_path)
            
            # Combine and filter highlights
            combined_highlights = self._combine_highlights(
                audio_highlights, visual_highlights, duration
            )
            
            video.close()
            return combined_highlights
            
        except Exception as e:
            logger.error(f"Error detecting highlights: {e}")
            return []
    
    async def _analyze_audio_energy(self, video_path: str) -> List[Tuple[float, float]]:
        """Analyze audio energy to detect exciting moments"""
        try:
            # Extract audio features
            y, sr = librosa.load(video_path, sr=22050)
            
            # Calculate energy features
            hop_length = 512
            frame_length = 2048
            
            # RMS energy
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Spectral centroid
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Tempo and beat tracking
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
            
            # Combine features
            times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
            
            # Normalize features
            rms_norm = (rms - np.mean(rms)) / np.std(rms)
            sc_norm = (spectral_centroid - np.mean(spectral_centroid)) / np.std(spectral_centroid)
            zcr_norm = (zcr - np.mean(zcr)) / np.std(zcr)
            
            # Calculate excitement score
            excitement_score = rms_norm + sc_norm + zcr_norm
            
            # Find peaks (exciting moments)
            threshold = np.percentile(excitement_score, 75)  # Top 25% moments
            exciting_indices = np.where(excitement_score > threshold)[0]
            
            # Group consecutive exciting moments
            highlights = []
            if len(exciting_indices) > 0:
                start_idx = exciting_indices[0]
                prev_idx = exciting_indices[0]
                
                for idx in exciting_indices[1:]:
                    if idx - prev_idx > 10:  # Gap larger than ~5 seconds
                        end_idx = prev_idx
                        start_time = times[start_idx]
                        end_time = times[end_idx]
                        
                        if end_time - start_time >= settings.min_clip_duration:
                            highlights.append((start_time, end_time))
                        
                        start_idx = idx
                    prev_idx = idx
                
                # Add final segment
                end_idx = exciting_indices[-1]
                start_time = times[start_idx]
                end_time = times[end_idx]
                if end_time - start_time >= settings.min_clip_duration:
                    highlights.append((start_time, end_time))
            
            return highlights
            
        except Exception as e:
            logger.error(f"Error in audio analysis: {e}")
            return []
    
    async def _analyze_visual_changes(self, video_path: str) -> List[Tuple[float, float]]:
        """Analyze visual changes to detect scene transitions"""
        try:
            video = VideoFileClip(video_path)
            duration = video.duration
            
            # Sample frames every 2 seconds
            sample_interval = 2.0
            timestamps = np.arange(0, duration, sample_interval)
            
            if len(timestamps) < 2:
                video.close()
                return []
            
            # Calculate frame differences
            frame_diffs = []
            prev_frame = None
            
            for t in timestamps:
                try:
                    frame = video.get_frame(t)
                    if prev_frame is not None:
                        # Calculate histogram difference
                        diff = np.sum(np.abs(frame.mean(axis=2) - prev_frame.mean(axis=2)))
                        frame_diffs.append(diff)
                    prev_frame = frame
                except:
                    frame_diffs.append(0)
            
            video.close()
            
            if len(frame_diffs) == 0:
                return []
            
            # Find significant scene changes
            threshold = np.percentile(frame_diffs, 80)  # Top 20% changes
            change_indices = np.where(np.array(frame_diffs) > threshold)[0]
            
            # Convert to time segments
            highlights = []
            for idx in change_indices:
                start_time = max(0, timestamps[idx] - 10)  # 10 seconds before change
                end_time = min(duration, timestamps[idx] + 20)  # 20 seconds after change
                
                if end_time - start_time >= settings.min_clip_duration:
                    highlights.append((start_time, end_time))
            
            return highlights
            
        except Exception as e:
            logger.error(f"Error in visual analysis: {e}")
            return []
    
    def _combine_highlights(self, audio_highlights: List[Tuple[float, float]], 
                          visual_highlights: List[Tuple[float, float]], 
                          duration: float) -> List[Tuple[float, float]]:
        """Combine audio and visual highlights, avoiding overlaps"""
        
        all_highlights = audio_highlights + visual_highlights
        
        if not all_highlights:
            # Fallback: create segments from the video
            num_segments = max(1, int(duration // 60))  # One segment per minute
            segment_duration = min(settings.max_clip_duration, duration / num_segments)
            
            fallback_highlights = []
            for i in range(num_segments):
                start = i * segment_duration
                end = min(start + segment_duration, duration)
                if end - start >= settings.min_clip_duration:
                    fallback_highlights.append((start, end))
            
            return fallback_highlights
        
        # Sort by start time
        all_highlights.sort(key=lambda x: x[0])
        
        # Merge overlapping highlights
        merged = []
        current_start, current_end = all_highlights[0]
        
        for start, end in all_highlights[1:]:
            if start <= current_end + 5:  # Allow 5 second gap
                current_end = max(current_end, end)
            else:
                # Ensure clip duration limits
                duration_clip = current_end - current_start
                if duration_clip > settings.max_clip_duration:
                    current_end = current_start + settings.max_clip_duration
                
                if duration_clip >= settings.min_clip_duration:
                    merged.append((current_start, current_end))
                
                current_start, current_end = start, end
        
        # Add final segment
        duration_clip = current_end - current_start
        if duration_clip > settings.max_clip_duration:
            current_end = current_start + settings.max_clip_duration
        
        if duration_clip >= settings.min_clip_duration:
            merged.append((current_start, current_end))
        
        return merged
    
    async def create_clip(self, video_path: str, start_time: float, end_time: float, output_path: str) -> bool:
        """Create a clip from video using FFmpeg"""
        try:
            duration = end_time - start_time
            
            (
                ffmpeg
                .input(video_path, ss=start_time, t=duration)
                .output(output_path, vcodec='libx264', acodec='aac', 
                       **{'b:v': '2M', 'b:a': '128k'})
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Created clip: {output_path} ({start_time:.2f}s - {end_time:.2f}s)")
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
