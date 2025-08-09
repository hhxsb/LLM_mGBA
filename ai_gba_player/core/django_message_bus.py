"""
Django Channels integration for the AI GBA Player message bus system.
Bridges the existing message bus with Django Channels WebSocket consumers.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

# Import the existing message bus and types
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    from core.message_bus import message_bus as global_message_bus
    from core.message_types import UnifiedMessage, create_websocket_message
    from core.logging_config import get_logger
except ImportError as e:
    # If running from Django context, try alternative import paths
    try:
        import os
        core_path = os.path.join(project_root, 'core')
        sys.path.append(core_path)
        
        from message_bus import message_bus as global_message_bus
        from message_types import UnifiedMessage, create_websocket_message
        from logging_config import get_logger
    except ImportError:
        # Fallback to mock implementations for testing
        print(f"Warning: Could not import core modules ({e}), using mock implementations")
        
        class MockMessageBus:
            def subscribe(self, handler, is_async=True): pass
            def publish_sync(self, message): pass
            def get_stats(self): return {}
            def health_check(self): return {}
            def get_message_history(self, message_type=None, limit=10): return []
        
        class MockUnifiedMessage:
            @staticmethod
            def create_gif_message(*args, **kwargs): return {}
            @staticmethod  
            def create_response_message(*args, **kwargs): return {}
            @staticmethod
            def create_action_message(*args, **kwargs): return {}
            @staticmethod
            def create_system_message(*args, **kwargs): return {}
            @staticmethod
            def create_screenshots_message(*args, **kwargs): return {}
        
        def mock_create_websocket_message(message): return {'type': 'mock', 'data': {}}
        def mock_get_logger(name): return logging.getLogger(name)
        
        global_message_bus = MockMessageBus()
        UnifiedMessage = MockUnifiedMessage()
        create_websocket_message = mock_create_websocket_message
        get_logger = mock_get_logger

logger = get_logger("django_message_bus")

class DjangoChannelsMessageBridge:
    """
    Bridges the existing message bus with Django Channels.
    Subscribes to the global message bus and forwards messages to Django Channels groups.
    """
    
    def __init__(self, channel_layer=None):
        self.channel_layer = channel_layer or get_channel_layer()
        self.group_name = 'dashboard'
        self.is_initialized = False
        self.message_count = 0
        
        logger.info("🌉 Django Channels message bridge initialized")
    
    async def initialize(self):
        """Initialize the bridge by subscribing to the message bus"""
        if self.is_initialized:
            return
            
        # Subscribe to the global message bus
        global_message_bus.subscribe(self._handle_unified_message, is_async=True)
        self.is_initialized = True
        
        logger.info("🔗 Message bridge connected to global message bus")
    
    async def _handle_unified_message(self, message: UnifiedMessage):
        """
        Handle unified message from the global message bus and forward to Django Channels
        """
        try:
            self.message_count += 1
            logger.debug(f"🚌 Received message from bus: {message.type} - {message.id[:8]}")
            
            # Convert to WebSocket message format
            ws_message = create_websocket_message(message)
            
            # Send to Django Channels group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'broadcast_message',
                    'message': ws_message
                }
            )
            
            logger.info(f"📤 FORWARDED | type={message.type} | id={message.id[:8]} | group={self.group_name}")
            
        except Exception as e:
            logger.error(f"❌ Error forwarding message to Django Channels: {e}")
    
    async def send_to_dashboard(self, message_type: str, data: Dict[str, Any]):
        """
        Send a message directly to the dashboard group
        """
        try:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'broadcast_message',
                    'message': {
                        'type': message_type,
                        'timestamp': time.time(),
                        'data': data
                    }
                }
            )
            logger.debug(f"📤 Sent direct message: {message_type}")
            
        except Exception as e:
            logger.error(f"❌ Error sending direct message: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics"""
        return {
            'initialized': self.is_initialized,
            'messages_forwarded': self.message_count,
            'channel_layer_active': self.channel_layer is not None,
            'group_name': self.group_name
        }


