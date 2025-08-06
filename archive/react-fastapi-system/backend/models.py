"""
Data models for the AI Pokemon Trainer Dashboard
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel
from enum import Enum
import time

class MessageType(str, Enum):
    GIF = "gif"
    RESPONSE = "response" 
    ACTION = "action"
    SYSTEM = "system"

class ProcessStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

class GifData(BaseModel):
    data: Optional[str] = None  # base64 encoded GIF or None if purged
    metadata: Dict[str, Any] = {
        "frameCount": 0,
        "duration": 0.0,
        "size": 0,
        "timestamp": 0.0
    }
    available: bool = True

class ResponseData(BaseModel):
    text: str
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None

class ActionData(BaseModel):
    buttons: List[str]
    durations: List[float]
    button_names: List[str] = []

class ChatMessage(BaseModel):
    id: str
    type: MessageType
    timestamp: float
    sequence: int
    content: Dict[str, Any] = {}
    
    @classmethod
    def create_gif_message(cls, gif_data: GifData, sequence: int) -> "ChatMessage":
        return cls(
            id=f"gif_{int(time.time()*1000)}",
            type=MessageType.GIF,
            timestamp=time.time(),
            sequence=sequence,
            content={"gif": gif_data.dict()}
        )
    
    @classmethod
    def create_response_message(cls, response_data: ResponseData, sequence: int) -> "ChatMessage":
        return cls(
            id=f"response_{int(time.time()*1000)}",
            type=MessageType.RESPONSE,
            timestamp=time.time(),
            sequence=sequence,
            content={"response": response_data.dict()}
        )
    
    @classmethod
    def create_action_message(cls, action_data: ActionData, sequence: int) -> "ChatMessage":
        return cls(
            id=f"action_{int(time.time()*1000)}",
            type=MessageType.ACTION,
            timestamp=time.time(),
            sequence=sequence,
            content={"action": action_data.dict()}
        )

class WebSocketMessage(BaseModel):
    type: str
    timestamp: float
    data: Dict[str, Any]

class ProcessInfo(BaseModel):
    name: str
    status: ProcessStatus
    pid: Optional[int] = None
    port: Optional[int] = None
    uptime: float = 0.0
    last_error: Optional[str] = None
    restart_count: int = 0

class SystemStatus(BaseModel):
    processes: Dict[str, ProcessInfo]
    total_messages: int
    active_connections: int
    uptime: float
    memory_usage: Optional[Dict[str, float]] = None

class KnowledgeUpdate(BaseModel):
    update_type: str  # 'task_added', 'task_completed', 'npc_learned', etc.
    content: Dict[str, Any]
    timestamp: float = time.time()

class DashboardConfig(BaseModel):
    enabled: bool = True
    port: int = 3000
    websocket_port: int = 3001
    chat_history_limit: int = 100
    gif_retention_minutes: int = 30
    auto_start_processes: bool = True
    theme: str = "pokemon"
    streaming_mode: bool = False