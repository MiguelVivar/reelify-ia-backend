from pydantic import BaseModel
from typing import List, Optional

class ClipInput(BaseModel):
    url: str

class ClipSelectionRequest(BaseModel):
    clips: List[ClipInput]

class ViralClip(BaseModel):
    url: str
    keywords: List[str]
    duration: float
    viral_score: Optional[float] = None
    transcript: Optional[str] = None

class ClipSelectionResponse(BaseModel):
    status: str
    viral_clips: List[ViralClip]
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    status: str
    error: str
    details: Optional[str] = None
