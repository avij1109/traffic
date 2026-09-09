"""Graph representation of the Delhi NCR camera network.
Handles distance queries, shortest paths, physical transit times, and camera statuses.
"""

from typing import Dict, List, Optional, Tuple
import networkx as nx
from simulator.mock_data import CAMERAS_SEED, ROAD_EDGES_SEED


class CameraTopology:
    """Graph representation of the city camera network.
    Handles distance queries, shortest paths, and physical transit times.
    """

    def __init__(
        self,
        cameras: Optional[List[dict]] = None,
        edges: Optional[List[Tuple[str, str, float]]] = None
    ):
        self.graph = nx.Graph()
        cam_list = cameras if cameras is not None else CAMERAS_SEED
        # Shallow copy each camera dict to ensure test and instance isolation
        self.cameras: Dict[str, dict] = {cam["id"]: dict(cam) for cam in cam_list}
        self.edges = edges if edges is not None else ROAD_EDGES_SEED
        self._build_graph()

    def _build_graph(self):
        # Add nodes with camera metadata
        for cam_id, cam in self.cameras.items():
            self.graph.add_node(
                cam_id,
                name=cam.get("name", cam_id),
                latitude=cam.get("latitude", 0.0),
                longitude=cam.get("longitude", 0.0),
                speed_limit=cam.get("speed_limit_kmh", 50.0),
                zone=cam.get("zone", "General"),
                status=cam.get("status", "ACTIVE")
            )

        # Add bidirectional edges
        for u, v, dist in self.edges:
            if u not in self.cameras or v not in self.cameras:
                continue
            speed_limit = min(
                self.cameras[u].get("speed_limit_kmh", 50.0),
                self.cameras[v].get("speed_limit_kmh", 50.0)
            )
            # Base travel time in seconds: (distance in km / speed in km/h) * 3600
            travel_time_sec = (dist / max(speed_limit, 1.0)) * 3600.0
            self.graph.add_edge(
                u, v,
                distance_km=dist,
                speed_limit_kmh=speed_limit,
                base_time_sec=travel_time_sec
            )

    def get_all_camera_ids(self) -> List[str]:
        return list(self.cameras.keys())

    def get_camera(self, camera_id: str) -> Optional[dict]:
        return self.cameras.get(camera_id)

    def is_camera_active(self, camera_id: str) -> bool:
        cam = self.cameras.get(camera_id)
        return bool(cam and cam.get("status") == "ACTIVE")

    def set_camera_status(self, camera_id: str, status: str) -> bool:
        """Sets the operating status of a camera (ACTIVE, OFFLINE, MAINTENANCE)."""
        if camera_id in self.cameras:
            self.cameras[camera_id]["status"] = status
            if self.graph.has_node(camera_id):
                self.graph.nodes[camera_id]["status"] = status
            return True
        return False

    def get_active_camera_ids(self) -> List[str]:
        return [cid for cid, cam in self.cameras.items() if cam.get("status") == "ACTIVE"]

    def get_neighbors(self, camera_id: str) -> List[str]:
        if self.graph.has_node(camera_id):
            return list(self.graph.neighbors(camera_id))
        return []

    def get_distance(self, u: str, v: str) -> float:
        """Returns shortest path physical distance between two cameras in kilometers."""
        if u == v:
            return 0.0
        try:
            return nx.shortest_path_length(self.graph, source=u, target=v, weight="distance_km")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return 9999.0

    def get_path_distance(self, path: List[str]) -> float:
        """Calculates total distance along a sequence of camera hops."""
        if not path or len(path) <= 1:
            return 0.0
        total = 0.0
        for i in range(len(path) - 1):
            total += self.get_distance(path[i], path[i + 1])
        return total

    def get_shortest_path(self, source: str, target: str) -> List[str]:
        """Returns sequence of camera IDs along shortest road path."""
        if source == target:
            return [source]
        try:
            return nx.shortest_path(self.graph, source=source, target=target, weight="distance_km")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return [source, target]

    def get_edge_data(self, u: str, v: str) -> Optional[dict]:
        return self.graph.get_edge_data(u, v)

    def to_geojson(self) -> dict:
        """Exports camera nodes and road edges in GeoJSON format for the map."""
        features = []
        # Nodes
        for cam_id, cam in self.cameras.items():
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [cam["longitude"], cam["latitude"]]
                },
                "properties": {
                    "id": cam_id,
                    "name": cam["name"],
                    "zone": cam["zone"],
                    "speed_limit": cam["speed_limit_kmh"],
                    "status": cam.get("status", "ACTIVE"),
                    "type": "camera"
                }
            })
        # Edges
        for u, v, data in self.graph.edges(data=True):
            cam_u = self.cameras[u]
            cam_v = self.cameras[v]
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [cam_u["longitude"], cam_u["latitude"]],
                        [cam_v["longitude"], cam_v["latitude"]]
                    ]
                },
                "properties": {
                    "source": u,
                    "target": v,
                    "distance_km": data["distance_km"],
                    "speed_limit": data["speed_limit_kmh"],
                    "type": "road"
                }
            })
        return {"type": "FeatureCollection", "features": features}
