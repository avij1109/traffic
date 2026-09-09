import math
import time
from datetime import datetime, timezone, timedelta
import pytest

from simulator.topology import CameraTopology
from analytics.impossible_travel import ImpossibleTravelDetector, haversine_distance_km
from analytics.plate_clone import PlateCloneDetector
from analytics.trajectory_reconstruction import TrajectoryReconstructor
from analytics.congestion_analyzer import CongestionAnalyzer
from analytics.graph_engine import SpatialGraphEngine, calculate_initial_bearing
from backend.app.schemas.vehicle import VehicleTrajectoryResponse


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture
def topology():
    """Provides a fresh instance of the city camera network topology."""
    return CameraTopology()


@pytest.fixture
def impossible_detector(topology):
    return ImpossibleTravelDetector(topology, max_physical_speed_kmh=160.0)


@pytest.fixture
def clone_detector(topology):
    return PlateCloneDetector(topology, window_seconds=900, max_transit_speed_kmh=160.0)


@pytest.fixture
def trajectory_reconstructor(topology):
    return TrajectoryReconstructor(topology)


@pytest.fixture
def congestion_analyzer(topology):
    return CongestionAnalyzer(topology, window_seconds=120)


# ---------------------------------------------------------------------------
# 1. IMPOSSIBLE TRAVEL TESTS
# ---------------------------------------------------------------------------

