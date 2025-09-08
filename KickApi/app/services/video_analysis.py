"""
Servicio de análisis de video
"""
import subprocess
import json
from typing import Dict, Any
from app.models import VideoInfo


class VideoAnalysisService:
    """Servicio para analizar propiedades de video"""
    
    @staticmethod
    def analyze_video(input_path: str) -> VideoInfo:
        """
        Analiza el video y devuelve información técnica
        
        Args:
            input_path: Ruta al archivo de video
            
        Returns:
            Objeto VideoInfo con las propiedades del video
        """
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', 
                '-show_streams', input_path
            ]
            # Ejecutar ffprobe y capturar salida JSON
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            data = json.loads(result.stdout)
            
            video_info = VideoInfo()
            
            # Extraer información de formato
            if 'format' in data:
                video_info.duration = float(data['format'].get('duration', 0))
                video_info.bitrate = int(data['format'].get('bit_rate', 0))
            
            # Extraer información de streams
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_info.width = stream.get('width', 0)
                    video_info.height = stream.get('height', 0)
                    video_info.codec = stream.get('codec_name', 'unknown')
                    
                    # Calcular FPS
                    fps_str = stream.get('r_frame_rate', '0/1')
                    if '/' in fps_str:
                        num, den = fps_str.split('/')
                        video_info.fps = int(num) / int(den) if int(den) > 0 else 0
                    
                    # Calcular relación de aspecto
                    if video_info.width > 0 and video_info.height > 0:
                        video_info.aspect_ratio = f"{video_info.width}:{video_info.height}"
                
                elif stream.get('codec_type') == 'audio':
                    video_info.has_audio = True
            
            # Mensaje de depuración en español
            print(f"📊 Análisis de video: {video_info.width}x{video_info.height}, {video_info.fps:.1f}fps, {video_info.duration:.1f}s")
            return video_info
            
        except Exception as e:
            # Mensaje de error en español
            print(f"⚠️ Error analizando video: {e}")
            return VideoInfo()  # Devolver valores por defecto
