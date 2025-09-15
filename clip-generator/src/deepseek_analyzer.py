import os
import uuid
import logging
import asyncio
import aiohttp
import whisper
import ffmpeg
import subprocess
import json
import numpy as np
import librosa
import re
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
from config import settings

logger = logging.getLogger(__name__)

@dataclass
class ClipCandidate:
    """Estructura para candidatos de clips con metadatos avanzados"""
    start: float
    end: float
    base_score: float
    emotional_intensity: float
    speech_clarity: float
    keyword_density: float
    conversation_flow: float
    audio_energy: float
    final_score: float
    reason: str
    transcription: str
    confidence: float

class ViralContentDetector:
    """Detector avanzado de contenido viral con análisis semántico y temporal"""
    
    def __init__(self):
        # Patrones virales por categoría con pesos dinámicos
        self.viral_patterns = {
            'emociones_fuertes': {
                'patterns': [
                    r'\b(increíble|impresionante|alucinante|brutal|épico)\b',
                    r'\b(no puedo creer|no way|imposible|qué locura)\b',
                    r'\b(amor|odio|detesto|adoro|fascina)\b',
                    r'\b(perfecto|horrible|terrible|maravilloso)\b'
                ],
                'weight': 2.5
            },
            'reacciones_autenticas': {
                'patterns': [
                    r'\b(wow|guau|ostras|joder|madre mía)\b',
                    r'\b(en serio|de verdad|no me digas|qué fuerte)\b',
                    r'\b(me muero|me parto|me cago)\b',
                    r'[!]{2,}|[?]{2,}'
                ],
                'weight': 2.0
            },
            'humor_engagement': {
                'patterns': [
                    r'\b(gracioso|divertido|chistoso|cómico)\b',
                    r'\b(jajaja|jejeje|jijijij)\b',
                    r'\b(meme|viral|tendencia|trend)\b',
                    r'\b(risa|reír|carcajada)\b'
                ],
                'weight': 1.8
            },
            'contenido_controversial': {
                'patterns': [
                    r'\b(polémico|controversial|escándalo)\b',
                    r'\b(opinión|debate|discusión|problema)\b',
                    r'\b(critica|defiende|ataca|polémica)\b'
                ],
                'weight': 1.5
            },
            'urgencia_accion': {
                'patterns': [
                    r'\b(ahora|inmediatamente|urgente|rápido)\b',
                    r'\b(limitado|exclusivo|por tiempo limitado)\b',
                    r'\b(última oportunidad|no te pierdas)\b'
                ],
                'weight': 1.3
            },
            'valor_informativo': {
                'patterns': [
                    r'\b(secreto|truco|tip|consejo|hack)\b',
                    r'\b(aprende|descubre|revela|desvela)\b',
                    r'\b(método|técnica|estrategia|fórmula)\b'
                ],
                'weight': 1.2
            }
        }
        
        # Patrones anti-virales (reducen score)
        self.anti_viral_patterns = [
            r'\b(aburrido|monótono|lento|pesado)\b',
            r'\b(complicado|difícil|complejo|técnico)\b',
            r'\b(largo|extenso|detallado|exhaustivo)\b',
            r'\b(obvio|evidente|normal|típico)\b'
        ]

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
        
        # Configuración de análisis mejorada
        self.segment_duration = settings.analysis_segment_duration
        self.max_segments = settings.max_analysis_segments
        self.highlight_threshold = settings.highlight_threshold
        
        # Inicializar detector de contenido viral
        self.viral_detector = ViralContentDetector()
        
        # Configuración de calidad temporal dinámica
        self.min_clip_separation = settings.min_clip_separation_seconds  # Usar configuración
        self.optimal_clip_duration = (settings.optimal_viral_duration_min, settings.optimal_viral_duration_max)  # Rango óptimo dinámico
        self.max_clips_per_video = settings.max_clips_per_video  # Máximo dinámico
        self.absolute_min_duration = settings.absolute_min_clip_duration  # Mínimo absoluto
        self.absolute_max_duration = settings.absolute_max_clip_duration  # Máximo absoluto
        
        # Inicializar Whisper para transcripciones
        # No cargar Whisper automáticamente: usar carga perezosa en _transcribe_segment
        self.whisper_model = None
        
        os.makedirs(self.temp_dir, exist_ok=True)

    def _analyze_viral_content(self, text: str) -> Dict[str, float]:
        """Análisis avanzado de contenido viral con puntuación detallada"""
        if not text:
            return {'score': 0.0, 'confidence': 0.0, 'category_scores': {}}
        
        text_lower = text.lower()
        category_scores = {}
        total_weight = 0
        weighted_score = 0
        
        # Analizar cada categoría de contenido viral
        for category, config in self.viral_detector.viral_patterns.items():
            category_score = 0
            matches = 0
            
            for pattern in config['patterns']:
                pattern_matches = len(re.findall(pattern, text_lower))
                if pattern_matches > 0:
                    matches += pattern_matches
                    category_score += pattern_matches
            
            # Normalizar score de categoría
            if matches > 0:
                # Bonus por diversidad de patrones en la categoría
                pattern_diversity = len([p for p in config['patterns'] if re.search(p, text_lower)]) / len(config['patterns'])
                category_score = min(category_score * (1 + pattern_diversity), 5.0)
            
            category_scores[category] = category_score
            weighted_score += category_score * config['weight']
            total_weight += config['weight']
        
        # Aplicar penalizaciones por contenido anti-viral
        penalty = 0
        for anti_pattern in self.viral_detector.anti_viral_patterns:
            penalty += len(re.findall(anti_pattern, text_lower)) * 0.3
        
        # Calcular score final
        if total_weight > 0:
            base_score = weighted_score / total_weight
        else:
            base_score = 0
        
        final_score = max(0, base_score - penalty)
        
        # Calcular confianza basada en la cantidad de evidencia
        total_matches = sum(category_scores.values())
        confidence = min(total_matches / 3.0, 1.0)  # Confianza máxima con 3+ matches
        
        return {
            'score': final_score,
            'confidence': confidence,
            'category_scores': category_scores,
            'penalty': penalty
        }

    def _analyze_speech_clarity(self, transcription: str, segment_duration: float) -> float:
        """Analiza la claridad del discurso basada en la transcripción"""
        if not transcription or segment_duration <= 0:
            return 0.0
        
        words = transcription.split()
        word_count = len(words)
        
        if word_count == 0:
            return 0.0
        
        # Calcular palabras por segundo
        words_per_second = word_count / segment_duration
        
        # Rango óptimo de palabras por segundo para claridad
        optimal_wps_range = (2.0, 4.0)
        
        if optimal_wps_range[0] <= words_per_second <= optimal_wps_range[1]:
            clarity_score = 1.0
        elif words_per_second < optimal_wps_range[0]:
            # Demasiado lento
            clarity_score = words_per_second / optimal_wps_range[0]
        else:
            # Demasiado rápido
            clarity_score = optimal_wps_range[1] / words_per_second
        return float(max(0.0, min(1.0, clarity_score)))

    def _compute_candidate_duration(self, candidate: ClipCandidate, video_duration: Optional[float] = None) -> float:
        """Calcula una duración objetivo para un candidato combinando:
        - Duración sugerida por Deepseek (si está en la razón o metadata)
        - Densidad de palabras (words/sec) para evitar clips demasiado largos o cortos
        - Jitter determinista por índice para evitar duraciones idénticas
        - Respeta límites absolutos y rango óptimo
        """
        # Preferencia por duración óptima del sistema (rango)
        min_opt, max_opt = self.optimal_clip_duration

        # Intentar extraer sugerencia de duración del reason o metadata
        suggested = None
        try:
            # Buscar patrones tipo 'duración: 12s' o 'optimal_duration' si viene en metadata
            m = re.search(r'(\b\d+(?:\.\d+)?)(?:s|sec|secs)?', candidate.reason or '')
            if m:
                suggested = float(m.group(1))
        except Exception:
            suggested = None

        # Calcular words/sec a partir de la transcripción
        words = (candidate.transcription or '').split()
        word_count = max(0, len(words))
        cand_duration_est = (candidate.end - candidate.start) if (candidate.end > candidate.start) else None

        words_per_second = None
        if cand_duration_est and cand_duration_est > 0:
            words_per_second = word_count / cand_duration_est

        # Base duration heuristic
        if suggested:
            target = suggested
        elif words_per_second and words_per_second > 0:
            # Ajustar la duración para que la densidad caiga en un rango óptimo (2-4 wps)
            optimal_wps = 3.0
            target = max(min_opt, min(max_opt, (word_count / optimal_wps) if word_count > 0 else min_opt))
        elif cand_duration_est:
            target = cand_duration_est
        else:
            target = (min_opt + max_opt) / 2.0

        # Aplicar jitter determinista basado en start para reproducibilidad
        jitter = (hash((round(candidate.start, 3), round(candidate.end, 3))) % 11 - 5) / 100.0  # +-0.05 ajuste
        target = target * (1.0 + jitter)

        # Clamp final
        target = max(self.absolute_min_duration, min(self.absolute_max_duration, target))

        # No exceder duración total del video
        if video_duration:
            target = min(target, video_duration)

        return float(target)
        
        # Bonus por diversidad de vocabulario
        unique_words = len(set(word.lower() for word in words))
        vocabulary_diversity = unique_words / word_count if word_count > 0 else 0
        
        # Ajustar por diversidad (máximo 20% de bonus)
        final_score = min(clarity_score * (1 + vocabulary_diversity * 0.2), 1.0)
        
        return final_score

    def _analyze_conversation_flow(self, transcription: str) -> float:
        """Analiza el flujo conversacional para engagement"""
        if not transcription:
            return 0.0
        
        text_lower = transcription.lower()
        flow_score = 0.0
        
        # Patrones de buen flujo conversacional
        flow_patterns = [
            r'\b(pero|sin embargo|aunque|además|también)\b',  # Conectores
            r'\b(entonces|por eso|así que|por tanto)\b',  # Causa-efecto
            r'\b(primero|segundo|después|finalmente)\b',  # Secuencia
            r'\b(por ejemplo|es decir|o sea|vamos)\b',  # Explicación
            r'[?]',  # Preguntas (engagement)
            r'\b(mira|fíjate|imagínate|piensa)\b'  # Llamadas de atención
        ]
        
        pattern_count = 0
        for pattern in flow_patterns:
            matches = len(re.findall(pattern, text_lower))
            pattern_count += matches
        
        # Normalizar por longitud del texto
        words = len(transcription.split())
        if words > 0:
            flow_density = pattern_count / words
            flow_score = min(flow_density * 20, 1.0)  # Escalar apropiadamente
        
        return flow_score

    def _calculate_advanced_score(self, clip_candidate: ClipCandidate) -> float:
        """Calcula puntuación final avanzada con múltiples factores"""
        
        # Pesos para cada factor
        weights = {
            'base_score': 0.35,
            'emotional_intensity': 0.25,
            'speech_clarity': 0.15,
            'conversation_flow': 0.15,
            'duration_optimality': 0.10
        }
        
        # Calcular optimalidad de duración
        duration = clip_candidate.end - clip_candidate.start
        optimal_min, optimal_max = self.optimal_clip_duration
        
        if optimal_min <= duration <= optimal_max:
            duration_score = 1.0
        elif duration < optimal_min:
            duration_score = duration / optimal_min
        else:
            duration_score = optimal_max / duration
        
        # Combinar todos los factores
        final_score = (
            clip_candidate.base_score * weights['base_score'] +
            clip_candidate.emotional_intensity * weights['emotional_intensity'] +
            clip_candidate.speech_clarity * weights['speech_clarity'] +
            clip_candidate.conversation_flow * weights['conversation_flow'] +
            duration_score * weights['duration_optimality']
        )
        
        # Aplicar bonus por confianza alta
        confidence_bonus = 1.0 + (clip_candidate.confidence * 0.2)
        final_score *= confidence_bonus
        
        return min(final_score, 1.0)

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

            logger.info(f"Transcripciones totales recogidas: {len(segment_transcriptions)} de {len(segments)} segmentos")
            
            # 4. Analizar con Deepseek
            highlights = await self._analyze_with_deepseek(segment_transcriptions)
            
            # 5. Convertir a clips válidos y filtrar solapamientos
            valid_clips = self._convert_to_clips(highlights)
            
            logger.info(f"Análisis completado: {len(valid_clips)} clips identificados")
            return valid_clips
            
        except Exception as e:
            logger.error(f"Error en análisis de video: {e}")
            return await self._fallback_analysis(video_path)
    
    def _create_analysis_segments(self, duration: float) -> List[Tuple[float, float]]:
        """Crea segmentos para análisis del video completo"""
        segments: List[Tuple[float, float]] = []

        # Si se fuerza cobertura completa, generamos segmentos contiguos hasta un tope seguro
        if getattr(settings, 'force_full_coverage', False):
            max_safe_segments = min(self.max_segments, 300)  # tope de seguridad
            estimated_segments = int((duration + self.segment_duration - 1) // self.segment_duration)
            if estimated_segments > max_safe_segments:
                logger.warning(f"FORCE_FULL_COVERAGE activo pero el número de segmentos ({estimated_segments}) excede el tope seguro ({max_safe_segments}). Se usarán {max_safe_segments} segmentos distribuidos uniformemente.")
                # distribuir max_safe_segments a lo largo del video
                step = duration / max_safe_segments
                for i in range(max_safe_segments):
                    start = max(0.0, i * step)
                    end = min(duration, start + self.segment_duration)
                    if end - start >= 0.01:
                        segments.append((start, end))
                return segments
            # si está dentro del tope, hacer segmentos contiguos
            current_time = 0.0
            while current_time < duration and len(segments) < estimated_segments:
                end_time = min(current_time + self.segment_duration, duration)
                segments.append((current_time, end_time))
                current_time += self.segment_duration
            return segments

        # Comportamiento por defecto: si el video cabe en max_segments se hacen contiguos
        if duration <= self.segment_duration * self.max_segments:
            current_time = 0.0
            while current_time < duration and len(segments) < self.max_segments:
                end_time = min(current_time + self.segment_duration, duration)
                segments.append((current_time, end_time))
                current_time += self.segment_duration
            return segments

        # Si el video es mucho más largo que el número máximo de segmentos,
        # distribuimos `max_segments` ventanas a lo largo de todo el video para cubrir todas las partes.
        total_slots = self.max_segments
        step = duration / total_slots
        for i in range(total_slots):
            start = max(0.0, i * step)
            end = min(duration, start + self.segment_duration)
            if end - start < 0.01:
                continue
            segments.append((start, end))

        return segments

    def _compute_backup_segment_duration(self, position: float, index: int, total: int, min_d: float, max_d: float) -> float:
        """Calcula una duración inteligente para clips de respaldo.

        - `position`: posición relativa en el video (0..1)
        - `index`: índice del clip (0..total-1)
        - `total`: número total de clips
        - `min_d`, `max_d`: límites absolutos

        La lógica busca:
        - Clips del principio y final más cortos (gancho / cierre)
        - Clips centrales más largos (más contexto)
        - Añadir una pequeña variación (jitter) dependiente del índice para evitar duraciones idénticas
        - Respetar `absolute_min_duration` y `absolute_max_duration`
        """
        # Peso base según distancia al centro (0..1)
        center_distance = abs(0.5 - position)

        # Más cerca del centro -> más largo. Invertir y normalizar.
        center_influence = 1.0 - (center_distance * 2.0)  # 1 en centro, 0 en extremos
        center_influence = max(0.0, min(1.0, center_influence))

        # Base duration interpolada entre min_d y max_d
        base_duration = min_d + (max_d - min_d) * (0.2 + 0.8 * center_influence)

        # Reducir levemente primer/último clip para gancho/cierre
        edge_factor = 1.0
        if index == 0 or index == total - 1:
            edge_factor = 0.65
        elif index == 1 or index == total - 2:
            edge_factor = 0.85

        duration = base_duration * edge_factor

        # Añadir jitter determinístico pequeño basado en índice (para reproducibilidad)
        jitter = (self._deterministic_jitter(index) - 0.5) * 0.15 * duration
        duration += jitter

        # Respetar límites absolutos configurados
        duration = max(duration, self.absolute_min_duration, min_d)
        duration = min(duration, self.absolute_max_duration, max_d)

        return float(duration)

    def _deterministic_jitter(self, index: int) -> float:
        """Genera un valor pseudoaleatorio determinístico 0..1 a partir del índice."""
        # Simple LCG para reproducibilidad
        a = 1664525
        c = 1013904223
        m = 2 ** 32
        seed = (index + 1) * 9781
        val = (a * seed + c) % m
        return (val / m)

    def _parse_time_to_seconds(self, value: Any) -> Optional[float]:
        """Parsea distintos formatos de tiempo a segundos.

        Acepta números (int/float), cadenas como 'mm:ss' o 'hh:mm:ss' o '123.5'.
        Devuelve None si no puede parsear.
        """
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                v = value.strip()
                # Formato hh:mm:ss o mm:ss
                parts = v.split(":")
                if len(parts) == 3:
                    h, m, s = parts
                    return float(h) * 3600 + float(m) * 60 + float(s)
                if len(parts) == 2:
                    m, s = parts
                    return float(m) * 60 + float(s)
                # Simple número en string
                return float(v)
        except Exception:
            return None

    def _clamp(self, val: float, low: float, high: float) -> float:
        return max(low, min(high, val))

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """Extrae el primer objeto JSON válido de un texto que puede contener markdown u otros wrappers.

        Devuelve la substring con JSON o None si no encuentra.
        """
        if not text:
            return None
        # Intento simple: buscar primer '{' y último '}'
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end+1]
            return candidate

        # Eliminar bloques de código Markdown y buscar de nuevo
        cleaned = re.sub(r'```[\s\S]*?```', '', text)
        cleaned = cleaned.strip()
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1 and end > start:
            return cleaned[start:end+1]

        return None
    
    async def _transcribe_segment(self, video_path: str, start_time: float, end_time: float) -> Optional[str]:
        """Transcribe un segmento específico del video"""
        # Lazy-load modelo Whisper si está configurado para cargarse en inicio o si no está aún cargado
        if not self.whisper_model:
            try:
                if settings.whisper_load_on_start or True:
                    model_name = getattr(settings, 'whisper_model_name', 'base')
                    logger.info(f"Cargando modelo Whisper '{model_name}' para transcripción (lazy-load)")
                    self.whisper_model = whisper.load_model(model_name)
                    logger.info("Modelo Whisper cargado correctamente (lazy)")
            except Exception as e:
                logger.error(f"Error cargando modelo Whisper: {e}")
                self.whisper_model = None
        if not self.whisper_model:
            logger.warning("Modelo Whisper no disponible tras intento de carga")
            return None
        
        try:
            # Extraer audio del segmento
            segment_id = str(uuid.uuid4())[:8]
            audio_path = os.path.join(self.temp_dir, f"audio_segment_{segment_id}.wav")
            
            logger.info(f"Extrayendo audio del segmento {start_time:.1f}s - {end_time:.1f}s")
            
            # Usar ffmpeg para extraer el audio del segmento
            try:
                try:
                    (
                        ffmpeg
                        .input(video_path, ss=start_time, t=end_time - start_time)
                        .output(audio_path, acodec='pcm_s16le', ac=1, ar='16000')
                        .overwrite_output()
                        .run(quiet=True)
                    )
                except Exception as e:
                    # Fallback robusto: intentar invocar ffmpeg directamente por subprocess
                    logger.warning(f"ffmpeg-python falló ({e}), intentando fallback con subprocess")
                    cmd = [
                        'ffmpeg',
                        '-y',
                        '-ss', str(start_time),
                        '-t', str(end_time - start_time),
                        '-i', video_path,
                        '-acodec', 'pcm_s16le',
                        '-ac', '1',
                        '-ar', '16000',
                        audio_path
                    ]
                    try:
                        completed = subprocess.run(cmd, check=True, capture_output=True, timeout=30)
                        if completed.returncode != 0:
                            logger.error(f"FFmpeg returned non-zero code: {completed.returncode} - {completed.stderr.decode(errors='ignore')}" )
                    except subprocess.TimeoutExpired as te:
                        logger.error(f"FFmpeg timeout al extraer segmento: {te}")
                    except subprocess.CalledProcessError as ce:
                        stderr = ce.stderr.decode(errors='ignore') if ce.stderr else str(ce)
                        logger.error(f"FFmpeg error en subprocess: {stderr}")
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
            
            prompt = f"""Eres un experto en identificar contenido VIRAL en redes sociales. Analiza estas transcripciones y selecciona TODOS los momentos con potencial viral real.

TRANSCRIPCIONES:
{transcription_text}

CRITERIOS VIRALES FLEXIBLES (Score mínimo 0.65):
🔥 EMOCIONES INTENSAS: Reacciones auténticas, sorpresas, risas explosivas
💬 FRASES MEMORABLES: Citas pegajosas, declaraciones polémicas apropiadas
⚡ MOMENTOS CLIMÁTICOS: Puntos de tensión, revelaciones, plot twists
🎯 VALOR ÚNICO: Información exclusiva, secretos, trucos desconocidos
💡 ENGAGEMENT NATURAL: Preguntas directas, llamadas a la acción implícitas
🔄 POTENCIAL SHARE: Contenido que la gente querría compartir inmediatamente

EVITAR ABSOLUTAMENTE:
❌ Explicaciones largas sin gancho emocional
❌ Momentos de transición o relleno sin valor
❌ Contenido técnico sin emoción
❌ Repeticiones o información redundante
❌ Momentos monótonos o de baja energía

REGLAS TEMPORALES DINÁMICAS:
- Duración COMPLETAMENTE FLEXIBLE: 15 segundos - 3 minutos según el contenido
- Clips cortos (15-30s): Para momentos de máximo impacto, reacciones explosivas
- Clips medianos (30-90s): Para historias completas, explicaciones valiosas
- MÍNIMO 1 MINUTO de separación entre clips
- SIN LÍMITE FIJO de clips - encuentra TODOS los momentos virales
- La duración debe ajustarse PERFECTAMENTE al contenido
- Priorizar CALIDAD y COMPLETITUD sobre restricciones arbitrarias

DISTRIBUCIÓN INTELIGENTE:
- Analiza TODO el video completo
- Identifica CADA momento con potencial viral
- No te limites a un número específico de clips
- Distribuye clips a lo largo del video según el contenido
- Si hay 10 momentos virales, devuelve 10 clips
- Si hay 2 momentos virales, devuelve 2 clips

INSTRUCCIONES ESPECÍFICAS:
1. Lee TODA la transcripción antes de decidir
2. Identifica TODOS los momentos que harían que alguien pause el scroll
3. Ajusta la duración EXACTA necesaria para cada momento
4. Incluye contexto suficiente para entender completamente el momento
5. Los tiempos deben ser EXACTOS del video completo
6. No te autolimites - encuentra todos los clips valiosos

FORMATO DE RESPUESTA (JSON ESTRICTO):
{{
    "highlights": [
        {{
            "segment_index": 0,
            "score": 0.85,
            "reason": "Reacción explosiva inesperada que genera engagement inmediato",
            "start_time": 125.5,
            "end_time": 165.2,
            "optimal_duration": 39.7,
            "viral_category": "emotional_reaction",
            "engagement_prediction": "high_share_potential",
            "duration_rationale": "Duración ajustada para capturar toda la reacción y contexto"
        }}
    ]
}}

NOTA CRÍTICA: NO te limites por números artificiales. Si encuentras 8 momentos virales, devuelve 8 clips. Si encuentras 15, devuelve 15. La duración debe ser la ÓPTIMA para cada momento específico."""
            
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

                        # Parsear la respuesta JSON robustamente
                        try:
                            json_text = self._extract_json_from_text(content)
                            if json_text is None:
                                raise json.JSONDecodeError('No JSON found', content, 0)
                            analysis_result = json.loads(json_text)
                            highlights = analysis_result.get("highlights", [])

                            logger.info(f"Deepseek parseó {len(highlights)} highlights candidatos")

                            # Calcular duración aproximada del video a partir de segmentos (fallback)
                            if segment_transcriptions:
                                video_duration = max(seg.get('end', 0) for seg in segment_transcriptions)
                            else:
                                video_duration = 0.0

                            # Mapear índices de segmento a tiempos reales
                            mapped_highlights = []
                            for i, highlight in enumerate(highlights):
                                segment_idx = highlight.get("segment_index", 0)
                                if segment_idx < len(segment_transcriptions):
                                    segment = segment_transcriptions[segment_idx]

                                    # Intentar parsear distintos formatos que pueda devolver Deepseek
                                    raw_start = highlight.get("start_time")
                                    raw_end = highlight.get("end_time")
                                    raw_duration = highlight.get("duration") or highlight.get("optimal_duration")

                                    parsed_start = self._parse_time_to_seconds(raw_start)
                                    parsed_end = self._parse_time_to_seconds(raw_end)
                                    parsed_duration = self._parse_time_to_seconds(raw_duration)

                                    # Si ambos tiempos están presentes y válidos, úsalos
                                    if parsed_start is not None and parsed_end is not None:
                                        final_start = parsed_start
                                        final_end = parsed_end
                                        logger.info(f"Highlight {i+1}: Usando tiempos específicos de Deepseek: {final_start:.2f}s - {final_end:.2f}s")
                                    else:
                                        # Si hay sólo duración, centrarla en el segmento
                                        if parsed_duration is not None:
                                            center_seg = (segment["start"] + segment["end"]) / 2
                                            final_start = center_seg - parsed_duration / 2
                                            final_end = center_seg + parsed_duration / 2
                                            logger.info(f"Highlight {i+1}: Usando duration proporcionada: {parsed_duration:.1f}s -> {final_start:.2f}s - {final_end:.2f}s")
                                        else:
                                            # Fallback al segmento completo, con intento de ajustar al texto (si Deepseek indica offsets relativos)
                                            final_start = segment["start"]
                                            final_end = segment["end"]
                                            # Intento: si start_time es string tipo '00:01:23' relativo al segmento, convertir sumando
                                            if isinstance(raw_start, str) and ":" in raw_start:
                                                rel = self._parse_time_to_seconds(raw_start)
                                                if rel is not None and rel < (segment["end"] - segment["start"]):
                                                    final_start = segment["start"] + rel
                                            if isinstance(raw_end, str) and ":" in raw_end:
                                                rel = self._parse_time_to_seconds(raw_end)
                                                if rel is not None and rel <= (segment["end"] - segment["start"]):
                                                    final_end = segment["start"] + rel
                                            logger.info(f"Highlight {i+1}: Usando tiempos del segmento como fallback: {final_start:.2f}s - {final_end:.2f}s")

                                    # Clamp dentro del video
                                    final_start = self._clamp(final_start, 0.0, video_duration)
                                    final_end = self._clamp(final_end, 0.0, video_duration)

                                    # Si end <= start, expandir ligeramente alrededor del segmento
                                    if final_end <= final_start:
                                        final_start = max(0.0, segment["start"]) 
                                        final_end = min(video_duration, segment["end"]) 

                                    # Asegurar duración mínima
                                    if final_end - final_start < self.absolute_min_duration:
                                        add = (self.absolute_min_duration - (final_end - final_start)) / 2
                                        final_start = max(0.0, final_start - add)
                                        final_end = min(video_duration, final_end + add)

                                    mapped_highlights.append({
                                        "start": float(final_start),
                                        "end": float(final_end),
                                        "score": float(highlight.get("score", 0.5)),
                                        "reason": highlight.get("reason", "Momento destacado identificado por IA"),
                                        "transcription": segment.get("transcription", "")
                                    })

                            # Filtrar clips solapados o muy cercanos
                            filtered_highlights = self._filter_overlapping_clips(mapped_highlights)
                            logger.info(f"Deepseek identificó {len(mapped_highlights)} highlights, filtrados a {len(filtered_highlights)} clips válidos")
                            return filtered_highlights

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
    
    def _filter_overlapping_clips(self, highlights: List[Dict]) -> List[Dict]:
        """
        Filtrado avanzado de clips con algoritmo de optimización viral.
        Usa programación dinámica para seleccionar la mejor combinación.
        """
        if not highlights:
            return []
        
        logger.info(f"Iniciando filtrado avanzado de {len(highlights)} clips candidatos")
        
        # Convertir a ClipCandidates con análisis completo y generar candidatos alternativos
        candidates: List[ClipCandidate] = []
        for highlight in highlights:
            start = float(highlight["start"])
            end = float(highlight["end"])
            transcription = highlight.get("transcription", "") or ""
            base_score = float(highlight.get("score", 0.5))

            # Análisis viral avanzado
            viral_analysis = self._analyze_viral_content(transcription)
            emotional_intensity = viral_analysis['score']
            confidence = viral_analysis['confidence']

            # Análisis de claridad del habla
            duration = max(0.01, end - start)
            speech_clarity = self._analyze_speech_clarity(transcription, duration)

            # Análisis de flujo conversacional
            conversation_flow = self._analyze_conversation_flow(transcription)

            # Keyword density (palabras por segundo)
            keyword_density = len(transcription.split()) / duration if duration > 0 else 0.0

            # Audio energy placeholder (puede estimarse via librosa si se dispone del audio)
            audio_energy = 0.5

            # Crear candidato principal
            candidate = ClipCandidate(
                start=start,
                end=end,
                base_score=base_score,
                emotional_intensity=emotional_intensity,
                speech_clarity=speech_clarity,
                keyword_density=keyword_density,
                conversation_flow=conversation_flow,
                audio_energy=audio_energy,
                final_score=0.0,
                reason=highlight.get("reason", "Momento destacado"),
                transcription=transcription,
                confidence=confidence
            )

            # Calcular score final avanzado
            candidate.final_score = self._calculate_advanced_score(candidate)
            candidates.append(candidate)

            # Generar variantes: usar la heurística de duration y añadir pequeñas variaciones deterministas
            base_target = self._compute_candidate_duration(candidate)
            # Variantes: extendida (contexto), compacta (gancho) y original ajustada
            variant_factors = [1.25, 0.85, 1.0]
            for factor in variant_factors:
                target = max(self.absolute_min_duration, min(self.absolute_max_duration, base_target * factor))
                # determinista pequeño offset para evitar duraciones idénticas
                offset = ((hash((round(start,2), round(target,2), int(factor*100))) % 9) - 4) / 100.0
                target = max(self.absolute_min_duration, target * (1.0 + offset))
                center = (start + end) / 2.0
                s = max(0.0, center - target / 2.0)
                e = s + target
                if e - s >= self.absolute_min_duration:
                    var_candidate = ClipCandidate(
                        start=s,
                        end=e,
                        base_score=base_score * (0.98 if factor==1.0 else 0.95),
                        emotional_intensity=emotional_intensity,
                        speech_clarity=speech_clarity,
                        keyword_density=keyword_density,
                        conversation_flow=conversation_flow,
                        audio_energy=audio_energy,
                        final_score=0.0,
                        reason=f"{highlight.get('reason', 'Momento')} (variante)",
                        transcription=transcription,
                        confidence=confidence
                    )
                    var_candidate.final_score = self._calculate_advanced_score(var_candidate)
                    candidates.append(var_candidate)
        
        # Aplicar algoritmo de selección óptima
        optimal_clips = self._select_optimal_clips(candidates)
        
        # Convertir de vuelta a diccionarios
        result_clips = []
        for candidate in optimal_clips:
            result_clips.append({
                "start": candidate.start,
                "end": candidate.end,
                "score": candidate.final_score,
                "reason": f"{candidate.reason} (Score: {candidate.final_score:.3f}, Confianza: {candidate.confidence:.3f})",
                "transcription": getattr(candidate, 'transcription', ''),
                "metadata": {
                    "emotional_intensity": candidate.emotional_intensity,
                    "speech_clarity": candidate.speech_clarity,
                    "conversation_flow": candidate.conversation_flow,
                    "confidence": candidate.confidence
                }
            })
        
        logger.info(f"Filtrado completado: {len(result_clips)} clips seleccionados de {len(candidates)} candidatos")
        return result_clips

    def _select_optimal_clips(self, candidates: List[ClipCandidate]) -> List[ClipCandidate]:
        """
        Selección óptima de clips usando algoritmo de programación dinámica
        que maximiza el score total mientras respeta las restricciones temporales.
        """
        if not candidates:
            return []
        
        # Ordenar candidatos por tiempo de inicio
        candidates.sort(key=lambda x: x.start)
        
        # Filtrar candidatos por score mínimo pero permitir mayor número basándonos en cantidad de candidatos
        min_viral_score = settings.viral_score_threshold  # umbral base configurable
        viral_candidates = [c for c in candidates if c.final_score >= min_viral_score]

        logger.info(f"Candidatos virales (score >= {min_viral_score}): {len(viral_candidates)} de {len(candidates)}")

        # Si no hay candidatos que cumplan el umbral, relajar progresivamente
        if not viral_candidates:
            relaxed_thresholds = [0.55, 0.5, 0.45, 0.4, 0.35]
            for threshold in relaxed_thresholds:
                viral_candidates = [c for c in candidates if c.final_score >= threshold]
                if viral_candidates:
                    logger.info(f"Se encontraron candidatos con threshold relajado: {threshold} -> {len(viral_candidates)}")
                    break

        # Si aún no hay ninguno, tomar los N mejores (N mayor para generar más clips)
        if not viral_candidates:
            candidates_sorted = sorted(candidates, key=lambda x: x.final_score, reverse=True)
            max_fallback_clips = min(max(5, int(len(candidates) * 0.5)), len(candidates))
            logger.info(f"Sin candidatos virales, tomando los {max_fallback_clips} mejores clips disponibles (fallback)")
            return candidates_sorted[:max_fallback_clips]
        
        # Aplicar algoritmo de selección con restricciones temporales dinámicas
        n = len(viral_candidates)
        if n == 1:
            return viral_candidates

        # Usar límite dinámico de clips basado en número de candidatos detectados
        # Queremos permitir tantos clips virales como se hayan encontrado, hasta un tope razonable
        dynamic_limit = min(self.max_clips_per_video, max(5, n))
        max_clips_allowed = min(dynamic_limit, n)

        # Crear matriz de compatibilidad temporal
        compatible = [[False] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                clip1, clip2 = viral_candidates[i], viral_candidates[j]
                # Calcular solapamiento real
                latest_start = max(clip1.start, clip2.start)
                earliest_end = min(clip1.end, clip2.end)
                overlap = max(0.0, earliest_end - latest_start)
                # Solapamiento relativo sobre la duración mayor
                max_duration = max(clip1.end - clip1.start, clip2.end - clip2.start, 1e-6)
                overlap_ratio = overlap / max_duration
                # Similitud textual
                sim = self._text_similarity(getattr(clip1, 'transcription', ''), getattr(clip2, 'transcription', ''))
                # Si son muy similares, requerir menos solapamiento permitido, si no, ser más permisivo
                sim_threshold = 0.6
                if sim >= sim_threshold:
                    allowed_overlap = 0.35
                else:
                    allowed_overlap = 0.5
                # Considerar compatibles si el overlap es pequeño y la separación minima se respeta
                separation_ok = (clip2.start - clip1.end) >= self.min_clip_separation or (clip1.start - clip2.end) >= self.min_clip_separation
                if overlap_ratio <= allowed_overlap or separation_ok:
                    compatible[i][j] = compatible[j][i] = True
                else:
                    compatible[i][j] = compatible[j][i] = False
        
        # Selección greedy primero: priorizar incluir tantos clips virales como sea posible
        selected_clips = []
        # Ordenar por score desc para intentar tomar los momentos más fuertes primero
        for clip in sorted(viral_candidates, key=lambda x: x.final_score, reverse=True):
            # Verificar que no solape excesivamente con clips ya seleccionados
            overlaps = any(max(0.0, min(c.end, clip.end) - max(c.start, clip.start)) / max(1e-6, max(c.end - c.start, clip.end - clip.start)) > 0.6 for c in selected_clips)
            separation_ok = all(abs(clip.start - c.end) >= self.min_clip_separation and abs(c.start - clip.end) >= self.min_clip_separation for c in selected_clips)
            if not overlaps or separation_ok:
                selected_clips.append(clip)
            if len(selected_clips) >= max_clips_allowed:
                break

        # Si la selección greedy no devolvió suficientes clips y n>1, usar DP para obtener una alternativa
        if len(selected_clips) < max_clips_allowed and n > 1:
            dp_selected = self._dp_optimal_selection(viral_candidates, compatible, max_clips_allowed)
            dp_score = sum(c.final_score for c in dp_selected)
            greedy_score = sum(c.final_score for c in selected_clips)
            if dp_score > greedy_score:
                selected_clips = dp_selected

        logger.info(f"Clips seleccionados: {len(selected_clips)} de {n} candidatos (max allowed {max_clips_allowed})")
        # Ordenar por tiempo para resultado final
        selected_clips.sort(key=lambda x: x.start)
        return selected_clips

    def _dp_optimal_selection(self, candidates: List[ClipCandidate], compatible: List[List[bool]], max_clips: int) -> List[ClipCandidate]:
        """Algoritmo de programación dinámica para selección óptima con límite dinámico"""
        n = len(candidates)
        if n == 0:
            return []
        
        # Usar límite dinámico pero con flexibilidad
        max_clips_dynamic = min(max_clips, n)
        
        # dp[i][k] = (score_máximo, clips_seleccionados) usando hasta el clip i con k clips
        dp = [[(0.0, []) for _ in range(max_clips_dynamic + 1)] for _ in range(n)]

        # Inicialización para el primer elemento
        for k in range(max_clips_dynamic + 1):
            if k == 1:
                dp[0][k] = (candidates[0].final_score, [candidates[0]])
            else:
                dp[0][k] = (0.0, [])
        
        # Llenar tabla DP
        for i in range(1, n):
            current_candidate = candidates[i]
            
            for k in range(max_clips_dynamic + 1):
                # Opción 1: No tomar el clip actual
                dp[i][k] = dp[i-1][k]
                
                # Opción 2: Tomar el clip actual
                if k > 0:
                    # Tomar clip actual solo
                    if k == 1:
                        if current_candidate.final_score > dp[i][k][0]:
                            dp[i][k] = (current_candidate.final_score, [current_candidate])
                    else:
                        # Buscar el mejor clip compatible anterior considerando diversidad textual
                        best_score = 0.0
                        best_combination = []

                        for j in range(i):
                            if compatible[j][i] and dp[j][k-1][0] > 0:
                                prev_score, prev_list = dp[j][k-1]
                                # Penalizar similitud entre current_candidate y cada clip en prev_list
                                sim_penalty = 0.0
                                unique_tokens = set()
                                for pc in prev_list:
                                    s = self._text_similarity(getattr(pc, 'transcription', ''), getattr(current_candidate, 'transcription', ''))
                                    sim_penalty += s
                                    unique_tokens.update([w.lower() for w in getattr(pc, 'transcription', '').split() if w.strip()])

                                # Calcular diversity bonus proporcional a tokens únicos nuevos
                                current_tokens = set([w.lower() for w in getattr(current_candidate, 'transcription', '').split() if w.strip()])
                                new_tokens = current_tokens - unique_tokens
                                diversity_bonus = min(0.2, len(new_tokens) / max(1, len(current_tokens))) if current_tokens else 0.0

                                combined_score = prev_score + current_candidate.final_score - (sim_penalty * 0.15) + diversity_bonus
                                if combined_score > best_score:
                                    best_score = combined_score
                                    # create a new list to avoid shared references
                                    best_combination = list(prev_list) + [current_candidate]

                        if best_score > dp[i][k][0]:
                            dp[i][k] = (best_score, best_combination)
        
        # Encontrar la mejor solución
        best_score = 0.0
        best_clips = []
        
        for i in range(n):
            for k in range(1, max_clips_dynamic + 1):
                if dp[i][k][0] > best_score:
                    best_score = dp[i][k][0]
                    best_clips = dp[i][k][1]
        
        logger.info(f"Algoritmo DP seleccionó {len(best_clips)} clips con score total: {best_score:.3f}")
        return best_clips

    def _text_similarity(self, a: str, b: str) -> float:
        """Simple similitud Jaccard basada en tokens de palabras (0..1)."""
        if not a or not b:
            return 0.0
        sa = set([w.strip('.,!?;:()"\'').lower() for w in a.split() if w.strip()])
        sb = set([w.strip('.,!?;:()"\'').lower() for w in b.split() if w.strip()])
        if not sa or not sb:
            return 0.0
        inter = sa.intersection(sb)
        union = sa.union(sb)
        return float(len(inter) / len(union))
    
    def _validate_viral_potential(self, clips: List[Dict]) -> List[Dict]:
        """
        Validación flexible para asegurar que los clips tengan potencial viral.
        """
        if not clips:
            return clips
        
        viral_clips = []
        for clip in clips:
            score = clip.get("score", 0)
            reason = clip.get("reason", "")
            duration = clip["end"] - clip["start"]
            
            # Criterios de validación más flexibles
            is_viral_worthy = (
                score >= settings.viral_score_threshold and  # Score mínimo configurable
                self.absolute_min_duration <= duration <= self.absolute_max_duration and  # Duración flexible
                len(reason) > 5  # Razón descriptiva mínima
            )
            
            if is_viral_worthy:
                viral_clips.append(clip)
                logger.info(f"Clip validado como viral: {clip['start']:.1f}s-{clip['end']:.1f}s "
                           f"(duración: {duration:.1f}s, score: {score:.2f})")
            else:
                logger.info(f"Clip descartado en validación: {clip['start']:.1f}s-{clip['end']:.1f}s "
                           f"(duración: {duration:.1f}s, score: {score:.2f}) - "
                           f"Razones: score < {settings.viral_score_threshold}, "
                           f"duración fuera de rango [{self.absolute_min_duration}-{self.absolute_max_duration}]")
        
        logger.info(f"Validación completada: {len(viral_clips)} clips virales de {len(clips)} candidatos")
        return viral_clips
    
    def _convert_to_clips_with_metadata(self, highlights: List[Dict], video_duration: float) -> List[Dict[str, Any]]:
        """Convierte highlights a clips válidos con metadatos completos y duración dinámica"""
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
            
            # Usar duración dinámica basada en el análisis de Deepseek
            optimal_duration = highlight.get("optimal_duration")
            if optimal_duration:
                # Si Deepseek especifica una duración óptima, usarla
                target_duration = float(optimal_duration)
                logger.info(f"Usando duración óptima de Deepseek: {target_duration:.1f}s")
                
                # Ajustar tiempos manteniendo el centro del momento
                center_time = (start + end) / 2
                new_start = max(0, center_time - target_duration / 2)
                new_end = min(video_duration, center_time + target_duration / 2)
                
                # Verificar que no exceda los límites del video
                if new_end - new_start < target_duration:
                    # Ajustar hacia atrás si es necesario
                    if new_end == video_duration:
                        new_start = max(0, video_duration - target_duration)
                    else:
                        new_end = min(video_duration, new_start + target_duration)
                
                start = new_start
                end = new_end
                duration = end - start
                # Aplicar jitter determinista leve a la duración para diversidad entre clips
                jitter = (self._deterministic_jitter(int(start*1000)) - 0.5) * 0.08  # +-8%
                duration = max(self.absolute_min_duration, min(self.absolute_max_duration, duration * (1.0 + jitter)))
                # Recalcular start/end manteniendo el centro
                start = max(0, center_time - duration / 2)
                end = min(video_duration, start + duration)
            else:
                # Calcular una duración objetivo usando heurística basada en transcripción y metadata
                fake_candidate = ClipCandidate(
                    start=start,
                    end=end,
                    base_score=score,
                    emotional_intensity=0.0,
                    speech_clarity=0.0,
                    keyword_density=0.0,
                    conversation_flow=0.0,
                    audio_energy=0.0,
                    final_score=score,
                    reason=reason,
                    transcription=highlight.get('transcription', ''),
                    confidence=0.5
                )

                target_duration = self._compute_candidate_duration(fake_candidate, video_duration=video_duration)
                # Ajustar el clip manteniendo el centro del momento
                center = (start + end) / 2.0
                # Aplicar pequeñas variantes deterministas para generar múltiples opciones
                base_target = target_duration
                variants = [0.85, 1.0, 1.25]
                chosen_variant = variants[int(abs(hash((start, end))) % len(variants))]
                target_duration = max(self.absolute_min_duration, min(self.absolute_max_duration, base_target * chosen_variant))
                start = max(0, center - target_duration / 2)
                end = min(video_duration, center + target_duration / 2)
                duration = end - start
                logger.info(f"Clip ajustado dinámicamente: {start:.1f}s - {end:.1f}s (duración objetivo: {target_duration:.1f}s)")
            
            clip_data = {
                "start": start,
                "end": end,
                "score": score,
                "reason": reason,
                "duration": duration,
                "duration_rationale": highlight.get("duration_rationale", "Duración ajustada automáticamente")
            }
            clips.append(clip_data)
            
            logger.info(f"Clip con metadatos dinámicos: {start:.2f}s - {end:.2f}s "
                       f"(duración: {duration:.1f}s, score: {score:.2f})")
        
        return clips

    def _convert_to_clips(self, highlights: List[Dict]) -> List[Tuple[float, float]]:
        """Convierte highlights a clips válidos con duraciones apropiadas y dinámicas"""
        clips = []
        
        for highlight in highlights:
            start = float(highlight.get("start", 0))
            end = float(highlight.get("end", 0))
            duration = end - start
            
            # Validar que el clip tenga sentido
            if duration <= 0:
                continue
            
            # Usar duración dinámica basada en análisis de Deepseek
            optimal_duration = highlight.get("optimal_duration")
            if optimal_duration:
                # Si Deepseek especifica una duración óptima, respetarla
                target_duration = float(optimal_duration)
                center_time = (start + end) / 2
                start = max(0, center_time - target_duration / 2)
                end = center_time + target_duration / 2
                duration = end - start
                # Añadir pequeña variación determinista por clip
                jitter = (self._deterministic_jitter(int(start*1000)) - 0.5) * 0.08
                duration = max(self.absolute_min_duration, min(self.absolute_max_duration, duration * (1.0 + jitter)))
                start = max(0, center_time - duration / 2)
                end = min(end, start + duration)
                logger.info(f"Aplicando duración óptima de Deepseek: {target_duration:.1f}s (ajustada a {duration:.1f}s)")
            else:
                # Ajustar duración si es necesario con límites absolutos
                if duration < self.absolute_min_duration:
                    # Extender el clip para alcanzar la duración mínima
                    extension = (self.absolute_min_duration - duration) / 2
                    start = max(0, start - extension)
                    end = end + extension
                    duration = end - start
                
                if duration > self.absolute_max_duration:
                    # Acortar el clip a la duración máxima
                    end = start + self.absolute_max_duration
                    duration = self.absolute_max_duration

            # Generar una variante compacta y una extendida si el clip está dentro de un rango adecuado
            try:
                center_time = (start + end) / 2
                base_duration = duration
                variants = []
                # Compacta (gancho)
                compact = max(self.absolute_min_duration, base_duration * 0.75)
                # Extendida (contexto)
                extended = min(self.absolute_max_duration, base_duration * 1.4)
                # Añadir si son diferentes
                if abs(compact - base_duration) / base_duration > 0.12:
                    variants.append((center_time - compact / 2, center_time + compact / 2))
                if abs(extended - base_duration) / base_duration > 0.12:
                    variants.append((center_time - extended / 2, center_time + extended / 2))
                # Insertar variantes deterministas antes del clip principal para aumentar número de salidas
                for vs, ve in variants:
                    vs_clamped = max(0, vs)
                    ve_clamped = min(ve, ve if ve <= (vs + self.absolute_max_duration) else vs + self.absolute_max_duration)
                    if ve_clamped - vs_clamped >= self.absolute_min_duration:
                        clips.append({
                            "start": vs_clamped,
                            "end": ve_clamped,
                            "score": highlight.get("score", 0.5),
                            "reason": f"Variante - {highlight.get('reason', '')}"
                        })
            except Exception:
                pass
            
            clips.append({
                "start": start,
                "end": end,
                "score": highlight.get("score", 0.5),
                "reason": highlight.get("reason", "Momento destacado identificado por IA")
            })
            
            logger.info(f"Clip identificado dinámico: {start:.2f}s - {end:.2f}s "
                       f"(duración: {duration:.1f}s, score: {highlight.get('score', 0):.2f})")
        
        # Aplicar filtro de solapamiento
        filtered_highlights = self._filter_overlapping_clips(clips)
        
        # Convertir a tuplas para mantener compatibilidad
        return [(clip["start"], clip["end"]) for clip in filtered_highlights]
    
    async def _fallback_analysis_with_metadata(self, video_path: str) -> List[Dict[str, Any]]:
        """Análisis de respaldo con metadatos cuando no está disponible la API"""
        logger.info("Usando análisis de respaldo con metadatos (selección inteligente de segmentos)")
        
        duration = await self._get_video_duration(video_path)
        if duration <= 0:
            return []
        
        segments = []
        
        if duration < self.absolute_min_duration:
            return []
        
        if duration <= self.absolute_max_duration:
            return [{
                "start": 0.0,
                "end": duration,
                "score": 0.6,
                "reason": "Video completo - duración adecuada",
                "duration": duration
            }]
        
        # Crear clips estratégicamente distribuidos con duración dinámica
        clips_per_hour = 4
        total_clips = min(self.max_clips_per_video, max(2, int(duration / 3600 * clips_per_hour)))

        min_segment_duration = self.optimal_clip_duration[0]
        max_segment_duration = self.optimal_clip_duration[1]

        for i in range(total_clips):
            # Posición relativa en el video (0..1)
            segment_position = (i + 0.5) / total_clips

            # Calcular duración objetivo usando helper inteligente
            segment_duration = self._compute_backup_segment_duration(
                position=segment_position,
                index=i,
                total=total_clips,
                min_d=min_segment_duration,
                max_d=max_segment_duration
            )

            # Centrar el clip en la posición calculada
            center = segment_position * duration
            start_time = max(0, center - segment_duration / 2)
            end_time = min(duration, start_time + segment_duration)
            # Ajustar start si el end tocó el final
            start_time = max(0, end_time - segment_duration)

            if end_time - start_time >= self.absolute_min_duration:
                actual_duration = end_time - start_time
                segments.append({
                    "start": start_time,
                    "end": end_time,
                    "score": 0.5 + (i * 0.05),
                    "reason": f"Segmento estratégico {i + 1} - selección automática distribuida (duración: {actual_duration:.1f}s)",
                    "duration": actual_duration
                })

                logger.info(f"Segmento de respaldo {i+1}: {start_time:.1f}s - {end_time:.1f}s (duración: {actual_duration:.1f}s)")
        
        return segments

    async def _fallback_analysis(self, video_path: str) -> List[Tuple[float, float]]:
        """Análisis de respaldo cuando no está disponible la API"""
        logger.info("Usando análisis de respaldo (selección inteligente de segmentos)")
        
        duration = await self._get_video_duration(video_path)
        if duration <= 0:
            return []
        
        segments = []
        
        if duration < self.absolute_min_duration:
            return []
        
        if duration <= self.absolute_max_duration:
            return [(0.0, duration)]
        
        clips_per_hour = 4
        total_clips = min(self.max_clips_per_video, max(2, int(duration / 3600 * clips_per_hour)))

        min_segment_duration = self.optimal_clip_duration[0]
        max_segment_duration = self.optimal_clip_duration[1]

        for i in range(total_clips):
            segment_position = (i + 0.5) / total_clips

            segment_duration = self._compute_backup_segment_duration(
                position=segment_position,
                index=i,
                total=total_clips,
                min_d=min_segment_duration,
                max_d=max_segment_duration
            )

            center = segment_position * duration
            start_time = max(0, center - segment_duration / 2)
            end_time = min(duration, start_time + segment_duration)
            start_time = max(0, end_time - segment_duration)

            if end_time - start_time >= self.absolute_min_duration:
                segments.append((start_time, end_time))
                logger.info(f"Segmento de respaldo {i+1}: {start_time:.1f}s - {end_time:.1f}s "
                           f"(duración: {end_time - start_time:.1f}s)")

        
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
