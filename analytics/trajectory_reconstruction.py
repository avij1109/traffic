import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from simulator.topology import CameraTopology


def parse_timestamp(ts: Union[datetime, str, int, float]) -> datetime:
    """Parses arbitrary timestamp inputs to UTC datetime."""
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


class TrajectoryReconstructor:
    """Reconstructs the chronological spatio-temporal route taken by a vehicle,
    calculating segment speeds, distances, graph-smoothed paths, and
    Markov/Bayesian next-checkpoint predictions.
    """

    def __init__(self, topology: CameraTopology):
        self.topology = topology

    def reconstruct(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Takes a list of detection dictionaries, sorts chronologically, and reconstructs
        the full travel path with segment metrics, smoothed road graph geometry, and
        predictive next-camera transitions.
        """
        if not detections:
            return {
                "plate_number": "",
                "total_sightings": 0,
                "total_distance_km": 0.0,
                "visited_cameras": [],
                "segments": [],
                "geojson_path": {"type": "FeatureCollection", "features": []},
                "predicted_next_cameras": []
            }

        # Normalize and sort chronologically
        normalized_dets = []
        for i, d in enumerate(detections):
            dt = parse_timestamp(d.get("timestamp", datetime.now(timezone.utc)))
            det_id = str(d.get("id") or d.get("detection_id") or f"det-{i}")
            speed = float(d.get("speed_kmh", 50.0))
            conf = float(d.get("ocr_confidence") if d.get("ocr_confidence") is not None else d.get("confidence", 0.95))
            plate = str(d.get("plate_number") or "").replace(" ", "").upper()
            crop = d.get("synthetic_crop_svg") or d.get("crop_svg")

            normalized_dets.append({
                "raw_id": det_id,
                "camera_id": d.get("camera_id", ""),
                "plate_number": plate,
                "timestamp": dt,
                "speed_kmh": speed,
                "confidence": conf,
                "crop_svg": crop
            })

        sorted_dets = sorted(normalized_dets, key=lambda x: x["timestamp"])
        plate_number = sorted_dets[0]["plate_number"]

        visited_cameras = []
        segments = []
        total_distance = 0.0
        smooth_path_coordinates = []

        prev_cam_id: Optional[str] = None
        prev_time: Optional[datetime] = None

        for i, det in enumerate(sorted_dets):
            cam_id = det["camera_id"]
            cam_meta = self.topology.get_camera(cam_id)
            if not cam_meta:
                # Gracefully skip unknown camera nodes
                continue

            hop = {
                "detection_id": det["raw_id"],
                "camera_id": cam_id,
                "camera_name": cam_meta["name"],
                "zone": cam_meta["zone"],
                "latitude": float(cam_meta["latitude"]),
                "longitude": float(cam_meta["longitude"]),
                "timestamp": det["timestamp"],
                "speed_kmh": round(det["speed_kmh"], 1),
                "confidence": round(det["confidence"], 3),
                "crop_svg": det["crop_svg"]
            }
            visited_cameras.append(hop)

            # Reconstruct road segment between consecutive checkpoints
            if prev_cam_id is not None and prev_time is not None:
                # Segment distance & transit time
                dist = self.topology.get_distance(prev_cam_id, cam_id)
                delta_sec = max(0.5, abs((det["timestamp"] - prev_time).total_seconds()))
                hop_speed = (dist / delta_sec) * 3600.0
                total_distance += dist

                # Graph Smoothing: infer intermediate road checkpoints along shortest path
                road_path_nodes = self.topology.get_shortest_path(prev_cam_id, cam_id)
                for node_id in road_path_nodes:
                    node_cam = self.topology.get_camera(node_id)
                    if node_cam:
                        coord = [node_cam["longitude"], node_cam["latitude"]]
                        if not smooth_path_coordinates or smooth_path_coordinates[-1] != coord:
                            smooth_path_coordinates.append(coord)

                # Road speed limit
                cam_p = self.topology.get_camera(prev_cam_id)
                speed_limit = max(
                    cam_p.get("speed_limit_kmh", 60.0) if cam_p else 60.0,
                    cam_meta.get("speed_limit_kmh", 60.0)
                )

                segments.append({
                    "from_camera": prev_cam_id,
                    "to_camera": cam_id,
                    "distance_km": round(dist, 2),
                    "duration_seconds": round(delta_sec, 1),
                    "calculated_speed_kmh": round(hop_speed, 1),
                    "speed_limit_kmh": round(speed_limit, 1),
                    "is_anomalous": hop_speed > max(160.0, speed_limit * 1.5),
                    "intermediate_nodes": road_path_nodes
                })
            else:
                # First point
                smooth_path_coordinates.append([cam_meta["longitude"], cam_meta["latitude"]])

            prev_cam_id = cam_id
            prev_time = det["timestamp"]

        # Build GeoJSON LineString
        geojson_features = []
        if len(smooth_path_coordinates) >= 2:
            geojson_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": smooth_path_coordinates
                },
                "properties": {
                    "plate_number": plate_number,
                    "total_distance_km": round(total_distance, 2),
                    "checkpoints_visited": len(visited_cameras)
                }
            })

        # Bayesian / Markov Next-Camera Prediction
        predicted_next = []
        if visited_cameras:
            last_cam_id = visited_cameras[-1]["camera_id"]
            predicted_next = self._predict_next(last_cam_id, visited_cameras)

        return {
            "plate_number": plate_number,
            "total_sightings": len(visited_cameras),
            "total_distance_km": round(total_distance, 2),
            "visited_cameras": visited_cameras,
            "segments": segments,
            "geojson_path": {"type": "FeatureCollection", "features": geojson_features},
            "predicted_next_cameras": predicted_next
        }

    def _predict_next(
        self,
        current_camera_id: str,
        visited_history: List[dict]
    ) -> List[Dict[str, Any]]:
        """Predicts the top 3 most probable next cameras using a directional Bayesian prior
        over the road network graph.
        
        Mathematical Formulation:
            Heading Vector: u = (lon_curr - lon_prev, lat_curr - lat_prev)
            Candidate Vector: v_i = (lon_i - lon_curr, lat_i - lat_curr)
            Directional Momentum: cos(θ_i) = (u · v_i) / (||u|| * ||v_i||)
            Weight: w_i = exp(1.5 * cos(θ_i))
            Posterior Probability: P(next = n_i) = w_i / Σ_k w_k
        """
        neighbors = self.topology.get_neighbors(current_camera_id)
        if not neighbors:
            return []

        curr_cam = self.topology.get_camera(current_camera_id)
        if not curr_cam:
            return []

        # Determine directional heading if >= 2 checkpoints exist
        has_heading = False
        u_lon, u_lat = 0.0, 0.0
        prev_cam_id = None

        if len(visited_history) >= 2:
            prev_hop = visited_history[-2]
            prev_cam_id = prev_hop["camera_id"]
            prev_cam = self.topology.get_camera(prev_cam_id)
            if prev_cam and prev_cam_id != current_camera_id:
                u_lon = curr_cam["longitude"] - prev_cam["longitude"]
                u_lat = curr_cam["latitude"] - prev_cam["latitude"]
                u_norm = math.sqrt(u_lon ** 2 + u_lat ** 2)
                if u_norm > 1e-6:
                    u_lon /= u_norm
                    u_lat /= u_norm
                    has_heading = True

        # Exclude immediate backwards hop if other forward options exist
        candidates = [n for n in neighbors if n != prev_cam_id] if len(neighbors) > 1 else neighbors
        if not candidates:
            candidates = neighbors

        # Compute weights based on heading momentum
        weights = []
        candidate_metadata = []

        for cand_id in candidates:
            cand_cam = self.topology.get_camera(cand_id)
            if not cand_cam:
                continue

            dist = self.topology.get_distance(current_camera_id, cand_id)

            if has_heading:
                # Candidate vector from current camera
                v_lon = cand_cam["longitude"] - curr_cam["longitude"]
                v_lat = cand_cam["latitude"] - curr_cam["latitude"]
                v_norm = math.sqrt(v_lon ** 2 + v_lat ** 2)

                if v_norm > 1e-6:
                    v_lon /= v_norm
                    v_lat /= v_norm
                    cos_theta = (u_lon * v_lon) + (u_lat * v_lat)
                    # Bound to [-1.0, 1.0]
                    cos_theta = max(-1.0, min(1.0, cos_theta))
                else:
                    cos_theta = 0.0

                # Exponential momentum weighting
                w = math.exp(1.5 * cos_theta)
            else:
                # Uniform prior if no heading available
                w = 1.0

            weights.append(w)
            candidate_metadata.append({
                "camera_id": cand_id,
                "name": cand_cam["name"],
                "zone": cand_cam["zone"],
                "distance_km": round(dist, 2)
            })

        if not candidate_metadata:
            return []

        # Normalize weights to probabilities summing to 1.0
        total_w = sum(weights) or 1.0
        predictions = []
        for meta, w in zip(candidate_metadata, weights):
            prob = round(w / total_w, 3)
            predictions.append({
                "camera_id": meta["camera_id"],
                "name": meta["name"],
                "zone": meta["zone"],
                "probability": prob,
                "distance_km": meta["distance_km"]
            })

        # Sort descending by probability and take top 3
        predictions.sort(key=lambda x: x["probability"], reverse=True)
        return predictions[:3]
