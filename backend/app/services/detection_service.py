from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models.detection import Detection
from backend.app.models.vehicle import Vehicle
from providers.base import UnifiedDetectionPayload


class DetectionService:
    @staticmethod
    def record_detection(db: Session, payload: UnifiedDetectionPayload) -> Detection:
        """Stores a detection in the database and updates or creates the vehicle entity."""
        plate = payload.anpr.plate_text
        v_det = payload.detection
        now = payload.timestamp

        # Check/update vehicle profile
        vehicle = db.query(Vehicle).filter(Vehicle.plate_number == plate).first()
        if not vehicle:
            vehicle = Vehicle(
                plate_number=plate,
                vehicle_type=v_det.vehicle_type.value if hasattr(v_det.vehicle_type, 'value') else str(v_det.vehicle_type),
                color=v_det.color,
                make_model=v_det.make_model,
                is_ev=("EV" in (v_det.make_model or "")),
                first_seen_at=now,
                last_seen_at=now,
                is_flagged=("flag_reason" in payload.metadata),
                flag_reason=payload.metadata.get("flag_reason")
            )
            db.add(vehicle)
        else:
            vehicle.last_seen_at = now
            if "flag_reason" in payload.metadata:
                vehicle.is_flagged = True
                vehicle.flag_reason = payload.metadata.get("flag_reason")

        # Create Detection record
        db_detection = Detection(
            id=payload.id,
            camera_id=payload.camera_id,
            plate_number=plate,
            ocr_plate_text=payload.anpr.raw_text,
            ocr_confidence=payload.anpr.confidence,
            vehicle_type=v_det.vehicle_type.value if hasattr(v_det.vehicle_type, 'value') else str(v_det.vehicle_type),
            vehicle_color=v_det.color,
            speed_kmh=payload.estimated_speed_kmh or 0.0,
            fused_confidence=payload.fused_confidence,
            reid_hash=payload.reid.signature_hash if payload.reid else None,
            synthetic_crop_svg=payload.crop_svg,
            timestamp=now
        )
        db.add(db_detection)
        db.commit()
        db.refresh(db_detection)
        return db_detection

    @staticmethod
    def get_recent(
        db: Session,
        limit: int = 50,
        camera_id: Optional[str] = None,
        plate: Optional[str] = None
    ) -> List[Detection]:
        query = db.query(Detection)
        if camera_id:
            query = query.filter(Detection.camera_id == camera_id)
        if plate:
            query = query.filter(Detection.plate_number.like(f"%{plate}%"))
        return query.order_by(desc(Detection.timestamp)).limit(limit).all()

    @staticmethod
    def get_by_id(db: Session, detection_id: str) -> Optional[Detection]:
        return db.query(Detection).filter(Detection.id == detection_id).first()
