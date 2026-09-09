import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from simulator.topology import CameraTopology


def parse_timestamp_epoch(ts: Optional[Union[float, int, datetime, str]]) -> float:
    """Normalizes various timestamp representations into a POSIX epoch timestamp (seconds)."""
    if ts is None:
        return time.time()
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, datetime):
        return ts.timestamp()
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.timestamp()
        except ValueError:
            return time.time()
    return time.time()


class CongestionAnalyzer:
    """Computes real-time camera density, throughput, congestion levels,
    and normalized heatmap coordinates for Leaflet GIS overlays.

    Mathematical Model:
        Throughput (vpm): Rate = (N_detections / Window_minutes)
        Density Classification:
            - Rate > 45 vpm: GRIDLOCK (intensity: 1.0, color: #EF4444)
            - Rate > 25 vpm: HEAVY    (intensity: 0.75, color: #F97316)
            - Rate > 10 vpm: NORMAL   (intensity: 0.50, color: #FACC15)
            - Rate <= 10 vpm: LOW     (intensity: 0.20, color: #10B981)
    """

    def __init__(self, topology: CameraTopology, window_seconds: int = 120):
        self.topology = topology
        self.window_seconds = int(window_seconds)
        # camera_id -> deque of epoch timestamps
        self.camera_windows: Dict[str, deque] = defaultdict(deque)

    def record_detection(
        self,
        camera_id: str,
        timestamp: Optional[Union[float, int, datetime, str]] = None
    ) -> None:
        """Records a vehicle detection event at a specific camera checkpoint."""
        epoch = parse_timestamp_epoch(timestamp)
        self.camera_windows[camera_id].append(epoch)

    def _prune(self, now_epoch: float) -> None:
        """Removes timestamps outside the rolling time window."""
        cutoff = now_epoch - self.window_seconds
        for cam_id in list(self.camera_windows.keys()):
            dq = self.camera_windows[cam_id]
            while dq and dq[0] < cutoff:
                dq.popleft()

    def get_camera_metrics(self, current_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """Returns throughput, density index, and congestion classification for each camera.

        Args:
            current_time: Optional explicit timestamp for deterministic testing.
        """
        now = current_time if current_time is not None else time.time()
        self._prune(now)
        results = []

        window_minutes = self.window_seconds / 60.0

        for cam_id in self.topology.get_all_camera_ids():
            cam = self.topology.get_camera(cam_id)
            if not cam:
                continue

            count = len(self.camera_windows.get(cam_id, []))
            # Calculate vehicles per minute
            rate_vpm = round(count / window_minutes, 1)

            # Classify congestion tier
            if rate_vpm > 45.0:
                level = "GRIDLOCK"
                color = "#EF4444"  # Red
                intensity = 1.0
            elif rate_vpm > 25.0:
                level = "HEAVY"
                color = "#F97316"  # Orange
                intensity = 0.75
            elif rate_vpm > 10.0:
                level = "NORMAL"
                color = "#FACC15"  # Yellow
                intensity = 0.50
            else:
                level = "LOW"
                color = "#10B981"  # Emerald
                intensity = 0.20

            results.append({
                "camera_id": cam_id,
                "name": cam["name"],
                "zone": cam["zone"],
                "latitude": float(cam["latitude"]),
                "longitude": float(cam["longitude"]),
                "vehicles_per_minute": rate_vpm,
                "recent_count": count,
                "congestion_level": level,
                "color": color,
                "intensity": intensity
            })

        return sorted(results, key=lambda x: x["vehicles_per_minute"], reverse=True)

    def get_heatmap_points(self, current_time: Optional[float] = None) -> List[List[float]]:
        """Returns [latitude, longitude, intensity] points for Leaflet.heat overlays.

        Args:
            current_time: Optional explicit timestamp for deterministic testing.
        """
        metrics = self.get_camera_metrics(current_time=current_time)
        return [[m["latitude"], m["longitude"], m["intensity"]] for m in metrics]

    def reset(self) -> None:
        """Clears all sliding window buffers."""
        self.camera_windows.clear()
