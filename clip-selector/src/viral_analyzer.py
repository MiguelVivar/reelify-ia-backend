import os
import uuid
import logging
import ffmpeg
import subprocess
import json
import re
import math
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter
from config import settings
from whisper_service import WhisperService

logger = logging.getLogger(__name__)

@dataclass
class ViralMetrics:
    """Métricas avanzadas para análisis viral"""
    emotional_impact: float
    memorability_score: float
    shareability_index: float
    engagement_potential: float
    hook_strength: float
    retention_probability: float
    virality_coefficient: float

class AdvancedViralAnalyzer:
    """Analizador avanzado de viralidad con IA semántica"""
    
    def __init__(self):
        # Patrones virales con pesos neuronales
        self.viral_patterns = {
            'hooks_inmediatos': {
                'patterns': [
                    r'^\s*(espera|wait|para|no vas a creer|increíble)',
                    r'^\s*(mira esto|watch this|fíjate|check)',
                    r'^\s*(qué|what|cómo|how).*[!?]',
                    r'^\s*(nunca|never|jamás).*[!.]'
                ],
                'weight': 3.0,
                'viral_multiplier': 2.5
            },
            'tension_dramatica': {
                'patterns': [
                    r'\b(plot twist|giro|inesperado|sorpresa)\b',
                    r'\b(pero luego|but then|sin embargo|however)\b',
                    r'\b(de repente|suddenly|entonces|then)\b',
                    r'\b(resulta que|turns out|pasa que)\b'
                ],
                'weight': 2.8,
                'viral_multiplier': 2.2
            },
            'emociones_extremas': {
                'patterns': [
                    r'\b(love|hate|adoro|odio|detesto|amo)\b',
                    r'\b(increíble|amazing|incredible|insane)\b',
                    r'\b(perfecto|perfect|terrible|horrible)\b',
                    r'\b(best|worst|mejor|peor) .* (ever|nunca|vida)\b'
                ],
                'weight': 2.5,
                'viral_multiplier': 2.0
            },
            'llamadas_accion': {
                'patterns': [
                    r'\b(comparte|share|guarda|save|tag)\b',
                    r'\b(comenta|comment|dime|tell me)\b',
                    r'\b(sigue|follow|subscribe|suscríbete)\b',
                    r'\b(like si|like if|dale like)\b'
                ],
                'weight': 2.0,
                'viral_multiplier': 1.8
            },
            'exclusividad_urgencia': {
                'patterns': [
                    r'\b(secreto|secret|oculto|hidden)\b',
                    r'\b(exclusivo|exclusive|limitado|limited)\b',
                    r'\b(antes de que|before|rápido|quick)\b',
                    r'\b(pocos saben|few know|nadie sabe)\b'
                ],
                'weight': 1.8,
                'viral_multiplier': 1.6
            },
            'contraste_social': {
                'patterns': [
                    r'\b(rico vs pobre|rich vs poor)\b',
                    r'\b(antes vs después|before vs after)\b',
                    r'\b(expectativa vs realidad|expectation vs reality)\b',
                    r'\b(hombres vs mujeres|men vs women)\b'
                ],
                'weight': 1.5,
                'viral_multiplier': 1.4
            }
        }
        
        # Indicadores de baja viralidad
        self.viral_inhibitors = [
            r'\b(complicado|complicated|difícil|difficult|técnico|technical)\b',
            r'\b(aburrido|boring|monótono|monotone|lento|slow)\b',
            r'\b(largo|long|extenso|extensive|detallado|detailed)\b',
            r'\b(normal|regular|típico|typical|común|common)\b'
        ]
        
        # Patrones de retención (mantienen al viewer enganchado)
        self.retention_patterns = [
            r'\b(primero|first|paso 1|step 1)\b',
            r'\b(segundo|second|después|then|next)\b',
            r'\b(pero eso no es todo|but that\'s not all)\b',
            r'\b(espera a ver|wait to see|al final|at the end)\b'
        ]

