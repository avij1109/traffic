from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from backend.app.models.vehicle import Vehicle
from backend.app.models.detection import Detection
from backend.app.models.alert import Alert
from simulator.topology import CameraTopology
from analytics.trajectory_reconstruction import TrajectoryReconstructor


class VehicleService:
    def __init__(self, topology: Optional[CameraTopology] = None):
        self.topology = topology or CameraTopology()
        self.reconstructor = TrajectoryReconstructor(self.topology)

    def search_vehicles(
        self,
        db: Session,
        query_str: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        is_flagged: Optional[bool] = None,
        limit: int = 50
    ) -> List[dict]:
        query = db.query(Vehicle)
        if query_str:
            clean_q = query_str.replace(" ", "").upper()
            query = query.filter(Vehicle.plate_number.like(f"%{clean_q}%"))
        if vehicle_type:
            query = query.filter(Vehicle.vehicle_type == vehicle_type.upper())
        if is_flagged is not None:
            query = query.filter(Vehicle.is_flagged == is_flagged)

        vehicles = query.order_by(desc(Vehicle.last_seen_at)).limit(limit).all()
        
        # Enrich with total sightings
        results = []
        for v in vehicles:
            sightings = db.query(func.count(Detection.id)).filter(Detection.plate_number == v.plate_number).scalar()
            results.append({
                "plate_number": v.plate_number,
                "vehicle_type": v.vehicle_type,
                "color": v.color,
                "make_model": v.make_model,
                "is_ev": v.is_ev,
                "first_seen_at": v.first_seen_at,
                "last_seen_at": v.last_seen_at,
                "is_flagged": v.is_flagged,
                "flag_reason": v.flag_reason,
                "total_sightings": sightings or 0
            })
        return results

    def get_by_plate(self, db: Session, plate_number: str) -> Optional[dict]:
        clean_plate = plate_number.replace(" ", "").upper()
        v = db.query(Vehicle).filter(Vehicle.plate_number == clean_plate).first()
        if not v:
            return None
        sightings = db.query(func.count(Detection.id)).filter(Detection.plate_number == v.plate_number).scalar()
        return {
            "plate_number": v.plate_number,
            "vehicle_type": v.vehicle_type,
            "color": v.color,
            "make_model": v.make_model,
            "is_ev": v.is_ev,
            "first_seen_at": v.first_seen_at,
            "last_seen_at": v.last_seen_at,
            "is_flagged": v.is_flagged,
            "flag_reason": v.flag_reason,
            "total_sightings": sightings or 0
        }

    def get_trajectory(self, db: Session, plate_number: str) -> Dict[str, Any]:
        clean_plate = plate_number.replace(" ", "").upper()
        detections = db.query(Detection).filter(
            Detection.plate_number == clean_plate
        ).order_by(Detection.timestamp).all()

        det_dicts = [
            {
                "id": d.id,
                "camera_id": d.camera_id,
                "plate_number": d.plate_number,
                "timestamp": d.timestamp,
                "speed_kmh": d.speed_kmh,
                "ocr_confidence": d.ocr_confidence,
                "synthetic_crop_svg": d.synthetic_crop_svg
            }
            for d in detections
        ]

        trajectory = self.reconstructor.reconstruct(det_dicts)
        return trajectory

    def get_alerts(self, db: Session, plate_number: str) -> List[Alert]:
        clean_plate = plate_number.replace(" ", "").upper()
        return db.query(Alert).filter(
            Alert.plate_number == clean_plate
        ).order_by(desc(Alert.created_at)).all()
