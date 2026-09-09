"""Discrete-event continuous traffic simulator.
Simulates multi-camera vehicle flows in Delhi NCR, dispatching detection events
into the ingestion pipeline as vehicles cross camera checkpoints.
"""

import asyncio
import random
import time
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone

from simulator.topology import CameraTopology
from simulator.generator import VehicleGenerator
from simulator.anomalies import AnomalyScenarioManager
from providers.simulator_provider import SimulatorVisionProvider
from providers.base import UnifiedDetectionPayload, VehicleType


class VehicleSimState(str, Enum):
    """Explicit state machine for simulated vehicle progression."""
    IDLE = "IDLE"
    EN_ROUTE = "EN_ROUTE"
    CHECKPOINT_DETECTED = "CHECKPOINT_DETECTED"
    COMPLETED = "COMPLETED"


class SimulatedVehicleState:
    """Represents the real-time simulation state of a single vehicle."""

    def __init__(self, profile: dict, route: List[str]):
        self.profile = profile
        self.route = route
        self.current_hop_index = 0
        self.next_arrival_time = 0.0  # Unix timestamp
        self.status = VehicleSimState.EN_ROUTE
        self.total_detections = 0
        self.last_cam_id: Optional[str] = None
        self.last_detection_time: Optional[float] = None
        self.is_active = True


