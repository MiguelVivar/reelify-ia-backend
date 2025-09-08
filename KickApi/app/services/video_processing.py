"""
Servicio de procesamiento de video - Orquestador principal
"""
import os
import time
import tempfile
import shutil
import requests
from typing import Dict, Any, Optional
from app.core.config import Config, DEFAULT_HEADERS
from app.services.video_conversion import VideoConversionService
from app.services.video_analysis import VideoAnalysisService
from app.utils.cache import cache_manager
from app.utils import extract_filename_from_url
from app.models import OptimizedVideoRequest, ProcessingStats
from app.core.exceptions import DownloadError, ConversionError


class VideoProcessingService:
    """Servicio principal para la orquestación del procesamiento de video"""
    
    @staticmethod
    def get_processing_options_from_request(request: OptimizedVideoRequest) -> Dict[str, Any]:
        """Convertir la solicitud a opciones de procesamiento para FFmpeg"""
        options = {
            "add_subtitles": request.add_subtitles,
            "subtitle_language": request.subtitle_language,
            "target_fps": request.target_fps,
            "custom_bitrate": request.custom_bitrate,
            "split": request.split,  # Añadir opción de división
        }
        
        # Configurar filtros de video
        apply_filters = {}
        
        if request.apply_denoise:
            apply_filters["denoise"] = True
        
        if request.apply_sharpen:
            apply_filters["sharpen"] = True
            apply_filters["sharpen_strength"] = max(0.1, min(1.0, request.sharpen_strength))
        
        if request.apply_stabilization:
            apply_filters["stabilize"] = True
        
        if request.apply_color_correction:
            apply_filters["color_correction"] = True
            apply_filters["brightness"] = max(-1.0, min(1.0, request.brightness))
            apply_filters["contrast"] = max(0.1, min(3.0, request.contrast))
            apply_filters["saturation"] = max(0.0, min(3.0, request.saturation))
            apply_filters["gamma"] = max(0.1, min(3.0, request.gamma))
        
        if apply_filters:
            options["apply_filters"] = apply_filters
        
        return options
    
    @staticmethod
    async def process_video_background_advanced(
        cache_key: str,
        video_id: str, 
        video_url: str, 
        quality: str, 
        options: Dict[str, Any]
    ) -> None:
        """Procesar video en segundo plano con opciones avanzadas"""
        temp_dir = None
        try:
            print(f"🎬 Iniciando procesamiento ULTRA AVANZADO para {video_id} (cache: {cache_key})")
            
            # Actualizar estado
            cache_manager.video_cache.update(cache_key, {"status": "downloading"})
            
            # Crear directorio temporal
            temp_dir = tempfile.mkdtemp()
            
            # Usar video_id (nombre limpio) para nombrar archivos
            base_name = video_id
            
            # Generar nombres de archivo usando video_id
            input_filename = f"input_{base_name}.mp4"
            output_filename = f"{base_name}.mp4"
            
            input_path = os.path.join(temp_dir, input_filename)
            temp_output_path = os.path.join(temp_dir, output_filename)
            
            # Descargar video con cabeceras mejoradas
            print(f"⬇️ Descargando video para {video_id}: {video_url}")
            
            response = requests.get(
                video_url, 
                stream=True, 
                timeout=Config.DOWNLOAD_TIMEOUT,
                headers=DEFAULT_HEADERS
            )
            response.raise_for_status()
            
            # Descargar con progreso
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(input_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=Config.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"📥 Descarga: {progress:.1f}%", end='\r')
            
            print(f"\n✅ Descarga completada para {video_id}: {os.path.getsize(input_path) / (1024*1024):.1f} MB")
            
            # Analizar video descargado
            print(f"📊 Analizando video original...")
            video_info = VideoAnalysisService.analyze_video(input_path)
            
            # Actualizar estado
            cache_manager.video_cache.update(cache_key, {
                "status": "converting",
                "original_info": video_info.dict()
            })
            
            # Preparar opciones de conversión con valores por defecto
            conversion_options = {
                "add_subtitles": options.get("add_subtitles", False),
                "subtitle_language": options.get("subtitle_language", "auto"),
                "target_fps": options.get("target_fps", 30),
                "custom_bitrate": options.get("custom_bitrate"),
                "apply_filters": options.get("apply_filters", {}),
                "split": options.get("split", False)  # Añadir opción de división
            }
            
            # Convertir video con opciones avanzadas
            start_time = time.time()
            print(f"🎬 Convirtiendo video {video_id} con calidad: {quality}")
            
            # Usar conversión optimizada cuando se soliciten subtítulos, filtros o división, de lo contrario usar simple
            if (conversion_options.get("add_subtitles") or 
                conversion_options.get("apply_filters") or 
                conversion_options.get("split", False)):
                print(f"🎯 Usando conversión optimizada con subtítulos/filtros/división")
                conversion_success = VideoConversionService.convert_to_vertical_format_optimized(
                    input_path, 
                    temp_output_path, 
                    quality,
                    conversion_options
                )
            else:
                print(f"🎯 Usando conversión simplificada (sin subtítulos/filtros)")
                conversion_success = await VideoConversionService.convert_to_vertical_format_simple(
                    input_path, 
                    temp_output_path, 
                    quality
                )
            
            if conversion_success and os.path.exists(temp_output_path):
                conversion_time = time.time() - start_time
                file_size = os.path.getsize(temp_output_path)
                
                # Analizar video final
                final_info = VideoAnalysisService.analyze_video(temp_output_path)
                
                # Calcular estadísticas
                compression_ratio = video_info.bitrate / final_info.bitrate if final_info.bitrate > 0 else 0
                
                # Calcular estadísticas de procesamiento
                processing_stats = ProcessingStats(
                    original_size=os.path.getsize(input_path),
                    final_size=file_size,
                    size_reduction=((os.path.getsize(input_path) - file_size) / os.path.getsize(input_path)) * 100,
                    original_resolution=f"{video_info.width}x{video_info.height}",
                    final_resolution=f"{final_info.width}x{final_info.height}",
                    original_fps=video_info.fps,
                    final_fps=final_info.fps,
                    filters_applied=len(options.get("apply_filters", {})),
                    subtitles_generated=options.get("add_subtitles", False)
                )
                
                # Actualizar cache con éxito
                cache_manager.video_cache.update(cache_key, {
                    "status": "completed",
                    "file_path": temp_output_path,
                    "file_size": file_size,
                    "conversion_time": conversion_time,
                    "completed_at": time.time(),
                    "temp_dir": temp_dir,
                    "filename": output_filename,
                    "final_info": final_info.dict(),
                    "compression_ratio": compression_ratio,
                    "processing_stats": processing_stats.dict()
                })
                
                print(f"\n✅ Video {video_id} procesado exitosamente con ULTRA OPTIMIZACIÓN")
                print(f"⏱️ Tiempo total: {conversion_time:.1f}s")
                print(f"📁 Archivo final: {file_size / (1024*1024):.1f} MB")
                print(f"📊 Resolución final: {final_info.width}x{final_info.height}")
                print(f"🎯 FPS final: {final_info.fps:.1f}")
                
                if options.get("apply_filters"):
                    print(f"🎨 Filtros aplicados: {len(options['apply_filters'])} filtros")
                if options.get("add_subtitles"):
                    print(f"🎤 Subtítulos automáticos incluidos")
                
                # No limpiar temp_dir aquí, se limpiará cuando caduque el cache
            else:
                # Error de conversión
                cache_manager.video_cache.update(cache_key, {
                    "status": "error",
                    "error": "Error en la conversión de video con configuración avanzada"
                })
                
                print(f"❌ Error procesando video {video_id} con configuración avanzada")
                
                # Limpiar en caso de error
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass
                
        except Exception as e:
            print(f"❌ Error en el procesamiento avanzado en segundo plano para {video_id}: {e}")
            # Actualizar cache con error
            cache_manager.video_cache.update(cache_key, {
                "status": "error",
                "error": str(e)
            })
            
            # Limpiar en caso de error
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
