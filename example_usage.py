#!/usr/bin/env python3
"""
Ejemplo práctico de uso del sistema Reelify IA
Demuestra el flujo completo desde un video público hasta clips virales
"""

import requests
import json
import time
import os

# URLs de los servicios
CLIP_GENERATOR_URL = "http://localhost:8001"
CLIP_SELECTOR_URL = "http://localhost:8002"

def main():
    """Flujo completo de ejemplo"""
    print("🎬 Ejemplo de uso - Sistema Reelify IA")
    print("=" * 50)
    
    # Paso 1: Generar clips desde un video público
    print("\n📹 Paso 1: Generando clips desde video público...")
    
    video_request = {
        "video_url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
    }
    
    try:
        response = requests.post(
            f"{CLIP_GENERATOR_URL}/api/v1/generate-initial-clips",
            json=video_request,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            clips = result.get('clips', [])
            print(f"✅ Generados {len(clips)} clips:")
            
            for i, clip in enumerate(clips):
                print(f"   Clip {i+1}: {clip['url']} ({clip['duration']:.1f}s)")
                
                # Verificar que el archivo existe
                download_url = f"{CLIP_GENERATOR_URL}{clip['url']}"
                head_response = requests.head(download_url, timeout=10)
                if head_response.status_code == 200:
                    print(f"     ✅ Disponible para descarga")
                else:
                    print(f"     ❌ Error: {head_response.status_code}")
            
            # Paso 2: Seleccionar clips virales
            if clips:
                print(f"\n🚀 Paso 2: Analizando clips para detectar contenido viral...")
                
                selection_request = {
                    "clips": [{"url": clip["url"]} for clip in clips[:3]]  # Analizar los primeros 3
                }
                
                response = requests.post(
                    f"{CLIP_SELECTOR_URL}/api/v1/select-viral-clips",
                    json=selection_request,
                    timeout=180
                )
                
                if response.status_code == 200:
                    result = response.json()
                    viral_clips = result.get('viral_clips', [])
                    
                    if viral_clips:
                        print(f"✅ Detectados {len(viral_clips)} clips virales:")
                        
                        for i, viral_clip in enumerate(viral_clips):
                            print(f"   Clip viral {i+1}:")
                            print(f"     • URL: {viral_clip['url']}")
                            print(f"     • Duración: {viral_clip['duration']:.1f}s")
                            print(f"     • Score viral: {viral_clip['viral_score']:.3f}")
                            print(f"     • Keywords: {', '.join(viral_clip['keywords'])}")
                            print(f"     • Transcripción: {viral_clip['transcript'][:100]}...")
                            
                            # Verificar disponibilidad
                            download_url = f"{CLIP_SELECTOR_URL}{viral_clip['url']}"
                            head_response = requests.head(download_url, timeout=10)
                            if head_response.status_code == 200:
                                print(f"     ✅ Disponible para descarga")
                                
                                # Ejemplo: descargar el primer clip viral
                                if i == 0:
                                    print(f"\n📥 Descargando primer clip viral...")
                                    download_response = requests.get(download_url, timeout=30)
                                    if download_response.status_code == 200:
                                        filename = f"clip_viral_ejemplo.mp4"
                                        with open(filename, 'wb') as f:
                                            f.write(download_response.content)
                                        print(f"✅ Clip descargado como: {filename}")
                                        print(f"   Tamaño: {len(download_response.content)} bytes")
                            else:
                                print(f"     ❌ Error: {head_response.status_code}")
                        
                        # Paso 3: Estadísticas del procesamiento
                        print(f"\n📊 Paso 3: Resumen del procesamiento:")
                        print(f"   • Video original procesado: ✅")
                        print(f"   • Clips generados: {len(clips)}")
                        print(f"   • Clips analizados: {len(selection_request['clips'])}")
                        print(f"   • Clips virales detectados: {len(viral_clips)}")
                        
                        if viral_clips:
                            avg_viral_score = sum(c['viral_score'] for c in viral_clips) / len(viral_clips)
                            print(f"   • Score viral promedio: {avg_viral_score:.3f}")
                            
                            all_keywords = []
                            for clip in viral_clips:
                                all_keywords.extend(clip['keywords'])
                            unique_keywords = list(set(all_keywords))
                            print(f"   • Keywords únicos detectados: {', '.join(unique_keywords)}")
                        
                    else:
                        print("⚠️  No se detectaron clips con potencial viral")
                        print("   Posibles motivos:")
                        print("   - Umbral viral muy alto")
                        print("   - Contenido no contiene palabras clave configuradas")
                        print("   - Audio no es claro para transcripción")
                        
                else:
                    print(f"❌ Error en análisis viral: {response.status_code}")
                    print(f"   Respuesta: {response.text}")
            else:
                print("❌ No se generaron clips para analizar")
                
        else:
            print(f"❌ Error generando clips: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except Exception as e:
        print(f"❌ Error en el flujo: {e}")
    
    print(f"\n🎯 Ejemplo completado!")
    print(f"\n💡 Próximos pasos:")
    print(f"   1. Usa tus propias URLs de video públicas")
    print(f"   2. Ajusta las palabras clave virales en las variables de entorno")
    print(f"   3. Modifica el umbral viral (MIN_VIRAL_SCORE)")
    print(f"   4. Integra con tu aplicación usando las APIs REST")

if __name__ == "__main__":
    main()
