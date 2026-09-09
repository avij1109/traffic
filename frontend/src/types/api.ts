// TypeScript interfaces mirroring backend schemas

export interface Camera {
  id: string;
  name: string;
  zone: string;
  latitude: float;
  longitude: float;
  speed_limit_kmh: number;
  status: 'ACTIVE' | 'OFFLINE' | 'MAINTENANCE';
  fps: number;
}

export type float = number;

export interface Detection {
  id: string;
  camera_id: string;
  plate_number: string;
  ocr_plate_text: string;
  ocr_confidence: number;
  vehicle_type: string;
  vehicle_color: string;
  speed_kmh: number;
  fused_confidence: number;
  reid_hash?: string | null;
  synthetic_crop_svg?: string | null;
  timestamp: string;
}

export interface AlertDetails {
  calculated_speed_kmh?: number;
  speed_limit_kmh?: number;
  speed_excess_kmh?: number;
  distance_km?: number;
  time_seconds?: number;
  min_feasible_seconds?: number;
  physics_ratio?: number;
  from_camera?: string;
  to_camera?: string;
  message?: string;
  first_sighting?: {
    camera_id: string;
    timestamp: string;
    vehicle_type: string;
    color: string;
    make_model: string;
  };
  second_sighting?: {
    camera_id: string;
    timestamp: string;
    vehicle_type: string;
    color: string;
    make_model: string;
  };
  conflict?: string;
  [key: string]: unknown;
}

export interface Alert {
  id: string;
  alert_type: 'IMPOSSIBLE_TRAVEL' | 'CLONED_PLATE' | 'SPEED_VIOLATION' | 'CAMERA_OFFLINE' | 'SUSPICIOUS_ROUTE' | string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  plate_number?: string | null;
  camera_id?: string | null;
  details: AlertDetails;
  status: 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED';
  created_at: string;
}

export interface Vehicle {
  plate_number: string;
  vehicle_type: string;
  color: string;
  make_model?: string | null;
  is_ev: boolean;
  is_flagged: boolean;
  flag_reason?: string | null;
  first_seen_at: string;
  last_seen_at: string;
  total_sightings: number;
}

export interface TrajectoryHop {
  detection_id: string;
  camera_id: string;
  camera_name: string;
  zone: string;
  latitude: number;
  longitude: number;
  timestamp: string;
  speed_kmh: number;
  confidence: number;
  crop_svg?: string | null;
}

export interface TrajectorySegment {
  from_camera_id: string;
  from_camera_name: string;
  to_camera_id: string;
  to_camera_name: string;
  distance_km: number;
  travel_time_seconds: number;
  calculated_speed_kmh: number;
  speed_limit_kmh: number;
  is_speeding: boolean;
  is_impossible: boolean;
  from_lat: number;
  from_lng: number;
  to_lat: number;
  to_lng: number;
}

export interface PredictedCamera {
  camera_id: string;
  name: string;
  zone: string;
  probability: number;
  est_arrival_seconds: number;
}

export interface VehicleTrajectoryResponse {
  plate_number: string;
  total_sightings: number;
  total_distance_km: number;
  visited_cameras: TrajectoryHop[];
  segments: TrajectorySegment[];
  geojson_path: {
    type: string;
    coordinates: [number, number][];
  };
  predicted_next_cameras: PredictedCamera[];
}

export interface SystemOverviewMetrics {
  total_vehicles_tracked: number;
  total_detections_today: number;
  active_cameras: number;
  total_cameras: number;
  critical_alerts: number;
  total_active_alerts: number;
  network_average_speed_kmh: number;
  system_status: string;
}

export interface CongestionCameraMetric {
  camera_id: string;
  name: string;
  zone: string;
  latitude: number;
  longitude: number;
  vehicles_per_minute: number;
  recent_count: number;
  congestion_level: 'LOW' | 'NORMAL' | 'MODERATE' | 'HIGH' | 'CONGESTED';
  color: string;
  intensity: number;
}

export interface CongestionResponse {
  cameras: CongestionCameraMetric[];
  heatmap_points: [number, number, number][]; // [lat, lng, intensity]
}

export interface HourlyFlowMetric {
  hour: string;
  car_count: number;
  suv_count: number;
  motorcycle_count: number;
  commercial_count: number;
  total: number;
}

export interface SimulatorStatus {
  is_running: boolean;
  fleet_size: number;
  speed_multiplier: number;
  total_events_generated: number;
  events_per_minute: number;
  uptime_seconds: number;
}

export interface WebSocketEventEnvelope<T = unknown> {
  event: 'NEW_DETECTION' | 'NEW_ALERT' | 'CAMERA_STATUS_CHANGED' | 'CONGESTION_UPDATE' | 'METRICS_UPDATE';
  timestamp: string;
  data: T;
}
