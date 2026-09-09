import math
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return R * c


def calculate_initial_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the initial bearing (forward azimuth) from point 1 to point 2 in degrees [0, 360)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)

    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    bearing_rad = math.atan2(y, x)
    return (math.degrees(bearing_rad) + 360.0) % 360.0


class SpatialGraphEngine:
    """NetworkX-powered spatial road topology engine for camera network routing,
    Dijkstra shortest path search, and transition probability modeling.
    """

    def __init__(self, cameras: Optional[List[dict]] = None, edges: Optional[List[Tuple[str, str, float]]] = None):
        self.graph = nx.Graph()
        self.cameras: Dict[str, dict] = {}
        if cameras:
            self.load_cameras(cameras)
        if edges:
            self.load_edges(edges)

    def load_cameras(self, cameras: List[dict]) -> None:
        for cam in cameras:
            cam_id = cam["id"]
            self.cameras[cam_id] = cam
            self.graph.add_node(
                cam_id,
                name=cam.get("name", cam_id),
                latitude=float(cam["latitude"]),
                longitude=float(cam["longitude"]),
                speed_limit=float(cam.get("speed_limit_kmh", 60.0)),
                zone=cam.get("zone", "General")
            )

    def load_edges(self, edges: List[Tuple[str, str, float]]) -> None:
        for u, v, dist in edges:
            if u in self.cameras and v in self.cameras:
                speed_limit = min(
                    float(self.cameras[u].get("speed_limit_kmh", 60.0)),
                    float(self.cameras[v].get("speed_limit_kmh", 60.0))
                )
                travel_time_sec = (dist / max(1.0, speed_limit)) * 3600.0
                self.graph.add_edge(
                    u, v,
                    distance_km=float(dist),
                    speed_limit_kmh=speed_limit,
                    base_time_sec=travel_time_sec
                )

    def get_distance(self, u: str, v: str) -> float:
        """Returns shortest path physical road distance in km, or Haversine if disconnected."""
        if u == v:
            return 0.0
        try:
            return nx.shortest_path_length(self.graph, source=u, target=v, weight="distance_km")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            if u in self.cameras and v in self.cameras:
                c1, c2 = self.cameras[u], self.cameras[v]
                return haversine_distance_km(c1["latitude"], c1["longitude"], c2["latitude"], c2["longitude"])
            return 9999.0

    def get_shortest_path(self, source: str, target: str) -> List[str]:
        """Returns camera node sequence along Dijkstra shortest road path."""
        try:
            return nx.shortest_path(self.graph, source=source, target=target, weight="distance_km")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return [source, target] if source in self.cameras and target in self.cameras else []

    def get_neighbors(self, camera_id: str) -> List[str]:
        if self.graph.has_node(camera_id):
            return list(self.graph.neighbors(camera_id))
        return []

    def compute_transition_matrix(self) -> Dict[str, Dict[str, float]]:
        """Computes uniform Markov transition probabilities between adjacent camera nodes."""
        matrix = {}
        for node in self.graph.nodes():
            neighbors = list(self.graph.neighbors(node))
            if neighbors:
                prob = round(1.0 / len(neighbors), 4)
                matrix[node] = {n: prob for n in neighbors}
            else:
                matrix[node] = {}
        return matrix
