from pydantic import BaseModel
from typing import List, Optional

class VideoRequest(BaseModel):
    video_url: str

class ClipMetadata(BaseModel):
    url: str
    start: float
    end: float
    duration: float

class ClipGenerationResponse(BaseModel):
    status: str
    clips: List[ClipMetadata]
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    status: str
    error: str
    details: Optional[str] = None
