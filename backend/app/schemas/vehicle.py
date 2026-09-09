from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class VehicleBase(BaseModel):
    plate_number: str
    vehicle_type: str
    color: str
    make_model: Optional[str] = None
    is_ev: bool = False
    is_flagged: bool = False
    flag_reason: Optional[str] = None


class VehicleResponse(VehicleBase):
    first_seen_at: datetime
    last_seen_at: datetime
    total_sightings: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class VehicleTrajectoryHop(BaseModel):
    detection_id: str
    camera_id: str
    camera_name: str
    zone: str
    latitude: float
    longitude: float
    timestamp: datetime
    speed_kmh: float
    confidence: float
    crop_svg: Optional[str] = None


class VehicleTrajectoryResponse(BaseModel):
    plate_number: str
    total_sightings: int
    total_distance_km: float
    visited_cameras: list[VehicleTrajectoryHop]
    segments: list[dict]
    geojson_path: dict
    predicted_next_cameras: list[dict]
