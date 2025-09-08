"""
Servicio de verificación del sistema
"""
import subprocess
import json
from typing import Dict, List, Any
from app.core.exceptions import FFmpegNotAvailableError, WhisperNotAvailableError


class SystemVerificationService:
    """Servicio para verificar las capacidades del sistema"""

    @staticmethod
    def check_ffmpeg() -> bool:
        """Comprobar si FFmpeg está disponible"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                check=True,
                text=True
            )
            # Mensaje de depuración en español
            print(f"✅ FFmpeg disponible: {result.stdout.split()[2] if len(result.stdout.split()) > 2 else 'versión detectada'}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Mensaje de depuración en español
            print("❌ FFmpeg no encontrado. Instale FFmpeg para usar las funciones de conversión.")
            return False

    @staticmethod
    def check_whisper() -> bool:
        """Comprobar si Whisper está disponible"""
        try:
            subprocess.run(['whisper', '--help'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def get_ffmpeg_info() -> Dict[str, Any]:
        """Obtener información detallada de FFmpeg"""
        info = {
            "ffmpeg_available": SystemVerificationService.check_ffmpeg(),
            "whisper_available": SystemVerificationService.check_whisper()
        }

        if info["ffmpeg_available"]:
            try:
                # Obtener la versión de FFmpeg
                result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                version_line = lines[0] if lines else "Unknown"

                # Obtener códecs disponibles
                codecs_result = subprocess.run(['ffmpeg', '-codecs'], capture_output=True, text=True)

                # Comprobar códecs específicos
                h264_available = 'libx264' in codecs_result.stdout
                aac_available = 'aac' in codecs_result.stdout

                # Obtener filtros disponibles
                filters_result = subprocess.run(['ffmpeg', '-filters'], capture_output=True, text=True)

                # Comprobar filtros específicos
                filters_available = {
                    "gblur": "gblur" in filters_result.stdout,
                    "unsharp": "unsharp" in filters_result.stdout,
                    "nlmeans": "nlmeans" in filters_result.stdout,
                    "hqdn3d": "hqdn3d" in filters_result.stdout,
                    "eq": "eq" in filters_result.stdout,
                    "scale": "scale" in filters_result.stdout,
                    "subtitles": "subtitles" in filters_result.stdout,
                    "vidstabdetect": "vidstabdetect" in filters_result.stdout,
                    "vidstabtransform": "vidstabtransform" in filters_result.stdout
                }

                info.update({
                    "ffmpeg_version": version_line,
                    "codecs": {
                        "h264_libx264": h264_available,
                        "aac": aac_available
                    },
                    "filters": filters_available,
                    "capabilities": {
                        "vertical_conversion": True,
                        "background_blur": filters_available["gblur"],
                        "video_stabilization": filters_available["vidstabdetect"] and filters_available["vidstabtransform"],
                        "noise_reduction": filters_available["nlmeans"] or filters_available["hqdn3d"],
                        "sharpening": filters_available["unsharp"],
                        "color_correction": filters_available["eq"],
                        "subtitle_overlay": filters_available["subtitles"],
                        "professional_scaling": filters_available["scale"]
                    }
                })

            except Exception as e:
                # Guardar error de FFmpeg en español para depuración
                info["ffmpeg_error"] = str(e)

        if info["whisper_available"]:
            try:
                # Verificar versión de Whisper (comprobación básica)
                result = subprocess.run(['whisper', '--help'], capture_output=True, text=True)
                info["whisper_info"] = {
                    "available": True,
                    "models": ["tiny", "base", "small", "medium", "large"],
                    "languages": ["auto", "es", "en", "fr", "de", "it", "pt", "ja", "ko", "zh", "ar", "ru"],
                    "formats": ["srt", "vtt", "txt", "json"]
                }
            except Exception as e:
                # Guardar error de Whisper en español para depuración
                info["whisper_error"] = str(e)

        return info

    @staticmethod
    def get_system_recommendations() -> List[Dict[str, str]]:
        """Obtener recomendaciones de configuración del sistema"""
        recommendations = []
        info = SystemVerificationService.get_ffmpeg_info()

        if not info["ffmpeg_available"]:
            recommendations.append({
                "component": "FFmpeg",
                "issue": "Not installed",
                "solution": "Install FFmpeg from https://ffmpeg.org/download.html",
                "impact": "Video processing will not work without FFmpeg"
            })

        if not info["whisper_available"]:
            recommendations.append({
                "component": "OpenAI Whisper",
                "issue": "Not installed",
                "solution": "Run: pip install openai-whisper",
                "impact": "Automatic subtitle generation will not work without Whisper"
            })

        if info["ffmpeg_available"] and not info.get("capabilities", {}).get("video_stabilization", False):
            recommendations.append({
                "component": "VidStab (stabilization)",
                "issue": "Stabilization filters not available",
                "solution": "Compile FFmpeg with --enable-libvidstab or use a complete build",
                "impact": "Video stabilization will not work"
            })

        return recommendations

    @staticmethod
    def verify_ffmpeg_or_raise() -> None:
        """Verificar que FFmpeg esté disponible o lanzar excepción"""
        if not SystemVerificationService.check_ffmpeg():
            raise FFmpegNotAvailableError("FFmpeg is not available. Install FFmpeg to use conversion functions.")

    @staticmethod
    def verify_whisper_or_raise() -> None:
        """Verificar que Whisper esté disponible o lanzar excepción"""
        if not SystemVerificationService.check_whisper():
            raise WhisperNotAvailableError("Whisper is not available. Install OpenAI Whisper for subtitle generation.")
