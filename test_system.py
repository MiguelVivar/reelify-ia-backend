#!/usr/bin/env python3
"""
Script de prueba para validar ambos microservicios
"""

import requests
import json
import time
import sys

# URLs de los servicios
CLIP_GENERATOR_URL = "http://localhost:8001"
CLIP_SELECTOR_URL = "http://localhost:8002"

def test_health_endpoints():
    """Probar endpoints de salud"""
    print("🏥 Probando endpoints de salud...")
    
    try:
        # Test Clip Generator health
        response = requests.get(f"{CLIP_GENERATOR_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Clip Generator: Saludable")
        else:
            print(f"❌ Clip Generator: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Clip Generator: No disponible - {e}")
        return False
    
    try:
        # Test Clip Selector health
        response = requests.get(f"{CLIP_SELECTOR_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Clip Selector: Saludable")
        else:
            print(f"❌ Clip Selector: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Clip Selector: No disponible - {e}")
        return False
    
    return True

def test_clip_generator():
    """Probar generación de clips"""
    print("\n🎬 Probando generación de clips...")
    
    # Datos de prueba
    test_data = {
        "video_url": "https://storage.asumarket.com/agentetiktok/test_video.mp4"
    }
    
    try:
        response = requests.post(
            f"{CLIP_GENERATOR_URL}/api/v1/generate-initial-clips",
            json=test_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Clips generados: {len(result.get('clips', []))}")
            print(f"   Status: {result.get('status')}")
            print(f"   Mensaje: {result.get('message')}")
            return result.get('clips', [])
        else:
            print(f"❌ Error generando clips: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Error en request: {e}")
        return []

def test_clip_selector(clips):
    """Probar selección de clips virales"""
    print("\n🚀 Probando selección de clips virales...")
    
    if not clips:
        print("⚠️  No hay clips para probar")
        return
    
    # Usar solo los primeros 2 clips para la prueba
    test_clips = clips[:2]
    test_data = {
        "clips": [{"url": clip["url"]} for clip in test_clips]
    }
    
    try:
        response = requests.post(
            f"{CLIP_SELECTOR_URL}/api/v1/select-viral-clips",
            json=test_data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            viral_clips = result.get('viral_clips', [])
            print(f"✅ Clips virales seleccionados: {len(viral_clips)}")
            print(f"   Status: {result.get('status')}")
            print(f"   Mensaje: {result.get('message')}")
            
            for i, clip in enumerate(viral_clips[:2]):  # Mostrar solo los primeros 2
                print(f"   Clip {i+1}:")
                print(f"     • URL: {clip.get('url')}")
                print(f"     • Duración: {clip.get('duration')}s")
                print(f"     • Score viral: {clip.get('viral_score')}")
                print(f"     • Keywords: {clip.get('keywords')}")
                
                # Probar descarga del clip viral
                if clip.get('url', '').startswith('/clips/viral/'):
                    viral_url = f"{CLIP_SELECTOR_URL}{clip['url']}"
                    try:
                        download_response = requests.head(viral_url, timeout=10)
                        if download_response.status_code == 200:
                            print(f"     • ✅ Archivo disponible para descarga")
                        else:
                            print(f"     • ❌ Error descargando: {download_response.status_code}")
                    except Exception as e:
                        print(f"     • ❌ Error verificando descarga: {e}")
                
        else:
            print(f"❌ Error seleccionando clips: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except Exception as e:
        print(f"❌ Error en request: {e}")

def main():
    """Función principal"""
    print("🧪 Iniciando pruebas del sistema Reelify IA")
    print("=" * 50)
    
    # Probar endpoints de salud
    if not test_health_endpoints():
        print("\n❌ Los servicios no están disponibles. Verifica que Docker Compose esté corriendo.")
        sys.exit(1)
    
    print("\n✅ Todos los servicios están operativos")
    
    # Probar generación de clips
    clips = test_clip_generator()
    
    # Probar selección de clips virales
    test_clip_selector(clips)
    
    print("\n🎉 Pruebas completadas!")
    print("\n📝 Notas:")
    print("   • Las pruebas usan URLs de ejemplo que pueden no existir")
    print("   • Para pruebas reales, sube un video a MinIO primero")
    print("   • Revisa los logs con: docker-compose logs -f")

if __name__ == "__main__":
    main()
