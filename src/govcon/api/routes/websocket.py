"""WebSocket routes for real-time updates."""

from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
from datetime import datetime

from govcon.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# Connection manager
class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "system": set(),
            "agents": set(),
            "errors": set(),
            "logs": set()
        }

    async def connect(self, websocket: WebSocket, channel: str):
        """Connect a WebSocket to a channel."""
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        logger.info(f"WebSocket connected to channel: {channel}")

    def disconnect(self, websocket: WebSocket, channel: str):
        """Disconnect a WebSocket from a channel."""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        logger.info(f"WebSocket disconnected from channel: {channel}")

    async def broadcast(self, message: dict, channel: str):
        """Broadcast message to all connections in a channel."""
        if channel not in self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        self.active_connections[channel] -= disconnected

    async def send_personal(self, message: dict, websocket: WebSocket):
        """Send message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")


manager = ConnectionManager()


@router.websocket("/ws/system")
async def websocket_system(websocket: WebSocket):
    """WebSocket endpoint for system metrics and status."""
    await manager.connect(websocket, "system")
    try:
        # Send initial status
        await manager.send_personal({
            "type": "connected",
            "channel": "system",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)

        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await manager.send_personal({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, "system")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, "system")


@router.websocket("/ws/agents")
async def websocket_agents(websocket: WebSocket):
    """WebSocket endpoint for agent status updates."""
    await manager.connect(websocket, "agents")
    try:
        await manager.send_personal({
            "type": "connected",
            "channel": "agents",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "subscribe_agent":
                agent_name = message.get("agent_name")
                await manager.send_personal({
                    "type": "subscribed",
                    "agent_name": agent_name,
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, "agents")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, "agents")


@router.websocket("/ws/errors")
async def websocket_errors(websocket: WebSocket):
    """WebSocket endpoint for error notifications."""
    await manager.connect(websocket, "errors")
    try:
        await manager.send_personal({
            "type": "connected",
            "channel": "errors",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)

        while True:
            await asyncio.sleep(1)  # Keep connection alive

    except WebSocketDisconnect:
        manager.disconnect(websocket, "errors")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, "errors")


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await manager.connect(websocket, "logs")
    try:
        await manager.send_personal({
            "type": "connected",
            "channel": "logs",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "set_filter":
                await manager.send_personal({
                    "type": "filter_set",
                    "filters": message.get("filters", {}),
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, "logs")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, "logs")


# Utility functions for broadcasting updates
async def broadcast_system_update(data: dict):
    """Broadcast system status update."""
    await manager.broadcast({
        "type": "system_update",
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }, "system")


async def broadcast_agent_update(agent_name: str, status: str, data: dict = None):
    """Broadcast agent status update."""
    await manager.broadcast({
        "type": "agent_update",
        "agent_name": agent_name,
        "status": status,
        "data": data or {},
        "timestamp": datetime.utcnow().isoformat()
    }, "agents")


async def broadcast_error(error: dict):
    """Broadcast error notification."""
    await manager.broadcast({
        "type": "error",
        "error": error,
        "timestamp": datetime.utcnow().isoformat()
    }, "errors")


async def broadcast_log(log: dict):
    """Broadcast log entry."""
    await manager.broadcast({
        "type": "log",
        "log": log,
        "timestamp": datetime.utcnow().isoformat()
    }, "logs")
