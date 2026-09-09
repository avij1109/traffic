import json
from datetime import datetime, timezone
from typing import List, Any
from fastapi import WebSocket


class ConnectionManager:
    """Manages connected WebSocket clients and handles real-time JSON event broadcasts."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_event(self, event_type: str, data: Any):
        """Broadcasts structured event envelope to all active clients."""
        if not self.active_connections:
            return

        envelope = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }

        # Handle datetime / custom objects serialization
        message = json.dumps(envelope, default=str)
        dead_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = ConnectionManager()
