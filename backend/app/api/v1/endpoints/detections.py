from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.detection import DetectionResponse
from backend.app.services.detection_service import DetectionService

router = APIRouter()


@router.get("/recent", response_model=List[DetectionResponse])
def get_recent_detections(
    limit: int = Query(50, ge=1, le=200),
    camera_id: Optional[str] = None,
    plate: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve recent real-time vehicle detections across the camera network."""
    return DetectionService.get_recent(db, limit=limit, camera_id=camera_id, plate=plate)


@router.get("/{detection_id}", response_model=DetectionResponse)
def get_detection(detection_id: str, db: Session = Depends(get_db)):
    """Retrieve a single detection event with synthetic plate crop and confidence scores."""
    det = DetectionService.get_by_id(db, detection_id)
    if not det:
        raise HTTPException(status_code=404, detail="Detection not found")
    return det
