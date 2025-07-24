"""
WebSocket handler for real-time communication with the dashboard frontend
"""
import asyncio
import json
import time
import logging
from typing import Dict, List, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from models import ChatMessage, WebSocketMessage, KnowledgeUpdate, SystemStatus
from core.logging_config import get_logger, get_timeline_logger
from core.message_bus import message_bus
from core.message_types import UnifiedMessage, create_websocket_message

logger = get_logger("dashboard.websocket")
timeline_logger = get_timeline_logger("dashboard")

class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.start_time = time.time()
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"📡 New WebSocket connection. Total: {len(self.active_connections)}")
        
        # Send connection established confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "timestamp": time.time(),
            "data": {"message": "WebSocket connection ready"}
        }))
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"📡 WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast_message(self, message: Dict):
        """Broadcast a message to all connected clients (fire-and-forget)"""
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
        
        # Send to all connections (use copy to avoid iteration issues)
        disconnected = set()
        connections_copy = set(self.active_connections)
        for connection in connections_copy:
            try:
                # Use timeout to prevent blocking on slow connections
                await asyncio.wait_for(connection.send_text(message_json), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Connection timeout during message send")
                disconnected.add(connection)
            except Exception as e:
                # Only log if it's not a common disconnect error
                if "1011" not in str(e) and "ping timeout" not in str(e):
                    logger.warning(f"⚠️ Failed to send to connection: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)
    
    async def broadcast_chat_message(self, chat_message: ChatMessage):
        """Broadcast a chat message (fire-and-forget)"""
        logger.info(f"🔍 Broadcasting chat message: type={chat_message.type}, id={chat_message.id}, connections={len(self.active_connections)}")
        
        await self.broadcast_message({
            "type": "chat_message",
            "data": {
                "message": chat_message.dict()
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
    
    async def broadcast_log_stream(self, log_data: Dict):
        """Broadcast log stream message"""
        await self.broadcast_message({
            "type": "log_stream",
            "data": log_data
        })
    
    
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
        
        # Subscribe to message bus for unified messages
        message_bus.subscribe(self._handle_unified_message, is_async=True)
        logger.info("📡 Subscribed to message bus for unified messages")
    
    async def handle_websocket(self, websocket: WebSocket):
        """Handle a WebSocket connection lifecycle"""
        await self.connection_manager.connect(websocket)
        
        try:
            while True:
                # Use timeout to prevent blocking indefinitely
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    await self._handle_client_message(websocket, data)
                except asyncio.TimeoutError:
                    # Send ping to check if connection is still alive
                    try:
                        await websocket.send_text(json.dumps({"type": "ping", "timestamp": time.time()}))
                    except:
                        # Connection is dead, break the loop
                        break
                
        except WebSocketDisconnect:
            await self.connection_manager.disconnect(websocket)
        except Exception as e:
            logger.warning(f"⚠️ WebSocket connection lost: {e}")
            await self.connection_manager.disconnect(websocket)
    
    async def _handle_unified_message(self, message: UnifiedMessage):
        """Handle unified message from message bus and broadcast to all clients"""
        try:
            logger.debug(f"🚌 Received unified message from bus: {message.type} - {message.id}")
            
            # Convert to WebSocket message format and broadcast
            ws_message = create_websocket_message(message)
            await self.connection_manager.broadcast_message(ws_message)
            
            # Log successful broadcast with structured format
            client_count = self.connection_manager.get_connection_count()
            logger.info(f"📤 BROADCAST | type={message.type} | id={message.id[:8]} | clients={client_count}")
            
            # Handle message-specific processing
            if message.type == "gif":
                # Cache GIF data for retention policy
                gif_content = message.content.get("gif", {})
                if gif_content.get("data"):
                    self.gif_cache[message.id] = {
                        "data": gif_content["data"],
                        "timestamp": message.timestamp
                    }
                    # Cleanup old GIFs
                    await self._cleanup_old_gifs()
                    
        except Exception as e:
            logger.error(f"❌ Error handling unified message: {e}")
    
    async def _handle_client_message(self, websocket: WebSocket, data: str):
        """Handle incoming messages from clients"""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            logger.debug(f"🔍 CLIENT MSG | type={message_type} | size={len(data)}")
            
            # Simplified client message handling - most messages now come via message bus
            if message_type == "ping":
                # Respond to ping
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
            
            elif message_type == "request_status":
                # Send current system status
                await websocket.send_text(json.dumps({
                    "type": "status_response",
                    "data": {"message": "Status request received"}
                }))
            
            elif message_type == "pong":
                # Handle pong response from client - connection is alive
                logger.debug(f"📡 Received pong from client - connection alive")
            
            elif message_type in ["gif_message", "response_message", "action_message", "chat_message"]:
                # These messages now come through message bus, log for debugging
                logger.warning(f"ℹ️ Legacy message type {message_type} received - should come via message bus")
            
            else:
                logger.warning(f"⚠️ Unknown client message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.warning(f"⚠️ Invalid JSON from client: {data[:100]}")
        except Exception as e:
            logger.error(f"❌ Error handling client message: {e}")
    
    # Old message handling methods removed - now using unified message bus handler
    
    async def send_gif_message(self, gif_data: str, metadata: Dict):
        """Send a GIF message to all clients"""
        from models import GifData, ChatMessage
        
        # TIMELINE EVENT 3: T+0.2s - GIF MESSAGE appears in frontend chat
        timeline_logger.log_event(3, "0.2s", "GIF MESSAGE appears in frontend chat")
        logger.info(f"🔍 Creating GIF message: data_length={len(gif_data)}, metadata={metadata}")
        
        # Create GIF data object
        gif_obj = GifData(
            data=gif_data,
            metadata=metadata,
            available=True
        )
        
        # Create chat message
        chat_message = ChatMessage.create_gif_message(gif_obj, 0)  # Sequence will be set by broadcast
        
        logger.info(f"🔍 Created chat message: id={chat_message.id}, type={chat_message.type}")
        
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
        
        # TIMELINE EVENT 7: T+6.1s - AI RESPONSE MESSAGE appears in frontend chat  
        timeline_logger.log_event(7, "6.1s", "AI RESPONSE MESSAGE appears in frontend chat")
        logger.info(f"🔍 Creating response message: text_length={len(response_text)}, has_reasoning={reasoning is not None}")
        
        response_data = ResponseData(
            text=response_text,
            reasoning=reasoning,
            processing_time=processing_time
        )
        
        chat_message = ChatMessage.create_response_message(response_data, 0)
        logger.info(f"🔍 Created response chat message: id={chat_message.id}, type={chat_message.type}")
        
        await self.connection_manager.broadcast_chat_message(chat_message)
    
    async def send_action_message(self, buttons: List[str], durations: List[float], 
                                 button_names: List[str] = None):
        """Send an action message to all clients"""
        from models import ActionData, ChatMessage
        
        # TIMELINE EVENT 9: T+6.3s - ACTION MESSAGE appears in frontend chat
        timeline_logger.log_event(9, "6.3s", "ACTION MESSAGE appears in frontend chat")
        
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