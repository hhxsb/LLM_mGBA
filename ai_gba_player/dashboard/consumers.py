import json
import logging
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage, Process, SystemLog

# Import Django message bus integration
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
try:
    from core.django_message_bus import django_message_bridge, initialize_django_message_bus
except ImportError as e:
    # Fallback if message bus integration is not available
    logger.warning(f"Message bus integration not available: {e}")
    
    async def initialize_django_message_bus():
        """Mock initialization function"""
        pass
    
    class MockMessageBridge:
        def get_stats(self): return {'initialized': False, 'error': 'Message bus not available'}
    
    django_message_bridge = MockMessageBridge()

logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for dashboard real-time updates"""
    
    async def connect(self):
        # Join dashboard group
        self.group_name = 'dashboard'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"🔌 Dashboard WebSocket connected: {self.channel_name}")
        
        # Initialize message bus bridge on first connection
        await initialize_django_message_bus()
        
        # Send initial status
        await self.send_initial_status()
    
    async def disconnect(self, close_code):
        # Leave dashboard group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"🔌 Dashboard WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            elif message_type == 'get_status':
                await self.send_system_status()
            elif message_type == 'get_recent_messages':
                await self.send_recent_messages()
            elif message_type == 'clear_chat':
                await self.clear_chat()
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def send_initial_status(self):
        """Send initial dashboard status"""
        await self.send_system_status()
        await self.send_recent_messages()
    
    async def send_system_status(self):
        """Send current system status"""
        try:
            processes = await self.get_process_status()
            await self.send(text_data=json.dumps({
                'type': 'system_status',
                'timestamp': 0,  # Django will handle timestamps
                'data': {
                    'system': {
                        'processes': processes,
                        'uptime': 0,  # Will be calculated by management command
                        'memory_usage': {}
                    },
                    'websocket': {
                        'active_connections': 1,  # Simplified for now
                        'uptime': 0,
                        'message_count': 0
                    },
                    'timestamp': 0
                }
            }))
        except Exception as e:
            logger.error(f"Error sending system status: {e}")
    
    async def send_recent_messages(self):
        """Send recent chat messages"""
        try:
            messages = await self.get_recent_chat_messages()
            for message in messages:
                await self.send(text_data=json.dumps({
                    'type': 'chat_message',
                    'timestamp': message['timestamp'],
                    'data': {
                        'id': message['message_id'],
                        'type': message['message_type'],
                        'timestamp': message['timestamp'],
                        'source': message['source'],
                        'content': message['content'],
                        'sequence': message['sequence']
                    }
                }))
        except Exception as e:
            logger.error(f"Error sending recent messages: {e}")
    
    async def clear_chat(self):
        """Clear chat messages"""
        try:
            await self.clear_chat_messages()
            await self.send(text_data=json.dumps({
                'type': 'chat_cleared',
                'timestamp': 0
            }))
        except Exception as e:
            logger.error(f"Error clearing chat: {e}")
    
    # Message handlers for group messages
    async def broadcast_message(self, event):
        """Handle broadcast message from message bus bridge"""
        message = event['message']
        
        # Store message in database for persistence
        if message.get('type') == 'chat_message':
            await self.store_chat_message(message.get('data', {}))
        
        # Forward to WebSocket client
        await self.send(text_data=json.dumps(message))
        logger.debug(f"📤 Forwarded message to client: {message.get('type')}")
    
    async def chat_message(self, event):
        """Handle chat message from group"""
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'timestamp': message.get('timestamp', 0),
            'data': message
        }))
    
    async def system_status(self, event):
        """Handle system status from group"""
        await self.send(text_data=json.dumps({
            'type': 'system_status',
            'timestamp': event['message'].get('timestamp', 0),
            'data': event['message']
        }))
    
    async def log_message(self, event):
        """Handle log message from group"""
        await self.send(text_data=json.dumps({
            'type': 'log_stream',
            'timestamp': event['message'].get('timestamp', 0),
            'data': event['message']
        }))
    
    # Database operations
    @database_sync_to_async
    def get_process_status(self):
        """Get current process status from database"""
        processes = {}
        for process in Process.objects.all():
            processes[process.name] = {
                'status': process.status,
                'pid': process.pid,
                'port': process.port,
                'last_error': process.last_error,
                'updated_at': process.updated_at.isoformat() if process.updated_at else None
            }
        return processes
    
    @database_sync_to_async
    def get_recent_chat_messages(self):
        """Get recent chat messages from database"""
        messages = []
        for msg in ChatMessage.objects.all()[:50]:  # Last 50 messages
            messages.append({
                'message_id': msg.message_id,
                'message_type': msg.message_type,
                'source': msg.source,
                'content': msg.content,
                'timestamp': msg.timestamp,
                'sequence': msg.sequence
            })
        return list(reversed(messages))  # Oldest first
    
    @database_sync_to_async
    def clear_chat_messages(self):
        """Clear all chat messages from database"""
        ChatMessage.objects.all().delete()
    
    @database_sync_to_async
    def store_chat_message(self, message_data):
        """Store chat message in database for persistence"""
        try:
            ChatMessage.objects.create(
                message_id=message_data.get('id', ''),
                message_type=message_data.get('type', 'unknown'),
                source=message_data.get('source', 'unknown'),
                content=message_data.get('content', {}),
                timestamp=message_data.get('timestamp', time.time()),
                sequence=message_data.get('sequence', 0)
            )
            logger.debug(f"💾 Stored message in database: {message_data.get('id', 'unknown')}")
        except Exception as e:
            logger.error(f"❌ Error storing message in database: {e}")