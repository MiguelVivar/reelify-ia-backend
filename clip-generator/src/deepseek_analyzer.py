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
        try:
            self.whisper_model = whisper.load_model("base")
            logger.info("Modelo Whisper cargado correctamente")
        except Exception as e:
            logger.error(f"Error cargando modelo Whisper: {e}")
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
            
            # 5. Convertir a clips válidos y filtrar solapamientos
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
        
        # Convertir a ClipCandidates con análisis completo
        candidates = []
        for highlight in highlights:
            start = highlight["start"]
            end = highlight["end"]
            transcription = highlight.get("transcription", "")
            base_score = highlight.get("score", 0.5)
            
            # Análisis viral avanzado
            viral_analysis = self._analyze_viral_content(transcription)
            emotional_intensity = viral_analysis['score']
            confidence = viral_analysis['confidence']
            
            # Análisis de claridad del habla
            duration = end - start
            speech_clarity = self._analyze_speech_clarity(transcription, duration)
            
            # Análisis de flujo conversacional
            conversation_flow = self._analyze_conversation_flow(transcription)
            
            # Crear candidato
            candidate = ClipCandidate(
                start=start,
                end=end,
                base_score=base_score,
                emotional_intensity=emotional_intensity,
                speech_clarity=speech_clarity,
                keyword_density=len(transcription.split()) / max(duration, 1),
                conversation_flow=conversation_flow,
                audio_energy=0.5,  # Placeholder - se podría calcular del audio
                final_score=0.0,  # Se calculará después
                reason=highlight.get("reason", "Momento destacado"),
                confidence=confidence
            )
            
            # Calcular score final avanzado
            candidate.final_score = self._calculate_advanced_score(candidate)
            candidates.append(candidate)
        
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
                "transcription": highlights[0].get("transcription", ""),  # Buscar transcripción original
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
        
        # Filtrar candidatos por score mínimo más flexible
        min_viral_score = settings.viral_score_threshold  # Usar configuración dinámica
        viral_candidates = [c for c in candidates if c.final_score >= min_viral_score]
        
        logger.info(f"Candidatos virales (score >= {min_viral_score}): {len(viral_candidates)} de {len(candidates)}")
        
        if not viral_candidates:
            # Si no hay candidatos virales, relajar el criterio gradualmente
            relaxed_thresholds = [0.5, 0.4, 0.3]
            for threshold in relaxed_thresholds:
                viral_candidates = [c for c in candidates if c.final_score >= threshold]
                if viral_candidates:
                    logger.info(f"Usando threshold relajado de {threshold}: {len(viral_candidates)} candidatos encontrados")
                    break
            
            if not viral_candidates:
                # Si aún no hay candidatos, tomar los mejores disponibles
                candidates.sort(key=lambda x: x.final_score, reverse=True)
                max_fallback_clips = min(3, len(candidates))
                logger.info(f"Sin candidatos virales, tomando los {max_fallback_clips} mejores clips disponibles")
                return candidates[:max_fallback_clips]
        
        # Aplicar algoritmo de selección con restricciones temporales dinámicas
        n = len(viral_candidates)
        if n == 1:
            return viral_candidates
        
        # Usar límite dinámico de clips basado en configuración
        max_clips_allowed = min(self.max_clips_per_video, n)
        
        # Crear matriz de compatibilidad temporal
        compatible = [[False] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                clip1, clip2 = viral_candidates[i], viral_candidates[j]
                # Verificar separación mínima
                separation = abs(clip1.start - clip2.end) if clip1.start > clip2.end else abs(clip2.start - clip1.end)
                if separation >= self.min_clip_separation:
                    compatible[i][j] = compatible[j][i] = True
        
        # Programación dinámica para encontrar la mejor combinación
        selected_clips = self._dp_optimal_selection(viral_candidates, compatible, max_clips_allowed)
        
        # Sin limitación artificial estricta - usar todos los clips válidos de calidad
        logger.info(f"Clips seleccionados por algoritmo DP: {len(selected_clips)} de {n} candidatos")
        
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
        dp = [[(0.0, [])] * (max_clips_dynamic + 1) for _ in range(n)]
        
        # Inicialización
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
                        # Buscar el mejor clip compatible anterior
                        best_score = 0.0
                        best_combination = []
                        
                        for j in range(i):
                            if compatible[j][i] and dp[j][k-1][0] > 0:
                                combined_score = dp[j][k-1][0] + current_candidate.final_score
                                if combined_score > best_score:
                                    best_score = combined_score
                                    best_combination = dp[j][k-1][1] + [current_candidate]
                        
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
            else:
                # Validar duración contra límites absolutos
                if duration < self.absolute_min_duration:
                    # Extender el clip para alcanzar la duración mínima absoluta
                    extension = (self.absolute_min_duration - duration) / 2
                    start = max(0, start - extension)
                    end = min(video_duration, end + extension)
                    duration = end - start
                    logger.info(f"Clip extendido a duración mínima: {duration:.1f}s")
                
                if duration > self.absolute_max_duration:
                    # Acortar el clip a la duración máxima absoluta
                    end = start + self.absolute_max_duration
                    duration = self.absolute_max_duration
                    logger.info(f"Clip acortado a duración máxima: {duration:.1f}s")
            
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
                logger.info(f"Aplicando duración óptima de Deepseek: {target_duration:.1f}s")
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
