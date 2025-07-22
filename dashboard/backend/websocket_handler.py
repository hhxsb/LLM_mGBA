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
sys.path.append(str(Path(__file__).parent.parent.parent))

from models import ChatMessage, WebSocketMessage, KnowledgeUpdate, SystemStatus
from core.logging_config import get_logger, get_timeline_logger

logger = get_logger("dashboard.websocket")
timeline_logger = get_timeline_logger("dashboard")

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
        """Broadcast a chat message"""
        self.message_sequence += 1
        chat_message.sequence = self.message_sequence
        
        logger.info(f"🔍 Broadcasting chat message: type={chat_message.type}, id={chat_message.id}, connections={len(self.active_connections)}")
        
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
    
    async def broadcast_log_stream(self, log_data: Dict):
        """Broadcast log stream message"""
        await self.broadcast_message({
            "type": "log_stream",
            "data": log_data
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
    
    async def _handle_client_message(self, websocket: WebSocket, data: str):
        """Handle incoming messages from clients"""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            logger.info(f"🔍 Received WebSocket message: type={message_type}, data_length={len(data)}")
            
            # Enhanced logging for debugging real mode
            if message_type == "chat_message":
                chat_data = message.get("data", {}).get("message", {})
                logger.info(f"🔍 CHAT MESSAGE DETAILS: id={chat_data.get('id')}, type={chat_data.get('type')}, has_content={bool(chat_data.get('content'))}")
            else:
                logger.debug(f"🔍 Non-chat message: {message_type}")
            
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
            
            elif message_type == "chat_message":
                # Handle chat message from AI processes
                await self._handle_chat_message(message)
            
            elif message_type == "pong":
                # Handle pong response from client - connection is alive
                logger.debug(f"📡 Received pong from client - connection alive")
            
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
    
    async def _handle_chat_message(self, message: Dict):
        """Handle chat message from AI processes"""
        try:
            data = message.get("data", {})
            chat_data = data.get("message", {})
            
            logger.info(f"🔍 Processing chat message: data_keys={list(data.keys())}, chat_data_keys={list(chat_data.keys())}")
            
            if not chat_data:
                logger.warning("⚠️ Empty chat message data")
                return
            
            message_type = chat_data.get("type")
            content = chat_data.get("content", {})
            
            logger.info(f"🔍 Chat message details: type={message_type}, content_keys={list(content.keys())}")
            
            if message_type == "gif" and "gif" in content:
                # Handle GIF message
                gif_info = content["gif"]
                await self.send_gif_message(
                    gif_info.get("data", ""),
                    gif_info.get("metadata", {})
                )
                logger.info("📤 Processed chat GIF message")
                
            elif message_type == "response" and "response" in content:
                # Handle AI response message
                response_info = content["response"]
                await self.send_response_message(
                    response_info.get("text", ""),
                    response_info.get("reasoning"),
                    response_info.get("processing_time")
                )
                logger.info("📤 Processed chat response message")
                
            elif message_type == "action" and "action" in content:
                # Handle action message
                action_info = content["action"]
                await self.send_action_message(
                    action_info.get("buttons", []),
                    action_info.get("durations", []),
                    action_info.get("button_names", [])
                )
                logger.info("📤 Processed chat action message")
                
            else:
                logger.warning(f"⚠️ Unknown chat message type: {message_type}")
            
        except Exception as e:
            logger.error(f"❌ Error handling chat message: {e}")
    
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