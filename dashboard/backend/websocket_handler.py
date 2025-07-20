"""
WebSocket handler for real-time communication with the dashboard frontend
"""
import asyncio
import json
import time
import logging
from typing import Dict, List, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from collections import deque
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from models import ChatMessage, WebSocketMessage, KnowledgeUpdate, SystemStatus

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.message_history: deque = deque(maxlen=100)  # Keep last 100 messages
        self.message_sequence = 0
        self.start_time = time.time()
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"📡 New WebSocket connection. Total: {len(self.active_connections)}")
        
        # Send recent message history to new connection
        await self._send_message_history(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"📡 WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast_message(self, message: Dict):
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            return
        
        # Create WebSocket message
        ws_message = WebSocketMessage(
            type=message.get("type", "unknown"),
            timestamp=time.time(),
            data=message
        )
        
        message_json = ws_message.json()
        logger.debug(f"📤 Broadcasting: {message.get('type', 'unknown')}")
        
        # Store in history
        self.message_history.append(ws_message.dict())
        
        # Send to all connections
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"⚠️ Failed to send to connection: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)
    
    async def broadcast_chat_message(self, chat_message: ChatMessage):
        """Broadcast a chat message"""
        self.message_sequence += 1
        chat_message.sequence = self.message_sequence
        
        await self.broadcast_message({
            "type": "chat_message",
            "data": {
                "message": chat_message.dict(),
                "sequence": self.message_sequence
            }
        })
    
    async def broadcast_knowledge_update(self, update: KnowledgeUpdate):
        """Broadcast a knowledge update"""
        await self.broadcast_message({
            "type": "knowledge_update",
            "data": update.dict()
        })
    
    async def broadcast_system_status(self, status: Dict):
        """Broadcast system status"""
        await self.broadcast_message({
            "type": "system_status",
            "data": status
        })
    
    async def broadcast_process_health(self, process_name: str, health_data: Dict):
        """Broadcast process health update"""
        await self.broadcast_message({
            "type": "process_health",
            "data": {
                "process": process_name,
                "health": health_data,
                "timestamp": time.time()
            }
        })
    
    async def _send_message_history(self, websocket: WebSocket):
        """Send recent message history to a newly connected client"""
        if not self.message_history:
            return
        
        try:
            # Send a batch of recent messages
            history_message = WebSocketMessage(
                type="message_history",
                timestamp=time.time(),
                data={
                    "messages": list(self.message_history),
                    "total_count": len(self.message_history)
                }
            )
            
            await websocket.send_text(history_message.json())
            logger.info(f"📤 Sent {len(self.message_history)} historical messages to new client")
            
        except Exception as e:
            logger.error(f"❌ Failed to send message history: {e}")
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_uptime(self) -> float:
        """Get WebSocket server uptime"""
        return time.time() - self.start_time

class DashboardWebSocketHandler:
    """Handles WebSocket communication for the dashboard"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.gif_retention_time = 30 * 60  # 30 minutes in seconds
        self.gif_cache: Dict[str, Dict] = {}
        self.last_cleanup = time.time()
    
    async def handle_websocket(self, websocket: WebSocket):
        """Handle a WebSocket connection lifecycle"""
        await self.connection_manager.connect(websocket)
        
        try:
            while True:
                # Listen for messages from client (if needed for future features)
                data = await websocket.receive_text()
                await self._handle_client_message(websocket, data)
                
        except WebSocketDisconnect:
            await self.connection_manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"❌ WebSocket error: {e}")
            await self.connection_manager.disconnect(websocket)
    
    async def _handle_client_message(self, websocket: WebSocket, data: str):
        """Handle incoming messages from clients"""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "ping":
                # Respond to ping
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
            
            elif message_type == "request_status":
                # Send current system status
                # This would be implemented when we have access to process manager
                await websocket.send_text(json.dumps({
                    "type": "status_response",
                    "data": {"message": "Status request received"}
                }))
            
            elif message_type == "gif_message":
                # Handle GIF message from video capture process
                await self._handle_gif_message(message)
            
            elif message_type == "response_message":
                # Handle AI response message from game control process
                await self._handle_response_message(message)
            
            elif message_type == "action_message":
                # Handle action message from game control process
                await self._handle_action_message(message)
            
            else:
                logger.warning(f"⚠️ Unknown client message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.warning(f"⚠️ Invalid JSON from client: {data[:100]}")
        except Exception as e:
            logger.error(f"❌ Error handling client message: {e}")
    
    async def _handle_gif_message(self, message: Dict):
        """Handle GIF message from video capture process"""
        try:
            data = message.get("data", {})
            gif_data = data.get("gif_data")
            metadata = data.get("metadata", {})
            
            if gif_data and metadata:
                # Send GIF to all connected dashboard clients
                await self.send_gif_message(gif_data, metadata)
                logger.info(f"📤 Forwarded GIF to dashboard: {metadata.get('frameCount', 0)} frames")
            
        except Exception as e:
            logger.error(f"❌ Error handling GIF message: {e}")
    
    async def _handle_response_message(self, message: Dict):
        """Handle AI response message from game control process"""
        try:
            data = message.get("data", {})
            response_text = data.get("response_text", "")
            reasoning = data.get("reasoning")
            processing_time = data.get("processing_time")
            
            if response_text:
                # Send response to all connected dashboard clients
                await self.send_response_message(response_text, reasoning, processing_time)
                logger.info(f"📤 Forwarded AI response to dashboard: {len(response_text)} chars")
            
        except Exception as e:
            logger.error(f"❌ Error handling response message: {e}")
    
    async def _handle_action_message(self, message: Dict):
        """Handle action message from game control process"""
        try:
            data = message.get("data", {})
            buttons = data.get("buttons", [])
            durations = data.get("durations", [])
            button_names = data.get("button_names", [])
            
            if buttons:
                # Send actions to all connected dashboard clients
                await self.send_action_message(buttons, durations, button_names)
                logger.info(f"📤 Forwarded actions to dashboard: {len(buttons)} buttons")
            
        except Exception as e:
            logger.error(f"❌ Error handling action message: {e}")
    
    async def send_gif_message(self, gif_data: str, metadata: Dict):
        """Send a GIF message to all clients"""
        from models import GifData, ChatMessage
        
        # Create GIF data object
        gif_obj = GifData(
            data=gif_data,
            metadata=metadata,
            available=True
        )
        
        # Create chat message
        chat_message = ChatMessage.create_gif_message(gif_obj, 0)  # Sequence will be set by broadcast
        
        # Cache the GIF for retention policy
        self.gif_cache[chat_message.id] = {
            "data": gif_data,
            "timestamp": time.time()
        }
        
        # Broadcast the message
        await self.connection_manager.broadcast_chat_message(chat_message)
        
        # Cleanup old GIFs
        await self._cleanup_old_gifs()
    
    async def send_response_message(self, response_text: str, reasoning: Optional[str] = None, 
                                   processing_time: Optional[float] = None):
        """Send an AI response message to all clients"""
        from models import ResponseData, ChatMessage
        
        response_data = ResponseData(
            text=response_text,
            reasoning=reasoning,
            processing_time=processing_time
        )
        
        chat_message = ChatMessage.create_response_message(response_data, 0)
        await self.connection_manager.broadcast_chat_message(chat_message)
    
    async def send_action_message(self, buttons: List[str], durations: List[float], 
                                 button_names: List[str] = None):
        """Send an action message to all clients"""
        from models import ActionData, ChatMessage
        
        action_data = ActionData(
            buttons=buttons,
            durations=durations,
            button_names=button_names or []
        )
        
        chat_message = ChatMessage.create_action_message(action_data, 0)
        await self.connection_manager.broadcast_chat_message(chat_message)
    
    async def send_knowledge_update(self, update_type: str, content: Dict):
        """Send a knowledge update to all clients"""
        from models import KnowledgeUpdate
        
        update = KnowledgeUpdate(
            update_type=update_type,
            content=content
        )
        
        await self.connection_manager.broadcast_knowledge_update(update)
    
    async def _cleanup_old_gifs(self):
        """Clean up old GIF data to save memory"""
        current_time = time.time()
        
        # Only cleanup every 5 minutes
        if current_time - self.last_cleanup < 300:
            return
        
        self.last_cleanup = current_time
        
        # Remove GIFs older than retention time
        expired_gifs = []
        for gif_id, gif_info in self.gif_cache.items():
            if current_time - gif_info["timestamp"] > self.gif_retention_time:
                expired_gifs.append(gif_id)
        
        for gif_id in expired_gifs:
            del self.gif_cache[gif_id]
            
            # Mark message as no longer available
            await self.connection_manager.broadcast_message({
                "type": "gif_expired",
                "data": {
                    "gif_id": gif_id,
                    "message": "GIF no longer available"
                }
            })
        
        if expired_gifs:
            logger.info(f"🧹 Cleaned up {len(expired_gifs)} expired GIFs")

# Global connection manager instance
connection_manager = ConnectionManager()
websocket_handler = DashboardWebSocketHandler(connection_manager)