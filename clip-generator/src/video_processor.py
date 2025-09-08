import os
import uuid
import logging
import ffmpeg
import subprocess
import json
from typing import List, Tuple
from config import settings
from deepseek_analyzer import DeepseekVideoAnalyzer

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.temp_dir = settings.temp_dir
        self.deepseek_analyzer = DeepseekVideoAnalyzer()
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def detect_highlights(self, video_path: str) -> List[Tuple[float, float]]:
        """
        Detecta los momentos destacados usando Deepseek AI para análisis inteligente
        Retorna una lista de tuplas (start_time, end_time)
        """
        try:
            logger.info(f"Iniciando detección de highlights con IA para: {video_path}")
            
            # Obtener la duración del video
            duration = await self._get_video_duration(video_path)
            
            if duration <= 0:
                logger.warning("No se pudo obtener la duración del video o es inválida")
                return []
            
            logger.info(f"Video duration: {duration:.2f}s - Analizando con Deepseek...")
            
            # Usar Deepseek para análisis inteligente de highlights
            highlights = await self.deepseek_analyzer.analyze_video_highlights(video_path)

            if not highlights:
                logger.warning("Deepseek no encontró highlights, usando análisis de respaldo")
                highlights = self._create_simple_segments(duration)

            logger.info(f"Detección completada: {len(highlights)} highlights identificados")
            for i, (start, end) in enumerate(highlights):
                logger.info(f"  Highlight {i+1}: {start:.2f}s - {end:.2f}s (duración: {end-start:.2f}s)")
            
            return highlights
            
        except Exception as e:
            logger.error(f"Error detectando puntos destacados: {e}")
            # Fallback a análisis simple
            duration = await self._get_video_duration(video_path)
            if duration > 0:
                return self._create_simple_segments(duration)
            return []
    
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
                logger.error(f"FFprobe error: {result.stderr}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error obteniendo la duración del video: {e}")
            return 0.0

    async def _get_video_dimensions(self, video_path: str) -> Tuple[int, int]:
        """Obtener el ancho y alto del video usando FFprobe"""
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
                logger.error(f"FFprobe error obteniendo dimensiones: {result.stderr}")
                return 1920, 1080  
                
        except Exception as e:
            logger.error(f"Error obteniendo dimensiones del video: {e}")
            return 1920, 1080  

    async def _check_audio_stream(self, video_path: str) -> bool:
        """Checkar si el video tiene pista de audio"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'csv=p=0',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            has_audio = result.returncode == 0 and 'audio' in result.stdout.strip()
            logger.info(f"Video tiene audio: {has_audio}")
            return has_audio
                
        except Exception as e:
            logger.error(f"Error obteniendo la pista de audio: {e}")
            return True

    def _create_simple_segments(self, duration: float) -> List[Tuple[float, float]]:
        """Crea segmentos simples basados en la duración del video"""
        
        segments = []
        max_clip_duration = settings.max_clip_duration
        min_clip_duration = settings.min_clip_duration

        logger.info(f"Crea segmentos para la duración del video: {duration:.2f}s "
                   f"(min: {min_clip_duration}s, max: {max_clip_duration}s)")
        
        # Si la duración es menor que la mínima, no crear clips
        if duration < min_clip_duration:
            logger.warning(f"Video demasiado corto ({duration:.2f}s < {min_clip_duration}s), omitiendo")
            return segments

        # Si el video es más corto que la duración máxima del clip, devolver el video completo
        if duration <= max_clip_duration:
            segments.append((0.0, duration))
            logger.info(f"Video cabe en un solo clip: 0.0s - {duration:.2f}s")
            return segments

        # Crear múltiples segmentos de max_clip_duration
        current_time = 0.0
        segment_count = 0
        
        while current_time < duration and segment_count < 10:  # Maximo 10 segmentos
            end_time = min(current_time + max_clip_duration, duration)

            # Solo agregar segmento si cumple con la duración mínima
            if end_time - current_time >= min_clip_duration:
                segments.append((current_time, end_time))
                logger.info(f"Agregado segmento {segment_count + 1}: {current_time:.2f}s - {end_time:.2f}s "
                           f"(duración: {end_time - current_time:.2f}s)")
                segment_count += 1
            
            # Mover el tiempo actual, con un pequeño solapamiento para continuidad
            current_time += max_clip_duration * 0.9  # 10% overlap

        logger.info(f"Se crearon {len(segments)} segmentos a partir del video de {duration:.2f}s")
        return segments
    
    async def create_clip(self, video_path: str, start_time: float, end_time: float, output_path: str) -> bool:
        """Crea un clip vertical (dimensiones configurables) a partir de un video horizontal con barras negras para redes sociales"""
        try:
            duration = end_time - start_time

            # Obtener dimensiones originales del video y verificar audio
            original_width, original_height = await self._get_video_dimensions(video_path)
            has_audio = await self._check_audio_stream(video_path)
            
            # Dimensiones objetivo desde la configuración (por defecto 1080x1920 para TikTok/Reels)
            default_w, default_h = 1080, 1920
            clip_w = getattr(settings, 'clip_width', default_w) or default_w
            clip_h = getattr(settings, 'clip_height', default_h) or default_h

            # Asegurar enteros válidos
            try:
                clip_w = int(clip_w)
                clip_h = int(clip_h)
            except Exception:
                clip_w, clip_h = default_w, default_h

            # Muchos códecs requieren dimensiones pares -> forzar paridad
            clip_w += clip_w % 2
            clip_h += clip_h % 2

            # Escribir de vuelta en settings para que la asignación siguiente use valores validados
            setattr(settings, 'clip_width', clip_w)
            setattr(settings, 'clip_height', clip_h)
            target_width = settings.clip_width
            target_height = settings.clip_height
            
            # Calcula la escala manteniendo la relación de aspecto
            # y asegurando que el video encaje dentro de las dimensiones objetivo
            # Queremos escalar en función del ancho, ya que estamos ajustando el video horizontal en un formato vertical
            scale_factor = target_width / original_width
            scaled_height = int(original_height * scale_factor)

            # Si la altura escalada excede nuestra altura objetivo, escalar en función de la altura en su lugar
            if scaled_height > target_height:
                scale_factor = target_height / original_height
                scaled_width = int(original_width * scale_factor)
                scaled_height = target_height
            else:
                scaled_width = target_width
            
            logger.info(f"Procesando clip {start_time:.2f}s-{end_time:.2f}s (duration: {duration:.2f}s)")
            logger.info(f"Escalando video de {original_width}x{original_height} a {scaled_width}x{scaled_height} "
                       f"para objetivo {target_width}x{target_height}")
            logger.info(f"Audio presente: {has_audio}")

            # Crear video vertical con fondo negro y video horizontal centrado
            input_stream = ffmpeg.input(video_path, ss=start_time, t=duration)
            
            # Procesamiento del video pipeline
            video = (
                input_stream
                .video
                .filter('setsar', '1')  # Asegura píxeles cuadrados para evitar problemas de relación de aspecto
                .filter('pad', target_width, target_height, '(ow-iw)/2', '(oh-ih)/2', 'black')  # Centrar video horizontal
            )
            
            video = (
                input_stream
                .video
                .filter('setsar', '1')  # píxeles cuadrados
                .filter('scale', scaled_width, scaled_height)  # escalar manteniendo la relación calculada
                .filter('pad', target_width, target_height, '(ow-iw)/2', '(oh-ih)/2', 'black')  # centrar sobre fondo negro
                .filter('fps', '30')  # forzar 30 fps
                .filter('format', 'yuv420p')  # formato compatible para redes sociales
            )
            if has_audio:
                audio = input_stream.audio
                # Combinar video y audio
                (
                    ffmpeg
                    .output(video, audio, output_path,
                           vcodec='libx264', 
                           acodec='aac',
                           preset='fast',
                           crf=23,
                           **{
                               'b:a': '128k',
                               'ar': '44100',  # Audio 
                               'ac': '2',      # Estéreo
                               'r': '30',      # 30 fps
                               'pix_fmt': 'yuv420p',  # Asegurar compatibilidad
                               'movflags': '+faststart'  # Habilitar inicio rápido para web
                           })
                    .overwrite_output()
                    .run(quiet=True, cmd=['ffmpeg'])
                )
            else:
                # Video solo (no audio)
                (
                    ffmpeg
                    .output(video, output_path,
                           vcodec='libx264', 
                           preset='fast',
                           crf=23,
                           **{
                               'r': '30',      # 30 fps
                               'pix_fmt': 'yuv420p',  # Asegurar compatibilidad
                               'movflags': '+faststart'  # Habilitar inicio rápido para web
                           })
                    .overwrite_output()
                    .run(quiet=True, cmd=['ffmpeg'])
                )

            logger.info(f"Clip vertical ({target_width}x{target_height}): {output_path} ({start_time:.2f}s - {end_time:.2f}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error al crear clip: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def cleanup_temp_files(self, *file_paths):
        """Limpia archivos temporales"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not clean up {file_path}: {e}")
