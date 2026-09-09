from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict
from datetime import datetime


class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    plate_number: Optional[str] = None
    camera_id: Optional[str] = None
    details: Dict[str, Any]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertAcknowledge(BaseModel):
    status: str = "ACKNOWLEDGED"
