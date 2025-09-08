"""
Servicio KickAPI para interactuar con Kick.com
"""
import asyncio
from typing import List, Optional
from kickapi import KickAPI
from app.models import ClipResponse, VideoResponse, ChannelClipsResponse, ChannelVideosResponse
from app.core.exceptions import VideoNotFoundError


class KickService:
    """Servicio para interactuar con la API de Kick.com"""
    
    def __init__(self):
        self.kick_api = KickAPI()
    
    async def get_channel_clips(self, channel_name: str, limit: int = 20) -> ChannelClipsResponse:
        """
        Obtener clips de un canal específico
        
        Args:
            channel_name: Nombre del canal
            limit: Número máximo de clips a devolver
            
        Returns:
            ChannelClipsResponse con los datos de los clips
        """
        try:
            # Obtener información del canal
            channel = await asyncio.to_thread(self.kick_api.channel, channel_name)
            if not channel:
                raise VideoNotFoundError(f"Channel '{channel_name}' not found")
            
            # Obtener clips del canal
            clips = channel.clips
            
            clips_data = []
            for i, clip in enumerate(clips):
                if i >= limit:
                    break
                    
                clip_data = ClipResponse(
                    id=clip.id,
                    title=clip.title if clip.title else "No title",
                    duration=clip.duration,
                    views=getattr(clip, 'views', 0),
                    view_count=getattr(clip, 'view_count', 0),
                    likes=getattr(clip, 'likes', 0),
                    created_at=clip.created_at,
                    thumbnail_url=clip.thumbnail,
                    download_url=clip.stream,
                    mp4_download=f"/clip/{clip.id}/download/mp4",
                    mp3_download=f"/clip/{clip.id}/download/mp3",
                    clip_url=f"https://kick.com/{channel_name}/clips/{clip.id}",
                    creator=clip.creator.username if clip.creator else None,
                    category=clip.category.name if clip.category else None
                )
                clips_data.append(clip_data)
            
            return ChannelClipsResponse(
                channel=channel_name,
                total_clips=len(clips_data),
                clips=clips_data
            )
        
        except Exception as e:
            raise VideoNotFoundError(f"Error getting clips: {str(e)}")
    
    async def get_channel_videos(self, channel_name: str, limit: int = 20) -> ChannelVideosResponse:
        """
        Obtener vídeos (VODs) de un canal específico
        
        Args:
            channel_name: Nombre del canal
            limit: Número máximo de vídeos a devolver
            
        Returns:
            ChannelVideosResponse con los datos de los vídeos
        """
        try:
            # Obtener información del canal
            channel = await asyncio.to_thread(self.kick_api.channel, channel_name)
            if not channel:
                raise VideoNotFoundError(f"Channel '{channel_name}' not found")
            
            # Obtener vídeos del canal
            videos = channel.videos
            
            videos_data = []
            for i, video in enumerate(videos):
                if i >= limit:
                    break
                    
                video_data = VideoResponse(
                    id=video.id,
                    title=video.title if video.title else "No title",
                    duration=video.duration,
                    views=video.views,
                    created_at=video.created_at,
                    updated_at=video.updated_at,
                    thumbnail=video.thumbnail,
                    download_url=video.stream,
                    mp4_download=f"/video/{video.id}/download/mp4",
                    mp3_download=f"/video/{video.id}/download/mp3",
                    video_url=f"https://kick.com/{channel_name}/videos/{video.id}",
                    language=video.language,
                    uuid=video.uuid,
                    live_stream_id=video.live_stream_id
                )
                videos_data.append(video_data)
            
            return ChannelVideosResponse(
                channel=channel_name,
                total_videos=len(videos_data),
                videos=videos_data
            )
        
        except Exception as e:
            raise VideoNotFoundError(f"Error getting videos: {str(e)}")
    
    async def get_clip_by_id(self, clip_id: str) -> dict:
        """
        Obtener información de un clip por ID
        
        Args:
            clip_id: ID del clip
            
        Returns:
            Diccionario con la información del clip
        """
        try:
            clip = await asyncio.to_thread(self.kick_api.clip, clip_id)
            if not clip:
                raise VideoNotFoundError(f"Clip '{clip_id}' not found")
            
            return {
                "id": clip.id,
                "title": clip.title if clip.title else "No title",
                "duration": clip.duration,
                "views": getattr(clip, 'views', 0),
                "view_count": getattr(clip, 'view_count', 0),
                "likes": getattr(clip, 'likes', 0),
                "created_at": clip.created_at,
                "thumbnail_url": clip.thumbnail,
                "download_url": clip.stream,
                "creator": clip.creator.username if clip.creator else None,
                "category": clip.category.name if clip.category else None,
                "channel": {
                    "id": clip.channel.id,
                    "username": clip.channel.username
                } if clip.channel else None
            }
        
        except Exception as e:
            raise VideoNotFoundError(f"Error getting clip: {str(e)}")
    
    async def get_video_by_id(self, video_id: str) -> dict:
        """
        Obtener información de un vídeo por ID
        
        Args:
            video_id: ID del vídeo
            
        Returns:
            Diccionario con la información del vídeo
        """
        try:
            video = await asyncio.to_thread(self.kick_api.video, video_id)
            if not video:
                raise VideoNotFoundError(f"Video '{video_id}' not found")
            
            return {
                "id": video.id,
                "title": video.title if video.title else "No title",
                "duration": video.duration,
                "views": video.views,
                "created_at": video.created_at,
                "updated_at": video.updated_at,
                "thumbnail": video.thumbnail,
                "download_url": video.stream,
                "language": video.language,
                "uuid": video.uuid,
                "live_stream_id": video.live_stream_id,
                "channel": {
                    "id": video.channel.id,
                    "username": video.channel.username
                } if video.channel else None
            }
        
        except Exception as e:
            raise VideoNotFoundError(f"Error getting video: {str(e)}")


# Instancia global del servicio
kick_service = KickService()
