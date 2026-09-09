from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.analytics import SystemOverviewMetrics, CongestionResponse, HourlyFlowMetric
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.simulator_service import simulator_service

router = APIRouter()
analytics_service = AnalyticsService(
    simulator_service.topology,
    simulator_service.congestion_analyzer
)


@router.get("/overview", response_model=SystemOverviewMetrics)
def get_overview(db: Session = Depends(get_db)):
    """System-wide operational telemetry metrics."""
    return analytics_service.get_overview_metrics(db)


@router.get("/congestion", response_model=CongestionResponse)
def get_congestion():
    """Real-time camera density metrics and heatmap coordinates."""
    return analytics_service.get_congestion()


@router.get("/hourly-flow", response_model=List[HourlyFlowMetric])
def get_hourly_flow(db: Session = Depends(get_db)):
    """12-hour historical vehicle classification breakdown."""
    return analytics_service.get_hourly_flow(db)
