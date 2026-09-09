import sys
import os
import json
import pytest

# Ensure repository root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.services.camera_service import CameraService
from scripts.seed_db import seed_database


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Seeds test data into the database before test execution."""
    seed_database()
    yield


@pytest.fixture
def client():
    """Provides a TestClient context that executes the FastAPI lifespan."""
    with TestClient(app) as test_client:
        yield test_client


# =====================================================================
# 1. System Health & Discovery Endpoints
# =====================================================================

def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "api_v1" in data


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "simulator_running" in data


# =====================================================================
# 2. Camera Management Endpoints (/api/v1/cameras)
# =====================================================================

def test_get_all_cameras(client: TestClient):
    response = client.get("/api/v1/cameras")
    assert response.status_code == 200
    cameras = response.json()
    assert isinstance(cameras, list)
    assert len(cameras) >= 12
    # Verify CAM-01 attributes
    cam_ids = [c["id"] for c in cameras]
    assert "CAM-01" in cam_ids
    assert "CAM-02" in cam_ids


def test_get_camera_by_id(client: TestClient):
    response = client.get("/api/v1/cameras/CAM-01")
    assert response.status_code == 200
    cam = response.json()
    assert cam["id"] == "CAM-01"
    assert "Connaught Place" in cam["name"]
    assert cam["zone"] == "Central Delhi"
    assert cam["speed_limit_kmh"] == 40.0


def test_get_camera_not_found(client: TestClient):
    response = client.get("/api/v1/cameras/CAM-INVALID-99")
    assert response.status_code == 404


def test_update_camera_status(client: TestClient):
    response = client.post(
        "/api/v1/cameras/CAM-01/status",
        json={"status": "MAINTENANCE"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "CAM-01"
    assert data["status"] == "MAINTENANCE"

    # Revert back to ACTIVE for consistency
    client.post("/api/v1/cameras/CAM-01/status", json={"status": "ACTIVE"})


# =====================================================================
# 3. Detection Stream Endpoints (/api/v1/detections)
# =====================================================================

def test_get_recent_detections(client: TestClient):
    response = client.get("/api/v1/detections/recent?limit=25")
    assert response.status_code == 200
    detections = response.json()
    assert isinstance(detections, list)
    assert len(detections) > 0
    det = detections[0]
    assert "id" in det
    assert "plate_number" in det
    assert "camera_id" in det
    assert "ocr_confidence" in det


def test_get_recent_detections_filtered(client: TestClient):
    response = client.get("/api/v1/detections/recent?plate=DL04EQ9999")
    assert response.status_code == 200
    detections = response.json()
    assert isinstance(detections, list)
    assert len(detections) >= 1
    for d in detections:
        assert "DL04EQ9999" in d["plate_number"]


def test_get_detection_by_id(client: TestClient):
    response = client.get("/api/v1/detections/det_seed_imp_1")
    assert response.status_code == 200
    det = response.json()
    assert det["id"] == "det_seed_imp_1"
    assert det["plate_number"] == "DL04EQ9999"
    assert det["camera_id"] == "CAM-01"


def test_get_detection_not_found(client: TestClient):
    response = client.get("/api/v1/detections/det_nonexistent_99")
    assert response.status_code == 404


# =====================================================================
# 4. Vehicle Dossier & Trajectory Endpoints (/api/v1/vehicles)
# =====================================================================

def test_search_vehicles(client: TestClient):
    response = client.get("/api/v1/vehicles/search?q=DL04")
    assert response.status_code == 200
    vehicles = response.json()
    assert isinstance(vehicles, list)
    assert len(vehicles) >= 1
    assert vehicles[0]["plate_number"] == "DL04EQ9999"


def test_search_vehicles_by_filter(client: TestClient):
    response = client.get("/api/v1/vehicles/search?is_flagged=true")
    assert response.status_code == 200
    flagged = response.json()
    assert len(flagged) >= 2
    for v in flagged:
        assert v["is_flagged"] is True


def test_get_vehicle_profile(client: TestClient):
    response = client.get("/api/v1/vehicles/DL04EQ9999")
    assert response.status_code == 200
    profile = response.json()
    assert profile["plate_number"] == "DL04EQ9999"
    assert profile["vehicle_type"] == "SUV"
    assert profile["is_flagged"] is True
    assert profile["total_sightings"] >= 2


def test_get_vehicle_not_found(client: TestClient):
    response = client.get("/api/v1/vehicles/XX99ZZ9999")
    assert response.status_code == 404


def test_get_vehicle_trajectory(client: TestClient):
    response = client.get("/api/v1/vehicles/UP16AB1234/trajectory")
    assert response.status_code == 200
    traj = response.json()
    assert traj["plate_number"] == "UP16AB1234"
    assert traj["total_sightings"] >= 4
    assert len(traj["visited_cameras"]) >= 4
    assert "geojson_path" in traj
    assert "predicted_next_cameras" in traj


def test_get_vehicle_alerts(client: TestClient):
    response = client.get("/api/v1/vehicles/DL04EQ9999/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)
    assert len(alerts) >= 1
    assert alerts[0]["alert_type"] == "IMPOSSIBLE_TRAVEL"


# =====================================================================
# 5. Anomaly & Alert Engine Endpoints (/api/v1/alerts)
# =====================================================================

def test_get_all_alerts(client: TestClient):
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)
    assert len(alerts) >= 3


def test_get_alerts_filtered(client: TestClient):
    response = client.get("/api/v1/alerts?severity=CRITICAL")
    assert response.status_code == 200
    critical_alerts = response.json()
    assert len(critical_alerts) >= 2
    for a in critical_alerts:
        assert a["severity"] == "CRITICAL"


def test_acknowledge_alert(client: TestClient):
    response = client.patch("/api/v1/alerts/alt_seed_imp_01/acknowledge")
    assert response.status_code == 200
    alert = response.json()
    assert alert["id"] == "alt_seed_imp_01"
    assert alert["status"] == "ACKNOWLEDGED"


# =====================================================================
# 6. City Traffic Analytics Endpoints (/api/v1/analytics)
# =====================================================================

def test_analytics_overview(client: TestClient):
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    overview = response.json()
    assert overview["total_cameras"] == 12
    assert overview["total_vehicles_tracked"] >= 40
    assert "network_average_speed_kmh" in overview
    assert "system_status" in overview


def test_analytics_congestion(client: TestClient):
    response = client.get("/api/v1/analytics/congestion")
    assert response.status_code == 200
    congestion = response.json()
    assert "cameras" in congestion
    assert "heatmap_points" in congestion
    assert len(congestion["cameras"]) >= 12


def test_analytics_hourly_flow(client: TestClient):
    response = client.get("/api/v1/analytics/hourly-flow")
    assert response.status_code == 200
    flow = response.json()
    assert isinstance(flow, list)
    assert len(flow) > 0
    first_hour = flow[0]
    assert "hour" in first_hour
    assert "car_count" in first_hour
    assert "suv_count" in first_hour
    assert "total" in first_hour


# =====================================================================
# 7. Simulator Control Endpoints (/api/v1/simulator)
# =====================================================================

def test_simulator_status(client: TestClient):
    response = client.get("/api/v1/simulator/status")
    assert response.status_code == 200
    status = response.json()
    assert "fleet_size" in status
    assert "speed_multiplier" in status
    assert "total_events_generated" in status


def test_simulator_controls(client: TestClient):
    # Pause
    res_pause = client.post("/api/v1/simulator/pause")
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "PAUSED"

    # Resume
    res_resume = client.post("/api/v1/simulator/resume")
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "RESUMED"

    # Speed multiplier update
    res_speed = client.post("/api/v1/simulator/speed", json={"multiplier": 3.0})
    assert res_speed.status_code == 200
    assert res_speed.json()["multiplier"] == 3.0

    # Start
    res_start = client.post("/api/v1/simulator/start")
    assert res_start.status_code == 200


def test_simulator_inject_impossible_travel(client: TestClient):
    response = client.post(
        "/api/v1/simulator/inject-anomaly",
        json={"anomaly_type": "IMPOSSIBLE_TRAVEL"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INJECTED"
    assert data["type"] == "IMPOSSIBLE_TRAVEL"


def test_simulator_inject_cloned_plate(client: TestClient):
    response = client.post(
        "/api/v1/simulator/inject-anomaly",
        json={"anomaly_type": "CLONED_PLATE"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INJECTED"
    assert data["type"] == "CLONED_PLATE"


# =====================================================================
# 8. Real-Time WebSocket Endpoint (/ws/live-feed)
# =====================================================================

def test_websocket_live_feed(client: TestClient):
    with client.websocket_connect("/ws/live-feed") as websocket:
        # Send heartbeat ping
        websocket.send_text(json.dumps({"type": "ping"}))
        response = websocket.receive_json()
        assert response.get("type") == "pong"
        assert "timestamp" in response
