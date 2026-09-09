from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.camera import CameraResponse, CameraStatusUpdate
from backend.app.services.camera_service import CameraService
from backend.app.websockets.connection_manager import ws_manager

router = APIRouter()


@router.get("", response_model=List[CameraResponse])
def get_cameras(db: Session = Depends(get_db)):
    """List all camera checkpoints with GPS coordinates and operational status."""
    return CameraService.get_all(db)


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: str, db: Session = Depends(get_db)):
    """Get metadata for a specific camera checkpoint."""
    cam = CameraService.get_by_id(db, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cam


@router.post("/{camera_id}/status", response_model=CameraResponse)
async def update_camera_status(
    camera_id: str,
    status_update: CameraStatusUpdate,
    db: Session = Depends(get_db)
):
    """Toggle camera status (ACTIVE, OFFLINE, MAINTENANCE) to simulate camera blackouts."""
    cam = CameraService.update_status(db, camera_id, status_update.status)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Broadcast camera status change via WebSocket
    await ws_manager.broadcast_event("CAMERA_STATUS_CHANGED", {
        "camera_id": cam.id,
        "status": cam.status,
        "name": cam.name
    })
    return cam
