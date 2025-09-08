"""
Servicio de conversión de vídeo
"""
import subprocess
import asyncio
import os
import time
from typing import Dict, Any, Optional
from app.core.config import Config, QUALITY_SETTINGS, PLATFORM_MAPPINGS
from app.services.video_analysis import VideoAnalysisService
from app.services.subtitle_service import SubtitleService
from app.core.exceptions import ConversionError


class VideoConversionService:
    """Servicio para la conversión de formatos de vídeo"""
    
    @staticmethod
    def optimize_for_platform(quality: str, platform: str) -> str:
        """Optimiza la calidad según la plataforma"""
        return PLATFORM_MAPPINGS.get(platform.lower(), quality)
    
    @staticmethod
    async def convert_to_vertical_format_simple(
        input_path: str, 
        output_path: str, 
        quality: str = "medium"
    ) -> bool:
        """
        Conversión simplificada y robusta a formato vertical
        
        Args:
            input_path: Ruta del vídeo de entrada
            output_path: Ruta del vídeo de salida
            quality: Ajuste de calidad
            
        Returns:
            True si es exitoso, False en caso contrario
        """
        try:
            print(f"🎬 Iniciando conversión simplificada...")
            
            # Comando FFmpeg básico pero efectivo
            cmd = [
                "ffmpeg", "-i", input_path, "-y",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                output_path
            ]
            
            print(f"📋 Ejecutando: {' '.join(cmd[:5])}...")
            
            # Ejecutar con timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=Config.FFMPEG_TIMEOUT
            )
            
            if process.returncode == 0:
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"✅ Conversión completada: {os.path.getsize(output_path) / (1024*1024):.1f} MB")
                    return True
            
            error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "Error desconocido"
            print(f"❌ Error de FFmpeg: {error_msg[:200]}")
            return False
            
        except asyncio.TimeoutError:
            print("⚠️ Tiempo de conversión agotado")
            return False
        except Exception as e:
            print(f"❌ Error de conversión: {str(e)}")
            return False
    
    @staticmethod
    @staticmethod
    def convert_to_vertical_format_optimized(
        input_path: str, 
        output_path: str, 
        quality: str = "medium", 
        options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Convertir vídeo a formato vertical con optimizaciones avanzadas
        
        Args:
            input_path: Ruta del vídeo de entrada
            output_path: Ruta del vídeo de salida
            quality: Ajuste de calidad
            options: Opciones adicionales de procesamiento
            
        Returns:
            True si es exitoso, False en caso contrario
        """
        try:
            if options is None:
                options = {}
            
            # Comprobar si el modo dividido está habilitado
            if options.get("split", False):
                print("🔄 Modo dividido - separando vídeo en mitades izquierda/derecha")
                return VideoConversionService._convert_with_split(
                    input_path, output_path, quality, options
                )
            
            # Lógica original para modo no dividido
            # Analizar vídeo de entrada
            video_info = VideoAnalysisService.analyze_video(input_path)
            print(f"📊 Vídeo original: {video_info.width}x{video_info.height}, {video_info.fps:.1f}fps")

            settings = QUALITY_SETTINGS.get(quality, QUALITY_SETTINGS["medium"])
            target_width, target_height = map(int, settings["scale"].split(":"))
            
            # Usar bitrate personalizado si se especifica
            if options.get("custom_bitrate"):
                settings["bitrate"] = options["custom_bitrate"]
                settings["maxrate"] = str(int(options["custom_bitrate"].replace('k', '')) * 1.5) + 'k'
            
            # Generar subtítulos si se solicita
            subtitle_file = None
            if options.get("add_subtitles", False):
                temp_dir = os.path.dirname(output_path)
                subtitle_language = options.get("subtitle_language", "auto")
                subtitle_file = SubtitleService.generate_subtitles_with_whisper(
                    input_path, temp_dir, subtitle_language
                )
            
            # Usar conversión simplificada cuando se solicitan subtítulos para evitar conflictos de filtros
            if subtitle_file and os.path.exists(subtitle_file):
                print(f"📝 Usando conversión simplificada con subtítulos: {os.path.basename(subtitle_file)}")
                return VideoConversionService._convert_with_subtitles_simple(
                    input_path, output_path, subtitle_file, quality
                )
            
            # Construir filtro complejo
            filter_parts = []
            
            # División de entrada
            filter_parts.append("[0:v]split=2[bg][main]")
            
            # Fondo difuminado
            bg_filter = (
                f"[bg]scale={target_width*1.5}:{target_height*1.5}:force_original_aspect_ratio=increase,"
                f"crop={target_width}:{target_height}:({target_width*1.5}-{target_width})/2:({target_height*1.5}-{target_height})/2,"
                f"gblur=sigma=15:steps=3[blurred_bg]"
            )
            filter_parts.append(bg_filter)
            
            # Escalado del vídeo principal
            main_filter = (
                f"[main]scale='if(gt(iw/ih,{target_width}/{target_height}),{target_width},-1)':'if(gt(iw/ih,{target_width}/{target_height}),-1,{target_height})':flags=lanczos,"
                f"pad={target_width}:{target_height}:({target_width}-iw)/2:({target_height}-ih)/2:color=black[main_scaled]"
            )
            filter_parts.append(main_filter)
            
            # Aplicar filtros adicionales si se solicita
            if options.get("apply_filters"):
                filters = options["apply_filters"]
                additional_filters = []
                
                if filters.get("denoise", False):
                    additional_filters.append("hqdn3d=2:1:2:1")
                
                if filters.get("sharpen", False):
                    strength = filters.get("sharpen_strength", 0.3)
                    additional_filters.append(f"unsharp=5:5:{strength}:5:5:{strength}")
                
                if filters.get("color_correction", False):
                    brightness = filters.get("brightness", 0.0)
                    contrast = filters.get("contrast", 1.0)
                    saturation = filters.get("saturation", 1.0)
                    gamma = filters.get("gamma", 1.0)
                    additional_filters.append(f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}:gamma={gamma}")
                
                if additional_filters:
                    main_filter = main_filter.replace("[main_scaled]", f",{','.join(additional_filters)}[main_scaled]")
                    filter_parts[-1] = main_filter
            
            # Componer resultado final
            filter_parts.append("[blurred_bg][main_scaled]overlay=0:0[video_out]")
            
            # Añadir subtítulos si están disponibles
            if subtitle_file and os.path.exists(subtitle_file):
                print(f"📝 Integrando subtítulos: {os.path.basename(subtitle_file)}")
                subtitle_filter = f"subtitles='{subtitle_file.replace(chr(92), '/')}':force_style='FontName=Arial,FontSize=16,PrimaryColour=&Hffffff,SecondaryColour=&Hffffff,OutlineColour=&H000000,BackColour=&H80000000,Outline=2,Shadow=1,Bold=0,Alignment=2,MarginV=40'"
                
                if len(filter_parts) > 0:
                    last_filter = filter_parts[-1]
                    filter_parts[-1] = last_filter.replace("[video_out]", f"[video_temp];[video_temp]{subtitle_filter}[video_out]")
            
            filter_complex = ";".join(filter_parts)
            
            # FPS objetivo
            target_fps = options.get("target_fps", 30)
            
            # Construir comando FFmpeg
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path,
                '-filter_complex', filter_complex,
                '-map', '[video_out]',
                '-map', '0:a?',  # Audio opcional
                 
                # Configuración de codificación de vídeo
                '-c:v', 'libx264',
                '-profile:v', 'high',
                '-level', '4.2',
                '-x264-params', 'me=hex:subme=8:ref=3:bframes=3:b-pyramid=normal:weightb=1:analyse=all:8x8dct=1:deadzone-inter=21:deadzone-intra=11:me-range=24:chroma-me=1:cabac=1:ref=3:deblock=1:analyse=0x3:0x113:subme=8:psy=1:psy_rd=1.00:0.00:mixed_ref=1:me_range=16:chroma_me=1:trellis=2:8x8dct=1:cqm=0:deadzone=21,11:fast_pskip=1:chroma_qp_offset=-2:threads=auto:lookahead_threads=auto:sliced_threads=0:nr=0:decimate=1:interlaced=0:bluray_compat=0:constrained_intra=0:fgo=0',
                
                # Control de calidad
                '-crf', settings["crf"],
                '-maxrate', settings["maxrate"],
                '-bufsize', settings["bufsize"],
                '-preset', settings["preset"],
                
                # Ajustes de frame rate
                '-r', str(target_fps),
                '-g', str(target_fps * 2),
                '-keyint_min', str(target_fps),
                
                # Configuración de audio
                '-c:a', 'aac',
                '-b:a', settings["audio_bitrate"],
                '-ar', '48000',
                '-ac', '2',
                '-af', 'acompressor=threshold=0.5:ratio=3:attack=10:release=80,alimiter=level_in=1:level_out=0.9:limit=0.95',
                
                # Formato de píxeles y compatibilidad
                '-pix_fmt', 'yuv420p',
                '-colorspace', 'bt709',
                '-color_primaries', 'bt709',
                '-color_trc', 'bt709',
                '-movflags', '+faststart+frag_keyframe+separate_moof+omit_tfhd_offset+disable_chpl',
                
                # Optimización de rendimiento
                '-threads', '0',
                '-avoid_negative_ts', 'make_zero',
                '-shortest',
                '-fflags', '+genpts+igndts',
                
                # Metadata
                '-metadata', f'title=Vídeo Vertical - {quality.upper()}',
                '-metadata', f'comment=Procesado con KickAPI - Calidad: {quality}',
                
                output_path, '-y'
            ]
            
            print(f"🔄 Convirtiendo vídeo con calidad ULTRA OPTIMIZADA: {quality}")
            print(f"🎯 Configuración: {settings['scale']}, {settings['bitrate']}, CRF:{settings['crf']}")
            if subtitle_file:
                print(f"📝 Subtítulos incluidos: {os.path.basename(subtitle_file)}")
            
            # Ejecutar comando con monitorización de progreso
            process = subprocess.Popen(
                ffmpeg_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                universal_newlines=True
            )
            
            # Monitorizar progreso
            stderr_output = ""
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    stderr_output += output
                    if 'time=' in output:
                        # Extraer tiempo de progreso
                        for part in output.split():
                            if part.startswith('time='):
                                current_time = part.split('=')[1]
                                print(f"⏱️ Progreso: {current_time}", end='\r')
            
            rc = process.poll()
            
            if rc == 0:
                # Verificar archivo de salida
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    final_size = os.path.getsize(output_path)
                    print(f"\n✅ Conversión ULTRA OPTIMIZADA completada con éxito")
                    print(f"📁 Archivo final: {final_size / (1024*1024):.1f} MB")
                    
                    # Analizar vídeo final
                    final_info = VideoAnalysisService.analyze_video(output_path)
                    print(f"📊 Vídeo final: {final_info.width}x{final_info.height}, {final_info.fps:.1f}fps")
                    
                    # Mantener archivo de subtítulos temporalmente para depuración
                    if subtitle_file and os.path.exists(subtitle_file):
                        print(f"🐛 Archivo de subtítulos conservado para depuración: {subtitle_file}")
                        # try:
                        #     os.remove(subtitle_file)
                        #     print(f"🧹 Archivo temporal de subtítulos eliminado")
                        # except:
                        #     pass
                    
                    return True
                else:
                    print(f"\n❌ Error: archivo de salida inválido")
                    return False
            else:
                print(f"\n❌ Error de FFmpeg (código {rc})")
                if stderr_output:
                    print(f"FFmpeg stderr: {stderr_output[-500:]}")
                return False
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error de FFmpeg: {e}")
            if e.stderr:
                print(f"FFmpeg stderr: {e.stderr[-300:]}")
            
            # Reintentar sin subtítulos si el error puede estar relacionado con subtítulos
            if options.get("add_subtitles", False):
                print("🔧 Reintentando conversión sin subtítulos...")
                options_no_subs = options.copy()
                options_no_subs["add_subtitles"] = False
                return VideoConversionService.convert_to_vertical_format_optimized(
                    input_path, output_path, quality, options_no_subs
                )
            else:
                # Intentar fallback simple
                print("🔧 Intentando conversión con configuración simplificada...")
                return VideoConversionService._convert_simple_fallback(input_path, output_path, quality)
            
        except Exception as e:
            print(f"❌ Error al convertir el vídeo: {e}")
            
            # Intentar fallback si se solicitaron subtítulos
            if options and options.get("add_subtitles", False):
                print("🔧 Reintentando sin subtítulos debido al error...")
                options_no_subs = options.copy()
                options_no_subs["add_subtitles"] = False
                return VideoConversionService.convert_to_vertical_format_optimized(
                    input_path, output_path, quality, options_no_subs
                )
            
            return False
    
    @staticmethod
    def _convert_simple_fallback(input_path: str, output_path: str, quality: str = "medium") -> bool:
        """Conversión de respaldo con filtro simple"""
        try:
            print("🔧 Iniciando conversión de respaldo simplificada...")
            
            settings = QUALITY_SETTINGS.get(quality, QUALITY_SETTINGS["medium"])
            target_width, target_height = map(int, settings["scale"].split(":"))
            
            # Filtro simple pero efectivo: escalar y añadir relleno negro
            video_filter = f'scale=\'if(gt(iw/ih,{target_width}/{target_height}),{target_width},-1)\':\'if(gt(iw/ih,{target_width}/{target_height}),-1,{target_height})\',pad={target_width}:{target_height}:({target_width}-iw)/2:({target_height}-ih)/2:color=black'
            
            # Comando FFmpeg simplificado pero optimizado
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', video_filter,
                '-c:v', 'libx264',
                '-profile:v', 'high',
                '-level', '4.2',
                '-crf', settings["crf"],
                '-preset', settings["preset"],
                '-c:a', 'aac',
                '-b:a', '128k',
                '-ar', '48000',
                '-ac', '2',
                '-r', '30',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-threads', '0',
                '-y', output_path
            ]
            
            print(f"🔧 Ejecutando conversión de respaldo...")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=Config.FFMPEG_TIMEOUT)
            
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"✅ Conversión de respaldo completada con éxito")
                return True
            else:
                print(f"❌ Error de FFmpeg en respaldo (código {result.returncode})")
                if result.stderr:
                    print(f"FFmpeg stderr: {result.stderr[-200:]}")
                return False
            
        except subprocess.TimeoutExpired:
            print("❌ Tiempo de espera de conversión de respaldo agotado (5 minutos)")
            return False
        except Exception as e:
            print(f"❌ Error en respaldo: {e}")
            return False
    
    @staticmethod
    async def convert_m3u8_to_mp4(m3u8_url: str, output_path: str) -> bool:
        """Convertir stream M3U8 a MP4"""
        cmd = [
            'ffmpeg', '-i', m3u8_url, 
            '-c', 'copy', '-bsf:a', 'aac_adtstoasc', 
            '-f', 'mp4', output_path, '-y'
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    
    @staticmethod
    def _convert_with_subtitles_simple(input_path: str, output_path: str, subtitle_file: str, quality: str = "medium") -> bool:
        """Conversión simple con overlay de subtítulos para máxima compatibilidad"""
        try:
            print("🎬 Iniciando conversión simplificada con subtítulos...")
            
            settings = QUALITY_SETTINGS.get(quality, QUALITY_SETTINGS["medium"])
            target_width, target_height = map(int, settings["scale"].split(":"))
            
            # Conversión simple pero efectiva con subtítulos - Pequeños, centrados, posicionados abajo
            subtitle_filter = f"subtitles='{subtitle_file.replace(chr(92), '/')}':force_style='FontName=Arial,FontSize=16,PrimaryColour=&Hffffff,SecondaryColour=&Hffffff,OutlineColour=&H000000,BackColour=&H80000000,Outline=2,Shadow=1,Bold=0,Alignment=2,MarginV=40'"
            video_filter = f'scale=\'if(gt(iw/ih,{target_width}/{target_height}),{target_width},-1)\':\'if(gt(iw/ih,{target_width}/{target_height}),-1,{target_height})\',pad={target_width}:{target_height}:({target_width}-iw)/2:({target_height}-ih)/2:color=black,{subtitle_filter}'
            
            # Comando FFmpeg simplificado optimizado para subtítulos
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', video_filter,
                '-c:v', 'libx264',
                '-profile:v', 'high',
                '-level', '4.2',
                '-crf', settings["crf"],
                '-preset', 'medium',  # Usar preset medium para estabilidad
                '-c:a', 'aac',
                '-b:a', '128k',
                '-ar', '48000',
                '-ac', '2',
                '-r', '30',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-threads', '0',
                '-y', output_path
            ]
            
            print(f"🔧 Ejecutando conversión de subtítulos con configuración estable...")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=Config.FFMPEG_TIMEOUT)
            
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"✅ Conversión con subtítulos completada con éxito")
                
                # Mantener archivo de subtítulos temporalmente para depuración
                print(f"🐛 Archivo de subtítulos conservado para depuración: {subtitle_file}")
                # Clean up temporary subtitle file
                # try:
                #     os.remove(subtitle_file)
                #     print(f"🧹 Archivo temporal de subtítulos eliminado")
                # except:
                #     pass
                
                return True
            else:
                print(f"❌ Error en conversión con subtítulos (código {result.returncode})")
                if result.stderr:
                    print(f"FFmpeg stderr: {result.stderr[-300:]}")
                
                # Fallback: intentar sin subtítulos
                print("🔧 Reintentando sin subtítulos como respaldo...")
                return VideoConversionService._convert_simple_fallback(input_path, output_path, quality)
            
        except subprocess.TimeoutExpired:
            print("❌ Tiempo de espera en conversión de subtítulos")
            return VideoConversionService._convert_simple_fallback(input_path, output_path, quality)
        except Exception as e:
            print(f"❌ Error en conversión con subtítulos: {e}")
            return VideoConversionService._convert_simple_fallback(input_path, output_path, quality)

    @staticmethod
    async def convert_m3u8_to_mp3(m3u8_url: str, output_path: str) -> bool:
        """Convertir stream M3U8 a MP3"""
        cmd = [
            'ffmpeg', '-i', m3u8_url, 
            '-vn', '-acodec', 'mp3', '-ab', '192k', 
            output_path, '-y'
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0

    @staticmethod
    def _convert_with_split(
        input_path: str, 
        output_path: str, 
        quality: str, 
        options: Dict[str, Any]
    ) -> bool:
        """
        Convertir vídeo con funcionalidad de división - divide el vídeo en mitades izquierda/derecha,
        colocando la mitad izquierda arriba y la derecha abajo manteniendo el ancho original de la plataforma
        """
        try:
            # Analizar vídeo de entrada para obtener dimensiones originales
            video_info = VideoAnalysisService.analyze_video(input_path)
            print(f"📊 Vídeo original: {video_info.width}x{video_info.height}, {video_info.fps:.1f}fps")
            
            # Obtener configuración de calidad
            settings = QUALITY_SETTINGS.get(quality, QUALITY_SETTINGS["medium"])
            
            # Usar bitrate personalizado si se especifica
            if options.get("custom_bitrate"):
                settings["bitrate"] = options["custom_bitrate"]
                settings["maxrate"] = str(int(options["custom_bitrate"].replace('k', '')) * 1.5) + 'k'
            
            # FPS objetivo
            target_fps = options.get("target_fps", 30)
            
            # Calcular dimensiones para salida vertical (1080x1920)
            # Cada mitad será 1080x960 cuando se apilen verticalmente
            output_width = 1080
            output_height = 1920
            half_height = output_height // 2  # 960
            
            print(f"🎯 Dimensiones en modo dividido: {output_width}x{output_height} (cada mitad: {output_width}x{half_height})")
            
            # Aplicar filtros adicionales si se solicitan
            additional_filters = []
            if options.get("apply_filters"):
                filters = options["apply_filters"]
                
                if filters.get("denoise", False):
                    additional_filters.append("hqdn3d=2:1:2:1")
                
                if filters.get("sharpen", False):
                    strength = filters.get("sharpen_strength", 0.3)
                    additional_filters.append(f"unsharp=5:5:{strength}:5:5:{strength}")
                
                if filters.get("color_correction", False):
                    brightness = filters.get("brightness", 0.0)
                    contrast = filters.get("contrast", 1.0)
                    saturation = filters.get("saturation", 1.0)
                    gamma = filters.get("gamma", 1.0)
                    additional_filters.append(f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}:gamma={gamma}")
            
            # Construir filter_complex para modo dividido preservando ancho original
            filter_complex = (
                "[0:v]crop=iw/2:ih:0:0[left];"
                "[0:v]crop=iw/2:ih:iw/2:0[right];"
                f"[left]scale={output_width}:{half_height}[left_scaled];"
                f"[right]scale={output_width}:{half_height}[right_scaled];"
                "[left_scaled][right_scaled]vstack=inputs=2[outv]"
            )
            
            # Si hay filtros adicionales, aplicarlos antes del recorte
            if additional_filters:
                additional_filter_str = ",".join(additional_filters)
                filter_complex = (
                    f"[0:v]{additional_filter_str}[filtered];"
                    "[filtered]crop=iw/2:ih:0:0[left];"
                    "[filtered]crop=iw/2:ih:iw/2:0[right];"
                    f"[left]scale={output_width}:{half_height}[left_scaled];"
                    f"[right]scale={output_width}:{half_height}[right_scaled];"
                    "[left_scaled][right_scaled]vstack=inputs=2[outv]"
                )
            
            # Construir comando FFmpeg - AHORA INCLUYENDO AUDIO
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path,
                '-filter_complex', filter_complex,
                '-map', '[outv]',  # Mapear la salida de vídeo procesada
                '-map', '0:a?',    # Mapear la pista de audio si está disponible
                 
                # Configuración de codificación de vídeo
                '-c:v', 'libx264',
                '-profile:v', 'high',
                '-level', '4.2',
                '-crf', settings["crf"],
                '-preset', settings["preset"],
                '-maxrate', settings["maxrate"],
                '-bufsize', settings["bufsize"],
                
                # Ajustes de frame rate
                '-r', str(target_fps),
                '-g', str(target_fps * 2),
                '-keyint_min', str(target_fps),
                
                # Configuración de audio - PRESERVAR AUDIO
                '-c:a', 'aac',
                '-b:a', settings["audio_bitrate"],
                '-ar', '48000',
                '-ac', '2',
                '-af', 'acompressor=threshold=0.5:ratio=3:attack=10:release=80,alimiter=level_in=1:level_out=0.9:limit=0.95',
                
                # Formato de píxeles y compatibilidad
                '-pix_fmt', 'yuv420p',
                '-colorspace', 'bt709',
                '-color_primaries', 'bt709',
                '-color_trc', 'bt709',
                '-movflags', '+faststart+frag_keyframe+separate_moof+omit_tfhd_offset+disable_chpl',
                
                # Optimización de rendimiento
                '-threads', '0',
                '-avoid_negative_ts', 'make_zero',
                '-shortest',
                '-fflags', '+genpts+igndts',
                
                # Metadata
                '-metadata', f'title=Vídeo Dividido - {quality.upper()}',
                '-metadata', f'comment=Procesado en modo dividido con KickAPI - Calidad: {quality}',
                
                output_path, '-y'
            ]
            
            print(f"🔄 Convirtiendo vídeo en modo DIVIDIDO - Calidad: {quality}")
            print(f"🎯 Formato de salida: {output_width}x{output_height} (formato vertical para {quality} con audio)")
            print(f"📊 Cada mitad: {output_width}x{half_height}")
            
            # Ejecutar comando con monitorización de progreso
            process = subprocess.Popen(
                ffmpeg_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                universal_newlines=True
            )
            
            # Monitorizar progreso
            stderr_output = ""
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    stderr_output += output
                    if 'time=' in output:
                        # Extraer tiempo de progreso
                        for part in output.split():
                            if part.startswith('time='):
                                current_time = part.split('=')[1]
                                print(f"⏱️ Progreso (dividido): {current_time}", end='\r')
            
            rc = process.poll()
            
            if rc == 0:
                # Verificar archivo de salida
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    final_size = os.path.getsize(output_path)
                    print(f"\n✅ Conversión DIVIDIDA con AUDIO completada con éxito")
                    print(f"📁 Archivo final: {final_size / (1024*1024):.1f} MB")
                    
                    # Analizar vídeo final
                    final_info = VideoAnalysisService.analyze_video(output_path)
                    print(f"📊 Vídeo final: {final_info.width}x{final_info.height}, {final_info.fps:.1f}fps")
                    print(f"🔊 Audio preservado: {final_info.audio_codec if hasattr(final_info, 'audio_codec') else 'Sí'}")
                    
                    return True
                else:
                    print(f"\n❌ Error: archivo de salida inválido en modo dividido")
                    return False
            else:
                error_lines = stderr_output.split('\n')[-10:]
                error_msg = '\n'.join([line for line in error_lines if line.strip()])
                print(f"\n❌ Falló la conversión dividida de FFmpeg (código {rc}):")
                print(f"Error: {error_msg[:500]}")
                return False
                
        except Exception as e:
            print(f"❌ Error en conversión dividida: {str(e)}")
            return False
