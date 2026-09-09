from pydantic import BaseModel
from typing import Optional


class SimulatorStatusResponse(BaseModel):
    is_running: bool
    fleet_size: int
    speed_multiplier: float
    total_events_generated: int
    events_per_minute: float
    uptime_seconds: float


class SimulatorSpeedUpdate(BaseModel):
    multiplier: float


class AnomalyInjectionRequest(BaseModel):
    anomaly_type: str  # IMPOSSIBLE_TRAVEL, CLONED_PLATE, CONGESTION_SURGE, CAMERA_BLACKOUT
    target_camera_id: Optional[str] = None
    target_plate_number: Optional[str] = None
