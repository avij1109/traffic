from sqlalchemy import Column, String, Float, Integer
from backend.app.core.database import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    zone = Column(String, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed_limit_kmh = Column(Float, default=50.0)
    status = Column(String, default="ACTIVE", index=True)  # ACTIVE, OFFLINE, MAINTENANCE
    fps = Column(Integer, default=30)
