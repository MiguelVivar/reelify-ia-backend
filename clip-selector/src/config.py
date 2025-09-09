import os
from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Configuración de Whisper
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    
    # Configuración de detección viral mejorada - keywords expandidas y categorizadas
    viral_keywords_str: str = "viral,trending,increíble,brutal,épico,insane,mind-blowing,game-changer,life-hack,secreto,exclusivo,limitado,gratis,descuento,oferta,promoción,únete,suscríbete,comparte,tag,momento,impresionante,alucinante,no vas a creer,tienes que ver,mira esto,fíjate,check this,must see,amazing,incredible,wow,holy,omg,wtf,shocking,surprising,unexpected,plot twist,revelation,exposed,truth,behind scenes,secretos,trucos,hacks,tips,consejos,método,técnica,estrategia,fórmula,never seen,nunca visto,primera vez,first time,exclusiva,exclusive,breaking,urgente,ahora,inmediato,limited time,tiempo limitado,última oportunidad,no te pierdas,don't miss,viral moment,momento viral,trending now,tendencia,meme,challenge,reto,desafío"
    
    emotion_keywords_str: str = "amor,love,odio,hate,feliz,happy,triste,sad,enojado,angry,furious,surprised,sorprendido,emocionado,excited,increíble,incredible,genial,awesome,terrible,horrible,perfecto,perfect,amazing,wow,omg,lol,jaja,haha,divertido,funny,gracioso,hilarious,chistoso,risa,laugh,llorar,cry,miedo,scared,fear,nervioso,nervous,ansioso,anxious,orgulloso,proud,vergüenza,shame,embarrassed,confundido,confused,impresionado,impressed,decepcionado,disappointed,esperanzado,hopeful,desesperado,desperate,eufórico,euphoric,melancólico,melancholic,nostálgico,nostalgic,inspirado,inspired,motivado,motivated,relajado,relaxed,estresado,stressed,preocupado,worried,aliviado,relieved,agradecido,grateful,celoso,jealous,envidioso,envious"
    
    # Thresholds más estrictos para máxima selectividad viral
    min_viral_score: float = 0.75  # Aumentado de 0.3 a 0.75
    min_engagement_score: float = 0.6  # Nuevo threshold para engagement
    min_hook_strength: float = 0.5  # Nuevo threshold para hook strength
    
    # Configuración de análisis temporal avanzado
    energy_analysis_window: float = 3.0  # Ventana de análisis de energía en segundos
    peak_detection_threshold: float = 0.6  # Threshold para detección de picos
    optimal_clip_length_min: int = 20  # Duración mínima óptima para viral
    optimal_clip_length_max: int = 60  # Duración máxima óptima para viral
    
    # Configuración de retención y engagement
    retention_analysis_enabled: bool = True
    engagement_prediction_enabled: bool = True
    temporal_structure_analysis: bool = True
    
    # Factores de peso para scoring viral final
    emotional_impact_weight: float = 0.25
    hook_strength_weight: float = 0.20
    shareability_weight: float = 0.20
    engagement_weight: float = 0.15
    memorability_weight: float = 0.10
    retention_weight: float = 0.10
    
    # Configuración de clasificación por tiers
    viral_tier_thresholds: str = "0.8,0.65,0.45,0.25"  # viral_guaranteed,high,moderate,low
    
    # Almacenamiento de clips
    clips_input_dir: str = "/app/clips/raw"
    clips_output_dir: str = "/app/clips/viral"
    
    # Configuración del servicio
    service_name: str = "clip-selector"
    service_host: str = "0.0.0.0"
    service_port: int = 8002
    
    # Registro (logging)
    log_level: str = "INFO"
    
    # Directorio temporal
    temp_dir: str = "/tmp/clip_processing"
    
    @property
    def viral_keywords(self) -> List[str]:
        """Analiza las palabras clave virales expandidas desde la variable de entorno"""
        return [keyword.strip() for keyword in self.viral_keywords_str.split(',') if keyword.strip()]
    
    @property
    def emotion_keywords(self) -> List[str]:
        """Analiza las palabras clave de emoción expandidas desde la variable de entorno"""
        return [keyword.strip() for keyword in self.emotion_keywords_str.split(',') if keyword.strip()]
    
    @property
    def viral_tier_levels(self) -> List[float]:
        """Obtiene los niveles de threshold para clasificación viral"""
        return [float(x.strip()) for x in self.viral_tier_thresholds.split(',')]
    
    class Config:
        env_file = ".env"
        # Mapear variables de entorno a los nombres de campo internos
        fields = {
            'viral_keywords_str': {'env': 'VIRAL_KEYWORDS'},
            'emotion_keywords_str': {'env': 'EMOTION_KEYWORDS'},
            'viral_tier_thresholds': {'env': 'VIRAL_TIER_THRESHOLDS'}
        }

settings = Settings()
