import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models.alert import Alert


class AlertService:
    @staticmethod
    def create_alert(
        db: Session,
        alert_type: str,
        severity: str,
        plate_number: Optional[str],
        camera_id: Optional[str],
        details: Dict[str, Any]
    ) -> Alert:
        alert_id = f"alt_{uuid.uuid4().hex[:12]}"
        db_alert = Alert(
            id=alert_id,
            alert_type=alert_type,
            severity=severity,
            plate_number=plate_number,
            camera_id=camera_id,
            details_json=json.dumps(details),
            status="ACTIVE",
            created_at=datetime.now(timezone.utc)
        )
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        return db_alert

    @staticmethod
    def get_alerts(
        db: Session,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        alert_type: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        query = db.query(Alert)
        if severity:
            query = query.filter(Alert.severity == severity.upper())
        if status:
            query = query.filter(Alert.status == status.upper())
        if alert_type:
            query = query.filter(Alert.alert_type == alert_type.upper())

        alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()
        results = []
        for a in alerts:
            try:
                details = json.loads(a.details_json)
            except Exception:
                details = {"raw": a.details_json}
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

    @staticmethod
    def acknowledge_alert(db: Session, alert_id: str) -> Optional[dict]:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = "ACKNOWLEDGED"
            db.commit()
            db.refresh(alert)
            try:
                details = json.loads(alert.details_json)
            except Exception:
                details = {}
            return {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "plate_number": alert.plate_number,
                "camera_id": alert.camera_id,
                "details": details,
                "status": alert.status,
                "created_at": alert.created_at
            }
        return None
