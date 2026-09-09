from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class DetectionResponse(BaseModel):
    id: str
    camera_id: str
    plate_number: str
    ocr_plate_text: str
    ocr_confidence: float
    vehicle_type: str
    vehicle_color: str
    speed_kmh: float
    fused_confidence: float
    reid_hash: Optional[str] = None
    synthetic_crop_svg: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
