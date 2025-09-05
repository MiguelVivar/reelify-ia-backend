"""
Configuración para desarrollo local
Ejecuta este script para configurar el entorno de desarrollo
"""

import os
import subprocess
import sys

def create_virtual_environments():
    """Crear entornos virtuales para desarrollo local"""
    
    services = ['clip-generator', 'clip-selector']
    
    for service in services:
        venv_path = os.path.join(service, 'venv')
        
        if not os.path.exists(venv_path):
            print(f"Creando entorno virtual para {service}...")
            subprocess.run([sys.executable, '-m', 'venv', venv_path])
            
            # Instalar dependencias
            if os.name == 'nt':  # Windows
                pip_path = os.path.join(venv_path, 'Scripts', 'pip')
            else:  # Unix/Linux
                pip_path = os.path.join(venv_path, 'bin', 'pip')
            
            requirements_path = os.path.join(service, 'requirements.txt')
            if os.path.exists(requirements_path):
                print(f"Instalando dependencias para {service}...")
                subprocess.run([pip_path, 'install', '-r', requirements_path])
        else:
            print(f"Entorno virtual ya existe para {service}")

def create_dev_env_files():
    """Crear archivos .env para desarrollo"""
    
    services = {
        'clip-generator': {
            'MINIO_ENDPOINT': 'localhost:9000',
            'MINIO_ACCESS_KEY': 'minioadmin',
            'MINIO_SECRET_KEY': 'minioadmin',
            'MINIO_SECURE': 'false',
            'MINIO_BUCKET': 'agentetiktok',
            'SERVICE_HOST': '0.0.0.0',
            'SERVICE_PORT': '8001',
            'LOG_LEVEL': 'DEBUG',
            'TEMP_DIR': 'C:/tmp/video_processing' if os.name == 'nt' else '/tmp/video_processing'
        },
        'clip-selector': {
            'MINIO_ENDPOINT': 'localhost:9000',
            'MINIO_ACCESS_KEY': 'minioadmin',
            'MINIO_SECRET_KEY': 'minioadmin',
            'MINIO_SECURE': 'false',
            'MINIO_BUCKET': 'agentetiktok',
            'SERVICE_HOST': '0.0.0.0',
            'SERVICE_PORT': '8002',
            'LOG_LEVEL': 'DEBUG',
            'WHISPER_MODEL': 'base',
            'WHISPER_DEVICE': 'cpu',
            'TEMP_DIR': 'C:/tmp/clip_processing' if os.name == 'nt' else '/tmp/clip_processing'
        }
    }
    
    for service, env_vars in services.items():
        env_file = os.path.join(service, '.env.dev')
        
        print(f"Creando {env_file}...")
        with open(env_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

def main():
    """Función principal"""
    print("🛠️  Configurando entorno de desarrollo para Reelify IA")
    print("=" * 55)
    
    # Crear entornos virtuales
    create_virtual_environments()
    
    # Crear archivos de entorno
    create_dev_env_files()
    
    # Crear directorios temporales
    temp_dirs = [
        'C:/tmp/video_processing' if os.name == 'nt' else '/tmp/video_processing',
        'C:/tmp/clip_processing' if os.name == 'nt' else '/tmp/clip_processing'
    ]
    
    for temp_dir in temp_dirs:
        os.makedirs(temp_dir, exist_ok=True)
        print(f"Directorio temporal creado: {temp_dir}")
    
    print("\n✅ Configuración completada!")
    print("\n📝 Próximos pasos:")
    print("1. Inicia MinIO: docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ':9001'")
    print("2. Activa el entorno virtual:")
    if os.name == 'nt':
        print("   • clip-generator\\venv\\Scripts\\activate")
        print("   • clip-selector\\venv\\Scripts\\activate")
    else:
        print("   • source clip-generator/venv/bin/activate")
        print("   • source clip-selector/venv/bin/activate")
    print("3. Ejecuta los servicios:")
    print("   • cd clip-generator/src && python main.py")
    print("   • cd clip-selector/src && python main.py")

if __name__ == "__main__":
    main()
