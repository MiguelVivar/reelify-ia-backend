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
        
        # Configuración de calidad temporal
        self.min_clip_separation = 120.0  # 2 minutos entre clips para máxima distribución
        self.optimal_clip_duration = (25, 75)  # Duración óptima para viral (25-75 segundos)
        self.max_clips_per_hour = 2  # Máximo 2 clips por hora de video
        
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
            
            prompt = f"""Eres un experto en identificar contenido VIRAL en redes sociales. Analiza estas transcripciones y selecciona SOLO los momentos con mayor potencial viral.

TRANSCRIPCIONES:
{transcription_text}

CRITERIOS VIRALES ESTRICTOS (Score mínimo 0.8):
🔥 EMOCIONES INTENSAS: Reacciones auténticas, sorpresas, risas explosivas
💬 FRASES MEMORABLES: Citas pegajosas, declaraciones polémicas apropiadas
⚡ MOMENTOS CLIMÁTICOS: Puntos de tensión, revelaciones, plot twists
🎯 VALOR ÚNICO: Información exclusiva, secretos, trucos desconocidos
💡 ENGAGEMENT NATURAL: Preguntas directas, llamadas a la acción implícitas
🔄 POTENCIAL SHARE: Contenido que la gente querría compartir inmediatamente

EVITAR ABSOLUTAMENTE:
❌ Explicaciones largas sin gancho emocional
❌ Momentos de transición o relleno
❌ Contenido técnico sin emoción
❌ Repeticiones o información redundante
❌ Momentos monótonos o de baja energía

REGLAS TEMPORALES CRÍTICAS:
- Clips de 20-60 segundos (óptimo: 25-45 segundos)
- MÍNIMO 2 MINUTOS de separación entre clips
- Máximo 3 clips por video (selectividad extrema)
- Priorizar CALIDAD absoluta sobre cantidad
- Distribuir clips a lo largo del video completo

INSTRUCCIONES ESPECÍFICAS:
1. Lee TODA la transcripción antes de decidir
2. Identifica solo momentos que harían que alguien pause el scroll
3. Busca contenido que genere comentarios y shares
4. Evita clips similares o redundantes
5. Los tiempos deben ser EXACTOS del video completo
6. Incluye contexto suficiente para entender el momento

FORMATO DE RESPUESTA (JSON ESTRICTO):
{{
    "highlights": [
        {{
            "segment_index": 0,
            "score": 0.85,
            "reason": "Reacción explosiva inesperada que genera engagement inmediato",
            "start_time": 125.5,
            "end_time": 165.2,
            "viral_category": "emotional_reaction",
            "engagement_prediction": "high_share_potential"
        }}
    ]
}}

NOTA CRÍTICA: Si no hay momentos con score >= 0.8, devuelve array vacío. Mejor CERO clips que clips mediocres."""
            
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
        
        # Filtrar candidatos por score mínimo estricto
        min_viral_score = 0.6  # Score mínimo para consideración
        viral_candidates = [c for c in candidates if c.final_score >= min_viral_score]
        
        logger.info(f"Candidatos virales (score >= {min_viral_score}): {len(viral_candidates)} de {len(candidates)}")
        
        if not viral_candidates:
            # Si no hay candidatos virales, tomar los mejores 2
            candidates.sort(key=lambda x: x.final_score, reverse=True)
            return candidates[:2]
        
        # Aplicar algoritmo de selección con restricciones temporales
        n = len(viral_candidates)
        if n == 1:
            return viral_candidates
        
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
        selected_clips = self._dp_optimal_selection(viral_candidates, compatible)
        
        # Validación final y limitación
        if len(selected_clips) > 3:
            # Si tenemos más de 3, tomar los 3 mejores
            selected_clips.sort(key=lambda x: x.final_score, reverse=True)
            selected_clips = selected_clips[:3]
        
        # Ordenar por tiempo para resultado final
        selected_clips.sort(key=lambda x: x.start)
        
        return selected_clips

    def _dp_optimal_selection(self, candidates: List[ClipCandidate], compatible: List[List[bool]]) -> List[ClipCandidate]:
        """Algoritmo de programación dinámica para selección óptima"""
        n = len(candidates)
        if n == 0:
            return []
        
        # DP con máximo 3 clips
        max_clips = min(3, n)
        
        # dp[i][k] = (score_máximo, clips_seleccionados) usando hasta el clip i con k clips
        dp = [[(0.0, [])] * (max_clips + 1) for _ in range(n)]
        
        # Inicialización
        for k in range(max_clips + 1):
            if k == 1:
                dp[0][k] = (candidates[0].final_score, [candidates[0]])
            else:
                dp[0][k] = (0.0, [])
        
        # Llenar tabla DP
        for i in range(1, n):
            current_candidate = candidates[i]
            
            for k in range(max_clips + 1):
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
            for k in range(1, max_clips + 1):
                if dp[i][k][0] > best_score:
                    best_score = dp[i][k][0]
                    best_clips = dp[i][k][1]
        
        return best_clips
    
    def _validate_viral_potential(self, clips: List[Dict]) -> List[Dict]:
        """
        Validación adicional para asegurar que los clips tengan potencial viral.
        """
        if not clips:
            return clips
        
        viral_clips = []
        for clip in clips:
            score = clip.get("score", 0)
            reason = clip.get("reason", "")
            duration = clip["end"] - clip["start"]
            
            # Criterios adicionales de validación
            is_viral_worthy = (
                score >= 0.75 and  # Score mínimo alto
                15 <= duration <= 90 and  # Duración apropiada para viral
                len(reason) > 10  # Razón descriptiva
            )
            
            if is_viral_worthy:
                viral_clips.append(clip)
                logger.info(f"Clip validado como viral: {clip['start']:.1f}s-{clip['end']:.1f}s (score: {score:.2f})")
            else:
                logger.info(f"Clip descartado en validación viral: {clip['start']:.1f}s-{clip['end']:.1f}s (score: {score:.2f})")
        
        return viral_clips
    
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
            
            clips.append({
                "start": start,
                "end": end,
                "score": highlight.get("score", 0.5),
                "reason": highlight.get("reason", "Momento destacado identificado por IA")
            })
            
            logger.info(f"Clip identificado: {start:.2f}s - {end:.2f}s "
                       f"(score: {highlight.get('score', 0):.2f}, "
                       f"reason: {highlight.get('reason', 'N/A')[:50]}...)")
        
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
        
        # Crear clips estratégicamente distribuidos (no consecutivos)
        total_clips = min(5, max(2, int(duration / 180)))  # 1 clip cada 3 minutos aproximadamente
        segment_duration = min(max_clip_duration, 60)  # Clips de hasta 60 segundos
        
        # Distribuir clips a lo largo del video
        for i in range(total_clips):
            # Calcular posición estratégica en el video
            segment_position = (i + 0.5) / total_clips  # Evitar inicio y final del video
            start_time = segment_position * duration
            
            # Ajustar para no exceder la duración del video
            end_time = min(start_time + segment_duration, duration)
            start_time = max(0, end_time - segment_duration)
            
            if end_time - start_time >= min_clip_duration:
                segments.append({
                    "start": start_time,
                    "end": end_time,
                    "score": 0.5 + (i * 0.1),  # Score ligeramente variable
                    "reason": f"Segmento estratégico {i + 1} - selección automática distribuida"
                })
                
                logger.info(f"Segmento de respaldo {i+1}: {start_time:.1f}s - {end_time:.1f}s")
        
        return segments

    async def _fallback_analysis(self, video_path: str) -> List[Tuple[float, float]]:
        """Análisis de respaldo cuando no está disponible la API"""
        logger.info("Usando análisis de respaldo (selección inteligente de segmentos)")
        
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
        
        # Crear clips estratégicamente distribuidos (no consecutivos)
        total_clips = min(5, max(2, int(duration / 180)))  # 1 clip cada 3 minutos aproximadamente
        segment_duration = min(max_clip_duration, 60)  # Clips de hasta 60 segundos
        
        # Distribuir clips a lo largo del video
        for i in range(total_clips):
            # Calcular posición estratégica en el video
            segment_position = (i + 0.5) / total_clips  # Evitar inicio y final del video
            start_time = segment_position * duration
            
            # Ajustar para no exceder la duración del video
            end_time = min(start_time + segment_duration, duration)
            start_time = max(0, end_time - segment_duration)
            
            if end_time - start_time >= min_clip_duration:
                segments.append((start_time, end_time))
                logger.info(f"Segmento de respaldo {i+1}: {start_time:.1f}s - {end_time:.1f}s")
        
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