class TestImpossibleTravel:
    def test_normal_speed_transit(self, impossible_detector):
        """Standard commuter travel at legal speed should NOT generate an alert."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        # CAM-01 (Connaught Place) to CAM-02 (India Gate) is ~2.8 km
        # 3 minutes = 180 seconds -> ~56 km/h (speed limit 50 km/h, threshold 160 km/h)
        t1 = t0 + timedelta(seconds=180)

        alert = impossible_detector.check_transit(
            plate_number="DL01AB1234",
            prev_camera_id="CAM-01",
            prev_time=t0,
            curr_camera_id="CAM-02",
            curr_time=t1,
            vehicle_type="CAR"
        )
        assert alert is None

    def test_physics_violating_speed_transit(self, impossible_detector):
        """Transit requiring supersonic or impossible road velocity triggers CRITICAL alert."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        # CAM-01 (Connaught Place) to CAM-09 (Cyber Hub) is ~20 km
        # 15 seconds -> 4800 km/h
        t1 = t0 + timedelta(seconds=15)

        alert = impossible_detector.check_transit(
            plate_number="DL03AX8821",
            prev_camera_id="CAM-01",
            prev_time=t0,
            curr_camera_id="CAM-09",
            curr_time=t1,
            vehicle_type="CAR"
        )

        assert alert is not None
        assert alert["alert_type"] == "IMPOSSIBLE_TRAVEL"
        assert alert["severity"] == "CRITICAL"
        assert alert["plate_number"] == "DL03AX8821"
        assert alert["camera_id"] == "CAM-09"

        # Check exhaustive mathematical proof in details
        details = alert["details"]
        assert details["distance_km"] > 15.0
        assert details["elapsed_seconds"] == 15.0
        assert details["calculated_speed_kmh"] > 1000.0
        assert details["calculated_kmh"] == details["calculated_speed_kmh"]
        assert details["threshold_kmh"] >= 160.0
        assert "reason" in details
        assert "root_cause_explanation" in details
        assert "480" in str(int(details["calculated_speed_kmh"])) or details["calculated_speed_kmh"] > 1000.0

    def test_zero_delta_time_handling(self, impossible_detector):
        """Simultaneous detections at different cameras (Δt = 0) must not raise ZeroDivisionError."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)

        alert = impossible_detector.check_transit(
            plate_number="DL05XY9999",
            prev_camera_id="CAM-01",
            prev_time=t0,
            curr_camera_id="CAM-07",  # Airport, ~15km away
            curr_time=t0,  # Exactly 0 seconds delta
            vehicle_type="SUV"
        )

        assert alert is not None
        assert alert["alert_type"] == "IMPOSSIBLE_TRAVEL"
        assert alert["severity"] == "CRITICAL"
        assert alert["details"]["elapsed_seconds"] == 0.0
        assert alert["details"]["calculated_speed_kmh"] > 10000.0

    def test_same_camera_duplicate_packet(self, impossible_detector):
        """Successive detections at the same camera do not constitute transit travel."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=1)

        alert = impossible_detector.check_transit(
            plate_number="DL01AB1234",
            prev_camera_id="CAM-01",
            prev_time=t0,
            curr_camera_id="CAM-01",
            curr_time=t1,
            vehicle_type="CAR"
        )
        assert alert is None

    def test_unknown_camera_node_graceful_handling(self, impossible_detector):
        """Detections referencing non-existent cameras must return None without raising exceptions."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=10)

        alert = impossible_detector.check_transit(
            plate_number="DL01AB1234",
            prev_camera_id="CAM-NONEXISTENT",
            prev_time=t0,
            curr_camera_id="CAM-02",
            curr_time=t1
        )
        assert alert is None

    def test_out_of_order_timestamps(self, impossible_detector):
        """Detections received out of order should use absolute time delta."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=15)

        # Pass t1 as prev and t0 as curr (reversed order)
        alert = impossible_detector.check_transit(
            plate_number="DL03AX8821",
            prev_camera_id="CAM-01",
            prev_time=t1,
            curr_camera_id="CAM-09",
            curr_time=t0,
            vehicle_type="CAR"
        )
        assert alert is not None
        assert alert["alert_type"] == "IMPOSSIBLE_TRAVEL"
        assert alert["details"]["elapsed_seconds"] == 15.0

    def test_string_iso_timestamps(self, impossible_detector):
        """ISO timestamp strings should parse cleanly."""
        t0_str = "2026-09-09T14:00:00Z"
        t1_str = "2026-09-09T14:00:15Z"

        alert = impossible_detector.check_transit(
            plate_number="DL03AX8821",
            prev_camera_id="CAM-01",
            prev_time=t0_str,
            curr_camera_id="CAM-09",
            curr_time=t1_str
        )
        assert alert is not None
        assert alert["details"]["calculated_speed_kmh"] > 1000.0

    def test_disconnected_graph_haversine_fallback(self, topology):
        """If graph edge is missing or disconnected, detector uses Haversine geodesic fallback."""
        # Create a topology where all edges are removed
        disconnected_topo = CameraTopology()
        disconnected_topo.graph.clear_edges()

        detector = ImpossibleTravelDetector(disconnected_topo, max_physical_speed_kmh=160.0)
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=10)

        # CAM-01 to CAM-09 is ~20km, 10 seconds = 7200 km/h
        alert = detector.check_transit(
            plate_number="DL99ZZ0000",
            prev_camera_id="CAM-01",
            prev_time=t0,
            curr_camera_id="CAM-09",
            curr_time=t1
        )
        assert alert is not None
        assert alert["details"]["distance_km"] > 15.0
        assert alert["details"]["calculated_speed_kmh"] > 1000.0

    def test_sub_millisecond_latency_benchmark(self, impossible_detector):
        """Ensures anomaly evaluation completes well under the 5 ms SLA requirement."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=60)

        # Benchmark 1000 executions
        start = time.perf_counter()
        for _ in range(1000):
            impossible_detector.check_transit(
                plate_number="DL01AB1234",
                prev_camera_id="CAM-01",
                prev_time=t0,
                curr_camera_id="CAM-02",
                curr_time=t1,
                vehicle_type="CAR"
            )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        avg_latency_ms = elapsed_ms / 1000.0

        # Must be well below 5 ms (typically < 0.05 ms)
        assert avg_latency_ms < 1.0, f"Average latency was {avg_latency_ms:.3f} ms, expected < 1.0 ms"



# ---------------------------------------------------------------------------
# 2. PLATE CLONE DETECTION TESTS
# ---------------------------------------------------------------------------

class TestPlateClone:
    def test_visual_discrepancy_vehicle_type_mismatch(self, clone_detector):
        """Identical registration number seen on different vehicle types (e.g. SUV vs CAR)."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=30)

        # First sighting: White SUV at India Gate
        res1 = clone_detector.record_and_check(
            plate_number="HR26DQ9999",
            camera_id="CAM-02",
            timestamp=t0,
            vehicle_type="SUV",
            color="Pearl White",
            make_model="Hyundai Creta"
        )
        assert res1 is None

        # Second sighting: Red CAR at Airport
        res2 = clone_detector.record_and_check(
            plate_number="HR26DQ9999",
            camera_id="CAM-07",
            timestamp=t1,
            vehicle_type="CAR",
            color="Cherry Red",
            make_model="Maruti Swift"
        )

        assert res2 is not None
        assert res2["alert_type"] == "PLATE_CLONE"
        assert res2["severity"] == "CRITICAL"
        assert res2["plate_number"] == "HR26DQ9999"
        assert res2["details"]["discrepancy"] == "VISUAL_PROFILE_MISMATCH"
        assert "SUV" in res2["details"]["primary_vehicle"]
        assert "CAR" in res2["details"]["secondary_vehicle"]

    def test_color_discrepancy_mismatch(self, clone_detector):
        """Identical plate with conflicting colors (e.g., Black Sedan vs Yellow Sedan)."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=45)

        clone_detector.record_and_check(
            plate_number="DL08BC5555",
            camera_id="CAM-01",
            timestamp=t0,
            vehicle_type="SEDAN",
            color="Black"
        )

        alert = clone_detector.record_and_check(
            plate_number="DL08BC5555",
            camera_id="CAM-03",
            timestamp=t1,
            vehicle_type="SEDAN",
            color="Yellow"
        )

        assert alert is not None
        assert alert["alert_type"] == "PLATE_CLONE"
        assert alert["details"]["discrepancy"] == "VISUAL_PROFILE_MISMATCH"

    def test_geographical_discordance_simultaneous_distant_sightings(self, clone_detector):
        """Identical vehicle profile sighted simultaneously at distant cameras."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        # Sighted at CAM-01 and CAM-09 (20 km apart) within 10 seconds
        t1 = t0 + timedelta(seconds=10)

        clone_detector.record_and_check(
            plate_number="UP16AA1111",
            camera_id="CAM-01",
            timestamp=t0,
            vehicle_type="CAR",
            color="Silver",
            make_model="Honda City"
        )

        alert = clone_detector.record_and_check(
            plate_number="UP16AA1111",
            camera_id="CAM-09",
            timestamp=t1,
            vehicle_type="CAR",
            color="Silver",
            make_model="Honda City"
        )

        assert alert is not None
        assert alert["alert_type"] == "PLATE_CLONE"
        assert alert["severity"] == "CRITICAL"
        assert alert["details"]["discrepancy"] == "SIMULTANEOUS_DISTANT_SIGHTINGS"
        assert alert["details"]["distance_km"] > 15.0
        assert alert["details"]["delta_seconds"] == 10.0

    def test_benign_normal_sequential_sightings(self, clone_detector):
        """Legitimate travel over adequate time window should NOT trigger clone alerts."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        # CAM-01 to CAM-02 (~2.8 km) in 6 minutes
        t1 = t0 + timedelta(minutes=6)

        clone_detector.record_and_check(
            plate_number="DL10CD7777",
            camera_id="CAM-01",
            timestamp=t0,
            vehicle_type="CAR",
            color="White"
        )

        alert = clone_detector.record_and_check(
            plate_number="DL10CD7777",
            camera_id="CAM-02",
            timestamp=t1,
            vehicle_type="CAR",
            color="White"
        )
        assert alert is None

    def test_case_insensitivity_normalization(self, clone_detector):
        """Attributes differing only in casing (e.g., 'car' vs 'CAR') should not flag false alarms."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(minutes=5)

        clone_detector.record_and_check(
            plate_number="dl 01 ab 1234",
            camera_id="CAM-01",
            timestamp=t0,
            vehicle_type="car",
            color="white"
        )

        alert = clone_detector.record_and_check(
            plate_number="DL01AB1234",
            camera_id="CAM-02",
            timestamp=t1,
            vehicle_type="CAR",
            color="WHITE"
        )
        assert alert is None

    def test_sliding_window_pruning_expiry(self, clone_detector):
        """Sightings separated by more than window_seconds (15 min) should not trigger false clone."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        # 20 minutes later (> 15 min window)
        t1 = t0 + timedelta(minutes=20)

        clone_detector.record_and_check(
            plate_number="DL12EE9999",
            camera_id="CAM-01",
            timestamp=t0,
            vehicle_type="SUV",
            color="Black"
        )

        # Vehicle with different color seen 20 minutes later outside sliding window
        alert = clone_detector.record_and_check(
            plate_number="DL12EE9999",
            camera_id="CAM-02",
            timestamp=t1,
            vehicle_type="SUV",
            color="White"
        )
        assert alert is None

    def test_same_camera_visual_discrepancy(self, clone_detector):
        """Different vehicle types appearing with identical plate at same camera indicates cloning."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=10)

        clone_detector.record_and_check(
            plate_number="HR05ZZ8888",
            camera_id="CAM-01",
            timestamp=t0,
            vehicle_type="SEDAN",
            color="Blue"
        )

        alert = clone_detector.record_and_check(
            plate_number="HR05ZZ8888",
            camera_id="CAM-01",
            timestamp=t1,
            vehicle_type="TRUCK",
            color="Red"
        )
        assert alert is not None
        assert alert["alert_type"] == "PLATE_CLONE"
        assert alert["details"]["discrepancy"] == "VISUAL_PROFILE_MISMATCH"

    def test_sub_millisecond_latency_clone_benchmark(self, clone_detector):
        """Ensures plate clone evaluation latency is well under 1 ms."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        start = time.perf_counter()
        for i in range(1000):
            clone_detector.record_and_check(
                plate_number=f"DL{i%20:02d}AA1234",
                camera_id="CAM-01",
                timestamp=t0,
                vehicle_type="CAR",
                color="White"
            )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        avg_latency_ms = elapsed_ms / 1000.0
        assert avg_latency_ms < 1.0, f"Average latency was {avg_latency_ms:.3f} ms, expected < 1.0 ms"



# ---------------------------------------------------------------------------
# 3. TRAJECTORY RECONSTRUCTION TESTS
# ---------------------------------------------------------------------------

class TestTrajectoryReconstruction:
    def test_empty_detections(self, trajectory_reconstructor):
        """Empty input list returns valid zero-state structure."""
        traj = trajectory_reconstructor.reconstruct([])
        assert traj["plate_number"] == ""
        assert traj["total_sightings"] == 0
        assert traj["total_distance_km"] == 0.0
        assert traj["visited_cameras"] == []
        assert traj["segments"] == []
        assert traj["geojson_path"]["type"] == "FeatureCollection"

    def test_single_detection(self, trajectory_reconstructor):
        """Single sighting provides 1 hop, 0 segments, and predictions based on camera neighbors."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        detections = [{
            "id": "det-1",
            "camera_id": "CAM-01",
            "plate_number": "DL01AX1234",
            "timestamp": t0,
            "speed_kmh": 45.0,
            "ocr_confidence": 0.98
        }]

        traj = trajectory_reconstructor.reconstruct(detections)
        assert traj["plate_number"] == "DL01AX1234"
        assert traj["total_sightings"] == 1
        assert traj["total_distance_km"] == 0.0
        assert len(traj["visited_cameras"]) == 1
        assert traj["segments"] == []
        assert len(traj["predicted_next_cameras"]) > 0

    def test_multi_hop_reconstruction_with_smoothing(self, trajectory_reconstructor):
        """Multi-checkpoint journey computes segment metrics and graph-smoothed geometry."""
        t0 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(minutes=4)
        t2 = t1 + timedelta(minutes=6)

        # Journey: CAM-01 (Connaught Place) -> CAM-02 (India Gate) -> CAM-04 (Lajpat Nagar)
        detections = [
            # Out of order to verify automatic chronological sorting
            {
                "id": "det-2",
                "camera_id": "CAM-02",
                "plate_number": "DL01AB9999",
                "timestamp": t1,
                "speed_kmh": 48.0,
                "ocr_confidence": 0.96
            },
            {
                "id": "det-1",
                "camera_id": "CAM-01",
                "plate_number": "DL01AB9999",
                "timestamp": t0,
                "speed_kmh": 42.0,
                "ocr_confidence": 0.99
            },
            {
                "id": "det-3",
                "camera_id": "CAM-04",
                "plate_number": "DL01AB9999",
                "timestamp": t2,
                "speed_kmh": 50.0,
                "ocr_confidence": 0.94
            }
        ]

        traj = trajectory_reconstructor.reconstruct(detections)

        # Check trajectory overview
        assert traj["plate_number"] == "DL01AB9999"
        assert traj["total_sightings"] == 3
        assert traj["total_distance_km"] > 5.0

        # Check ordered visited cameras
        visited = traj["visited_cameras"]
        assert [v["camera_id"] for v in visited] == ["CAM-01", "CAM-02", "CAM-04"]
        assert "Connaught Place" in visited[0]["camera_name"]

        # Check segments
        segments = traj["segments"]
        assert len(segments) == 2
        assert segments[0]["from_camera"] == "CAM-01"
        assert segments[0]["to_camera"] == "CAM-02"
        assert segments[0]["calculated_speed_kmh"] > 0
        assert not segments[0]["is_anomalous"]

        # Check GeoJSON LineString
        features = traj["geojson_path"]["features"]
        assert len(features) == 1
        assert features[0]["geometry"]["type"] == "LineString"
        assert len(features[0]["geometry"]["coordinates"]) >= 3

        # Check Next-Camera Predictions (Bayesian momentum)
        predictions = traj["predicted_next_cameras"]
        assert len(predictions) > 0
        # The immediate reverse camera (CAM-02) should not be the top predicted forward direction
        assert predictions[0]["camera_id"] != "CAM-02"

        # Validate with Backend Pydantic Schema
        validated = VehicleTrajectoryResponse(**traj)
        assert validated.plate_number == "DL01AB9999"
        assert len(validated.visited_cameras) == 3

    def test_robustness_with_missing_and_none_fields(self, trajectory_reconstructor):
        """Detections with missing IDs, unknown cameras, and ISO timestamps must process cleanly."""
        detections = [
            {
                # Missing 'id', uses fallback
                "camera_id": "CAM-01",
                "plate_number": "DL99XX1111",
                "timestamp": "2026-09-09T14:00:00Z"
            },
            {
                # Unknown camera node, should be gracefully skipped
                "id": "det-bad",
                "camera_id": "CAM-GHOST",
                "plate_number": "DL99XX1111",
                "timestamp": "2026-09-09T14:02:00Z"
            },
            {
                "id": "det-good",
                "camera_id": "CAM-02",
                "plate_number": "DL99XX1111",
                "timestamp": "2026-09-09T14:05:00Z",
                "ocr_confidence": None  # Fallback to default
            }
        ]

        traj = trajectory_reconstructor.reconstruct(detections)
        assert traj["total_sightings"] == 2
        assert len(traj["visited_cameras"]) == 2
        assert traj["visited_cameras"][0]["camera_id"] == "CAM-01"
        assert traj["visited_cameras"][1]["camera_id"] == "CAM-02"


