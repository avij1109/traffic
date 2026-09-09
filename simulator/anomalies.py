"""Anomaly scenario injection engine for judge demonstrations.
Supports on-demand simulation of:
- Cloned / duplicate license plates sighted simultaneously across distant zones
- Impossible travel speed violations (e.g. 500+ km/h)
- Camera blackouts and blind-spot routing
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from providers.base import VehicleType, UnifiedDetectionPayload
from simulator.topology import CameraTopology


class AnomalyScenarioManager:
    """Manages on-demand injection of anomalous scenarios for judge demonstrations."""

    def __init__(self, topology: CameraTopology, vision_provider):
        self.topology = topology
        self.vision_provider = vision_provider

    async def create_impossible_travel_event(
        self,
        plate_number: str = "DL03AX8821",
        vehicle_type: VehicleType = VehicleType.CAR,
        color: str = "Carbon Black",
        make_model: str = "BMW 3 Series",
        cam_start: str = "CAM-01",  # Connaught Place
        cam_end: str = "CAM-09",    # Cyber Hub (~20km away)
        delta_seconds: float = 15.0,
        timestamp: Optional[datetime] = None
    ) -> List[UnifiedDetectionPayload]:
        """Emits two events with small delta across a large distance (yielding impossible calculated speeds)."""
        dist = self.topology.get_distance(cam_start, cam_end)
        t1 = timestamp or datetime.now(timezone.utc)
        t2 = t1 + timedelta(seconds=delta_seconds)

        # First checkpoint
        det1 = await self.vision_provider.generate_simulated_detection(
            camera_id=cam_start,
            plate_number=plate_number,
            vehicle_type=vehicle_type,
            color=color,
            make_model=make_model,
            speed_kmh=45.0,
            ocr_noise=False
        )
        det1.timestamp = t1

        # Calculate impossible velocity in km/h
        calc_speed = (dist / max(delta_seconds, 0.1)) * 3600.0

        # Second checkpoint with physics-violating transit
        det2 = await self.vision_provider.generate_simulated_detection(
            camera_id=cam_end,
            plate_number=plate_number,
            vehicle_type=vehicle_type,
            color=color,
            make_model=make_model,
            speed_kmh=round(min(calc_speed, 999.0), 1),
            ocr_noise=False
        )
        det2.timestamp = t2
        det2.estimated_speed_kmh = round(calc_speed, 1)
        det2.metadata["anomaly_injected"] = "IMPOSSIBLE_TRAVEL"
        det2.metadata["distance_km"] = round(dist, 2)
        det2.metadata["delta_seconds"] = round(delta_seconds, 1)
        det2.metadata["calculated_speed_kmh"] = round(calc_speed, 1)

        return [det1, det2]

    async def create_cloned_plate_events(
        self,
        cloned_plate: str = "HR26DQ9999",
        cam_a: str = "CAM-02",  # India Gate
        cam_b: str = "CAM-07",  # IGI Airport T3 (far away)
        delta_seconds: float = 2.0,
        timestamp: Optional[datetime] = None
    ) -> List[UnifiedDetectionPayload]:
        """Emits twin near-simultaneous detections of the identical plate on two distinct vehicles:
        One is a White Creta SUV, the other is a Red Swift Sedan.
        """
        dist = self.topology.get_distance(cam_a, cam_b)
        t1 = timestamp or datetime.now(timezone.utc)
        t2 = t1 + timedelta(seconds=delta_seconds)

        det_a = await self.vision_provider.generate_simulated_detection(
            camera_id=cam_a,
            plate_number=cloned_plate,
            vehicle_type=VehicleType.SUV,
            color="Pearl White",
            make_model="Hyundai Creta",
            speed_kmh=48.0,
            ocr_noise=False
        )
        det_a.timestamp = t1
        det_a.metadata["anomaly_injected"] = "CLONED_PLATE_PRIMARY"
        det_a.metadata["distance_km"] = round(dist, 2)

        det_b = await self.vision_provider.generate_simulated_detection(
            camera_id=cam_b,
            plate_number=cloned_plate,
            vehicle_type=VehicleType.CAR,
            color="Cherry Red",
            make_model="Maruti Swift",
            speed_kmh=52.0,
            ocr_noise=False
        )
        det_b.timestamp = t2
        det_b.metadata["anomaly_injected"] = "CLONED_PLATE_IMPOSTOR"
        det_b.metadata["distance_km"] = round(dist, 2)
        det_b.metadata["delta_seconds"] = round(delta_seconds, 1)

        return [det_a, det_b]

    def create_camera_blackout(
        self,
        camera_id: str = "CAM-01",
        status: str = "OFFLINE"
    ) -> Dict[str, Any]:
        """Simulates a camera blackout / failure at a critical junction."""
        cam = self.topology.get_camera(camera_id)
        prev_status = cam.get("status", "ACTIVE") if cam else "UNKNOWN"
        success = self.topology.set_camera_status(camera_id, status)
        return {
            "success": success,
            "camera_id": camera_id,
            "previous_status": prev_status,
            "new_status": status,
            "is_active": False if status != "ACTIVE" else True
        }

    def restore_camera(
        self,
        camera_id: str = "CAM-01"
    ) -> Dict[str, Any]:
        """Restores a blacked out camera back to ACTIVE status."""
        return self.create_camera_blackout(camera_id, status="ACTIVE")
