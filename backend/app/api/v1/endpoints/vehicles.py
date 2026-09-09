from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.vehicle import VehicleResponse, VehicleTrajectoryResponse
from backend.app.schemas.alert import AlertResponse
from backend.app.services.vehicle_service import VehicleService

router = APIRouter()
vehicle_service = VehicleService()


@router.get("/search", response_model=List[VehicleResponse])
def search_vehicles(
    q: Optional[str] = Query(None, description="Plate number substring"),
    vehicle_type: Optional[str] = None,
    is_flagged: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Fuzzy plate search and vehicle filter by attributes."""
    return vehicle_service.search_vehicles(
        db, query_str=q, vehicle_type=vehicle_type, is_flagged=is_flagged, limit=limit
    )


@router.get("/{plate_number}", response_model=VehicleResponse)
def get_vehicle(plate_number: str, db: Session = Depends(get_db)):
    """Retrieve vehicle master profile."""
    v = vehicle_service.get_by_plate(db, plate_number)
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found in registry")
    return v


@router.get("/{plate_number}/trajectory", response_model=VehicleTrajectoryResponse)
def get_vehicle_trajectory(plate_number: str, db: Session = Depends(get_db)):
    """Reconstruct chronological multi-camera journey, segment speeds, and predicted next camera."""
    return vehicle_service.get_trajectory(db, plate_number)


@router.get("/{plate_number}/alerts")
def get_vehicle_alerts(plate_number: str, db: Session = Depends(get_db)):
    """Retrieve all anomaly alerts triggered by this vehicle."""
    alerts = vehicle_service.get_alerts(db, plate_number)
    import json
    results = []
    for a in alerts:
        try:
            details = json.loads(a.details_json)
        except Exception:
            details = {}
        results.append({
            "id": a.id,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "plate_number": a.plate_number,
            "camera_id": a.camera_id,
            "details": details,
            "status": a.status,
            "created_at": a.created_at
        })
    return results
