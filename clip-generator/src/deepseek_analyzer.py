import os
import uuid
import logging
import asyncio
import aiohttp
import whisper
import ffmpeg
import subprocess
import json
from typing import List, Dict, Tuple, Any, Optional
from config import settings

logger = logging.getLogger(__name__)

class DeepseekVideoAnalyzer:
    """
    Analizador de video que usa Deepseek de OpenRouter para identificar 
    los mejores momentos del video antes de generar clips.
    """
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.deepseek_model
        self.temp_dir = settings.temp_dir
        
        # Configuración de análisis
        self.segment_duration = settings.analysis_segment_duration
        self.max_segments = settings.max_analysis_segments
        self.highlight_threshold = settings.highlight_threshold
        
        # Inicializar Whisper para transcripciones
        try:
            self.whisper_model = whisper.load_model("base")
            logger.info("Modelo Whisper cargado correctamente")
        except Exception as e:
            logger.error(f"Error cargando modelo Whisper: {e}")
            self.whisper_model = None
        
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def analyze_video_highlights_with_metadata(self, video_path: str) -> List[Dict[str, Any]]:
        """
        Analiza todo el video para identificar los mejores momentos para clips.
        Retorna metadatos completos incluyendo scores y razones.
        
        Args:
            video_path: Ruta al archivo de video
            
        Returns:
            Lista de diccionarios con start, end, score, reason
        """
        try:
            if not self.api_key:
                logger.warning("API key de OpenRouter no configurada, usando análisis básico")
                return await self._fallback_analysis_with_metadata(video_path)
            
            logger.info(f"Iniciando análisis de video con Deepseek (con metadatos): {video_path}")
            
            # 1. Obtener duración del video
            duration = await self._get_video_duration(video_path)
            if duration <= 0:
                logger.error("No se pudo obtener la duración del video")
                return []
            
            logger.info(f"Duración del video: {duration:.2f}s")
            
            # 2. Dividir video en segmentos para análisis
            segments = self._create_analysis_segments(duration)
            logger.info(f"Video dividido en {len(segments)} segmentos para análisis")
            
            # 3. Transcribir cada segmento
            segment_transcriptions = []
            for i, (start, end) in enumerate(segments):
                logger.info(f"Transcribiendo segmento {i+1}/{len(segments)}: {start:.1f}s - {end:.1f}s")
                transcription = await self._transcribe_segment(video_path, start, end)
                if transcription:
                    segment_transcriptions.append({
                        'start': start,
                        'end': end,
                        'transcription': transcription,
                        'segment_index': i
                    })
                    logger.info(f"Segmento {i+1} transcrito: {len(transcription)} caracteres")
                else:
                    logger.warning(f"No se pudo transcribir el segmento {i+1}")
            
            if not segment_transcriptions:
                logger.warning("No se pudieron transcribir segmentos, usando análisis de respaldo")
                return await self._fallback_analysis_with_metadata(video_path)
            
            logger.info(f"Total de segmentos transcritos: {len(segment_transcriptions)}")
            
            # 4. Analizar con Deepseek
            highlights = await self._analyze_with_deepseek(segment_transcriptions)
            
            if not highlights:
                logger.warning("Deepseek no devolvió highlights, usando análisis de respaldo")
                return await self._fallback_analysis_with_metadata(video_path)
            
            # 5. Convertir a clips válidos con metadatos
            valid_clips = self._convert_to_clips_with_metadata(highlights, duration)
            
            logger.info(f"Análisis completado: {len(valid_clips)} clips identificados con metadatos")
            return valid_clips
            
        except Exception as e:
            logger.error(f"Error en análisis de video con metadatos: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return await self._fallback_analysis_with_metadata(video_path)

    async def analyze_video_highlights(self, video_path: str) -> List[Tuple[float, float]]:
        """
        Analiza todo el video para identificar los mejores momentos para clips.
        
        Args:
            video_path: Ruta al archivo de video
            
        Returns:
            Lista de tuplas (start_time, end_time) con los mejores momentos
        """
        try:
            if not self.api_key:
                logger.warning("API key de OpenRouter no configurada, usando análisis básico")
                return await self._fallback_analysis(video_path)
            
            logger.info(f"Iniciando análisis de video con Deepseek: {video_path}")
            
            # 1. Obtener duración del video
            duration = await self._get_video_duration(video_path)
            if duration <= 0:
                logger.error("No se pudo obtener la duración del video")
                return []
            
            # 2. Dividir video en segmentos para análisis
            segments = self._create_analysis_segments(duration)
            logger.info(f"Video dividido en {len(segments)} segmentos para análisis")
            
            # 3. Transcribir cada segmento
            segment_transcriptions = []
            for i, (start, end) in enumerate(segments):
                transcription = await self._transcribe_segment(video_path, start, end)
                if transcription:
                    segment_transcriptions.append({
                        'start': start,
                        'end': end,
                        'transcription': transcription,
                        'segment_index': i
                    })
            
            # 4. Analizar con Deepseek
            highlights = await self._analyze_with_deepseek(segment_transcriptions)
            
            # 5. Convertir a clips válidos
            valid_clips = self._convert_to_clips(highlights)
            
            logger.info(f"Análisis completado: {len(valid_clips)} clips identificados")
            return valid_clips
            
        except Exception as e:
            logger.error(f"Error en análisis de video: {e}")
            return await self._fallback_analysis(video_path)
    
    def _create_analysis_segments(self, duration: float) -> List[Tuple[float, float]]:
        """Crea segmentos para análisis del video completo"""
        segments = []
        current_time = 0.0
        
        while current_time < duration and len(segments) < self.max_segments:
            end_time = min(current_time + self.segment_duration, duration)
            segments.append((current_time, end_time))
            current_time += self.segment_duration
        
        return segments
    
    async def _transcribe_segment(self, video_path: str, start_time: float, end_time: float) -> Optional[str]:
        """Transcribe un segmento específico del video"""
        if not self.whisper_model:
            logger.warning("Modelo Whisper no disponible")
            return None
        
        try:
            # Extraer audio del segmento
            segment_id = str(uuid.uuid4())[:8]
            audio_path = os.path.join(self.temp_dir, f"audio_segment_{segment_id}.wav")
            
            logger.info(f"Extrayendo audio del segmento {start_time:.1f}s - {end_time:.1f}s")
            
            # Usar ffmpeg para extraer el audio del segmento
            try:
                (
                    ffmpeg
                    .input(video_path, ss=start_time, t=end_time - start_time)
                    .output(audio_path, acodec='pcm_s16le', ac=1, ar='16000')
                    .overwrite_output()
                    .run(quiet=True, timeout=30)  # Timeout de 30 segundos
                )
            except Exception as e:
                logger.error(f"Error extrayendo audio del segmento: {e}")
                return None
            
            # Verificar que el archivo de audio se creó
            if not os.path.exists(audio_path):
                logger.error(f"Archivo de audio no se creó: {audio_path}")
                return None
            
            # Transcribir con Whisper
            try:
                logger.info(f"Transcribiendo audio: {audio_path}")
                result = self.whisper_model.transcribe(audio_path, language='es')  # Especificar español
                transcription = result["text"].strip()
                
                # Limpiar archivo temporal
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                
                if transcription:
                    logger.info(f"Transcripción exitosa: {len(transcription)} caracteres")
                    return transcription
                else:
                    logger.warning("Transcripción vacía")
                    return None
                
            except Exception as e:
                logger.error(f"Error en transcripción: {e}")
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                return None
                
        except Exception as e:
            logger.error(f"Error en transcripción de segmento: {e}")
            return None
    
    async def _analyze_with_deepseek(self, segment_transcriptions: List[Dict]) -> List[Dict]:
        """Analiza las transcripciones con Deepseek para identificar mejores momentos"""
        try:
            # Preparar el prompt para Deepseek
            transcription_text = "\n\n".join([
                f"Segmento {seg['segment_index']} ({seg['start']:.1f}s - {seg['end']:.1f}s):\n{seg['transcription']}"
                for seg in segment_transcriptions if seg['transcription']
            ])
            
            logger.info(f"Enviando {len(segment_transcriptions)} transcripciones a Deepseek para análisis")
            
            prompt = f"""Analiza estas transcripciones de video e identifica los mejores momentos para clips virales.

TRANSCRIPCIONES:
{transcription_text}

INSTRUCCIONES:
1. Busca momentos emocionantes, graciosos, informativos o controversiales
2. Cada clip debe durar 15-20 segundos
3. Responde solo con JSON válido
4. Incluye solo momentos con score >= 0.7

FORMATO DE RESPUESTA:
{{
    "highlights": [
        {{
            "segment_index": 0,
            "score": 0.8,
            "reason": "Momento divertido",
            "start_time": 15.0,
            "end_time": 35.0
        }}
    ]
}}

Los tiempos start_time y end_time deben ser absolutos del video completo."""
            
            # Hacer llamada a OpenRouter
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Reelify IA Video Analyzer"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        
                        logger.info(f"Respuesta de Deepseek recibida: {content[:200]}...")
                        
                        # Parsear la respuesta JSON
                        try:
                            analysis_result = json.loads(content)
                            highlights = analysis_result.get("highlights", [])
                            
                            logger.info(f"Deepseek parseó {len(highlights)} highlights candidatos")
                            
                            # Mapear índices de segmento a tiempos reales
                            mapped_highlights = []
                            for i, highlight in enumerate(highlights):
                                segment_idx = highlight.get("segment_index", 0)
                                if segment_idx < len(segment_transcriptions):
                                    segment = segment_transcriptions[segment_idx]
                                    
                                    # Usar tiempos específicos de Deepseek si están disponibles
                                    start_time = highlight.get("start_time")
                                    end_time = highlight.get("end_time")
                                    
                                    if start_time is not None and end_time is not None:
                                        # Usar tiempos específicos de Deepseek
                                        final_start = float(start_time)
                                        final_end = float(end_time)
                                        logger.info(f"Highlight {i+1}: Usando tiempos específicos de Deepseek: {final_start:.2f}s - {final_end:.2f}s")
                                    else:
                                        # Usar tiempos del segmento como fallback
                                        final_start = segment["start"]
                                        final_end = segment["end"]
                                        logger.info(f"Highlight {i+1}: Usando tiempos del segmento: {final_start:.2f}s - {final_end:.2f}s")
                                    
                                    mapped_highlights.append({
                                        "start": final_start,
                                        "end": final_end,
                                        "score": highlight.get("score", 0.5),
                                        "reason": highlight.get("reason", "Momento destacado identificado por IA"),
                                        "transcription": segment["transcription"]
                                    })
                            
                            logger.info(f"Deepseek identificó {len(mapped_highlights)} highlights válidos")
                            return mapped_highlights
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parseando respuesta de Deepseek: {e}")
                            logger.error(f"Contenido recibido: {content}")
                            return []
                    else:
                        error_text = await response.text()
                        logger.error(f"Error en API de OpenRouter: {response.status} - {error_text}")
                        return []
        
        except Exception as e:
            logger.error(f"Error en análisis con Deepseek: {e}")
            return []
    
    def _convert_to_clips_with_metadata(self, highlights: List[Dict], video_duration: float) -> List[Dict[str, Any]]:
        """Convierte highlights a clips válidos con metadatos completos"""
        clips = []
        
        for highlight in highlights:
            start = float(highlight.get("start", 0))
            end = float(highlight.get("end", 0))
            score = highlight.get("score", 0.5)
            reason = highlight.get("reason", "Momento destacado identificado por IA")
            duration = end - start
            
            # Validar que el clip tenga sentido
            if duration <= 0:
                continue
            
            # Ajustar duración si es necesario
            if duration < settings.min_clip_duration:
                # Extender el clip para alcanzar la duración mínima
                extension = (settings.min_clip_duration - duration) / 2
                start = max(0, start - extension)
                end = min(video_duration, end + extension)
                duration = end - start
            
            if duration > settings.max_clip_duration:
                # Acortar el clip a la duración máxima
                end = start + settings.max_clip_duration
                duration = settings.max_clip_duration
            
            clip_data = {
                "start": start,
                "end": end,
                "score": score,
                "reason": reason
            }
            clips.append(clip_data)
            
            logger.info(f"Clip con metadatos: {start:.2f}s - {end:.2f}s "
                       f"(score: {score:.2f}, reason: {reason[:50]}...)")
        
        return clips

    def _convert_to_clips(self, highlights: List[Dict]) -> List[Tuple[float, float]]:
        """Convierte highlights a clips válidos con duraciones apropiadas"""
        clips = []
        
        for highlight in highlights:
            start = float(highlight.get("start", 0))
            end = float(highlight.get("end", 0))
            duration = end - start
            
            # Validar que el clip tenga sentido
            if duration <= 0:
                continue
            
            # Ajustar duración si es necesario
            if duration < settings.min_clip_duration:
                # Extender el clip para alcanzar la duración mínima
                extension = (settings.min_clip_duration - duration) / 2
                start = max(0, start - extension)
                end = end + extension
                duration = end - start
            
            if duration > settings.max_clip_duration:
                # Acortar el clip a la duración máxima
                end = start + settings.max_clip_duration
                duration = settings.max_clip_duration
            
            clips.append((start, end))
            logger.info(f"Clip identificado: {start:.2f}s - {end:.2f}s "
                       f"(score: {highlight.get('score', 0):.2f}, "
                       f"reason: {highlight.get('reason', 'N/A')[:50]}...)")
        
        return clips
    
    async def _fallback_analysis_with_metadata(self, video_path: str) -> List[Dict[str, Any]]:
        """Análisis de respaldo con metadatos cuando no está disponible la API"""
        logger.info("Usando análisis de respaldo con metadatos (segmentación simple)")
        
        duration = await self._get_video_duration(video_path)
        if duration <= 0:
            return []
        
        segments = []
        max_clip_duration = settings.max_clip_duration
        min_clip_duration = settings.min_clip_duration
        
        if duration < min_clip_duration:
            return []
        
        if duration <= max_clip_duration:
            return [{
                "start": 0.0,
                "end": duration,
                "score": 0.6,
                "reason": "Video completo - duración adecuada"
            }]
        
        # Crear segmentos con overlap para mejores transiciones
        current_time = 0.0
        segment_count = 0
        
        while current_time < duration and segment_count < 5:  # Máximo 5 clips de respaldo
            end_time = min(current_time + max_clip_duration, duration)
            
            if end_time - current_time >= min_clip_duration:
                segments.append({
                    "start": current_time,
                    "end": end_time,
                    "score": 0.5,  # Score neutro para fallback
                    "reason": f"Segmento automático {segment_count + 1}"
                })
                segment_count += 1
            
            current_time += max_clip_duration * 0.7  # 30% overlap
        
        return segments

    async def _fallback_analysis(self, video_path: str) -> List[Tuple[float, float]]:
        """Análisis de respaldo cuando no está disponible la API"""
        logger.info("Usando análisis de respaldo (segmentación simple)")
        
        duration = await self._get_video_duration(video_path)
        if duration <= 0:
            return []
        
        segments = []
        max_clip_duration = settings.max_clip_duration
        min_clip_duration = settings.min_clip_duration
        
        if duration < min_clip_duration:
            return []
        
        if duration <= max_clip_duration:
            return [(0.0, duration)]
        
        # Crear segmentos con overlap para mejores transiciones
        current_time = 0.0
        segment_count = 0
        
        while current_time < duration and segment_count < 5:  # Máximo 5 clips de respaldo
            end_time = min(current_time + max_clip_duration, duration)
            
            if end_time - current_time >= min_clip_duration:
                segments.append((current_time, end_time))
                segment_count += 1
            
            current_time += max_clip_duration * 0.7  # 30% overlap
        
        return segments
    
    async def _get_video_duration(self, video_path: str) -> float:
        """Obtiene la duración del video usando FFprobe"""
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
            logger.error(f"Error obteniendo duración del video: {e}")
            return 0.0
