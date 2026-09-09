import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import engine, Base, SessionLocal
from backend.app.services.camera_service import CameraService
from backend.app.services.simulator_service import simulator_service
from backend.app.websockets.connection_manager import ws_manager
from backend.app.api.v1.router import api_router

# Ensure all models are registered with Base metadata
import backend.app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization, camera seeding,
    and background traffic simulator lifecycle.
    """
    # 1. Create database schema tables
    Base.metadata.create_all(bind=engine)

    # 2. Seed initial camera checkpoints if not present
    db = SessionLocal()
    try:
        CameraService.seed_initial_cameras(db)
    finally:
        db.close()

    # 3. Start discrete-event traffic simulator engine if auto-start is enabled
    if settings.SIMULATOR_AUTO_START:
        simulator_service.start()

    yield

    # Shutdown: cleanly terminate simulator background loop
    simulator_service.engine.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Intelligent Traffic Surveillance & ANPR Multi-Camera Correlation Platform API",
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS) for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register REST API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def root():
    """Service health and metadata discovery endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "ONLINE",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Liveness probe returning operational state."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulator_running": simulator_service.engine.is_running
    }


@app.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket):
    """Real-time bidirectional WebSocket stream for detection events,
    threat alerts, and network telemetry.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.websocket("/ws/alerts")
async def websocket_alerts_alias(websocket: WebSocket):
    """WebSocket stream alias dedicated to alert consumers."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
