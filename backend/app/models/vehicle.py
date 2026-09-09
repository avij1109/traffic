from sqlalchemy import Column, String, Boolean, DateTime
from datetime import datetime, timezone
from backend.app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    plate_number = Column(String, primary_key=True, index=True)
    vehicle_type = Column(String, nullable=False, index=True)
    color = Column(String, nullable=False)
    make_model = Column(String, nullable=True)
    is_ev = Column(Boolean, default=False)
    first_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    is_flagged = Column(Boolean, default=False, index=True)
    flag_reason = Column(String, nullable=True)
