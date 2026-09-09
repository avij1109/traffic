from fastapi import APIRouter

from backend.app.api.v1.endpoints.cameras import router as cameras_router
from backend.app.api.v1.endpoints.detections import router as detections_router
from backend.app.api.v1.endpoints.vehicles import router as vehicles_router
from backend.app.api.v1.endpoints.alerts import router as alerts_router
from backend.app.api.v1.endpoints.analytics import router as analytics_router
from backend.app.api.v1.endpoints.simulator import router as simulator_router

api_router = APIRouter()

api_router.include_router(cameras_router, prefix="/cameras", tags=["Cameras"])
api_router.include_router(detections_router, prefix="/detections", tags=["Detections"])
api_router.include_router(vehicles_router, prefix="/vehicles", tags=["Vehicles"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(simulator_router, prefix="/simulator", tags=["Simulator"])