# ---------------------------------------------------------------------------
# 4. CONGESTION ANALYZER TESTS
# ---------------------------------------------------------------------------

class TestCongestionAnalyzer:
    def test_empty_baseline(self, congestion_analyzer):
        """Zero detections in window results in LOW congestion across all cameras."""
        metrics = congestion_analyzer.get_camera_metrics()
        assert len(metrics) > 0
        for m in metrics:
            assert m["vehicles_per_minute"] == 0.0
            assert m["congestion_level"] == "LOW"
            assert m["intensity"] == 0.20

    def test_density_classification_tiers(self, congestion_analyzer):
        """Verifies throughput threshold transitions: LOW -> NORMAL -> HEAVY -> GRIDLOCK."""
        now = 1757410000.0  # Fixed epoch for deterministic testing

        # Window is 120s = 2 minutes
        # Camera 1: 10 detections in 2 mins = 5 vpm -> LOW
        for _ in range(10):
            congestion_analyzer.record_detection("CAM-01", timestamp=now - 30)

        # Camera 2: 30 detections in 2 mins = 15 vpm -> NORMAL
        for _ in range(30):
            congestion_analyzer.record_detection("CAM-02", timestamp=now - 40)

        # Camera 3: 70 detections in 2 mins = 35 vpm -> HEAVY
        for _ in range(70):
            congestion_analyzer.record_detection("CAM-03", timestamp=now - 20)

        # Camera 4: 120 detections in 2 mins = 60 vpm -> GRIDLOCK
        for _ in range(120):
            congestion_analyzer.record_detection("CAM-04", timestamp=now - 10)

        metrics_map = {m["camera_id"]: m for m in congestion_analyzer.get_camera_metrics(current_time=now)}

        assert metrics_map["CAM-01"]["congestion_level"] == "LOW"
        assert metrics_map["CAM-01"]["vehicles_per_minute"] == 5.0

        assert metrics_map["CAM-02"]["congestion_level"] == "NORMAL"
        assert metrics_map["CAM-02"]["vehicles_per_minute"] == 15.0

        assert metrics_map["CAM-03"]["congestion_level"] == "HEAVY"
        assert metrics_map["CAM-03"]["vehicles_per_minute"] == 35.0

        assert metrics_map["CAM-04"]["congestion_level"] == "GRIDLOCK"
        assert metrics_map["CAM-04"]["vehicles_per_minute"] == 60.0
        assert metrics_map["CAM-04"]["intensity"] == 1.0

    def test_sliding_window_pruning(self, congestion_analyzer):
        """Detections older than window_seconds (120s) must be purged."""
        now = 1757410000.0

        # Old detection (200s ago)
        congestion_analyzer.record_detection("CAM-01", timestamp=now - 200)
        # Recent detection (20s ago)
        congestion_analyzer.record_detection("CAM-01", timestamp=now - 20)

        metrics_map = {m["camera_id"]: m for m in congestion_analyzer.get_camera_metrics(current_time=now)}
        assert metrics_map["CAM-01"]["recent_count"] == 1
        assert metrics_map["CAM-01"]["vehicles_per_minute"] == 0.5

    def test_reset_functionality(self, congestion_analyzer):
        """Reset clears all internal camera detection queues."""
        now = 1757410000.0
        congestion_analyzer.record_detection("CAM-01", timestamp=now)
        assert len(congestion_analyzer.camera_windows["CAM-01"]) == 1
        congestion_analyzer.reset()
        assert len(congestion_analyzer.camera_windows) == 0

    def test_heatmap_points_format(self, congestion_analyzer):
        """Heatmap points must conform to [lat, lng, intensity] for Leaflet."""
        now = 1757410000.0
        congestion_analyzer.record_detection("CAM-01", timestamp=now - 10)

        points = congestion_analyzer.get_heatmap_points(current_time=now)
        assert len(points) > 0
        for pt in points:
            assert len(pt) == 3
            lat, lng, intensity = pt
            assert 20.0 < lat < 40.0
            assert 70.0 < lng < 85.0
            assert 0.1 <= intensity <= 1.0


