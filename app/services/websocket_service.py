from fastapi import WebSocket
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Stores connections by conversation_id
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)
        logger.info(f"WebSocket client connected to conversation {conversation_id}. Total connections in this room: {len(self.active_connections[conversation_id])}")

    def disconnect(self, websocket: WebSocket, conversation_id: str):
        if conversation_id in self.active_connections:
            if websocket in self.active_connections[conversation_id]:
                self.active_connections[conversation_id].remove(websocket)
                if not self.active_connections[conversation_id]:
                    del self.active_connections[conversation_id]
            logger.info(f"WebSocket client disconnected from conversation {conversation_id}.")

    async def broadcast(self, message: str, conversation_id: str):
        if conversation_id in self.active_connections:
            connections = self.active_connections[conversation_id]
            logger.info(f"Broadcasting message to {len(connections)} clients in conversation {conversation_id}")
            for connection in connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending message to client: {str(e)}")
                    # We might want to disconnect here, but let's leave it safe for now
                    pass
        else:
             logger.info(f"No active connections for conversation {conversation_id}")

manager = ConnectionManager()
