"""
Unified message types for the Pokemon AI system.
Provides consistent message format across all processes.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Any
import time
import uuid
import json


@dataclass
class UnifiedMessage:
    """Unified message format for all system communication"""
    id: str
    type: str  # 'gif', 'response', 'action', 'system'
    timestamp: float
    source: str
    content: Dict[str, Any]
    sequence: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedMessage':
        """Create from dictionary"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UnifiedMessage':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))
    
    @classmethod
    def create_gif_message(cls, gif_data: str, metadata: Dict[str, Any], source: str = "video_capture") -> 'UnifiedMessage':
        """Create a GIF message"""
        return cls(
            id=f"gif_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            type="gif",
            timestamp=time.time(),
            source=source,
            content={
                "gif": {
                    "data": gif_data,
                    "metadata": metadata,
                    "available": True
                }
            }
        )
    
    @classmethod
    def create_response_message(cls, text: str, reasoning: str = None, processing_time: float = None, 
                              confidence: float = 0.95, source: str = "game_control") -> 'UnifiedMessage':
        """Create an AI response message"""
        return cls(
            id=f"response_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            type="response", 
            timestamp=time.time(),
            source=source,
            content={
                "response": {
                    "text": text,
                    "reasoning": reasoning,
                    "processing_time": processing_time,
                    "confidence": confidence
                }
            }
        )
    
    @classmethod
    def create_action_message(cls, buttons: List[str], durations: List[float], 
                            button_names: List[str] = None, source: str = "game_control") -> 'UnifiedMessage':
        """Create an action message"""
        return cls(
            id=f"action_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            type="action",
            timestamp=time.time(), 
            source=source,
            content={
                "action": {
                    "buttons": buttons,
                    "button_names": button_names or buttons,
                    "durations": durations
                }
            }
        )
    
    @classmethod
    def create_system_message(cls, message: str, level: str = "info", source: str = "system") -> 'UnifiedMessage':
        """Create a system message"""
        return cls(
            id=f"system_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            type="system",
            timestamp=time.time(),
            source=source,
            content={
                "system": {
                    "message": message,
                    "level": level  # 'info', 'warning', 'error'
                }
            }
        )


# Type aliases for clarity
GifMessage = UnifiedMessage
ResponseMessage = UnifiedMessage
ActionMessage = UnifiedMessage
SystemMessage = UnifiedMessage


def create_websocket_message(unified_message: UnifiedMessage) -> Dict[str, Any]:
    """Convert UnifiedMessage to WebSocket message format"""
    return {
        "type": "chat_message",
        "timestamp": unified_message.timestamp,
        "data": unified_message.to_dict()
    }


def extract_unified_message_from_websocket(ws_message: Dict[str, Any]) -> Optional[UnifiedMessage]:
    """Extract UnifiedMessage from WebSocket message format"""
    try:
        if ws_message.get("type") == "chat_message" and "data" in ws_message:
            return UnifiedMessage.from_dict(ws_message["data"])
        return None
    except Exception as e:
        print(f"❌ Error extracting unified message: {e}")
        return None


# Validation functions
def validate_gif_content(content: Dict[str, Any]) -> bool:
    """Validate GIF message content structure"""
    if "gif" not in content:
        return False
    gif_data = content["gif"]
    required_fields = ["data", "metadata", "available"]
    return all(field in gif_data for field in required_fields)


def validate_response_content(content: Dict[str, Any]) -> bool:
    """Validate response message content structure"""
    if "response" not in content:
        return False
    response_data = content["response"]
    return "text" in response_data


def validate_action_content(content: Dict[str, Any]) -> bool:
    """Validate action message content structure"""
    if "action" not in content:
        return False
    action_data = content["action"]
    required_fields = ["buttons", "durations"]
    return all(field in action_data for field in required_fields)


def validate_system_content(content: Dict[str, Any]) -> bool:
    """Validate system message content structure"""
    if "system" not in content:
        return False
    system_data = content["system"]
    required_fields = ["message", "level"]
    return all(field in system_data for field in required_fields)


def validate_unified_message(message: UnifiedMessage) -> bool:
    """Validate a unified message structure"""
    # Check required fields
    if not all([message.id, message.type, message.timestamp, message.source, message.content]):
        return False
    
    # Validate content based on type
    validators = {
        "gif": validate_gif_content,
        "response": validate_response_content,
        "action": validate_action_content,
        "system": validate_system_content
    }
    
    validator = validators.get(message.type)
    if validator:
        return validator(message.content)
    
    # Unknown type, but basic structure is valid
    return True