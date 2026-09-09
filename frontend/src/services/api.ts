import {
  Camera,
  Detection,
  Alert,
  Vehicle,
  VehicleTrajectoryResponse,
  SystemOverviewMetrics,
  CongestionResponse,
  HourlyFlowMetric,
  SimulatorStatus,
} from '../types/api';

const API_BASE = '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorText = await res.text().catch(() => 'Unknown error');
    throw new Error(`API Error ${res.status}: ${errorText}`);
  }
  return res.json();
}

export const api = {
  // Cameras
  async getCameras(): Promise<Camera[]> {
    const res = await fetch(`${API_BASE}/cameras`);
    return handleResponse<Camera[]>(res);
  },

  async getCamera(cameraId: string): Promise<Camera> {
    const res = await fetch(`${API_BASE}/cameras/${encodeURIComponent(cameraId)}`);
    return handleResponse<Camera>(res);
  },

  async updateCameraStatus(cameraId: string, status: 'ACTIVE' | 'OFFLINE' | 'MAINTENANCE'): Promise<Camera> {
    const res = await fetch(`${API_BASE}/cameras/${encodeURIComponent(cameraId)}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    return handleResponse<Camera>(res);
  },

  // Detections
  async getRecentDetections(limit = 50, cameraId?: string, plate?: string): Promise<Detection[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cameraId) params.append('camera_id', cameraId);
    if (plate) params.append('plate', plate);
    const res = await fetch(`${API_BASE}/detections/recent?${params.toString()}`);
    return handleResponse<Detection[]>(res);
  },

  async getDetection(id: string): Promise<Detection> {
    const res = await fetch(`${API_BASE}/detections/${encodeURIComponent(id)}`);
    return handleResponse<Detection>(res);
  },

  // Vehicles
  async searchVehicles(q?: string, vehicleType?: string, isFlagged?: boolean, limit = 50): Promise<Vehicle[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (q) params.append('q', q);
    if (vehicleType) params.append('vehicle_type', vehicleType);
    if (isFlagged !== undefined) params.append('is_flagged', isFlagged.toString());
    const res = await fetch(`${API_BASE}/vehicles/search?${params.toString()}`);
    return handleResponse<Vehicle[]>(res);
  },

  async getVehicle(plateNumber: string): Promise<Vehicle> {
    const res = await fetch(`${API_BASE}/vehicles/${encodeURIComponent(plateNumber)}`);
    return handleResponse<Vehicle>(res);
  },

  async getVehicleTrajectory(plateNumber: string): Promise<VehicleTrajectoryResponse> {
    const res = await fetch(`${API_BASE}/vehicles/${encodeURIComponent(plateNumber)}/trajectory`);
    return handleResponse<VehicleTrajectoryResponse>(res);
  },

  async getVehicleAlerts(plateNumber: string): Promise<Alert[]> {
    const res = await fetch(`${API_BASE}/vehicles/${encodeURIComponent(plateNumber)}/alerts`);
    return handleResponse<Alert[]>(res);
  },

  // Alerts
  async getAlerts(severity?: string, status?: string, alertType?: string, limit = 50): Promise<Alert[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (severity) params.append('severity', severity);
    if (status) params.append('status', status);
    if (alertType) params.append('alert_type', alertType);
    const res = await fetch(`${API_BASE}/alerts?${params.toString()}`);
    return handleResponse<Alert[]>(res);
  },

  async acknowledgeAlert(alertId: string): Promise<Alert> {
    const res = await fetch(`${API_BASE}/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
      method: 'PATCH',
    });
    return handleResponse<Alert>(res);
  },

  // Analytics
  async getOverviewMetrics(): Promise<SystemOverviewMetrics> {
    const res = await fetch(`${API_BASE}/analytics/overview`);
    return handleResponse<SystemOverviewMetrics>(res);
  },

  async getCongestion(): Promise<CongestionResponse> {
    const res = await fetch(`${API_BASE}/analytics/congestion`);
    return handleResponse<CongestionResponse>(res);
  },

  async getHourlyFlow(): Promise<HourlyFlowMetric[]> {
    const res = await fetch(`${API_BASE}/analytics/hourly-flow`);
    return handleResponse<HourlyFlowMetric[]>(res);
  },

  // Simulator
  async getSimulatorStatus(): Promise<SimulatorStatus> {
    const res = await fetch(`${API_BASE}/simulator/status`);
    return handleResponse<SimulatorStatus>(res);
  },

  async startSimulator(): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/simulator/start`, { method: 'POST' });
    return handleResponse<{ status: string }>(res);
  },

  async pauseSimulator(): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/simulator/pause`, { method: 'POST' });
    return handleResponse<{ status: string }>(res);
  },

  async resumeSimulator(): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/simulator/resume`, { method: 'POST' });
    return handleResponse<{ status: string }>(res);
  },

  async setSimulatorSpeed(multiplier: number): Promise<{ status: string; multiplier: number }> {
    const res = await fetch(`${API_BASE}/simulator/speed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ multiplier }),
    });
    return handleResponse<{ status: string; multiplier: number }>(res);
  },

  async injectAnomaly(anomalyType: string): Promise<{ status: string; type?: string; events_count?: number }> {
    const res = await fetch(`${API_BASE}/simulator/inject-anomaly`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anomaly_type: anomalyType }),
    });
    return handleResponse<{ status: string; type?: string; events_count?: number }>(res);
  },
};
