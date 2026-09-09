from fastapi import APIRouter
from backend.app.schemas.simulator import (
    SimulatorStatusResponse,
    SimulatorSpeedUpdate,
    AnomalyInjectionRequest
)
from backend.app.services.simulator_service import simulator_service

router = APIRouter()


@router.get("/status", response_model=SimulatorStatusResponse)
def get_simulator_status():
    """Retrieve live simulator throughput, fleet size, and uptime."""
    return simulator_service.get_status()


@router.post("/start")
def start_simulator():
    """Start continuous traffic simulation."""
    simulator_service.start()
    return {"status": "STARTED"}


@router.post("/pause")
def pause_simulator():
    """Pause traffic simulation."""
    simulator_service.pause()
    return {"status": "PAUSED"}


@router.post("/resume")
def resume_simulator():
    """Resume traffic simulation."""
    simulator_service.resume()
    return {"status": "RESUMED"}


@router.post("/speed")
def set_simulator_speed(speed: SimulatorSpeedUpdate):
    """Set time compression multiplier (1x, 2x, 5x, 10x)."""
    simulator_service.set_speed(speed.multiplier)
    return {"status": "UPDATED", "multiplier": speed.multiplier}


@router.post("/inject-anomaly")
async def inject_anomaly(req: AnomalyInjectionRequest):
    """Trigger demonstration scenarios: IMPOSSIBLE_TRAVEL, CLONED_PLATE."""
    res = await simulator_service.inject_anomaly(req.anomaly_type)
    return res