class DjangoMessageBusAdapter:
    """
    Provides a Django-compatible interface to the existing message bus system.
    Allows Django views and management commands to easily publish messages.
    """
    
    def __init__(self):
        self.message_bus = global_message_bus
        logger.info("📱 Django message bus adapter initialized")
    
    def publish_gif_message(self, gif_data: str, metadata: Dict, source: str = "django_dashboard"):
        """Publish a GIF message through the message bus"""
        message = UnifiedMessage.create_gif_message(gif_data, metadata, source)
        self.message_bus.publish_sync(message)
        logger.info(f"📤 Published GIF message: {message.id[:8]}")
        return message
    
    def publish_response_message(self, text: str, reasoning: str = None, 
                               processing_time: float = None, confidence: float = 0.95,
                               source: str = "django_dashboard"):
        """Publish an AI response message through the message bus"""
        message = UnifiedMessage.create_response_message(text, reasoning, processing_time, confidence, source)
        self.message_bus.publish_sync(message)
        logger.info(f"📤 Published response message: {message.id[:8]}")
        return message
    
    def publish_action_message(self, buttons: list, durations: list, 
                             button_names: list = None, source: str = "django_dashboard"):
        """Publish an action message through the message bus"""
        message = UnifiedMessage.create_action_message(buttons, durations, button_names, source)
        self.message_bus.publish_sync(message)
        logger.info(f"📤 Published action message: {message.id[:8]}")
        return message
    
    def publish_system_message(self, text: str, level: str = "info", source: str = "django_dashboard"):
        """Publish a system message through the message bus"""
        message = UnifiedMessage.create_system_message(text, level, source)
        self.message_bus.publish_sync(message)
        logger.info(f"📤 Published system message: {message.id[:8]}")
        return message
    
    def publish_screenshots_message(self, before_image: str = None, after_image: str = None,
                                  metadata: dict = None, source: str = "django_dashboard"):
        """Publish a screenshots message through the message bus"""
        message = UnifiedMessage.create_screenshots_message(before_image, after_image, metadata, source)
        self.message_bus.publish_sync(message)
        logger.info(f"📤 Published screenshots message: {message.id[:8]}")
        return message
    
    def get_message_history(self, message_type: str = None, limit: int = 10):
        """Get recent message history from the message bus"""
        return self.message_bus.get_message_history(message_type, limit)
    
    def get_stats(self):
        """Get message bus statistics"""
        return self.message_bus.get_stats()
    
    def health_check(self):
        """Get message bus health status"""
        return self.message_bus.health_check()


# Global instances
django_message_bridge = DjangoChannelsMessageBridge()
django_message_adapter = DjangoMessageBusAdapter()


async def initialize_django_message_bus():
    """
    Initialize the Django message bus integration.
    Should be called during Django startup or in consumers.
    """
    await django_message_bridge.initialize()
    logger.info("✅ Django message bus integration fully initialized")


def sync_initialize_django_message_bus():
    """
    Synchronous wrapper for initializing the Django message bus integration.
    For use in Django management commands or views.
    """
    async_to_sync(initialize_django_message_bus)()


# Convenience functions for Django views and management commands
def publish_gif_message(gif_data: str, metadata: Dict, source: str = "django_dashboard"):
    """Convenience function to publish GIF message from Django"""
    return django_message_adapter.publish_gif_message(gif_data, metadata, source)

def publish_response_message(text: str, reasoning: str = None, processing_time: float = None,
                           confidence: float = 0.95, source: str = "django_dashboard"):
    """Convenience function to publish AI response message from Django"""
    return django_message_adapter.publish_response_message(text, reasoning, processing_time, confidence, source)

def publish_action_message(buttons: list, durations: list, button_names: list = None,
                         source: str = "django_dashboard"):
    """Convenience function to publish action message from Django"""
    return django_message_adapter.publish_action_message(buttons, durations, button_names, source)

def publish_system_message(text: str, level: str = "info", source: str = "django_dashboard"):
    """Convenience function to publish system message from Django"""
    return django_message_adapter.publish_system_message(text, level, source)

def publish_screenshots_message(before_image: str = None, after_image: str = None,
                              metadata: dict = None, source: str = "django_dashboard"):
    """Convenience function to publish screenshots message from Django"""
    return django_message_adapter.publish_screenshots_message(before_image, after_image, metadata, source)

def get_message_history(message_type: str = None, limit: int = 10):
    """Convenience function to get message history from Django"""
    return django_message_adapter.get_message_history(message_type, limit)

def get_message_bus_stats():
    """Convenience function to get message bus statistics from Django"""
    return django_message_adapter.get_stats()

def get_message_bus_health():
    """Convenience function to get message bus health from Django"""
    return django_message_adapter.health_check()