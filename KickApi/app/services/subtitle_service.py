"""
Servicio de generación de subtítulos
"""
import subprocess
import os
from typing import Optional
from app.core.config import Config
from app.services import SystemVerificationService


class SubtitleService:
    """Servicio para generar subtítulos usando Whisper"""
    
    @staticmethod
    def generate_subtitles_with_whisper(
        input_path: str, 
        output_dir: str, 
        language: str = "auto"
    ) -> Optional[str]:
        """
        Generar subtítulos automáticos usando OpenAI Whisper
        
        Args:
            input_path: Ruta del video de entrada
            output_dir: Directorio donde guardar los subtítulos
            language: Código de idioma (auto, es, en, etc.)
            
        Returns:
            Ruta al archivo SRT generado o None si falla
        """
        try:
            if not SystemVerificationService.check_whisper():
                print("⚠️ Whisper no disponible. Omitiendo generación de subtítulos.")
                return None
            
            print(f"🎤 Generando subtítulos automáticos con Whisper...")
            
            # Comando Whisper con ajustes optimizados
            cmd = [
                'whisper', input_path,
                '--output_dir', output_dir,
                '--output_format', 'srt',
                '--model', Config.WHISPER_MODEL,
                '--fp16', 'False',
                '--task', 'transcribe',
                '--no_speech_threshold', '0.6',
                '--condition_on_previous_text', 'False'
            ]
            
            if language != "auto" and language in ['es', 'en', 'fr', 'de', 'it', 'pt']:
                cmd.extend(['--language', language])
            
            # Ejecutar con timeout
            print(f"⏱️ Procesando audio con Whisper (timeout: {Config.WHISPER_TIMEOUT}s)...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=Config.WHISPER_TIMEOUT)
            
            if result.returncode != 0:
                print(f"⚠️ Whisper terminó con código {result.returncode}")
                if result.stderr:
                    print(f"Whisper stderr: {result.stderr[:200]}")
                return None
            
            # Buscar el archivo SRT generado
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            srt_path = os.path.join(output_dir, f"{base_name}.srt")
            
            if os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
                print(f"✅ Subtítulos generados: {os.path.basename(srt_path)} ({os.path.getsize(srt_path)} bytes)")
                return srt_path
            else:
                print("⚠️ No se generaron subtítulos o el archivo está vacío")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout: Whisper tardó más de {Config.WHISPER_TIMEOUT} segundos. Continuando sin subtítulos.")
            return None
        except Exception as e:
            print(f"❌ Error al generar subtítulos: {e}")
            return None
