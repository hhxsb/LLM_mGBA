#!/usr/bin/env python3
"""
Data models for Pokemon AI SQLite storage system.
Provides structured data classes with serialization support.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json
import time


@dataclass
class GameSession:
    """Represents a complete game session."""
    session_id: str
    game_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    player_name: Optional[str] = None
    initial_objective: Optional[str] = None
    final_status: Optional[str] = None
    total_decisions: int = 0
    total_actions: int = 0
    session_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameSession':
        """Create from dictionary (database row)."""
        # Convert ISO strings back to datetime objects
        if data.get('start_time'):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data.get('end_time'):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        
        # Parse JSON metadata if string
        if isinstance(data.get('session_metadata'), str):
            data['session_metadata'] = json.loads(data['session_metadata'])
        
        return cls(**data)


@dataclass
class GameState:
    """Represents game state at a point in time."""
    map_id: int
    player_x: int
    player_y: int
    facing_direction: int
    map_name: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameState':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AIDecision:
    """Represents an AI decision with full context."""
    decision_id: str
    session_id: str
    timestamp: datetime
    sequence_number: int
    
    # LLM Response Data
    llm_response_text: Optional[str] = None
    llm_reasoning: Optional[str] = None
    llm_raw_response: Optional[str] = None
    processing_time_ms: Optional[float] = None
    
    # Game Context
    game_state: Optional[GameState] = None
    map_name: Optional[str] = None
    player_x: Optional[int] = None
    player_y: Optional[int] = None
    
    # Knowledge Context
    conversation_context: Dict[str, Any] = field(default_factory=dict)
    memory_context: Dict[str, Any] = field(default_factory=dict)
    tutorial_step: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        
        # Handle datetime
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        
        # Handle nested GameState
        if self.game_state:
            data['game_state_json'] = self.game_state.to_dict()
        else:
            data['game_state_json'] = {}
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIDecision':
        """Create from dictionary (database row)."""
        # Convert ISO string back to datetime
        if data.get('timestamp'):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        # Parse JSON fields if strings
        if isinstance(data.get('game_state_json'), str):
            game_state_data = json.loads(data['game_state_json'])
            data['game_state'] = GameState.from_dict(game_state_data) if game_state_data else None
        
        if isinstance(data.get('conversation_context'), str):
            data['conversation_context'] = json.loads(data['conversation_context'])
        
        if isinstance(data.get('memory_context'), str):
            data['memory_context'] = json.loads(data['memory_context'])
        
        # Remove JSON field since we converted it to object
        data.pop('game_state_json', None)
        
        return cls(**data)


@dataclass
class AIAction:
    """Represents an executed AI action."""
    action_id: str
    decision_id: str
    session_id: str
    timestamp: datetime
    
    # Button Actions
    button_codes: List[int] = field(default_factory=list)
    button_names: List[str] = field(default_factory=list)
    button_durations: List[int] = field(default_factory=list)
    
    # Execution Details
    execution_time_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        
        # Handle datetime
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIAction':
        """Create from dictionary (database row)."""
        # Convert ISO string back to datetime
        if data.get('timestamp'):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        # Parse JSON arrays if strings
        if isinstance(data.get('button_codes'), str):
            data['button_codes'] = json.loads(data['button_codes'])
        
        if isinstance(data.get('button_names'), str):
            data['button_names'] = json.loads(data['button_names'])
        
        if isinstance(data.get('button_durations'), str):
            data['button_durations'] = json.loads(data['button_durations'])
        
        return cls(**data)


@dataclass
class GameGIF:
    """Represents a stored game GIF with metadata."""
    gif_id: str
    decision_id: str
    session_id: str
    timestamp: datetime
    
    # GIF Metadata
    frame_count: int
    duration_seconds: float
    fps: float = 30.0
    start_timestamp: Optional[float] = None
    end_timestamp: Optional[float] = None
    
    # Storage (hybrid approach)
    gif_data: Optional[bytes] = None  # For BLOB storage
    gif_path: Optional[str] = None    # For file storage
    file_size_bytes: int = 0
    compression_ratio: float = 1.0
    
    # Visual Analysis
    visual_summary: Optional[str] = None
    key_events: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        
        # Handle datetime
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        
        # Convert bytes to base64 for JSON serialization if needed
        if self.gif_data and isinstance(self.gif_data, bytes):
            import base64
            data['gif_data_base64'] = base64.b64encode(self.gif_data).decode('utf-8')
            data.pop('gif_data', None)  # Remove binary data from dict
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameGIF':
        """Create from dictionary (database row)."""
        # Convert ISO string back to datetime
        if data.get('timestamp'):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        # Parse JSON array if string
        if isinstance(data.get('key_events'), str):
            data['key_events'] = json.loads(data['key_events'])
        
        # Handle base64 encoded GIF data
        if data.get('gif_data_base64'):
            import base64
            data['gif_data'] = base64.b64decode(data['gif_data_base64'])
            data.pop('gif_data_base64', None)
        
        return cls(**data)
    
    @property
    def storage_type(self) -> str:
        """Return storage type: 'blob' or 'file'."""
        if self.gif_data:
            return 'blob'
        elif self.gif_path:
            return 'file'
        else:
            return 'none'
    
    @property
    def is_large_gif(self) -> bool:
        """Check if GIF is considered large (> 1MB)."""
        return self.file_size_bytes > 1024 * 1024


@dataclass
class KnowledgeData:
    """Represents stored knowledge data."""
    knowledge_id: str
    session_id: str
    timestamp: datetime
    
    # Knowledge Categories
    knowledge_type: str  # 'conversation', 'character', 'dialogue', 'tutorial', 'context'
    category: Optional[str] = None
    
    # Content
    data: Dict[str, Any] = field(default_factory=dict)
    priority_score: int = 5
    
    # Relationships
    related_decision_id: Optional[str] = None
    related_map_name: Optional[str] = None
    related_npc: Optional[str] = None
    
    # Lifecycle
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data_dict = asdict(self)
        
        # Handle datetime objects
        for field_name in ['timestamp', 'created_at', 'updated_at']:
            if data_dict.get(field_name):
                data_dict[field_name] = data_dict[field_name].isoformat()
        
        return data_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeData':
        """Create from dictionary (database row)."""
        # Convert ISO strings back to datetime objects
        for field_name in ['timestamp', 'created_at', 'updated_at']:
            if data.get(field_name):
                data[field_name] = datetime.fromisoformat(data[field_name])
        
        # Parse JSON data if string
        if isinstance(data.get('data_json'), str):
            data['data'] = json.loads(data['data_json'])
            data.pop('data_json', None)
        elif data.get('data_json'):
            data['data'] = data['data_json']
            data.pop('data_json', None)
        
        return cls(**data)


@dataclass 
class SystemMetric:
    """Represents a system performance metric."""
    metric_id: str
    session_id: str
    timestamp: datetime
    
    # Performance Metrics
    metric_type: str  # 'performance', 'error', 'timeline', 'resource'
    metric_name: str
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    
    # Context
    process_name: Optional[str] = None
    component_name: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        
        # Handle datetime
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemMetric':
        """Create from dictionary (database row)."""
        # Convert ISO string back to datetime
        if data.get('timestamp'):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        # Parse JSON data if string
        if isinstance(data.get('additional_data'), str):
            data['additional_data'] = json.loads(data['additional_data'])
        
        return cls(**data)


# Utility functions for common operations

def create_session_from_config(config: Dict[str, Any]) -> GameSession:
    """Create a GameSession from configuration data."""
    return GameSession(
        session_id=f"session_{int(time.time() * 1000)}",
        game_name=config.get('game', 'unknown'),
        start_time=datetime.now(),
        player_name=config.get('player_name', 'GEMINI'),
        initial_objective=config.get('initial_objective', 'Complete Pokemon Red'),
        session_metadata={
            'config_version': config.get('version', '1.0'),
            'debug_mode': config.get('debug_mode', False),
            'dual_process_mode': config.get('dual_process_mode', {}).get('enabled', False)
        }
    )


def create_decision_from_response(session_id: str, sequence_number: int, 
                                 llm_response: str, game_state: Optional[GameState] = None,
                                 processing_time: Optional[float] = None) -> AIDecision:
    """Create an AIDecision from LLM response data."""
    return AIDecision(
        decision_id=f"decision_{int(time.time() * 1000)}",
        session_id=session_id,
        timestamp=datetime.now(),
        sequence_number=sequence_number,
        llm_response_text=llm_response,
        game_state=game_state,
        processing_time_ms=processing_time,
        map_name=game_state.map_name if game_state else None,
        player_x=game_state.player_x if game_state else None,
        player_y=game_state.player_y if game_state else None
    )


def create_action_from_buttons(decision_id: str, session_id: str,
                              button_codes: List[int], button_names: List[str],
                              button_durations: List[int]) -> AIAction:
    """Create an AIAction from button data."""
    return AIAction(
        action_id=f"action_{int(time.time() * 1000)}",
        decision_id=decision_id,
        session_id=session_id,
        timestamp=datetime.now(),
        button_codes=button_codes,
        button_names=button_names,
        button_durations=button_durations
    )


def create_gif_from_data(decision_id: str, session_id: str, gif_bytes: bytes,
                        frame_count: int, duration: float, fps: float = 30.0) -> GameGIF:
    """Create a GameGIF from raw GIF data."""
    return GameGIF(
        gif_id=f"gif_{int(time.time() * 1000)}",
        decision_id=decision_id,
        session_id=session_id,
        timestamp=datetime.now(),
        frame_count=frame_count,
        duration_seconds=duration,
        fps=fps,
        gif_data=gif_bytes if len(gif_bytes) < 1024 * 1024 else None,  # 1MB threshold
        gif_path=None,  # Will be set by storage service if needed
        file_size_bytes=len(gif_bytes),
        compression_ratio=1.0
    )