# ---------------------------------------------------------------------------
# 5. SPATIAL GRAPH & MATHEMATICAL FORMULAS
# ---------------------------------------------------------------------------

class TestSpatialGraphMath:
    def test_haversine_formula(self):
        """Tests Haversine great-circle calculation against known landmark distance."""
        # Connaught Place: 28.6315, 77.2167
        # India Gate: 28.6129, 77.2295
        dist = haversine_distance_km(28.6315, 77.2167, 28.6129, 77.2295)
        # Known straight-line distance is ~2.4 km
        assert 2.0 < dist < 2.8

    def test_bearing_calculation(self):
        """Tests initial forward azimuth calculation."""
        # Moving due East
        bearing_east = calculate_initial_bearing(0.0, 0.0, 0.0, 1.0)
        assert math.isclose(bearing_east, 90.0, abs_tol=0.1)

        # Moving due North
        bearing_north = calculate_initial_bearing(0.0, 0.0, 1.0, 0.0)
        assert math.isclose(bearing_north, 0.0, abs_tol=0.1)

    def test_spatial_graph_engine_paths(self, topology):
        """Tests Dijkstra shortest path search on camera topology."""
        engine = SpatialGraphEngine()
        engine.load_cameras([topology.get_camera(c) for c in topology.get_all_camera_ids()])
        edges = []
        for u, v, data in topology.graph.edges(data=True):
            edges.append((u, v, data["distance_km"]))
        engine.load_edges(edges)

        path = engine.get_shortest_path("CAM-01", "CAM-04")
        assert len(path) >= 2
        assert path[0] == "CAM-01"
        assert path[-1] == "CAM-04"

    def test_transition_matrix_probabilities(self, topology):
        """Tests Markov transition matrix generation where outgoing probabilities sum to ~1.0."""
        engine = SpatialGraphEngine()
        engine.load_cameras([topology.get_camera(c) for c in topology.get_all_camera_ids()])
        edges = [(u, v, data["distance_km"]) for u, v, data in topology.graph.edges(data=True)]
        engine.load_edges(edges)

        matrix = engine.compute_transition_matrix()
        assert "CAM-01" in matrix
        for node, transitions in matrix.items():
            if transitions:
                total_prob = sum(transitions.values())
                assert math.isclose(total_prob, 1.0, abs_tol=0.05)

