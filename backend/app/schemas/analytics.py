from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class SystemOverviewMetrics(BaseModel):
    total_vehicles_tracked: int
    total_detections_today: int
    active_cameras: int
    total_cameras: int
    critical_alerts: int
    total_active_alerts: int
    network_average_speed_kmh: float
    system_status: str


class CongestionCameraMetric(BaseModel):
    camera_id: str
    name: str
    zone: str
    latitude: float
    longitude: float
    vehicles_per_minute: float
    recent_count: int
    congestion_level: str
    color: str
    intensity: float


class HourlyFlowMetric(BaseModel):
    hour: str
    car_count: int
    suv_count: int
    motorcycle_count: int
    commercial_count: int
    total: int


class CongestionResponse(BaseModel):
    cameras: List[CongestionCameraMetric]
    heatmap_points: List[List[float]]  # [lat, lng, intensity]
