import os
import uuid
import logging
import ffmpeg
import subprocess
import json
from typing import List, Dict, Tuple, Any
from config import settings
from whisper_service import WhisperService
import re

logger = logging.getLogger(__name__)

class ViralClipAnalyzer:
    def __init__(self):
        self.whisper_service = WhisperService()
        self.temp_dir = settings.temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

        # Usa palabras clave virales y emocionales de la configuración
        self.viral_keywords = settings.viral_keywords
        self.emotion_keywords = settings.emotion_keywords
    
    async def analyze_clip(self, clip_path: str) -> Dict[str, Any]:
        """
        Analiza un clip para determinar su potencial viral.
        Devuelve resultados que incluyen transcripción y puntuación viral.
        """
        try:
            # Obtener duración del video usando FFprobe
            duration = await self._get_video_duration(clip_path)
            
            # Extraer audio para transcripción
            audio_path = await self._extract_audio(clip_path)
            
            # Transcribir audio
            transcription = await self.whisper_service.transcribe_audio(audio_path)
            
            # Analizar potencial viral
            viral_analysis = await self._analyze_viral_potential(transcription)
            
            # Limpiar archivo de audio
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
            logger.error(f"Error al analizar el clip {clip_path}: {e}")
            return {
                "duration": 0,
                "transcription": {"text": "", "segments": []},
                "viral_score": 0.0,
                "keywords_found": [],
                "emotions_found": [],
                "key_moments": []
            }
    
    async def _get_video_duration(self, video_path: str) -> float:
        """Obtener la duración del video usando FFprobe"""
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
                logger.error(f"Error de FFprobe: {result.stderr}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error al obtener la duración del video: {e}")
            return 0.0
    
    async def _extract_audio(self, video_path: str) -> str:
        """Extraer audio del video para transcripción"""
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
            logger.error(f"Error al extraer audio: {e}")
            raise
    
    async def _analyze_viral_potential(self, transcription: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analizar la transcripción para potencial viral usando coincidencia de palabras clave
        """
        text = transcription.get("text", "").lower()
        segments = transcription.get("segments", [])
        
        # Encontrar palabras clave virales
        viral_keywords_found = []
        for keyword in self.viral_keywords:
            if keyword.lower() in text:
                viral_keywords_found.append(keyword)
        
        # Encontrar palabras clave de emoción
        emotion_keywords_found = []
        for keyword in self.emotion_keywords:
            if keyword.lower() in text:
                emotion_keywords_found.append(keyword)
        
        # Calcular puntuación viral
        viral_score = self._calculate_viral_score(
            text, viral_keywords_found, emotion_keywords_found, segments
        )
        
        # Encontrar momentos clave (segmentos con alta potencial viral)
        key_moments = self._find_key_moments(segments, viral_keywords_found, emotion_keywords_found)
        
        return {
            "score": viral_score,
            "keywords": viral_keywords_found,
            "emotions": emotion_keywords_found,
            "key_moments": key_moments
        }
    
    def _calculate_viral_score(self, text: str, viral_keywords: List[str], 
                             emotion_keywords: List[str], segments: List[Dict]) -> float:
        """Calcular la puntuación viral basada en múltiples factores"""
        
        if not text:
            return 0.0
        
        score = 0.0
        text_length = len(text.split())
        
        # Puntuación por densidad de palabras clave (0-40 puntos)
        keyword_density = (len(viral_keywords) + len(emotion_keywords)) / max(text_length, 1)
        score += min(keyword_density * 100, 40)
        
        # Puntuación por variedad de categorías de palabras clave (0-20 puntos)
        unique_categories = set()
        if viral_keywords:
            unique_categories.add("viral")
        if emotion_keywords:
            unique_categories.add("emotion")
        score += len(unique_categories) * 10
        
        # Optimización por longitud de texto (0-20 puntos)
        # Favorece textos de longitud media (no muy cortos, no muy largos)
        if 20 <= text_length <= 100:
            score += 20
        elif 10 <= text_length < 20 or 100 < text_length <= 150:
            score += 15
        elif text_length > 5:
            score += 10
        
        # Patrones de engagement (0-20 puntos)
        engagement_patterns = [
            r'\b(incredible|wow|amazing|perfect|excellent)\b',
            r'\b(free|discount|offer|promotion)\b',
            r'\b(want|need|desire)\b',
            r'[!]{2,}',  # Múltiples signos de exclamación
            r'\b(now|today|limited|exclusive)\b'
        ]
        
        pattern_matches = 0
        for pattern in engagement_patterns:
            if re.search(pattern, text.lower()):
                pattern_matches += 1
        
        score += min(pattern_matches * 4, 20)
        
        # Normalizar puntuación a rango 0-1
        normalized_score = min(score / 100, 1.0)
        
        return round(normalized_score, 3)
    
    def _find_key_moments(self, segments: List[Dict], viral_keywords: List[str], 
                         emotion_keywords: List[str]) -> List[Dict]:
        """Encontrar segmentos con mayor potencial viral"""
        key_moments = []
        
        for segment in segments:
            segment_text = segment.get("text", "").lower()
            moment_score = 0
            found_keywords = []
            
            # Comprobar palabras clave virales en este segmento
            for keyword in viral_keywords:
                if keyword.lower() in segment_text:
                    moment_score += 1
                    found_keywords.append(keyword)
            
            # Comprobar palabras clave de emoción en este segmento
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
        
        # Ordenar por puntuación (mayor primero)
        key_moments.sort(key=lambda x: x["score"], reverse=True)
        
        return key_moments[:5]  # Devolver los 5 mejores momentos
    
    async def create_viral_clip(self, original_path: str, key_moments: List[Dict], 
                              output_path: str, target_duration: float = 30) -> bool:
        """
        Crear un nuevo clip viral basado en momentos clave
        """
        try:
            if not key_moments:
                # Si no hay momentos clave, tomar la parte central del clip
                duration = await self._get_video_duration(original_path)
                
                start_time = max(0, (duration - target_duration) / 2)
                end_time = min(duration, start_time + target_duration)
                
                return await self._extract_segment(original_path, start_time, end_time, output_path)
            
            # Seleccionar los mejores momentos que quepan dentro de la duración objetivo
            selected_moments = self._select_optimal_moments(key_moments, target_duration)
            
            if len(selected_moments) == 1:
                # Momento único - extender si es necesario
                moment = selected_moments[0]
                duration = moment["end"] - moment["start"]
                
                if duration < target_duration:
                    # Extender el clip de forma simétrica
                    extension = (target_duration - duration) / 2
                    start_time = max(0, moment["start"] - extension)
                    end_time = moment["end"] + extension
                else:
                    start_time = moment["start"]
                    end_time = moment["end"]
                
                return await self._extract_segment(original_path, start_time, end_time, output_path)
            
            else:
                # Múltiples momentos - tomar el primer mejor momento y rellenar hasta target
                best_moment = selected_moments[0]
                start_time = best_moment["start"]
                end_time = min(best_moment["end"] + target_duration, best_moment["start"] + target_duration)
                
                return await self._extract_segment(original_path, start_time, end_time, output_path)
                
        except Exception as e:
            logger.error(f"Error al crear el clip viral: {e}")
            return False
    
    def _select_optimal_moments(self, key_moments: List[Dict], target_duration: float) -> List[Dict]:
        """Seleccionar momentos óptimos que encajen en la duración objetivo"""
        
        if not key_moments:
            return []
        
        # Ordenar por puntuación
        sorted_moments = sorted(key_moments, key=lambda x: x["score"], reverse=True)
        
        selected = []
        total_duration = 0
        
        for moment in sorted_moments:
            moment_duration = moment["end"] - moment["start"]
            
            if total_duration + moment_duration <= target_duration:
                selected.append(moment)
                total_duration += moment_duration
            
            if total_duration >= target_duration * 0.8:  # 80% de la duración objetivo
                break
        
        return selected if selected else [sorted_moments[0]]
    
    async def _extract_segment(self, input_path: str, start_time: float, 
                             end_time: float, output_path: str) -> bool:
        """Extraer un segmento del video usando FFmpeg"""
        try:
            duration = end_time - start_time
            
            (
                ffmpeg
                .input(input_path, ss=start_time, t=duration)
                .output(output_path, vcodec='libx264', acodec='aac',
                       **{'b:v': '1M', 'b:a': '128k'})  # Bitrate reducido
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Clip viral creado: {output_path} ({start_time:.2f}s - {end_time:.2f}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error al extraer el segmento: {e}")
            return False
