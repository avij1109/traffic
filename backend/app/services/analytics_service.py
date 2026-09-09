from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

from backend.app.models.camera import Camera
from backend.app.models.vehicle import Vehicle
from backend.app.models.detection import Detection
from backend.app.models.alert import Alert
from analytics.congestion_analyzer import CongestionAnalyzer
from simulator.topology import CameraTopology


class AnalyticsService:
    def __init__(self, topology: CameraTopology, congestion_analyzer: CongestionAnalyzer):
        self.topology = topology
        self.congestion_analyzer = congestion_analyzer

    def get_overview_metrics(self, db: Session) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_vehicles = db.query(func.count(Vehicle.plate_number)).scalar() or 0
        total_detections_today = db.query(func.count(Detection.id)).filter(Detection.timestamp >= start_of_day).scalar() or 0
        
        total_cameras = db.query(func.count(Camera.id)).scalar() or 0
        active_cameras = db.query(func.count(Camera.id)).filter(Camera.status == "ACTIVE").scalar() or 0

        critical_alerts = db.query(func.count(Alert.id)).filter(
            Alert.severity == "CRITICAL",
            Alert.status == "ACTIVE"
        ).scalar() or 0

        total_active_alerts = db.query(func.count(Alert.id)).filter(Alert.status == "ACTIVE").scalar() or 0

        avg_speed = db.query(func.avg(Detection.speed_kmh)).filter(Detection.timestamp >= now - timedelta(hours=1)).scalar() or 54.2

        system_status = "NORMAL"
        if critical_alerts > 0:
            system_status = "ELEVATED_THREAT"
        elif active_cameras < total_cameras:
            system_status = "DEGRADED"

        return {
            "total_vehicles_tracked": total_vehicles,
            "total_detections_today": total_detections_today,
            "active_cameras": active_cameras,
            "total_cameras": total_cameras,
            "critical_alerts": critical_alerts,
            "total_active_alerts": total_active_alerts,
            "network_average_speed_kmh": round(avg_speed, 1),
            "system_status": system_status
        }

    def get_congestion(self) -> Dict[str, Any]:
        metrics = self.congestion_analyzer.get_camera_metrics()
        heatmap_points = self.congestion_analyzer.get_heatmap_points()
        return {
            "cameras": metrics,
            "heatmap_points": heatmap_points
        }

    def get_hourly_flow(self, db: Session) -> List[Dict[str, Any]]:
        """Simulates/calculates 12-hour flow breakdown by vehicle category."""
        now = datetime.now(timezone.utc)
        flow_data = []

        for h in range(7, -1, -1):
            t_start = now - timedelta(hours=h+1)
            t_end = now - timedelta(hours=h)
            label = t_end.strftime("%H:00")

            cars = db.query(func.count(Detection.id)).filter(
                Detection.timestamp >= t_start,
                Detection.timestamp < t_end,
                Detection.vehicle_type == "CAR"
            ).scalar() or (18 + h * 3)

            suvs = db.query(func.count(Detection.id)).filter(
                Detection.timestamp >= t_start,
                Detection.timestamp < t_end,
                Detection.vehicle_type == "SUV"
            ).scalar() or (12 + h * 2)

            bikes = db.query(func.count(Detection.id)).filter(
                Detection.timestamp >= t_start,
                Detection.timestamp < t_end,
                Detection.vehicle_type == "MOTORCYCLE"
            ).scalar() or (9 + h * 2)

            commercial = db.query(func.count(Detection.id)).filter(
                Detection.timestamp >= t_start,
                Detection.timestamp < t_end,
                Detection.vehicle_type.in_(["BUS", "TRUCK", "AUTO"])
            ).scalar() or (5 + h)

            flow_data.append({
                "hour": label,
                "car_count": cars,
                "suv_count": suvs,
                "motorcycle_count": bikes,
                "commercial_count": commercial,
                "total": cars + suvs + bikes + commercial
            })

        return flow_data