class ViralClipAnalyzer:
    def __init__(self):
        self.whisper_service = WhisperService()
        self.temp_dir = settings.temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

        # Inicializar analizador avanzado
        self.advanced_analyzer = AdvancedViralAnalyzer()
        
        # Configuración mejorada
        self.viral_threshold_strict = 0.75  # Threshold estricto para viralidad
        self.engagement_threshold = 0.6
        
        # Mantener compatibilidad con configuración existente
        self.viral_keywords = settings.viral_keywords
        self.emotion_keywords = settings.emotion_keywords
    
    async def analyze_clip(self, clip_path: str) -> Dict[str, Any]:
        """
        Analiza un clip para determinar su potencial viral usando IA avanzada.
        """
        try:
            logger.info(f"Iniciando análisis viral avanzado para: {clip_path}")
            
            # Obtener duración del video
            duration = await self._get_video_duration(clip_path)
            
            # Extraer audio para transcripción
            audio_path = await self._extract_audio(clip_path)
            
            # Transcribir audio con metadatos
            transcription = await self.whisper_service.transcribe_audio(audio_path)
            
            # Análisis viral avanzado
            viral_metrics = await self._analyze_advanced_viral_potential(transcription, duration)
            
            # Análisis temporal para optimización de cortes
            temporal_analysis = self._analyze_temporal_structure(transcription)
            
            # Predicción de engagement
            engagement_prediction = self._predict_engagement(viral_metrics, temporal_analysis)
            
            # Limpiar archivo de audio
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            result = {
                "duration": duration,
                "transcription": transcription,
                "viral_score": viral_metrics.virality_coefficient,
                "engagement_score": engagement_prediction["engagement_score"],
                "retention_probability": viral_metrics.retention_probability,
                "hook_strength": viral_metrics.hook_strength,
                "shareability_index": viral_metrics.shareability_index,
                "memorability_score": viral_metrics.memorability_score,
                "optimal_cut_points": temporal_analysis["optimal_cuts"],
                "viral_moments": temporal_analysis["peak_moments"],
                "recommendation": self._generate_recommendation(viral_metrics, engagement_prediction),
                
                # Mantener compatibilidad con formato anterior
                "keywords_found": self._extract_legacy_keywords(transcription),
                "emotions_found": self._extract_legacy_emotions(transcription),
                "key_moments": temporal_analysis["peak_moments"][:5]
            }
            
            logger.info(f"Análisis completado - Score viral: {viral_metrics.virality_coefficient:.3f}, "
                       f"Engagement: {engagement_prediction['engagement_score']:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error en análisis viral avanzado {clip_path}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                "duration": 0,
                "transcription": {"text": "", "segments": []},
                "viral_score": 0.0,
                "engagement_score": 0.0,
                "recommendation": "error_in_analysis",
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

    async def _analyze_advanced_viral_potential(self, transcription: Dict[str, Any], duration: float) -> ViralMetrics:
        """
        Análisis avanzado de potencial viral usando IA semántica
        """
        text = transcription.get("text", "").lower()
        segments = transcription.get("segments", [])
        
        if not text:
            return ViralMetrics(0, 0, 0, 0, 0, 0, 0)
        
        # 1. Análisis de impacto emocional
        emotional_impact = self._calculate_emotional_impact(text, segments)
        
        # 2. Análisis de memorabilidad
        memorability_score = self._calculate_memorability(text, segments)
        
        # 3. Índice de compartibilidad
        shareability_index = self._calculate_shareability(text, segments)
        
        # 4. Potencial de engagement
        engagement_potential = self._calculate_engagement_potential(text, segments)
        
        # 5. Fuerza del hook (primeros 3 segundos)
        hook_strength = self._calculate_hook_strength(segments)
        
        # 6. Probabilidad de retención
        retention_probability = self._calculate_retention_probability(text, segments, duration)
        
        # 7. Coeficiente viral final (algoritmo propietario)
        virality_coefficient = self._calculate_virality_coefficient(
            emotional_impact, memorability_score, shareability_index,
            engagement_potential, hook_strength, retention_probability
        )
        
        return ViralMetrics(
            emotional_impact=emotional_impact,
            memorability_score=memorability_score,
            shareability_index=shareability_index,
            engagement_potential=engagement_potential,
            hook_strength=hook_strength,
            retention_probability=retention_probability,
            virality_coefficient=virality_coefficient
        )

    def _calculate_emotional_impact(self, text: str, segments: List[Dict]) -> float:
        """Calcula el impacto emocional del contenido"""
        
        # Patrones de alta intensidad emocional
        high_intensity_patterns = [
            r'\b(increíble|alucinante|brutal|épico|insane)\b',
            r'\b(no puedo creer|can\'t believe|imposible)\b',
            r'\b(me muero|dying|me parto|hilarious)\b',
            r'[!]{2,}',  # Múltiples exclamaciones
            r'\b(amor|love|odio|hate) .* (muchísimo|so much)\b'
        ]
        
        impact_score = 0.0
        word_count = len(text.split())
        
        for pattern in high_intensity_patterns:
            matches = len(re.findall(pattern, text))
            impact_score += matches
        
        # Normalizar por longitud del texto
        if word_count > 0:
            density_score = impact_score / word_count
            final_score = min(density_score * 50, 1.0)  # Escalar apropiadamente
        else:
            final_score = 0.0
        
        # Bonus por variación emocional en segmentos
        if len(segments) > 1:
            emotion_variance = self._calculate_emotion_variance(segments)
            final_score = min(final_score * (1 + emotion_variance), 1.0)
        
        return final_score

    def _calculate_memorability(self, text: str, segments: List[Dict]) -> float:
        """Calcula qué tan memorable es el contenido"""
        
        memorability_indicators = [
            r'\b(recuerda|remember|nunca olvides|never forget)\b',
            r'\b(siempre|always|para toda la vida|forever)\b',
            r'\b(historia|story|experiencia|experience)\b',
            r'\b(primera vez|first time|nunca había|never had)\b'
        ]
        
        # Patrones de frases pegajosas
        catchy_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Nombres propios/marcas
            r'\b\d+.*tips?\b',  # "5 tips", "10 secretos"
            r'\b(secreto|secret|truco|hack|tip)\b',
            r'"[^"]{10,50}"'  # Citas entre 10-50 caracteres
        ]
        
        score = 0.0
        
        # Evaluar indicadores de memorabilidad
        for pattern in memorability_indicators:
            score += len(re.findall(pattern, text)) * 0.3
        
        # Evaluar frases pegajosas
        for pattern in catchy_patterns:
            score += len(re.findall(pattern, text)) * 0.4
        
        # Bonus por repetición de conceptos clave
        words = text.split()
        word_freq = Counter(w for w in words if len(w) > 4)
        repeated_concepts = sum(1 for freq in word_freq.values() if freq > 2)
        score += repeated_concepts * 0.2
        
        return min(score, 1.0)

    def _calculate_shareability(self, text: str, segments: List[Dict]) -> float:
        """Calcula qué tan probable es que el contenido sea compartido"""
        
        # Indicadores de contenido compartible
        share_triggers = [
            r'\b(comparte|share|tag|etiqueta)\b',
            r'\b(increíble|amazing|must see|debes ver)\b',
            r'\b(no vas a creer|won\'t believe|check this)\b',
            r'\b(todos deberían|everyone should|mundo debería)\b'
        ]
        
        # Contenido controvertido apropiado
        controversy_patterns = [
            r'\b(opinión|opinion|debate|discussion)\b',
            r'\b(estás de acuerdo|do you agree|qué piensas)\b',
            r'\b(polémica|controversial|divisive)\b'
        ]
        
        # Valor informativo/educativo
        value_patterns = [
            r'\b(aprende|learn|descubre|discover)\b',
            r'\b(sabías que|did you know|fact|dato)\b',
            r'\b(tip|consejo|advice|hack|truco)\b'
        ]
        
        shareability = 0.0
        
        # Evaluar triggers de compartición
        for pattern in share_triggers:
            shareability += len(re.findall(pattern, text)) * 0.4
        
        # Evaluar controversia apropiada
        for pattern in controversy_patterns:
            shareability += len(re.findall(pattern, text)) * 0.3
        
        # Evaluar valor informativo
        for pattern in value_patterns:
            shareability += len(re.findall(pattern, text)) * 0.25
        
        # Bonus por preguntas al público
        questions = len(re.findall(r'[?]', text))
        shareability += questions * 0.15
        
        return min(shareability, 1.0)

    def _calculate_engagement_potential(self, text: str, segments: List[Dict]) -> float:
        """Calcula el potencial de engagement (comentarios, likes, interacciones)"""
        
        engagement_triggers = [
            r'\b(comenta|comment|dime|tell me)\b',
            r'\b(qué piensas|what do you think|opinión)\b',
            r'\b(like si|like if|dale like)\b',
            r'\b(estás de acuerdo|do you agree)\b',
            r'\b(tu experiencia|your experience|les pasa)\b'
        ]
        
        # Contenido relatable
        relatable_patterns = [
            r'\b(todos|everyone|siempre nos pasa|always happens)\b',
            r'\b(típico|typical|clásico|classic)\b',
            r'\b(quién más|who else|alguien más|someone else)\b'
        ]
        
        engagement = 0.0
        
        # Triggers directos de engagement
        for pattern in engagement_triggers:
            engagement += len(re.findall(pattern, text)) * 0.5
        
        # Contenido relatable
        for pattern in relatable_patterns:
            engagement += len(re.findall(pattern, text)) * 0.3
        
        # Bonus por estructura conversacional
        if self._has_conversational_structure(text):
            engagement *= 1.3
        
        return min(engagement, 1.0)

    def _calculate_hook_strength(self, segments: List[Dict]) -> float:
        """Calcula la fuerza del hook en los primeros segundos"""
        
        if not segments:
            return 0.0
        
        # Obtener texto de los primeros 5 segundos
        hook_text = ""
        for segment in segments:
            if segment.get("start", 0) <= 5:
                hook_text += segment.get("text", "") + " "
            else:
                break
        
        if not hook_text:
            return 0.0
        
        hook_text = hook_text.lower()
        
        # Patrones de hooks fuertes
        strong_hooks = self.advanced_analyzer.viral_patterns['hooks_inmediatos']['patterns']
        
        hook_score = 0.0
        for pattern in strong_hooks:
            if re.search(pattern, hook_text):
                hook_score += 1.0
        
        # Bonus por urgencia/curiosidad en el hook
        curiosity_patterns = [
            r'\b(secreto|secret|nunca creeras|won\'t believe)\b',
            r'\b(mira esto|watch this|check|fíjate)\b',
            r'\b(increíble|amazing|insane|brutal)\b'
        ]
        
        for pattern in curiosity_patterns:
            hook_score += len(re.findall(pattern, hook_text)) * 0.5
        
        return min(hook_score / 3.0, 1.0)  # Normalizar

    def _calculate_retention_probability(self, text: str, segments: List[Dict], duration: float) -> float:
        """Calcula la probabilidad de que el viewer vea el clip completo"""
        
        retention_score = 0.5  # Base score
        
        # Factor 1: Estructura temporal
        if 15 <= duration <= 45:
            retention_score += 0.3  # Duración óptima
        elif duration > 60:
            retention_score -= 0.2  # Penalizar clips muy largos
        
        # Factor 2: Distribución de contenido interesante
        if segments:
            segment_scores = []
            for segment in segments:
                seg_text = segment.get("text", "").lower()
                seg_score = 0
                
                # Buscar elementos de retención en cada segmento
                for pattern in self.advanced_analyzer.retention_patterns:
                    seg_score += len(re.findall(pattern, seg_text))
                
                segment_scores.append(seg_score)
            
            # Bonus si hay contenido interesante distribuido uniformemente
            if segment_scores:
                non_zero_segments = sum(1 for score in segment_scores if score > 0)
                retention_score += (non_zero_segments / len(segments)) * 0.3
        
        # Factor 3: Tensión narrativa
        narrative_tension = self._analyze_narrative_tension(text, segments)
        retention_score += narrative_tension * 0.2
        
        return min(retention_score, 1.0)

    def _calculate_virality_coefficient(self, emotional_impact: float, memorability: float,
                                      shareability: float, engagement: float,
                                      hook_strength: float, retention: float) -> float:
        """
        Algoritmo propietario para calcular el coeficiente viral final
        """
        
        # Pesos optimizados para viralidad en redes sociales
        weights = {
            'hook_strength': 0.25,      # Crítico para stop-the-scroll
            'emotional_impact': 0.20,   # Impulsa reacciones inmediatas
            'shareability': 0.20,       # Directo al crecimiento viral
            'engagement': 0.15,         # Fomenta interacciones
            'memorability': 0.10,       # Longevidad del contenido
            'retention': 0.10           # Completitud de visualización
        }
        
        # Cálculo base ponderado
        base_score = (
            hook_strength * weights['hook_strength'] +
            emotional_impact * weights['emotional_impact'] +
            shareability * weights['shareability'] +
            engagement * weights['engagement'] +
            memorability * weights['memorability'] +
            retention * weights['retention']
        )
        
        # Multiplicadores de sinergia
        # Hook fuerte + alta emoción = multiplicador viral
        if hook_strength > 0.7 and emotional_impact > 0.6:
            base_score *= 1.3
        
        # Alta compartibilidad + alto engagement = multiplicador social
        if shareability > 0.6 and engagement > 0.6:
            base_score *= 1.2
        
        # Penalty por scores muy bajos en factores críticos
        critical_factors = [hook_strength, emotional_impact, shareability]
        low_critical_count = sum(1 for factor in critical_factors if factor < 0.3)
        if low_critical_count >= 2:
            base_score *= 0.7
        
        return min(base_score, 1.0)

    def _analyze_temporal_structure(self, transcription: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza la estructura temporal para identificar puntos de corte óptimos"""
        
        segments = transcription.get("segments", [])
        
        if not segments:
            return {"optimal_cuts": [], "peak_moments": [], "energy_curve": []}
        
        # Calcular energía por segmento
        energy_curve = []
        peak_moments = []
        
        for i, segment in enumerate(segments):
            text = segment.get("text", "").lower()
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            
            # Calcular energía del segmento
            energy = self._calculate_segment_energy(text)
            energy_curve.append({
                "time": start_time,
                "energy": energy,
                "text": segment.get("text", "")
            })
            
            # Identificar picos de energía
            if energy > 0.6:  # Threshold para momentos peak
                peak_moments.append({
                    "start": start_time,
                    "end": end_time,
                    "text": segment.get("text", ""),
                    "energy": energy,
                    "reason": self._identify_peak_reason(text)
                })
        
        # Identificar puntos de corte óptimos
        optimal_cuts = self._identify_optimal_cuts(energy_curve)
        
        return {
            "optimal_cuts": optimal_cuts,
            "peak_moments": sorted(peak_moments, key=lambda x: x["energy"], reverse=True),
            "energy_curve": energy_curve
        }

    def _calculate_segment_energy(self, text: str) -> float:
        """Calcula la energía/intensidad de un segmento de texto"""
        
        if not text:
            return 0.0
        
        energy = 0.0
        
        # Indicadores de alta energía
        high_energy_indicators = [
            (r'[!]{1,}', 0.3),          # Exclamaciones
            (r'[?]{1,}', 0.2),          # Preguntas
            (r'\b(wow|increíble|amazing|brutal)\b', 0.4),
            (r'\b(rápido|fast|urgente|urgent)\b', 0.3),
            (r'\b[A-Z]{2,}\b', 0.2),    # Palabras en mayúsculas
        ]
        
        for pattern, weight in high_energy_indicators:
            matches = len(re.findall(pattern, text))
            energy += matches * weight
        
        # Normalizar por longitud
        words = len(text.split())
        if words > 0:
            energy = energy / math.sqrt(words)  # Suavizar normalización
        
        return min(energy, 1.0)

    def _identify_optimal_cuts(self, energy_curve: List[Dict]) -> List[Dict]:
        """Identifica puntos óptimos para cortar clips"""
        
        if len(energy_curve) < 3:
            return []
        
        optimal_cuts = []
        
        # Buscar transiciones de alta a baja energía y viceversa
        for i in range(1, len(energy_curve) - 1):
            prev_energy = energy_curve[i-1]["energy"]
            curr_energy = energy_curve[i]["energy"]
            next_energy = energy_curve[i+1]["energy"]
            
            # Pico local (bueno para fin de clip)
            if curr_energy > prev_energy and curr_energy > next_energy and curr_energy > 0.5:
                optimal_cuts.append({
                    "time": energy_curve[i]["time"],
                    "type": "peak_end",
                    "confidence": curr_energy,
                    "reason": "Fin de momento de alta energía"
                })
            
            # Valle seguido de subida (bueno para inicio de clip)
            elif curr_energy < prev_energy and curr_energy < next_energy and next_energy > 0.4:
                optimal_cuts.append({
                    "time": energy_curve[i]["time"],
                    "type": "valley_start",
                    "confidence": next_energy,
                    "reason": "Inicio de momento ascendente"
                })
        
        # Ordenar por confianza y limitar resultados
        optimal_cuts.sort(key=lambda x: x["confidence"], reverse=True)
        return optimal_cuts[:10]  # Top 10 puntos de corte

    def _predict_engagement(self, viral_metrics: ViralMetrics, temporal_analysis: Dict) -> Dict[str, Any]:
        """Predice métricas de engagement específicas"""
        
        # Predicción de likes basada en factores emocionales
        like_prediction = (
            viral_metrics.emotional_impact * 0.4 +
            viral_metrics.hook_strength * 0.3 +
            viral_metrics.memorability_score * 0.3
        )
        
        # Predicción de shares basada en compartibilidad y valor
        share_prediction = (
            viral_metrics.shareability_index * 0.5 +
            viral_metrics.engagement_potential * 0.3 +
            viral_metrics.memorability_score * 0.2
        )
        
        # Predicción de comentarios basada en engagement triggers
        comment_prediction = (
            viral_metrics.engagement_potential * 0.6 +
            viral_metrics.shareability_index * 0.4
        )
        
        # Score de engagement general
        engagement_score = (like_prediction + share_prediction + comment_prediction) / 3
        
        # Predicción de retención basada en estructura temporal
        retention_prediction = viral_metrics.retention_probability
        
        # Ajustes por estructura temporal
        peak_count = len(temporal_analysis.get("peak_moments", []))
        if peak_count > 0:
            engagement_score *= (1 + min(peak_count * 0.1, 0.3))
        
        return {
            "engagement_score": engagement_score,
            "like_prediction": like_prediction,
            "share_prediction": share_prediction,
            "comment_prediction": comment_prediction,
            "retention_prediction": retention_prediction,
            "virality_tier": self._classify_virality_tier(viral_metrics.virality_coefficient)
        }

    def _classify_virality_tier(self, virality_score: float) -> str:
        """Clasifica el contenido en tiers de viralidad"""
        
        if virality_score >= 0.8:
            return "viral_guaranteed"
        elif virality_score >= 0.65:
            return "high_viral_potential"
        elif virality_score >= 0.45:
            return "moderate_viral_potential"
        elif virality_score >= 0.25:
            return "low_viral_potential"
        else:
            return "not_viral"

    def _generate_recommendation(self, viral_metrics: ViralMetrics, engagement_prediction: Dict) -> str:
        """Genera recomendación basada en el análisis"""
        
        virality_tier = engagement_prediction["virality_tier"]
        
        if virality_tier == "viral_guaranteed":
            return "PUBLICAR INMEDIATAMENTE - Contenido con garantía viral"
        elif virality_tier == "high_viral_potential":
            return "ALTAMENTE RECOMENDADO - Excelente potencial viral"
        elif virality_tier == "moderate_viral_potential":
            return "RECOMENDADO - Buen engagement esperado"
        elif virality_tier == "low_viral_potential":
            return "CONSIDERAR EDICIÓN - Potencial limitado"
        else:
            return "NO RECOMENDADO - Bajo potencial viral"

    # Métodos de compatibilidad con el sistema anterior
    def _extract_legacy_keywords(self, transcription: Dict) -> List[str]:
        """Extrae keywords usando el sistema legacy para compatibilidad"""
        text = transcription.get("text", "").lower()
        found_keywords = []
        
        for keyword in self.viral_keywords:
            if keyword.lower() in text:
                found_keywords.append(keyword)
        
        return found_keywords

    def _extract_legacy_emotions(self, transcription: Dict) -> List[str]:
        """Extrae emociones usando el sistema legacy para compatibilidad"""
        text = transcription.get("text", "").lower()
        found_emotions = []
        
        for emotion in self.emotion_keywords:
            if emotion.lower() in text:
                found_emotions.append(emotion)
        
        return found_emotions

    # Métodos auxiliares
    def _has_conversational_structure(self, text: str) -> bool:
        """Detecta si el texto tiene estructura conversacional"""
        
        conversational_indicators = [
            r'\b(pero|but|sin embargo|however)\b',
            r'\b(entonces|so|por eso|therefore)\b',
            r'\b(además|also|también|too)\b',
            r'[?].*[.!]',  # Pregunta seguida de afirmación
        ]
        
        indicator_count = 0
        for pattern in conversational_indicators:
            if re.search(pattern, text.lower()):
                indicator_count += 1
        
        return indicator_count >= 2

    def _calculate_emotion_variance(self, segments: List[Dict]) -> float:
        """Calcula la varianza emocional entre segmentos"""
        
        if len(segments) < 2:
            return 0.0
        
        segment_emotions = []
        for segment in segments:
            text = segment.get("text", "").lower()
            emotion_score = 0
            
            # Calcular intensidad emocional por segmento
            emotion_patterns = [
                r'\b(love|hate|amazing|terrible)\b',
                r'[!]+', r'[?]+',
                r'\b(wow|incredible|insane)\b'
            ]
            
            for pattern in emotion_patterns:
                emotion_score += len(re.findall(pattern, text))
            
            segment_emotions.append(emotion_score)
        
        # Calcular varianza normalizada
        if len(segment_emotions) > 1:
            mean_emotion = sum(segment_emotions) / len(segment_emotions)
            variance = sum((x - mean_emotion) ** 2 for x in segment_emotions) / len(segment_emotions)
            return min(variance / 10, 0.5)  # Normalizar
        
        return 0.0

    def _analyze_narrative_tension(self, text: str, segments: List[Dict]) -> float:
        """Analiza la tensión narrativa del contenido"""
        
        tension_indicators = [
            r'\b(pero luego|but then|sin embargo|however)\b',
            r'\b(de repente|suddenly|entonces|then)\b',
            r'\b(resulta que|turns out|pasa que)\b',
            r'\b(plot twist|giro|unexpected)\b'
        ]
        
        tension_score = 0.0
        for pattern in tension_indicators:
            tension_score += len(re.findall(pattern, text.lower()))
        
        # Normalizar por longitud
        words = len(text.split())
        if words > 0:
            tension_score = min(tension_score / words * 20, 1.0)
        
        return tension_score

    def _identify_peak_reason(self, text: str) -> str:
        """Identifica la razón de un pico de energía"""
        
        text_lower = text.lower()
        
        if re.search(r'\b(increíble|amazing|wow)\b', text_lower):
            return "Expresión de asombro"
        elif re.search(r'[!]{2,}', text):
            return "Alta excitación emocional"
        elif re.search(r'\b(secreto|secret|revelación)\b', text_lower):
            return "Revelación o información exclusiva"
        elif re.search(r'[?]', text):
            return "Pregunta engaging"
        else:
            return "Momento de alta energía"

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
