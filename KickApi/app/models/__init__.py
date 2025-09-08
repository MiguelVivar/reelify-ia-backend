"""
Paquete de modelos para KickAPI
"""
# Importa todos los modelos para un acceso sencillo
from .video_models import (
    OptimizedVideoRequest,
    VideoFilterOptions,
    VideoInfo,
    ProcessingStats,
    VideoCache
)

from .clip_models import (
    ClipResponse,
    VideoResponse,
    ChannelClipsResponse,
    ChannelVideosResponse
)

from .response_models import (
    ProcessVideoResponse,
    VideoStatusResponse
)

from .system_models import (
    SystemCapabilities
)

__all__ = [
    # Modelos de video
    "OptimizedVideoRequest",
    "VideoFilterOptions",
    "VideoInfo",
    "ProcessingStats",
    "VideoCache",

    # Modelos de clip
    "ClipResponse",
    "VideoResponse",
    "ChannelClipsResponse",
    "ChannelVideosResponse",

    # Modelos de respuesta
    "ProcessVideoResponse",
    "VideoStatusResponse",

    # Modelos del sistema
    "SystemCapabilities"
]
