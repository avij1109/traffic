from pydantic import BaseModel, ConfigDict
from typing import Optional


class CameraBase(BaseModel):
    id: str
    name: str
    zone: str
    latitude: float
    longitude: float
    speed_limit_kmh: float = 50.0
    status: str = "ACTIVE"
    fps: int = 30


class CameraCreate(CameraBase):
    pass


class CameraStatusUpdate(BaseModel):
    status: str  # ACTIVE, OFFLINE, MAINTENANCE


class CameraResponse(CameraBase):
    model_config = ConfigDict(from_attributes=True)
