"""
Modelos Pydantic relacionados con clips para KickAPI
"""
from pydantic import BaseModel
from typing import Optional, List


class ClipResponse(BaseModel):
    """Modelo de respuesta para datos de clip"""
    id: str
    title: Optional[str]
    duration: Optional[int]
    views: int = 0
    view_count: int = 0
    likes: int = 0
    created_at: Optional[str]
    thumbnail_url: Optional[str]
    download_url: Optional[str]
    mp4_download: str
    mp3_download: str
    clip_url: str
    creator: Optional[str]
    category: Optional[str]


class VideoResponse(BaseModel):
    """Modelo de respuesta para datos de video"""
    id: str
    title: Optional[str]
    duration: Optional[int]
    views: int = 0
    created_at: Optional[str]
    updated_at: Optional[str]
    thumbnail: Optional[str]
    download_url: Optional[str]
    mp4_download: str
    mp3_download: str
    video_url: str
    language: Optional[str]
    uuid: Optional[str]
    live_stream_id: Optional[int]


class ChannelClipsResponse(BaseModel):
    """Modelo de respuesta para clips de canal"""
    channel: str
    total_clips: int
    clips: List[ClipResponse]


class ChannelVideosResponse(BaseModel):
    """Modelo de respuesta para videos de canal"""
    channel: str
    total_videos: int
    videos: List[VideoResponse]
