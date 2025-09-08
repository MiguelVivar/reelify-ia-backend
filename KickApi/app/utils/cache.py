"""
Utilidades de gestión de caché
"""
import time
import threading
import shutil
import os
from typing import Dict, Any
from app.core.config import Config


class VideoCache:
    """Gestor de caché de videos seguro para hilos"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
    def get(self, video_id: str) -> Dict[str, Any]:
        """Obtener datos de video desde la caché"""
        with self._lock:
            return self._cache.get(video_id, {}).copy()
    
    def set(self, video_id: str, data: Dict[str, Any]) -> None:
        """Guardar datos de video en la caché"""
        with self._lock:
            if video_id not in self._cache:
                self._cache[video_id] = {}
            self._cache[video_id].update(data)
    
    def update(self, video_id: str, updates: Dict[str, Any]) -> None:
        """Actualizar datos de video en la caché"""
        with self._lock:
            if video_id in self._cache:
                self._cache[video_id].update(updates)
    
    def exists(self, video_id: str) -> bool:
        """Comprobar si el video existe en la caché"""
        with self._lock:
            return video_id in self._cache
    
    def remove(self, video_id: str) -> None:
        """Eliminar video de la caché"""
        with self._lock:
            if video_id in self._cache:
                del self._cache[video_id]
    
    def get_all_keys(self) -> list:
        """Obtener todas las claves de la caché"""
        with self._lock:
            return list(self._cache.keys())
    
    def keys(self) -> list:
        """Obtener todas las claves de la caché (alias de get_all_keys)"""
        return self.get_all_keys()
    
    def clean_expired(self) -> None:
        """Limpiar videos expirados de la caché"""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for video_id, data in self._cache.items():
                if current_time - data.get('created_at', 0) > Config.CACHE_EXPIRY_SECONDS:
                    expired_keys.append(video_id)
                    
                    # Limpiar archivos
                    temp_dir = data.get('temp_dir')
                    if temp_dir and os.path.exists(temp_dir):
                        try:
                            shutil.rmtree(temp_dir)
                            print(f"🗑️ Directorio temporal eliminado: {temp_dir}")
                        except Exception as e:
                            print(f"⚠️ Error al eliminar el directorio temporal: {e}")
                    
                    # Alternativa: eliminar archivo individual
                    file_path = data.get('file_path')
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            print(f"🗑️ Archivo eliminado: {file_path}")
                        except:
                            pass
            
            # Eliminar de la caché
            for key in expired_keys:
                del self._cache[key]
                print(f"🧹 Caché limpiada: {key}")


class CacheManager:
    """Gestor de caché con limpieza automática"""
    
    def __init__(self):
        self.video_cache = VideoCache()
        self._cleanup_thread = None
        self._should_stop = False
        
    def start_cleanup_thread(self) -> None:
        """Iniciar hilo de limpieza automático"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._should_stop = False
            self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self._cleanup_thread.start()
            print("🧹 Hilo de limpieza iniciado")
    
    def stop_cleanup_thread(self) -> None:
        """Detener el hilo de limpieza"""
        self._should_stop = True
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1)
    
    def _cleanup_worker(self) -> None:
        """Función worker para el hilo de limpieza"""
        while not self._should_stop:
            try:
                time.sleep(Config.CLEANUP_INTERVAL_SECONDS)
                if not self._should_stop:
                    self.video_cache.clean_expired()
            except Exception as e:
                print(f"⚠️ Error en el trabajador de limpieza: {e}")


# Instancia global de caché
cache_manager = CacheManager()
