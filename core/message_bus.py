"""
Central message bus for Pokemon AI system.
Handles all inter-process communication using publish/subscribe pattern.
"""

import asyncio
import threading
import time
from typing import Set, Callable, Dict, List, Optional
from dataclasses import dataclass
from core.message_types import UnifiedMessage, validate_unified_message
from core.logging_config import get_logger

logger = get_logger("message_bus")

# Create a dedicated message flow logger for tracking
def log_message_flow(action: str, message_type: str, message_id: str, source: str = None, destination: str = None, details: str = None):
    """Structured logging for message flow tracking"""
    log_parts = [f"🔄 {action}", f"type={message_type}", f"id={message_id[:8]}"]
    
    if source:
        log_parts.append(f"from={source}")
    if destination:
        log_parts.append(f"to={destination}")
    if details:
        log_parts.append(f"details={details}")
    
    logger.info(" | ".join(log_parts))


@dataclass
class MessageStats:
    """Statistics for message bus performance monitoring"""
    total_published: int = 0
    total_delivered: int = 0
    total_errors: int = 0
    message_types: Dict[str, int] = None
    last_message_time: Optional[float] = None
    
    def __post_init__(self):
        if self.message_types is None:
            self.message_types = {}


class MessageBus:
    """Central message bus for all system communication"""
    
    def __init__(self):
        self.subscribers: Set[Callable] = set()
        self.async_subscribers: Set[Callable] = set()
        self.sync_subscribers: Set[Callable] = set()
        self.stats = MessageStats()
        self.running = True
        self.message_history: List[UnifiedMessage] = []
        self.max_history = 100  # Keep last 100 messages for debugging
        self._lock = threading.Lock()
        
        logger.info("🚌 Message bus initialized")
    
    def subscribe(self, handler: Callable, is_async: bool = None):
        """Subscribe to receive all messages
        
        Args:
            handler: Function to handle messages
            is_async: Whether handler is async (auto-detected if None)
        """
        with self._lock:
            self.subscribers.add(handler)
            
            # Auto-detect async vs sync if not specified
            if is_async is None:
                is_async = asyncio.iscoroutinefunction(handler)
            
            if is_async:
                self.async_subscribers.add(handler)
                logger.debug(f"📥 Registered async subscriber: {handler.__name__}")
            else:
                self.sync_subscribers.add(handler)
                logger.debug(f"📥 Registered sync subscriber: {handler.__name__}")
    
    def unsubscribe(self, handler: Callable):
        """Unsubscribe from messages"""
        with self._lock:
            self.subscribers.discard(handler)
            self.async_subscribers.discard(handler)
            self.sync_subscribers.discard(handler)
            logger.debug(f"📤 Unregistered subscriber: {handler.__name__}")
    
    async def publish_async(self, message: UnifiedMessage):
        """Publish message to all subscribers (async version)"""
        if not self.running:
            logger.warning("⚠️ Message bus not running, dropping message")
            return
        
        # Validate message
        if not validate_unified_message(message):
            logger.error(f"❌ Invalid message format: {message}")
            self.stats.total_errors += 1
            return
        
        # Update stats
        self.stats.total_published += 1
        self.stats.last_message_time = time.time()
        self.stats.message_types[message.type] = self.stats.message_types.get(message.type, 0) + 1
        
        # Add to history
        with self._lock:
            self.message_history.append(message)
            if len(self.message_history) > self.max_history:
                self.message_history.pop(0)
        
        # Log message flow
        log_message_flow("PUBLISH", message.type, message.id, source=message.source, 
                        details=f"subscribers={len(self.subscribers)}")
        
        # Send to all subscribers
        delivered_count = 0
        error_count = 0
        
        # Handle async subscribers
        for handler in self.async_subscribers.copy():  # Copy to avoid modification during iteration
            try:
                await handler(message)
                delivered_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"❌ Error in async handler {handler.__name__}: {e}")
        
        # Handle sync subscribers in thread pool to avoid blocking
        for handler in self.sync_subscribers.copy():
            try:
                # Run sync handler in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler, message)
                delivered_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"❌ Error in sync handler {handler.__name__}: {e}")
        
        # Update delivery stats
        self.stats.total_delivered += delivered_count
        self.stats.total_errors += error_count
        
        # Only log if there are issues or in debug mode
        if delivered_count == 0:
            logger.warning(f"⚠️ No subscribers received {message.type} message: {message.id}")
        elif error_count > 0:
            logger.warning(f"⚠️ Published {message.type} message to {delivered_count} subscribers with {error_count} errors")
        else:
            logger.debug(f"📨 Published {message.type} message to {delivered_count} subscribers")
    
    def publish_sync(self, message: UnifiedMessage):
        """Publish message synchronously (creates async task)"""
        if not self.running:
            logger.warning("⚠️ Message bus not running, dropping message")
            return
        
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, schedule coroutine
                    asyncio.create_task(self.publish_async(message))
                else:
                    # If loop exists but not running, run until complete
                    loop.run_until_complete(self.publish_async(message))
            except RuntimeError:
                # No event loop in current thread, create new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.publish_async(message))
                finally:
                    loop.close()
                    
        except Exception as e:
            logger.error(f"❌ Error in sync publish: {e}")
            self.stats.total_errors += 1
    
    def get_stats(self) -> MessageStats:
        """Get message bus statistics"""
        return self.stats
    
    def get_subscriber_count(self) -> int:
        """Get number of active subscribers"""
        return len(self.subscribers)
    
    def get_message_history(self, message_type: str = None, limit: int = 10) -> List[UnifiedMessage]:
        """Get recent message history
        
        Args:
            message_type: Filter by message type (optional)
            limit: Maximum number of messages to return
        """
        with self._lock:
            messages = self.message_history
            
            if message_type:
                messages = [m for m in messages if m.type == message_type]
            
            return messages[-limit:] if limit else messages
    
    def clear_history(self):
        """Clear message history"""
        with self._lock:
            self.message_history.clear()
            logger.info("🧹 Message history cleared")
    
    def shutdown(self):
        """Shutdown message bus"""
        self.running = False
        with self._lock:
            self.subscribers.clear()
            self.async_subscribers.clear()
            self.sync_subscribers.clear()
        logger.info("🛑 Message bus shutdown")
    
    def health_check(self) -> Dict[str, any]:
        """Get health status of message bus"""
        return {
            "running": self.running,
            "subscriber_count": len(self.subscribers),
            "async_subscribers": len(self.async_subscribers),
            "sync_subscribers": len(self.sync_subscribers),
            "total_published": self.stats.total_published,
            "total_delivered": self.stats.total_delivered,
            "total_errors": self.stats.total_errors,
            "message_types": dict(self.stats.message_types),
            "last_message_time": self.stats.last_message_time,
            "history_size": len(self.message_history)
        }


