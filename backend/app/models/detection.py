from sqlalchemy import Column, String, Float, DateTime, Text, ForeignKey
from datetime import datetime, timezone
from backend.app.core.database import Base


class Detection(Base):
    __tablename__ = "detections"

    id = Column(String, primary_key=True, index=True)
    camera_id = Column(String, ForeignKey("cameras.id"), nullable=False, index=True)
    plate_number = Column(String, ForeignKey("vehicles.plate_number"), nullable=False, index=True)
    ocr_plate_text = Column(String, nullable=False)
    ocr_confidence = Column(Float, nullable=False)
    vehicle_type = Column(String, nullable=False)
    vehicle_color = Column(String, nullable=False)
    speed_kmh = Column(Float, default=0.0)
    fused_confidence = Column(Float, default=0.95)
    reid_hash = Column(String, nullable=True)
    synthetic_crop_svg = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
