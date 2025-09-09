"""
Puntos de integración para comunicarse con otros microservicios
"""
import requests
import asyncio
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.core.config import Config
from app.services.kick_service import KickService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class VideoProcessingRequest(BaseModel):
  """Modelo de solicitud para el pipeline simplificado de procesamiento de video"""
  channel_name: str
  clip_count: int = 5
  quality: str = "medium"
  platform: str = "general"
  generate_clips: bool = True
  # select_viral: bool = True  # Eliminado - clip-selector deprecado

class ProcessingStatus(BaseModel):
  """Modelo de respuesta para el estado del procesamiento"""
  task_id: str
  status: str
  message: str
  progress: float
  results: Dict[str, Any] = {}

# Almacenamiento en memoria de tareas (en producción usar Redis o similar)
processing_tasks: Dict[str, ProcessingStatus] = {}

@router.get("/microservices/status")
async def get_microservices_status():
  """Obtener el estado de todos los microservicios del sistema"""
  services = {
    "kick-api": {"url": f"http://localhost:{Config.PORT}/health", "status": "unknown"},
    "clip-generator": {"url": f"{Config.CLIP_GENERATOR_URL}/health", "status": "unknown"}
  }
  
  for service_name, service_info in services.items():
    try:
      response = requests.get(service_info["url"], timeout=5)
      if response.status_code == 200:
        services[service_name]["status"] = "healthy"
        services[service_name]["details"] = response.json()
      else:
        services[service_name]["status"] = "unhealthy"
    except Exception as e:
      services[service_name]["status"] = "unreachable"
      services[service_name]["error"] = str(e)
  
  return {
    "system_status": "healthy" if all(s["status"] == "healthy" for s in services.values()) else "degraded",
    "services": services
  }

@router.post("/process/complete-pipeline")
async def process_complete_pipeline(
  request: VideoProcessingRequest,
  background_tasks: BackgroundTasks
):
  """
  Pipeline simplificado de procesamiento de video:
  1. Obtener clips de Kick.com
  2. Generar clips (clip-generator)
  """
  import uuid
  task_id = str(uuid.uuid4())
  
  # Inicializar estado de la tarea
  processing_tasks[task_id] = ProcessingStatus(
    task_id=task_id,
    status="started",
    message="Pipeline iniciado",
    progress=0.0
  )
  
  # Iniciar procesamiento en segundo plano
  background_tasks.add_task(
    process_pipeline_background,
    task_id,
    request
  )
  
  return {
    "task_id": task_id,
    "status": "accepted",
    "message": "Pipeline de procesamiento iniciado en segundo plano",
    "check_status_url": f"/api/integration/process/status/{task_id}"
  }

@router.get("/process/status/{task_id}")
async def get_processing_status(task_id: str):
  """Obtener el estado de una tarea de procesamiento"""
  if task_id not in processing_tasks:
    raise HTTPException(status_code=404, detail="Task not found")
  
  return processing_tasks[task_id]

async def process_pipeline_background(task_id: str, request: VideoProcessingRequest):
  """Tarea en segundo plano para procesar el pipeline completo"""
  try:
    # Actualizar estado
    processing_tasks[task_id].status = "processing"
    processing_tasks[task_id].message = "Obteniendo clips de Kick.com"
    processing_tasks[task_id].progress = 10.0
    
    # Paso 1: Obtener clips de Kick.com
    kick_service = KickService()
    clips_data = await kick_service.get_channel_clips(
      channel_name=request.channel_name,
      limit=request.clip_count
    )
    
    if not clips_data or not clips_data.get("clips"):
      processing_tasks[task_id].status = "failed"
      processing_tasks[task_id].message = "No se encontraron clips en el canal"
      return
    
    processing_tasks[task_id].progress = 30.0
    processing_tasks[task_id].message = f"Encontrados {len(clips_data['clips'])} clips"
    
    video_urls = [clip.get("video_url") for clip in clips_data["clips"] if clip.get("video_url")]
    
    if request.generate_clips:
      # Paso 2: Generar clips usando el microservicio clip-generator
      processing_tasks[task_id].message = "Generando clips con clip-generator"
      processing_tasks[task_id].progress = 50.0
      
      clip_generation_results = []
      for i, video_url in enumerate(video_urls):
        try:
          response = requests.post(
            f"{Config.CLIP_GENERATOR_URL}/api/clips/generate",
            json={
              "video_url": video_url,
              "max_clips": 3,
              "clip_duration": 20,
              "output_format": "mp4"
            },
            timeout=120
          )
          
          if response.status_code == 200:
            clip_generation_results.append(response.json())
          else:
            logger.warning(f"No se generaron clips para el video {i+1}: {response.text}")
        
        except Exception as e:
          logger.error(f"Error al generar clips para el video {i+1}: {str(e)}")
        
        # Actualizar progreso
        progress = 50.0 + (i + 1) / len(video_urls) * 50.0  # Ahora va hasta 100%
        processing_tasks[task_id].progress = progress
      
      processing_tasks[task_id].results["clip_generation"] = clip_generation_results
    
    # Completar la tarea (clip-selector eliminado)
    processing_tasks[task_id].status = "completed"
    processing_tasks[task_id].message = "Pipeline completado exitosamente"
    processing_tasks[task_id].progress = 100.0
    processing_tasks[task_id].results["original_clips"] = clips_data
    
  except Exception as e:
    processing_tasks[task_id].status = "failed"
    processing_tasks[task_id].message = f"Error en el pipeline: {str(e)}"
    processing_tasks[task_id].progress = 0.0
    logger.error(f"Fallo del pipeline para la tarea {task_id}: {str(e)}")

@router.delete("/process/cleanup")
async def cleanup_completed_tasks():
  """Limpiar tareas de procesamiento completadas"""
  completed_tasks = [
    task_id for task_id, task in processing_tasks.items()
    if task.status in ["completed", "failed"]
  ]
  
  for task_id in completed_tasks:
    del processing_tasks[task_id]
  
  return {
    "message": f"Se limpiaron {len(completed_tasks)} tareas completadas",
    "active_tasks": len(processing_tasks)
  }

@router.get("/process/active-tasks")
async def get_active_tasks():
  """Obtener todas las tareas de procesamiento activas"""
  return {
    "active_tasks": len(processing_tasks),
    "tasks": list(processing_tasks.values())
  }