# Global message bus instance
message_bus = MessageBus()


# Convenience functions for easy publishing
def publish_gif_message(gif_data: str, metadata: Dict, source: str = "video_capture"):
    """Convenience function to publish GIF message"""
    message = UnifiedMessage.create_gif_message(gif_data, metadata, source)
    message_bus.publish_sync(message)
    return message


def publish_response_message(text: str, reasoning: str = None, processing_time: float = None, 
                           confidence: float = 0.95, source: str = "game_control"):
    """Convenience function to publish AI response message"""
    message = UnifiedMessage.create_response_message(text, reasoning, processing_time, confidence, source)
    message_bus.publish_sync(message)
    return message


def publish_action_message(buttons: List[str], durations: List[float], 
                         button_names: List[str] = None, source: str = "game_control"):
    """Convenience function to publish action message"""
    message = UnifiedMessage.create_action_message(buttons, durations, button_names, source)
    message_bus.publish_sync(message)
    return message


def publish_system_message(text: str, level: str = "info", source: str = "system"):
    """Convenience function to publish system message"""
    message = UnifiedMessage.create_system_message(text, level, source)
    message_bus.publish_sync(message)
    return message


# Testing and debugging functions
def test_message_bus():
    """Test message bus functionality"""
    logger.info("🧪 Testing message bus...")
    
    # Test message creation and publishing
    test_responses = []
    
    def test_handler(message: UnifiedMessage):
        test_responses.append(message)
        logger.info(f"🧪 Test handler received: {message.type} - {message.id}")
    
    # Subscribe test handler
    message_bus.subscribe(test_handler, is_async=False)
    
    # Test different message types
    gif_msg = publish_gif_message("test_gif_data", {"frameCount": 10, "duration": 2.0})
    response_msg = publish_response_message("Test AI response", "Test reasoning", 1.5)
    action_msg = publish_action_message(["A", "B"], [0.5, 0.5], ["A_BUTTON", "B_BUTTON"])
    system_msg = publish_system_message("Test system message", "info")
    
    # Give time for async processing
    time.sleep(0.1)
    
    # Check results
    expected_count = 4
    actual_count = len(test_responses)
    
    if actual_count == expected_count:
        logger.info(f"✅ Message bus test passed: {actual_count}/{expected_count} messages delivered")
        return True
    else:
        logger.error(f"❌ Message bus test failed: {actual_count}/{expected_count} messages delivered")
        return False


if __name__ == "__main__":
    # Run test when module is executed directly
    test_message_bus()