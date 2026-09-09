"""Comprehensive unit and integration test suite for the Traffic Simulator.
Tests cover:
1. Mock data integrity and Delhi NCR road network validity.
2. Camera topology graph, distance queries, shortest path routing, and GeoJSON export.
3. Fleet generation, Indian RTO plate formats, vehicle types, and deterministic seeding.
4. Continuous simulation engine, vehicle state machine, and camera blackout handling.
5. Anomaly injection (impossible travel, cloned plates, camera blackouts) and validation
   against analytics anomaly detectors.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
import pytest

from simulator.mock_data import CAMERAS_SEED, ROAD_EDGES_SEED
from simulator.topology import CameraTopology
from simulator.generator import VehicleGenerator
from simulator.anomalies import AnomalyScenarioManager
from simulator.engine import TrafficSimulatorEngine, VehicleSimState
from providers.base import VehicleType, UnifiedDetectionPayload
from providers.simulator_provider import SimulatorVisionProvider
from analytics.impossible_travel import ImpossibleTravelDetector
from analytics.plate_clone import PlateCloneDetector


# ==============================================================================
# 1. Mock Data & Road Network Integrity Tests
# ==============================================================================

class TestMockDataIntegrity:
    """Validates the static seed data for Delhi NCR camera network."""

    def test_cameras_seed_count_and_fields(self):
        """Verify minimum required cameras and mandatory schema fields."""
        assert len(CAMERAS_SEED) >= 10
        camera_ids = set()
        for cam in CAMERAS_SEED:
            assert "id" in cam and cam["id"].startswith("CAM-")
            assert "name" in cam and len(cam["name"]) > 0
            assert "zone" in cam
            assert 28.0 <= cam["latitude"] <= 29.0  # Delhi NCR latitude band
            assert 76.8 <= cam["longitude"] <= 77.5  # Delhi NCR longitude band
            assert 30.0 <= cam["speed_limit_kmh"] <= 120.0
            assert cam["status"] in ["ACTIVE", "OFFLINE", "MAINTENANCE"]
            assert cam["fps"] >= 15
            camera_ids.add(cam["id"])
        # IDs must be strictly unique
        assert len(camera_ids) == len(CAMERAS_SEED)

    def test_road_edges_seed_connectivity(self):
        """Verify all road edges reference valid cameras and have positive lengths."""
        camera_ids = {cam["id"] for cam in CAMERAS_SEED}
        assert len(ROAD_EDGES_SEED) >= 12
        for u, v, dist in ROAD_EDGES_SEED:
            assert u in camera_ids, f"Edge source {u} not in camera seed"
            assert v in camera_ids, f"Edge target {v} not in camera seed"
            assert u != v, "Self-loop edge detected"
            assert dist > 0.0, f"Distance must be positive, got {dist}"


# ==============================================================================
# 2. Camera Topology & Spatial Graph Tests
# ==============================================================================

class TestCameraTopology:
    """Validates the NetworkX graph wrapper for spatial queries."""

    @pytest.fixture
    def topology(self):
        return CameraTopology()

    def test_graph_initialization(self, topology):
        """Graph must contain all cameras and road edges."""
        all_ids = topology.get_all_camera_ids()
        assert len(all_ids) == len(CAMERAS_SEED)
        assert topology.graph.number_of_nodes() == len(CAMERAS_SEED)
        assert topology.graph.number_of_edges() == len(ROAD_EDGES_SEED)

    def test_camera_lookup(self, topology):
        """Metadata lookup for known and unknown cameras."""
        cam1 = topology.get_camera("CAM-01")
        assert cam1 is not None
        assert cam1["name"] == "Connaught Place"
        assert cam1["zone"] == "Central Delhi"
        assert topology.get_camera("NON_EXISTENT") is None

    def test_camera_neighbors(self, topology):
        """Verify adjacency queries."""
        neighbors = topology.get_neighbors("CAM-01")
        assert len(neighbors) >= 2
        assert "CAM-02" in neighbors
        assert topology.get_neighbors("NON_EXISTENT") == []

    def test_distance_calculations(self, topology):
        """Shortest path distance calculations."""
        # Self distance must be 0
        assert topology.get_distance("CAM-01", "CAM-01") == 0.0
        # Direct neighbor distance
        dist_direct = topology.get_distance("CAM-01", "CAM-02")
        assert dist_direct == 2.8
        # Multi-hop distance
        dist_multihop = topology.get_distance("CAM-01", "CAM-09")
        assert 15.0 < dist_multihop < 30.0
        # Non-existent node returns high distance fallback
        assert topology.get_distance("CAM-01", "UNKNOWN_CAM") == 9999.0

    def test_shortest_path_routing(self, topology):
        """Dijkstra shortest path returns valid camera sequence."""
        path = topology.get_shortest_path("CAM-01", "CAM-02")
        assert path == ["CAM-01", "CAM-02"]

        # Same origin-destination returns single-node list
        assert topology.get_shortest_path("CAM-01", "CAM-01") == ["CAM-01"]

        # Multi-hop path from Connaught Place (CAM-01) to Cyber Hub (CAM-09)
        path_long = topology.get_shortest_path("CAM-01", "CAM-09")
        assert len(path_long) >= 3
        assert path_long[0] == "CAM-01"
        assert path_long[-1] == "CAM-09"

        # Verify edge continuity in path
        for i in range(len(path_long) - 1):
            u, v = path_long[i], path_long[i + 1]
            assert topology.graph.has_edge(u, v)

    def test_path_distance(self, topology):
        """Verify cumulative path distance."""
        path = ["CAM-01", "CAM-02", "CAM-03"]
        dist = topology.get_path_distance(path)
        d1 = topology.get_distance("CAM-01", "CAM-02")
        d2 = topology.get_distance("CAM-02", "CAM-03")
        assert abs(dist - (d1 + d2)) < 0.001
        assert topology.get_path_distance([]) == 0.0
        assert topology.get_path_distance(["CAM-01"]) == 0.0

    def test_camera_status_mutation_isolation(self, topology):
        """Test status toggling and verify global seed is NOT mutated."""
        assert topology.is_camera_active("CAM-01") is True
        topology.set_camera_status("CAM-01", "OFFLINE")
        assert topology.is_camera_active("CAM-01") is False
        assert "CAM-01" not in topology.get_active_camera_ids()

        # Re-initialize new topology to verify CAMERAS_SEED wasn't mutated
        fresh_topology = CameraTopology()
        assert fresh_topology.is_camera_active("CAM-01") is True

    def test_geojson_export(self, topology):
        """GeoJSON export format check."""
        geojson = topology.to_geojson()
        assert geojson["type"] == "FeatureCollection"
        features = geojson["features"]
        cam_features = [f for f in features if f["properties"].get("type") == "camera"]
        road_features = [f for f in features if f["properties"].get("type") == "road"]
        assert len(cam_features) == len(CAMERAS_SEED)
        assert len(road_features) == len(ROAD_EDGES_SEED)


# ==============================================================================
# 3. Fleet Generation & Vehicle Profile Tests
# ==============================================================================

class TestVehicleGenerator:
    """Validates realistic Indian vehicle generation and fleet generation."""

    def test_plate_generation_format(self):
        """Registration plate format should follow authentic Indian RTO standards."""
        for _ in range(50):
            plate = VehicleGenerator.generate_plate()
            # Length should be 9-10 chars: e.g. DL01AB1234
            assert 8 <= len(plate) <= 11
            state_code = plate[:2]
            assert state_code in VehicleGenerator.STATES
            # Digits at end
            assert plate[-4:].isdigit()

    def test_state_specific_plate_generation(self):
        """Generates plates for specific requested states."""
        for state in ["DL", "HR", "UP", "PB"]:
            plate = VehicleGenerator.generate_plate(state=state)
            assert plate.startswith(state)

    def test_vehicle_profile_generation(self):
        """Profile contains realistic parameters and valid types."""
        profile = VehicleGenerator.generate_vehicle_profile()
        assert "plate_number" in profile
        assert isinstance(profile["vehicle_type"], VehicleType)
        assert "make_model" in profile
        assert profile["color"] in VehicleGenerator.COLORS
        assert 30.0 <= profile["cruising_speed_kmh"] <= 85.0
        assert "is_ev" in profile

    def test_fleet_generation_and_watchlist(self):
        """Fleet generator flags top vehicles for demo scenarios."""
        fleet = VehicleGenerator.generate_fleet(size=40)
        assert len(fleet) == 40
        # Watchlisted vehicles
        assert fleet[0]["is_flagged"] is True
        assert fleet[0]["flag_reason"] == "STOLEN_VEHICLE_REPORT_FIR_9021"
        assert fleet[1]["is_flagged"] is True
        assert fleet[1]["flag_reason"] == "SUSPECT_IN_ORGANIZED_CAR_THEFT"
        # Non-flagged regular commuter
        assert fleet[2]["is_flagged"] is False
        assert fleet[2]["flag_reason"] is None

    def test_fleet_generation_deterministic_seed(self):
        """Same random seed must produce identical fleet profiles."""
        fleet1 = VehicleGenerator.generate_fleet(size=10, seed=42)
        fleet2 = VehicleGenerator.generate_fleet(size=10, seed=42)
        assert [v["plate_number"] for v in fleet1] == [v["plate_number"] for v in fleet2]
        assert [v["make_model"] for v in fleet1] == [v["make_model"] for v in fleet2]

    def test_fleet_generation_edge_sizes(self):
        """Handles 0, 1, and small sizes without index errors."""
        assert len(VehicleGenerator.generate_fleet(size=0)) == 0
        single = VehicleGenerator.generate_fleet(size=1)
        assert len(single) == 1
        assert single[0]["is_flagged"] is True


# ==============================================================================
# 4. Continuous Simulation Engine & State Machine Tests
# ==============================================================================

class TestTrafficSimulatorEngine:
    """Validates the discrete-event traffic simulation engine."""

    @pytest.fixture
    def engine(self):
        topology = CameraTopology()
        vision_provider = SimulatorVisionProvider()
        return TrafficSimulatorEngine(
            topology=topology,
            vision_provider=vision_provider,
            fleet_size=15,
            speed_multiplier=5.0,
            seed=123
        )

    def test_engine_initialization(self, engine):
        """Engine sets up fleet and initial arrival times."""
        assert len(engine.vehicles) == 15
        assert engine.is_running is False
        assert engine.event_count == 0
        # Each vehicle must have a valid route
        for plate, state in engine.vehicles.items():
            assert len(state.route) >= 1
            assert state.status == VehicleSimState.EN_ROUTE
            assert state.next_arrival_time > 0

    @pytest.mark.asyncio
    async def test_deterministic_step_once(self, engine):
        """step_once steps all vehicles and dispatches detection payloads."""
        # Force all vehicles to be immediately due for arrival
        now = time.time()
        for state in engine.vehicles.values():
            state.next_arrival_time = now - 1.0

        emitted = await engine.step_once(current_time=now)
        assert len(emitted) > 0

        first_det = emitted[0]
        assert isinstance(first_det, UnifiedDetectionPayload)
        assert first_det.camera_id in engine.topology.get_all_camera_ids()
        assert first_det.detection.confidence >= 0.8
        assert first_det.anpr.confidence >= 0.6
        assert first_det.reid.signature_hash is not None
        assert first_det.crop_svg is not None
        assert "<svg" in first_det.crop_svg

    @pytest.mark.asyncio
    async def test_vehicle_state_machine_transition(self, engine):
        """Tests EN_ROUTE -> CHECKPOINT_DETECTED -> EN_ROUTE transitions."""
        plate, state = next(iter(engine.vehicles.items()))
        now = time.time()
        state.next_arrival_time = now - 0.5
        initial_hop = state.current_hop_index

        await engine.step_once(current_time=now)

        assert state.status in [VehicleSimState.CHECKPOINT_DETECTED, VehicleSimState.EN_ROUTE, VehicleSimState.COMPLETED]
        assert state.total_detections >= 1
        assert state.last_cam_id is not None
        assert state.current_hop_index > initial_hop or state.current_hop_index == 0

    @pytest.mark.asyncio
    async def test_camera_blackout_missed_detections(self, engine):
        """Vehicles passing through an offline camera do not emit detections."""
        now = time.time()
        # Find a vehicle and take its current destination camera offline
        plate, state = next(iter(engine.vehicles.items()))
        target_cam = state.route[state.current_hop_index]
        engine.topology.set_camera_status(target_cam, "OFFLINE")

        # Set arrival time to past for only this vehicle
        for p, s in engine.vehicles.items():
            s.next_arrival_time = now + 999.0
        state.next_arrival_time = now - 1.0

        emitted = await engine.step_once(current_time=now)
        # Should NOT emit detection for the offline camera
        assert len(emitted) == 0
        assert engine.missed_detections >= 1

    @pytest.mark.asyncio
    async def test_listener_dispatch(self, engine):
        """Registered listeners receive emitted payloads."""
        received = []

        def listener(payload: UnifiedDetectionPayload):
            received.append(payload)

        engine.register_listener(listener)
        now = time.time()
        for state in engine.vehicles.values():
            state.next_arrival_time = now - 0.1

        await engine.step_once(current_time=now)
        assert len(received) > 0

        # Unregister listener
        engine.unregister_listener(listener)
        count_before = len(received)
        await engine.step_once(current_time=now + 50.0)
        assert len(received) == count_before

    @pytest.mark.asyncio
    async def test_start_pause_resume_stop_lifecycle(self, engine):
        """Starts background simulation loop, pauses, resumes, and cleanly stops."""
        engine.start()
        assert engine.is_running is True

        # Let loop run for a brief moment
        await asyncio.sleep(0.3)
        assert engine.event_count >= 0

        engine.pause()
        assert engine._pause_event.is_set() is False

        engine.resume()
        assert engine._pause_event.is_set() is True

        await engine.stop_async()
        assert engine.is_running is False
        assert engine._task.done()

    def test_stats_reporting(self, engine):
        """Engine statistics output."""
        stats = engine.get_stats()
        assert "is_running" in stats
        assert stats["fleet_size"] == 15
        assert stats["speed_multiplier"] == 5.0
        assert "total_events_generated" in stats
        assert "active_cameras" in stats
        assert stats["total_cameras"] == len(CAMERAS_SEED)


# ==============================================================================
# 5. Anomaly Injection Scenarios & Analytics Integration Tests
# ==============================================================================

class TestAnomalyScenarios:
    """Validates anomaly generation and cross-verifies with analytics detectors."""

    @pytest.fixture
    def setup_anomaly_env(self):
        topology = CameraTopology()
        vision_provider = SimulatorVisionProvider()
        manager = AnomalyScenarioManager(topology, vision_provider)
        impossible_detector = ImpossibleTravelDetector(topology)
        clone_detector = PlateCloneDetector(topology)
        return {
            "topology": topology,
            "manager": manager,
            "impossible_detector": impossible_detector,
            "clone_detector": clone_detector
        }

    @pytest.mark.asyncio
    async def test_impossible_travel_anomaly_generation(self, setup_anomaly_env):
        """Generates physics-defying speed events and verifies alert detection."""
        env = setup_anomaly_env
        manager: AnomalyScenarioManager = env["manager"]
        detector: ImpossibleTravelDetector = env["impossible_detector"]

        base_time = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        events = await manager.create_impossible_travel_event(
            plate_number="DL03AX8821",
            vehicle_type=VehicleType.CAR,
            cam_start="CAM-01",  # Connaught Place
            cam_end="CAM-09",    # Cyber Hub (~20km away)
            delta_seconds=15.0,
            timestamp=base_time
        )

        assert len(events) == 2
        det1, det2 = events[0], events[1]
        assert det1.camera_id == "CAM-01"
        assert det2.camera_id == "CAM-09"
        assert det2.timestamp == base_time + timedelta(seconds=15.0)
        assert det2.metadata["anomaly_injected"] == "IMPOSSIBLE_TRAVEL"
        assert det2.metadata["calculated_speed_kmh"] > 1000.0

        # Cross-verify with ImpossibleTravelDetector from Analytics
        alert = detector.check_transit(
            plate_number="DL03AX8821",
            prev_camera_id=det1.camera_id,
            prev_time=det1.timestamp,
            curr_camera_id=det2.camera_id,
            curr_time=det2.timestamp,
            vehicle_type="CAR"
        )
        assert alert is not None
        assert alert["alert_type"] == "IMPOSSIBLE_TRAVEL"
        assert alert["severity"] == "CRITICAL"
        assert alert["plate_number"] == "DL03AX8821"
        assert alert["details"]["calculated_speed_kmh"] > 1000.0

    @pytest.mark.asyncio
    async def test_cloned_plate_anomaly_generation(self, setup_anomaly_env):
        """Generates twin simultaneous sightings and verifies clone detection."""
        env = setup_anomaly_env
        manager: AnomalyScenarioManager = env["manager"]
        clone_detector: PlateCloneDetector = env["clone_detector"]

        base_time = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        events = await manager.create_cloned_plate_events(
            cloned_plate="HR26DQ9999",
            cam_a="CAM-02",  # India Gate
            cam_b="CAM-07",  # IGI Airport T3
            delta_seconds=2.0,
            timestamp=base_time
        )

        assert len(events) == 2
        det_a, det_b = events[0], events[1]
        assert det_a.anpr.plate_text == "HR26DQ9999"
        assert det_b.anpr.plate_text == "HR26DQ9999"
        # Two distinct vehicle types
        assert det_a.detection.vehicle_type == VehicleType.SUV
        assert det_b.detection.vehicle_type == VehicleType.CAR

        # Feed first detection to CloneDetector
        alert1 = clone_detector.record_and_check(
            plate_number=det_a.anpr.plate_text,
            camera_id=det_a.camera_id,
            timestamp=det_a.timestamp,
            vehicle_type=det_a.detection.vehicle_type.value,
            color=det_a.detection.color,
            make_model=det_a.detection.make_model
        )
        assert alert1 is None  # First sighting, baseline established

        # Feed second conflicting detection to CloneDetector
        alert2 = clone_detector.record_and_check(
            plate_number=det_b.anpr.plate_text,
            camera_id=det_b.camera_id,
            timestamp=det_b.timestamp,
            vehicle_type=det_b.detection.vehicle_type.value,
            color=det_b.detection.color,
            make_model=det_b.detection.make_model
        )
        assert alert2 is not None
        assert alert2["alert_type"] == "PLATE_CLONE"
        assert alert2["severity"] == "CRITICAL"
        assert alert2["plate_number"] == "HR26DQ9999"

    def test_camera_blackout_and_restore(self, setup_anomaly_env):
        """Simulates camera outage and restoration."""
        env = setup_anomaly_env
        manager: AnomalyScenarioManager = env["manager"]
        topology: CameraTopology = env["topology"]

        # Blackout
        res = manager.create_camera_blackout("CAM-01", status="OFFLINE")
        assert res["success"] is True
        assert res["new_status"] == "OFFLINE"
        assert topology.is_camera_active("CAM-01") is False

        # Restore
        res_restore = manager.restore_camera("CAM-01")
        assert res_restore["success"] is True
        assert res_restore["new_status"] == "ACTIVE"
        assert topology.is_camera_active("CAM-01") is True

    @pytest.mark.asyncio
    async def test_engine_anomaly_trigger_methods(self):
        """Verifies trigger_impossible_travel and trigger_duplicate_plate on engine."""
        engine = TrafficSimulatorEngine(fleet_size=10, speed_multiplier=2.0)
        emitted = []
        engine.register_listener(lambda p: emitted.append(p))

        # Impossible travel with emit_delay=0.0 for instant execution
        events_imp = await engine.trigger_impossible_travel(emit_delay=0.0)
        assert len(events_imp) == 2
        assert len(emitted) == 2

        # Cloned plate with emit_delay=0.0
        events_clone = await engine.trigger_duplicate_plate(emit_delay=0.0)
        assert len(events_clone) == 2
        assert len(emitted) == 4

        # Blackout toggle
        res_blackout = engine.trigger_camera_blackout("CAM-05")
        assert res_blackout["new_status"] == "OFFLINE"
        assert engine.topology.is_camera_active("CAM-05") is False

        res_restore = engine.restore_camera("CAM-05")
        assert res_restore["new_status"] == "ACTIVE"
        assert engine.topology.is_camera_active("CAM-05") is True
