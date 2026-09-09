import math
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from simulator.topology import CameraTopology


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance in kilometers using the Haversine formula."""
    R = 6371.0088
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
        clean_str = ts.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(clean_str)
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


class PlateCloneDetector:
    """Detects duplicate and cloned license plates via geographical discordance
    and visual classification discrepancies.

    Mathematical Model:
        Minimum Flight Time: Δt_min = (Distance(A, B) / v_max) * 3600  [seconds]
        Geographical Discordance: Δt < Δt_min  ==> Simultaneous Distant Sightings
        Visual Discrepancy: Type_A ≠ Type_B or Color_A ≠ Color_B
    """

    def __init__(
        self,
        topology: CameraTopology,
        window_seconds: int = 900,
        max_transit_speed_kmh: float = 160.0
    ):
        self.topology = topology
        self.window_seconds = window_seconds
        self.max_transit_speed_kmh = float(max_transit_speed_kmh)
        # In-memory window of recent detections: {plate: [sighting_dict, ...]}
        self.recent_sightings: Dict[str, List[dict]] = {}

    def _normalize_str(self, val: Optional[str]) -> str:
        if not val:
            return ""
        return val.strip().upper()

    def record_and_check(
        self,
        plate_number: str,
        camera_id: str,
        timestamp: Union[datetime, str, int, float],
        vehicle_type: str = "UNKNOWN",
        color: str = "UNKNOWN",
        make_model: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Records a sighting and checks against recent sightings of the same plate.

        Returns:
            Alert dictionary with root cause details if cloning is detected, else None.
        """
        clean_plate = plate_number.replace(" ", "").upper()
        now_dt = parse_timestamp(timestamp)
        norm_type = self._normalize_str(vehicle_type)
        norm_color = self._normalize_str(color)
        norm_make = self._normalize_str(make_model)

        history = self.recent_sightings.setdefault(clean_plate, [])

        # Prune records older than the sliding window
        history = [
            h for h in history
            if abs((now_dt - h["timestamp"]).total_seconds()) <= self.window_seconds
        ]
        self.recent_sightings[clean_plate] = history

        # Check against previous records in the sliding window
        for prev in reversed(history):
            prev_cam = prev["camera_id"]
            prev_dt = prev["timestamp"]
            delta_sec = abs((now_dt - prev_dt).total_seconds())

            # Handle duplicate packets at the same camera within 2 seconds
            if prev_cam == camera_id and delta_sec < 2.0:
                p_type = prev["norm_type"]
                p_color = prev["norm_color"]
                if (p_type == norm_type or p_type == "UNKNOWN" or norm_type == "UNKNOWN") and \
                   (p_color == norm_color or p_color == "UNKNOWN" or norm_color == "UNKNOWN"):
                    # Benign duplicate detection packet
                    continue

            # -----------------------------------------------------------------
            # RULE 1: Visual Re-ID Profile Discrepancy
            # Same registration number detected on incompatible vehicles
            # -----------------------------------------------------------------
            p_type = prev["norm_type"]
            p_color = prev["norm_color"]
            p_make = prev["norm_make"]

            type_mismatch = (
                bool(p_type and norm_type) and
                p_type != "UNKNOWN" and norm_type != "UNKNOWN" and
                p_type != norm_type
            )
            color_mismatch = (
                bool(p_color and norm_color) and
                p_color != "UNKNOWN" and norm_color != "UNKNOWN" and
                p_color != norm_color and
                delta_sec <= 600  # Color mismatch within 10 minutes
            )
            make_mismatch = (
                bool(p_make and norm_make) and
                p_make != "UNKNOWN" and norm_make != "UNKNOWN" and
                p_make != norm_make
            )

            if type_mismatch or color_mismatch or (make_mismatch and type_mismatch):
                discrepancy_desc = []
                if type_mismatch:
                    discrepancy_desc.append(f"Type mismatch ({prev['vehicle_type']} vs {vehicle_type})")
                if color_mismatch:
                    discrepancy_desc.append(f"Color mismatch ({prev['color']} vs {color})")
                if make_mismatch and not type_mismatch:
                    discrepancy_desc.append(f"Make/Model mismatch ({prev['make_model']} vs {make_model})")

                discrepancy_reason = "; ".join(discrepancy_desc)

                new_entry = {
                    "camera_id": camera_id,
                    "timestamp": now_dt,
                    "vehicle_type": vehicle_type,
                    "color": color,
                    "make_model": make_model or "",
                    "norm_type": norm_type,
                    "norm_color": norm_color,
                    "norm_make": norm_make
                }
                history.append(new_entry)

                return {
                    "alert_type": "PLATE_CLONE",
                    "severity": "CRITICAL",
                    "plate_number": clean_plate,
                    "camera_id": camera_id,
                    "details": {
                        "primary_camera": prev_cam,
                        "primary_time": prev_dt.isoformat(),
                        "primary_vehicle": f"{prev['color']} {prev['vehicle_type']} ({prev.get('make_model', '')})".strip(),
                        "secondary_camera": camera_id,
                        "secondary_time": now_dt.isoformat(),
                        "secondary_vehicle": f"{color} {vehicle_type} ({make_model or ''})".strip(),
                        "delta_seconds": round(delta_sec, 1),
                        "discrepancy": "VISUAL_PROFILE_MISMATCH",
                        "reason": f"Visual discrepancy: {discrepancy_reason}",
                        "root_cause_explanation": (
                            f"Plate '{clean_plate}' was sighted on conflicting physical vehicles: "
                            f"Identified as '{prev['color']} {prev['vehicle_type']}' at {prev_cam}, "
                            f"and as '{color} {vehicle_type}' at {camera_id} ({delta_sec:.0f}s elapsed). "
                            f"Definite vehicle identity cloning detected."
                        )
                    }
                }

            # -----------------------------------------------------------------
            # RULE 2: Geographical Discordance & Minimum Flight Time Violation
            # Same registration number detected at disjoint locations too fast
            # -----------------------------------------------------------------
            if prev_cam != camera_id:
                cam_prev = self.topology.get_camera(prev_cam)
                cam_curr = self.topology.get_camera(camera_id)

                if cam_prev and cam_curr:
                    dist_km = self.topology.get_distance(prev_cam, camera_id)
                    if dist_km >= 9000.0 or dist_km <= 0.0:
                        dist_km = haversine_distance_km(
                            cam_prev["latitude"], cam_prev["longitude"],
                            cam_curr["latitude"], cam_curr["longitude"]
                        )

                    # Minimum physical transit time at max allowed speed
                    min_flight_sec = (dist_km / self.max_transit_speed_kmh) * 3600.0
                    calc_speed_kmh = (dist_km / max(0.5, delta_sec)) * 3600.0

                    # Condition A: Sightings violate physical transit time across significant distance
                    flight_time_violation = (delta_sec < min_flight_sec and dist_km >= 1.0)
                    # Condition B: Near-simultaneous sightings in distant zones (<90s, >5km)
                    distant_near_simultaneous = (delta_sec < 90.0 and dist_km > 5.0)
                    # Condition C: Exact simultaneous sighting (<5s, >0.2km)
                    exact_simultaneous = (delta_sec <= 5.0 and dist_km > 0.2)

                    if flight_time_violation or distant_near_simultaneous or exact_simultaneous:
                        new_entry = {
                            "camera_id": camera_id,
                            "timestamp": now_dt,
                            "vehicle_type": vehicle_type,
                            "color": color,
                            "make_model": make_model or "",
                            "norm_type": norm_type,
                            "norm_color": norm_color,
                            "norm_make": norm_make
                        }
                        history.append(new_entry)

                        return {
                            "alert_type": "PLATE_CLONE",
                            "severity": "CRITICAL",
                            "plate_number": clean_plate,
                            "camera_id": camera_id,
                            "details": {
                                "primary_camera": prev_cam,
                                "primary_time": prev_dt.isoformat(),
                                "secondary_camera": camera_id,
                                "secondary_time": now_dt.isoformat(),
                                "distance_km": round(dist_km, 2),
                                "delta_seconds": round(delta_sec, 1),
                                "minimum_flight_seconds": round(min_flight_sec, 1),
                                "calculated_speed_kmh": round(calc_speed_kmh, 1),
                                "discrepancy": "SIMULTANEOUS_DISTANT_SIGHTINGS",
                                "reason": f"Physical flight time violation ({dist_km:.1f} km in {delta_sec:.0f}s, min required: {min_flight_sec:.0f}s)",
                                "root_cause_explanation": (
                                    f"Plate '{clean_plate}' sighted near-simultaneously at disjoint cameras "
                                    f"{prev_cam} ({cam_prev['name']}) and {camera_id} ({cam_curr['name']}) "
                                    f"which are {dist_km:.1f} km apart, within {delta_sec:.0f} seconds. "
                                    f"Minimum flight time required at {self.max_transit_speed_kmh:.0f} km/h is "
                                    f"{min_flight_sec:.0f} seconds. Two physical vehicles are active simultaneously."
                                )
                            }
                        }

        # Sighting is valid; record into sliding window
        history.append({
            "camera_id": camera_id,
            "timestamp": now_dt,
            "vehicle_type": vehicle_type,
            "color": color,
            "make_model": make_model or "",
            "norm_type": norm_type,
            "norm_color": norm_color,
            "norm_make": norm_make
        })
        return None
