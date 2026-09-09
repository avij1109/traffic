import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.app.core.database import SessionLocal
from backend.app.services.detection_service import DetectionService
from backend.app.services.alert_service import AlertService
from backend.app.websockets.connection_manager import ws_manager

from simulator.topology import CameraTopology
from simulator.engine import TrafficSimulatorEngine
from providers.simulator_provider import SimulatorVisionProvider
from providers.base import UnifiedDetectionPayload

from analytics.impossible_travel import ImpossibleTravelDetector
from analytics.plate_clone import PlateCloneDetector
from analytics.congestion_analyzer import CongestionAnalyzer


class SimulatorService:
    """Coordinates traffic simulation, real-time analytics anomaly checking,
    database persistence, and WebSocket client broadcasting.
    """

    def __init__(self):
        self.topology = CameraTopology()
        self.vision_provider = SimulatorVisionProvider()
        self.engine = TrafficSimulatorEngine(
            topology=self.topology,
            vision_provider=self.vision_provider,
            fleet_size=50,
            speed_multiplier=2.5
        )

        self.impossible_detector = ImpossibleTravelDetector(self.topology)
        self.clone_detector = PlateCloneDetector(self.topology)
        self.congestion_analyzer = CongestionAnalyzer(self.topology)

        # In-memory track of last sighting per plate: {plate: (cam_id, timestamp)}
        self.last_sightings: Dict[str, tuple] = {}
        self._metric_broadcast_counter = 0

        # Wire simulator listener
        self.engine.register_listener(self._handle_simulated_detection)

    async def _handle_simulated_detection(self, payload: UnifiedDetectionPayload):
        """Processes each detection emitted by the simulator."""
        plate = payload.anpr.plate_text
        cam_id = payload.camera_id
        now = payload.timestamp
        v_type = str(payload.detection.vehicle_type.value if hasattr(payload.detection.vehicle_type, 'value') else payload.detection.vehicle_type)
        color = payload.detection.color
        make_model = payload.detection.make_model

        # 1. Update congestion tracker
        self.congestion_analyzer.record_detection(cam_id)

        # 2. Check for Impossible Travel
        detected_alert = None
        if plate in self.last_sightings:
            prev_cam, prev_time = self.last_sightings[plate]
            imp_alert = self.impossible_detector.check_transit(
                plate_number=plate,
                prev_camera_id=prev_cam,
                prev_time=prev_time,
                curr_camera_id=cam_id,
                curr_time=now,
                vehicle_type=v_type
            )
            if imp_alert:
                detected_alert = imp_alert

        # Update last sighting
        self.last_sightings[plate] = (cam_id, now)

        # 3. Check for Plate Cloning (if no impossible travel alert already generated)
        if not detected_alert:
            clone_alert = self.clone_detector.record_and_check(
                plate_number=plate,
                camera_id=cam_id,
                timestamp=now,
                vehicle_type=v_type,
                color=color,
                make_model=make_model
            )
            if clone_alert:
                detected_alert = clone_alert

        # 4. Persist detection and alert to DB in a thread-safe session
        db = SessionLocal()
        try:
            db_det = DetectionService.record_detection(db, payload)
            
            saved_alert = None
            if detected_alert:
                saved_alert = AlertService.create_alert(
                    db=db,
                    alert_type=detected_alert["alert_type"],
                    severity=detected_alert["severity"],
                    plate_number=detected_alert["plate_number"],
                    camera_id=detected_alert["camera_id"],
                    details=detected_alert["details"]
                )
        finally:
            db.close()

        # 5. Broadcast to connected WebSocket clients
        # Detection packet
        detection_data = {
            "id": payload.id,
            "camera_id": payload.camera_id,
            "plate_number": plate,
            "ocr_plate_text": payload.anpr.raw_text,
            "ocr_confidence": payload.anpr.confidence,
            "vehicle_type": v_type,
            "vehicle_color": color,
            "speed_kmh": payload.estimated_speed_kmh or 0.0,
            "fused_confidence": payload.fused_confidence,
            "synthetic_crop_svg": payload.crop_svg,
            "timestamp": now.isoformat()
        }
        await ws_manager.broadcast_event("NEW_DETECTION", detection_data)

        # Alert packet (if triggered)
        if detected_alert and saved_alert:
            alert_data = {
                "id": saved_alert.id,
                "alert_type": saved_alert.alert_type,
                "severity": saved_alert.severity,
                "plate_number": saved_alert.plate_number,
                "camera_id": saved_alert.camera_id,
                "details": detected_alert["details"],
                "status": saved_alert.status,
                "created_at": saved_alert.created_at.isoformat()
            }
            await ws_manager.broadcast_event("NEW_ALERT", alert_data)

        # Periodic metrics broadcast (every 10 detections)
        self._metric_broadcast_counter += 1
        if self._metric_broadcast_counter % 10 == 0:
            congestion_data = self.congestion_analyzer.get_camera_metrics()
            await ws_manager.broadcast_event("CONGESTION_UPDATE", {
                "cameras": congestion_data,
                "heatmap_points": self.congestion_analyzer.get_heatmap_points()
            })

    def start(self):
        self.engine.start()

    def pause(self):
        self.engine.pause()

    def resume(self):
        self.engine.resume()

    def set_speed(self, multiplier: float):
        self.engine.set_speed_multiplier(multiplier)

    def get_status(self) -> dict:
        return self.engine.get_stats()

    async def inject_anomaly(self, anomaly_type: str) -> dict:
        if anomaly_type == "IMPOSSIBLE_TRAVEL":
            events = await self.engine.trigger_impossible_travel()
            return {"status": "INJECTED", "type": "IMPOSSIBLE_TRAVEL", "events_count": len(events)}
        elif anomaly_type == "CLONED_PLATE":
            events = await self.engine.trigger_duplicate_plate()
            return {"status": "INJECTED", "type": "CLONED_PLATE", "events_count": len(events)}
        else:
            return {"status": "IGNORED", "message": f"Unknown anomaly type: {anomaly_type}"}


# Singleton simulator service
simulator_service = SimulatorService()
