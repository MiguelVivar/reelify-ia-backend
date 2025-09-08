"""
Excepciones personalizadas para KickAPI
"""


class KickAPIException(Exception):
    """Excepción base para KickAPI"""
    pass


class FFmpegNotAvailableError(KickAPIException):
    """Se lanza cuando FFmpeg no está disponible"""
    pass


class WhisperNotAvailableError(KickAPIException):
    """Se lanza cuando Whisper no está disponible"""
    pass


class VideoNotFoundError(KickAPIException):
    """Se lanza cuando no se encuentra el video"""
    pass


class VideoProcessingError(KickAPIException):
    """Se lanza cuando falla el procesamiento de video"""
    pass


class DownloadError(KickAPIException):
    """Se lanza cuando falla la descarga del video"""
    pass


class ConversionError(KickAPIException):
    """Se lanza cuando falla la conversión del video"""
    pass


class SubtitleGenerationError(KickAPIException):
    """Se lanza cuando falla la generación de subtítulos"""
    pass


class InvalidQualityError(KickAPIException):
    """Se lanza cuando se especifica una calidad no válida"""
    pass


class InvalidPlatformError(KickAPIException):
    """Se lanza cuando se especifica una plataforma no válida"""
    pass