class TrafficSimulatorEngine:
    """Discrete-event continuous traffic simulator.
    Simulates realistic multi-camera vehicle flows, dispatching detection events
    into the ingestion pipeline as vehicles cross camera checkpoints.
    """

    def __init__(
        self,
        topology: Optional[CameraTopology] = None,
        vision_provider: Optional[SimulatorVisionProvider] = None,
        fleet_size: int = 50,
        speed_multiplier: float = 2.0,
        seed: Optional[int] = None
    ):
        self.topology = topology or CameraTopology()
        self.vision_provider = vision_provider or SimulatorVisionProvider()
        self.anomalies = AnomalyScenarioManager(self.topology, self.vision_provider)
        self.fleet_size = fleet_size
        self.speed_multiplier = speed_multiplier
        self.seed = seed
        self._rng = random.Random(seed) if seed is not None else random

        self.is_running = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._task: Optional[asyncio.Task] = None

        self.vehicles: Dict[str, SimulatedVehicleState] = {}
        self.listeners: List[Callable[[UnifiedDetectionPayload], Any]] = []
        self.event_count = 0
        self.missed_detections = 0
        self.start_time = time.time()

        self._initialize_fleet()

    def _initialize_fleet(self):
        """Generates initial fleet and assigns origin-destination paths."""
        fleet_profiles = VehicleGenerator.generate_fleet(self.fleet_size, seed=self.seed)
        camera_ids = self.topology.get_all_camera_ids()
        now = time.time()

        for prof in fleet_profiles:
            origin = self._rng.choice(camera_ids)
            possible_destinations = [c for c in camera_ids if c != origin]
            destination = self._rng.choice(possible_destinations) if possible_destinations else origin
            route = self.topology.get_shortest_path(origin, destination)

            state = SimulatedVehicleState(prof, route)
            # Stagger initial arrivals over 0.1 to 1.8 seconds so dashboard is alive instantly
            state.next_arrival_time = now + self._rng.uniform(0.1, 1.8)
            self.vehicles[prof["plate_number"]] = state

    def register_listener(self, callback: Callable[[UnifiedDetectionPayload], Any]):
        """Registers a listener callback that receives each emitted detection event."""
        if callback not in self.listeners:
            self.listeners.append(callback)

    def unregister_listener(self, callback: Callable[[UnifiedDetectionPayload], Any]):
        """Removes a registered listener callback."""
        if callback in self.listeners:
            self.listeners.remove(callback)

    async def _emit_detection(self, payload: UnifiedDetectionPayload):
        """Dispatches detection event to registered listeners."""
        self.event_count += 1
        for listener in list(self.listeners):
            try:
                res = listener(payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass

    def _assign_new_route(self, state: SimulatedVehicleState, current_cam: str):
        """Assigns a new route when a vehicle completes its current journey."""
        camera_ids = self.topology.get_all_camera_ids()
        possible_destinations = [c for c in camera_ids if c != current_cam]
        new_dest = self._rng.choice(possible_destinations) if possible_destinations else current_cam
        new_route = self.topology.get_shortest_path(current_cam, new_dest)

        state.route = new_route
        state.current_hop_index = 0
        state.status = VehicleSimState.EN_ROUTE

    async def _step_vehicle(self, plate: str, state: SimulatedVehicleState, current_time: float):
        """Advances vehicle to next camera checkpoint if arrival time is reached."""
        if current_time < state.next_arrival_time:
            return

        if state.current_hop_index >= len(state.route):
            self._assign_new_route(state, state.route[-1] if state.route else "CAM-01")

        current_cam_id = state.route[state.current_hop_index]
        prof = state.profile

        # Camera Blackout / Offline Check:
        # If camera is down, skip detection dispatch (blind spot / outage simulation)
        if not self.topology.is_camera_active(current_cam_id):
            self.missed_detections += 1
            # Advance to next hop without emitting detection
            state.current_hop_index += 1
            if state.current_hop_index >= len(state.route):
                state.status = VehicleSimState.COMPLETED
                self._assign_new_route(state, current_cam_id)
            state.next_arrival_time = current_time + 1.5
            return

        # Vehicle State Machine transition: CHECKPOINT_DETECTED
        state.status = VehicleSimState.CHECKPOINT_DETECTED
        state.last_cam_id = current_cam_id
        state.last_detection_time = current_time
        state.total_detections += 1

        # Optical noise chance (3% chance of dirty plate / OCR misread)
        has_ocr_noise = self._rng.random() < 0.03

        # Speed calculation
        speed = prof["cruising_speed_kmh"] * self._rng.uniform(0.9, 1.1)

        # Generate realistic detection event via Vision Provider
        detection = await self.vision_provider.generate_simulated_detection(
            camera_id=current_cam_id,
            plate_number=prof["plate_number"],
            vehicle_type=prof["vehicle_type"],
            color=prof["color"],
            make_model=prof["make_model"],
            speed_kmh=speed,
            ocr_noise=has_ocr_noise
        )

        # If vehicle is flagged in registry, attach note
        if prof.get("is_flagged"):
            detection.metadata["flag_reason"] = prof.get("flag_reason")

        await self._emit_detection(detection)

        # Schedule next hop
        state.current_hop_index += 1
        if state.current_hop_index >= len(state.route):
            # Journey completed, pick a new destination
            state.status = VehicleSimState.COMPLETED
            self._assign_new_route(state, current_cam_id)
        else:
            state.status = VehicleSimState.EN_ROUTE

        # Calculate transit time to next camera
        next_cam_id = state.route[state.current_hop_index]
        edge_data = self.topology.get_edge_data(current_cam_id, next_cam_id)
        if edge_data:
            dist = edge_data.get("distance_km", 3.0)
            road_speed = edge_data.get("speed_limit_kmh", 50.0)
            actual_speed = min(speed, road_speed)
        else:
            dist = self.topology.get_distance(current_cam_id, next_cam_id)
            actual_speed = 50.0

        # Transit time in seconds, compressed by speed_multiplier
        transit_seconds = (dist / max(actual_speed, 20.0)) * 3600.0 / max(self.speed_multiplier, 0.1)
        # Cap transit time between 2.5 and 14 seconds in presentation mode so action is continuous
        clamped_transit = max(2.5, min(14.0, transit_seconds * 0.08))

        state.next_arrival_time = current_time + clamped_transit

    async def step_once(self, current_time: Optional[float] = None) -> List[UnifiedDetectionPayload]:
        """Advances the simulation by stepping all eligible vehicles at a given timestamp.
        Returns list of detections emitted during this step.
        Useful for deterministic testing and fast simulation verification.
        """
        now = time.time() if current_time is None else current_time
        emitted: List[UnifiedDetectionPayload] = []

        def collector(payload: UnifiedDetectionPayload):
            emitted.append(payload)

        self.register_listener(collector)
        try:
            for plate, state in list(self.vehicles.items()):
                await self._step_vehicle(plate, state, now)
        finally:
            self.unregister_listener(collector)

        return emitted

    async def _run_loop(self):
        """Main simulation tick loop."""
        try:
            while self.is_running:
                await self._pause_event.wait()
                if not self.is_running:
                    break
                now = time.time()

                # Step each vehicle in the fleet
                for plate, state in list(self.vehicles.items()):
                    try:
                        await self._step_vehicle(plate, state, now)
                    except Exception:
                        pass

                # Tick resolution: 250ms
                await asyncio.sleep(0.25)
        except asyncio.CancelledError:
            pass

    def start(self):
        """Starts the simulator loop as an asyncio background task."""
        if not self.is_running:
            self.is_running = True
            self._pause_event.set()
            self._task = asyncio.create_task(self._run_loop())

    def pause(self):
        """Pauses simulation events without destroying vehicle state."""
        self._pause_event.clear()

    def resume(self):
        """Resumes simulation events."""
        self._pause_event.set()

    def stop(self):
        """Stops the simulator."""
        self.is_running = False
        self._pause_event.set()
        if self._task and not self._task.done():
            self._task.cancel()

    async def stop_async(self):
        """Stops the simulator and awaits task completion."""
        self.stop()
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def set_speed_multiplier(self, multiplier: float):
        """Adjusts the simulation speed compression."""
        self.speed_multiplier = max(0.2, min(20.0, multiplier))

    async def trigger_impossible_travel(
        self,
        plate_number: str = "DL04EQ9999",
        cam_start: str = "CAM-01",
        cam_end: str = "CAM-09",
        emit_delay: float = 0.5
    ) -> List[UnifiedDetectionPayload]:
        """Manually injects an impossible travel anomaly for live demo."""
        events = await self.anomalies.create_impossible_travel_event(
            plate_number=plate_number,
            cam_start=cam_start,
            cam_end=cam_end
        )
        for i, ev in enumerate(events):
            await self._emit_detection(ev)
            if emit_delay > 0 and i < len(events) - 1:
                await asyncio.sleep(emit_delay)
        return events

    async def trigger_duplicate_plate(
        self,
        cloned_plate: str = "HR26CL0001",
        cam_a: str = "CAM-02",
        cam_b: str = "CAM-07",
        emit_delay: float = 0.3
    ) -> List[UnifiedDetectionPayload]:
        """Manually injects a cloned plate anomaly for live demo."""
        events = await self.anomalies.create_cloned_plate_events(
            cloned_plate=cloned_plate,
            cam_a=cam_a,
            cam_b=cam_b
        )
        for i, ev in enumerate(events):
            await self._emit_detection(ev)
            if emit_delay > 0 and i < len(events) - 1:
                await asyncio.sleep(emit_delay)
        return events

    def trigger_camera_blackout(self, camera_id: str = "CAM-01") -> Dict[str, Any]:
        """Simulates an abrupt camera outage."""
        return self.anomalies.create_camera_blackout(camera_id, status="OFFLINE")

    def restore_camera(self, camera_id: str = "CAM-01") -> Dict[str, Any]:
        """Restores a camera back online."""
        return self.anomalies.restore_camera(camera_id)

    def get_stats(self) -> dict:
        uptime = time.time() - self.start_time
        return {
            "is_running": self.is_running,
            "fleet_size": len(self.vehicles),
            "speed_multiplier": self.speed_multiplier,
            "total_events_generated": self.event_count,
            "events_per_minute": round((self.event_count / max(1.0, uptime)) * 60, 1),
            "uptime_seconds": round(uptime, 1),
            "active_cameras": len(self.topology.get_active_camera_ids()),
            "total_cameras": len(self.topology.get_all_camera_ids()),
            "missed_detections": self.missed_detections
        }
