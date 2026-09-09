from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.camera import Camera
from simulator.mock_data import CAMERAS_SEED


class CameraService:
    @staticmethod
    def get_all(db: Session) -> List[Camera]:
        return db.query(Camera).all()

    @staticmethod
    def get_by_id(db: Session, camera_id: str) -> Optional[Camera]:
        return db.query(Camera).filter(Camera.id == camera_id).first()

    @staticmethod
    def update_status(db: Session, camera_id: str, new_status: str) -> Optional[Camera]:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if camera:
            camera.status = new_status
            db.commit()
            db.refresh(camera)
        return camera

    @staticmethod
    def seed_initial_cameras(db: Session):
        """Seeds the 12 Delhi NCR cameras if the table is empty."""
        count = db.query(Camera).count()
        if count == 0:
            for seed in CAMERAS_SEED:
                cam = Camera(
                    id=seed["id"],
                    name=seed["name"],
                    zone=seed["zone"],
                    latitude=seed["latitude"],
                    longitude=seed["longitude"],
                    speed_limit_kmh=seed["speed_limit_kmh"],
                    status=seed["status"],
                    fps=seed["fps"]
                )
                db.add(cam)
            db.commit()
