"""
Funciones de utilidad para KickAPI
"""
import os
import hashlib
import random
import string
import time
from urllib.parse import urlparse
from typing import Optional, Generator


def extract_filename_from_url(url: str) -> str:
    """
    Extraer un nombre de archivo único de la URL
    
    Args:
        url: URL del video
        
    Returns:
        Nombre de archivo extraído o ID único generado
    """
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        # Para URLs de clips de Kick.com
        if 'kick.com' in parsed.netloc and '/clips/' in path:
            clip_id = path.split('/clips/')[-1].split('?')[0].split('#')[0]
            if clip_id:
                return clip_id
        
        # Para URLs de almacenamiento (como asumarket.com)
        if path and path != '/':
            filename = path.split('/')[-1].split('?')[0].split('#')[0]
            if filename:
                # Si ya tiene el formato deseado, devolver tal cual
                if filename.startswith('clip_') and len(filename) > 10:
                    return filename
                # Si no tiene extensión, usar directamente
                if '.' not in filename:
                    return filename
                # Si tiene extensión, removerla
                else:
                    return filename.rsplit('.', 1)[0]
        
        # Fallback: usar hash de la URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"video_{url_hash}"
        
    except Exception as e:
        print(f"⚠️ Error extrayendo nombre de archivo de la URL: {e}")
        # Fallback: usar timestamp
        return f"video_{int(time.time())}"


def generate_unique_id(base_name: str) -> str:
    """
    Generar un ID único basado en el nombre base
    
    Args:
        base_name: Nombre base para el ID
        
    Returns:
        ID único en formato: base_name_UNIQUEPART
    """
    unique_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=26))
    return f"{base_name}_{unique_part}"


def format_file_size(size_bytes: int) -> str:
    """
    Formatear el tamaño del archivo en formato legible para humanos
    
    Args:
        size_bytes: Tamaño en bytes
        
    Returns:
        Cadena de tamaño formateada
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """
    Formatear la duración en formato legible para humanos
    
    Args:
        seconds: Duración en segundos
        
    Returns:
        Cadena de duración formateada
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def ensure_directory_exists(directory_path: str) -> None:
    """
    Asegurar que el directorio existe, crearlo si no
    
    Args:
        directory_path: Ruta al directorio
    """
    os.makedirs(directory_path, exist_ok=True)


def safe_filename(filename: str) -> str:
    """
    Hacer el nombre de archivo seguro para el sistema de archivos
    
    Args:
        filename: Nombre de archivo original
        
    Returns:
        Nombre de archivo seguro
    """
    # Reemplazar caracteres inseguros
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Limitar longitud
    if len(filename) > 100:
        filename = filename[:100]
    
    return filename


def validate_quality(quality: str) -> bool:
    """
    Validar si la configuración de calidad es válida
    
    Args:
        quality: Configuración de calidad
        
    Returns:
        True si es válida, False en caso contrario
    """
    valid_qualities = ["low", "medium", "high", "ultra", "tiktok", "instagram", "youtube"]
    return quality in valid_qualities


def validate_platform(platform: str) -> bool:
    """
    Validar si la configuración de plataforma es válida
    
    Args:
        platform: Configuración de plataforma
        
    Returns:
        True si es válida, False en caso contrario
    """
    valid_platforms = ["general", "tiktok", "instagram", "youtube", "facebook"]
    return platform in valid_platforms


def get_file_extension(filename: str) -> str:
    """
    Obtener la extensión del archivo del nombre de archivo
    
    Args:
        filename: Nombre de archivo
        
    Returns:
        Extensión del archivo (sin punto)
    """
    return filename.split('.')[-1].lower() if '.' in filename else ''


def is_video_file(filename: str) -> bool:
    """
    Verificar si el archivo es un archivo de video basado en la extensión
    
    Args:
        filename: Nombre de archivo
        
    Returns:
        True si es archivo de video, False en caso contrario
    """
    video_extensions = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'm4v']
    extension = get_file_extension(filename)
    return extension in video_extensions


def is_audio_file(filename: str) -> bool:
    """
    Verificar si el archivo es un archivo de audio basado en la extensión
    
    Args:
        filename: Nombre de archivo
        
    Returns:
        True si es archivo de audio, False en caso contrario
    """
    audio_extensions = ['mp3', 'wav', 'aac', 'ogg', 'flac', 'm4a']
    extension = get_file_extension(filename)
    return extension in audio_extensions


def generate_file_stream(file_path: str, chunk_size: int = 8192) -> Generator[bytes, None, None]:
    """
    Generate file stream for downloading
    
    Args:
        file_path: Path to file
        chunk_size: Size of each chunk
        
    Yields:
        File chunks
    """
    with open(file_path, 'rb') as file:
        while chunk := file.read(chunk_size):
            yield chunk
