from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from datetime import datetime, timezone
from backend.app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, index=True)
    alert_type = Column(String, nullable=False, index=True)  # IMPOSSIBLE_TRAVEL, PLATE_CLONE, etc.
    severity = Column(String, nullable=False, index=True)    # LOW, MEDIUM, HIGH, CRITICAL
    plate_number = Column(String, ForeignKey("vehicles.plate_number"), nullable=True, index=True)
    camera_id = Column(String, ForeignKey("cameras.id"), nullable=True, index=True)
    details_json = Column(Text, nullable=False)              # Serialized JSON root cause metrics
    status = Column(String, default="ACTIVE", index=True)    # ACTIVE, ACKNOWLEDGED, RESOLVED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
