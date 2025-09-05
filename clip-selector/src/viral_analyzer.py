import os
import uuid
import logging
import ffmpeg
from typing import List, Dict, Tuple, Any
from moviepy.editor import VideoFileClip
from config import settings
from whisper_service import WhisperService
import re
import numpy as np

logger = logging.getLogger(__name__)

class ViralClipAnalyzer:
    def __init__(self):
        self.whisper_service = WhisperService()
        self.temp_dir = settings.temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Compile keyword patterns for better performance
        self.viral_patterns = [re.compile(rf'\b{keyword.lower()}\b') for keyword in settings.viral_keywords]
        self.emotion_patterns = [re.compile(rf'\b{keyword.lower()}\b') for keyword in settings.emotion_keywords]
    
    async def analyze_clip(self, clip_path: str) -> Dict[str, Any]:
        """
        Analyze a single clip for viral potential
        Returns analysis results including transcription and viral score
        """
        try:
            # Get video duration
            video = VideoFileClip(clip_path)
            duration = video.duration
            video.close()
            
            # Extract audio for transcription
            audio_path = await self._extract_audio(clip_path)
            
            # Transcribe audio
            transcription = await self.whisper_service.transcribe_audio(audio_path)
            
            # Analyze viral potential
            viral_analysis = await self._analyze_viral_potential(transcription)
            
            # Clean up audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return {
                "duration": duration,
                "transcription": transcription,
                "viral_score": viral_analysis["score"],
                "keywords_found": viral_analysis["keywords"],
                "emotions_found": viral_analysis["emotions"],
                "key_moments": viral_analysis["key_moments"]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing clip {clip_path}: {e}")
            return {
                "duration": 0,
                "transcription": {"text": "", "segments": []},
                "viral_score": 0.0,
                "keywords_found": [],
                "emotions_found": [],
                "key_moments": []
            }
    
    async def _extract_audio(self, video_path: str) -> str:
        """Extract audio from video for transcription"""
        audio_id = str(uuid.uuid4())
        audio_path = os.path.join(self.temp_dir, f"audio_{audio_id}.wav")
        
        try:
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True)
            )
            return audio_path
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            raise
    
    async def _analyze_viral_potential(self, transcription: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze transcription for viral potential using keyword matching
        and semantic analysis
        """
        text = transcription.get("text", "").lower()
        segments = transcription.get("segments", [])
        
        # Find viral keywords
        viral_keywords_found = []
        for i, pattern in enumerate(self.viral_patterns):
            if pattern.search(text):
                viral_keywords_found.append(settings.viral_keywords[i])
        
        # Find emotion keywords
        emotion_keywords_found = []
        for i, pattern in enumerate(self.emotion_patterns):
            if pattern.search(text):
                emotion_keywords_found.append(settings.emotion_keywords[i])
        
        # Calculate viral score
        viral_score = self._calculate_viral_score(
            text, viral_keywords_found, emotion_keywords_found, segments
        )
        
        # Find key moments (segments with high viral potential)
        key_moments = self._find_key_moments(segments, viral_keywords_found, emotion_keywords_found)
        
        return {
            "score": viral_score,
            "keywords": viral_keywords_found,
            "emotions": emotion_keywords_found,
            "key_moments": key_moments
        }
    
    def _calculate_viral_score(self, text: str, viral_keywords: List[str], 
                             emotion_keywords: List[str], segments: List[Dict]) -> float:
        """Calculate viral score based on multiple factors"""
        
        if not text:
            return 0.0
        
        score = 0.0
        text_length = len(text.split())
        
        # Keyword density score (0-40 points)
        keyword_density = (len(viral_keywords) + len(emotion_keywords)) / max(text_length, 1)
        score += min(keyword_density * 100, 40)
        
        # Keyword variety score (0-20 points)
        unique_categories = set()
        if viral_keywords:
            unique_categories.add("viral")
        if emotion_keywords:
            unique_categories.add("emotion")
        score += len(unique_categories) * 10
        
        # Text length optimization (0-20 points)
        # Favor medium-length texts (not too short, not too long)
        if 20 <= text_length <= 100:
            score += 20
        elif 10 <= text_length < 20 or 100 < text_length <= 150:
            score += 15
        elif text_length > 5:
            score += 10
        
        # Engagement patterns (0-20 points)
        engagement_patterns = [
            r'\b(increíble|wow|genial|perfecto|excelente)\b',
            r'\b(gratis|descuento|oferta|promoción)\b',
            r'\b(quiero|necesito|deseo)\b',
            r'[!]{2,}',  # Multiple exclamation marks
            r'\b(ahora|hoy|limitado|exclusivo)\b'
        ]
        
        pattern_matches = 0
        for pattern in engagement_patterns:
            if re.search(pattern, text.lower()):
                pattern_matches += 1
        
        score += min(pattern_matches * 4, 20)
        
        # Normalize score to 0-1 range
        normalized_score = min(score / 100, 1.0)
        
        return round(normalized_score, 3)
    
    def _find_key_moments(self, segments: List[Dict], viral_keywords: List[str], 
                         emotion_keywords: List[str]) -> List[Dict]:
        """Find segments with highest viral potential"""
        key_moments = []
        
        for segment in segments:
            segment_text = segment.get("text", "").lower()
            moment_score = 0
            found_keywords = []
            
            # Check for viral keywords in this segment
            for keyword in viral_keywords:
                if keyword.lower() in segment_text:
                    moment_score += 1
                    found_keywords.append(keyword)
            
            # Check for emotion keywords in this segment
            for keyword in emotion_keywords:
                if keyword.lower() in segment_text:
                    moment_score += 0.5
                    found_keywords.append(keyword)
            
            if moment_score > 0:
                key_moments.append({
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "text": segment.get("text", ""),
                    "score": moment_score,
                    "keywords": found_keywords
                })
        
        # Sort by score (highest first)
        key_moments.sort(key=lambda x: x["score"], reverse=True)
        
        return key_moments[:5]  # Return top 5 moments
    
    async def create_viral_clip(self, original_path: str, key_moments: List[Dict], 
                              output_path: str, target_duration: float = 30) -> bool:
        """
        Create a new viral clip based on key moments
        Uses FunClip-like approach to select best segments
        """
        try:
            if not key_moments:
                # If no key moments, take the middle part of the clip
                video = VideoFileClip(original_path)
                duration = video.duration
                video.close()
                
                start_time = max(0, (duration - target_duration) / 2)
                end_time = min(duration, start_time + target_duration)
                
                return await self._extract_segment(original_path, start_time, end_time, output_path)
            
            # Select best moments that fit within target duration
            selected_moments = self._select_optimal_moments(key_moments, target_duration)
            
            if len(selected_moments) == 1:
                # Single moment - extend it if needed
                moment = selected_moments[0]
                duration = moment["end"] - moment["start"]
                
                if duration < target_duration:
                    # Extend the clip symmetrically
                    extension = (target_duration - duration) / 2
                    start_time = max(0, moment["start"] - extension)
                    end_time = moment["end"] + extension
                else:
                    start_time = moment["start"]
                    end_time = moment["end"]
                
                return await self._extract_segment(original_path, start_time, end_time, output_path)
            
            else:
                # Multiple moments - create compilation (for now, take the first best moment)
                best_moment = selected_moments[0]
                start_time = best_moment["start"]
                end_time = min(best_moment["end"] + target_duration, best_moment["start"] + target_duration)
                
                return await self._extract_segment(original_path, start_time, end_time, output_path)
                
        except Exception as e:
            logger.error(f"Error creating viral clip: {e}")
            return False
    
    def _select_optimal_moments(self, key_moments: List[Dict], target_duration: float) -> List[Dict]:
        """Select optimal moments that fit within target duration"""
        
        if not key_moments:
            return []
        
        # Sort by score
        sorted_moments = sorted(key_moments, key=lambda x: x["score"], reverse=True)
        
        selected = []
        total_duration = 0
        
        for moment in sorted_moments:
            moment_duration = moment["end"] - moment["start"]
            
            if total_duration + moment_duration <= target_duration:
                selected.append(moment)
                total_duration += moment_duration
            
            if total_duration >= target_duration * 0.8:  # 80% of target duration
                break
        
        return selected if selected else [sorted_moments[0]]
    
    async def _extract_segment(self, input_path: str, start_time: float, 
                             end_time: float, output_path: str) -> bool:
        """Extract a segment from video using FFmpeg"""
        try:
            duration = end_time - start_time
            
            (
                ffmpeg
                .input(input_path, ss=start_time, t=duration)
                .output(output_path, vcodec='libx264', acodec='aac',
                       **{'b:v': '2M', 'b:a': '128k'})
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Created viral clip: {output_path} ({start_time:.2f}s - {end_time:.2f}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error extracting segment: {e}")
            return False
