import { useState, useEffect, useRef, useCallback } from 'react';
import { Detection, Alert, CongestionResponse, WebSocketEventEnvelope } from '../types/api';

interface UseWebSocketOptions {
  url?: string;
  maxDetections?: number;
  maxAlerts?: number;
  reconnectInterval?: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000/ws/live-feed`,
    maxDetections = 50,
    maxAlerts = 30,
    reconnectInterval = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [latestDetection, setLatestDetection] = useState<Detection | null>(null);
  const [latestAlert, setLatestAlert] = useState<Alert | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [congestion, setCongestion] = useState<CongestionResponse | null>(null);
  const [lastEventTime, setLastEventTime] = useState<Date | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pendingDetectionsRef = useRef<Detection[]>([]);
  const rafHandleRef = useRef<number | null>(null);

  // Batch high frequency detection updates via requestAnimationFrame
  const flushPendingDetections = useCallback(() => {
    if (pendingDetectionsRef.current.length > 0) {
      const incoming = [...pendingDetectionsRef.current];
      pendingDetectionsRef.current = [];

      setDetections((prev) => {
        const combined = [...incoming, ...prev];
        // Deduplicate by detection id
        const unique = Array.from(new Map(combined.map((d) => [d.id, d])).values());
        return unique.slice(0, maxDetections);
      });

      if (incoming.length > 0) {
        setLatestDetection(incoming[0]);
      }
    }
  }, [maxDetections]);

  useEffect(() => {
    const interval = setInterval(() => {
      flushPendingDetections();
    }, 150);

    return () => clearInterval(interval);
  }, [flushPendingDetections]);

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        setLastEventTime(new Date());
        try {
          const envelope: WebSocketEventEnvelope = JSON.parse(event.data);

          if (envelope.event === 'NEW_DETECTION') {
            const det = envelope.data as Detection;
            pendingDetectionsRef.current.unshift(det);
          } else if (envelope.event === 'NEW_ALERT') {
            const alert = envelope.data as Alert;
            setLatestAlert(alert);
            setAlerts((prev) => [alert, ...prev.filter((a) => a.id !== alert.id)].slice(0, maxAlerts));
          } else if (envelope.event === 'CONGESTION_UPDATE') {
            setCongestion(envelope.data as CongestionResponse);
          }
        } catch {
          // ignore parsing error
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = window.setTimeout(connect, reconnectInterval);
      };

      ws.onerror = () => {
        setIsConnected(false);
        ws.close();
      };
    } catch {
      setIsConnected(false);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = window.setTimeout(connect, reconnectInterval);
    }
  }, [url, maxAlerts, reconnectInterval]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (rafHandleRef.current) cancelAnimationFrame(rafHandleRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const addSimulatedDetection = useCallback((det: Detection) => {
    pendingDetectionsRef.current.unshift(det);
  }, []);

  const addSimulatedAlert = useCallback((alert: Alert) => {
    setLatestAlert(alert);
    setAlerts((prev) => [alert, ...prev].slice(0, maxAlerts));
  }, [maxAlerts]);

  return {
    isConnected,
    latestDetection,
    latestAlert,
    detections,
    alerts,
    congestion,
    lastEventTime,
    reconnect: connect,
    addSimulatedDetection,
    addSimulatedAlert,
  };
}
