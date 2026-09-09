import math
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union
from simulator.topology import CameraTopology


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes the great-circle distance between two geographic coordinates
    using the spherical law of haversines.

    Formula:
        a = sin²(Δφ / 2) + cos(φ1) * cos(φ2) * sin²(Δλ / 2)
        c = 2 * atan2(√a, √(1 - a))
        d = R * c
    where R = 6371.0088 km (mean Earth radius).
    """
    R = 6371.0088  # Mean Earth radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return R * c


def parse_timestamp(ts: Union[datetime, str, int, float]) -> datetime:
    """Parses various timestamp formats into a UTC datetime object."""
    if isinstance(ts, datetime):
        return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(ts, str):
        # Handle trailing 'Z' if present
        clean_str = ts.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(clean_str)
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


class ImpossibleTravelDetector:
    """Detects physics-defying transit speeds between camera checkpoints.

    Mathematical Model:
        Transit Velocity: v = (Distance(A, B) / Δt) * 3600  [km/h]
        Speed Threshold:  v_thresh = max(v_max_physical, v_road_limit * 1.5)
        Condition:        v > v_thresh ==> IMPOSSIBLE_TRAVEL Anomaly
    """

    def __init__(self, topology: CameraTopology, max_physical_speed_kmh: float = 160.0):
        self.topology = topology
        self.max_physical_speed_kmh = float(max_physical_speed_kmh)

    def check_transit(
        self,
        plate_number: str,
        prev_camera_id: str,
        prev_time: Union[datetime, str, int, float],
        curr_camera_id: str,
        curr_time: Union[datetime, str, int, float],
        vehicle_type: str = "UNKNOWN"
    ) -> Optional[Dict[str, Any]]:
        """Evaluates whether the transit between two cameras violates physical speed limits.

        Args:
            plate_number: License plate registration number
            prev_camera_id: Upstream camera identifier
            prev_time: Timestamp of upstream sighting
            curr_camera_id: Downstream camera identifier
            curr_time: Timestamp of downstream sighting
            vehicle_type: Classification of the vehicle

        Returns:
            Alert dictionary with mathematical proof if speed exceeds threshold, else None.
        """
        # Rule 0: Same camera sighting is not a transit segment (handles duplicate packets)
        if prev_camera_id == curr_camera_id:
            return None

        # Rule 1: Camera node verification (robust edge handling for unknown cameras)
        cam_prev = self.topology.get_camera(prev_camera_id)
        cam_curr = self.topology.get_camera(curr_camera_id)
        if not cam_prev or not cam_curr:
            # Cannot determine physical distance for unknown camera nodes
            return None

        # Rule 2: Spatio-temporal delta calculation
        dt_prev = parse_timestamp(prev_time)
        dt_curr = parse_timestamp(curr_time)
        delta_seconds = abs((dt_curr - dt_prev).total_seconds())

        # Zero delta time guard: clamp to minimum realistic packet jitter (0.5s)
        # to prevent division by zero while preserving physical calculation
        effective_delta_sec = max(0.5, delta_seconds)

        # Rule 3: Distance query with geodesic Haversine fallback
        dist_km = self.topology.get_distance(prev_camera_id, curr_camera_id)
        if dist_km >= 9000.0 or dist_km <= 0.0:
            # Unconnected or missing edge in road graph: fall back to great-circle Haversine distance
            dist_km = haversine_distance_km(
                cam_prev["latitude"], cam_prev["longitude"],
                cam_curr["latitude"], cam_curr["longitude"]
            )

        if dist_km <= 0.01:
            # Checkpoints are geographically identical
            return None

        # Rule 4: Velocity computation: (distance_km / seconds) * 3600 -> km/h
        calculated_speed_kmh = (dist_km / effective_delta_sec) * 3600.0

        # Road speed limit threshold
        road_speed_limit = max(
            cam_prev.get("speed_limit_kmh", 60.0),
            cam_curr.get("speed_limit_kmh", 60.0)
        )
        threshold = max(self.max_physical_speed_kmh, road_speed_limit * 1.5)

        # Rule 5: Violation check
        if calculated_speed_kmh > threshold:
            severity = "CRITICAL" if calculated_speed_kmh > 250.0 else "HIGH"
            return {
                "alert_type": "IMPOSSIBLE_TRAVEL",
                "severity": severity,
                "plate_number": plate_number,
                "camera_id": curr_camera_id,
                "details": {
                    "previous_camera_id": prev_camera_id,
                    "current_camera_id": curr_camera_id,
                    "distance_km": round(dist_km, 2),
                    "elapsed_seconds": round(delta_seconds, 2),
                    "effective_delta_seconds": round(effective_delta_sec, 2),
                    "calculated_kmh": round(calculated_speed_kmh, 1),
                    "calculated_speed_kmh": round(calculated_speed_kmh, 1),
                    "speed_limit_kmh": round(road_speed_limit, 1),
                    "threshold_kmh": round(threshold, 1),
                    "vehicle_type": vehicle_type,
                    "reason": "Physics violation: calculated transit speed exceeds maximum physical threshold",
                    "root_cause_explanation": (
                        f"Vehicle '{plate_number}' traversed {dist_km:.2f} km between {prev_camera_id} "
                        f"({cam_prev['name']}) and {curr_camera_id} ({cam_curr['name']}) in {delta_seconds:.1f} seconds. "
                        f"This requires a physically impossible velocity of {calculated_speed_kmh:.1f} km/h "
                        f"(threshold: {threshold:.1f} km/h, road limit: {road_speed_limit:.0f} km/h). "
                        f"Strong mathematical proof of cloned plates or falsified telemetry."
                    )
                }
            }

        return None
