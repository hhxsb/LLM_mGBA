#!/usr/bin/env python3
"""
High-level storage service for Pokemon AI.
Provides transactional operations for storing complete AI cycles.
"""

import asyncio
import os
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import PIL.Image
from io import BytesIO

from .database_manager import DatabaseManager
from .data_models import (
    GameSession, AIDecision, AIAction, GameGIF, KnowledgeData, SystemMetric,
    GameState, create_session_from_config, create_decision_from_response,
    create_action_from_buttons, create_gif_from_data
)
from .logging_config import get_logger


class StorageService:
    """High-level storage operations for Pokemon AI."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("storage_service")
        
        # Initialize database manager
        storage_config = config.get('storage', {})
        db_path = storage_config.get('database_path', 'data/pokemon_ai.db')
        enable_wal = storage_config.get('wal_mode', True)
        
        # Ensure absolute path
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)
        
        self.db_manager = DatabaseManager(db_path, enable_wal)
        
        # Storage settings
        self.gif_threshold_mb = storage_config.get('gif_storage_threshold_mb', 1)
        self.compression_level = storage_config.get('compression_level', 6)
        
        # Current session tracking
        self.current_session_id: Optional[str] = None
        self.sequence_counter = 0
        
        self.logger.info(f"🗃️ Storage service initialized: {db_path}")
    
    async def initialize(self) -> None:
        """Initialize the storage service and database."""
        await self.db_manager.initialize_database()
        self.logger.info("✅ Storage service ready")
    
    async def start_session(self, game_name: str = None, player_name: str = None) -> str:
        """Start a new game session."""
        if not game_name:
            game_name = self.config.get('game', 'pokemon_red')
        
        if not player_name:
            player_name = self.config.get('player_name', 'GEMINI')
        
        initial_objective = self.config.get('initial_objective', 'Complete Pokemon Red adventure')
        
        self.current_session_id = await self.db_manager.create_session(
            game_name=game_name,
            player_name=player_name,
            initial_objective=initial_objective
        )
        
        self.sequence_counter = 0
        self.logger.info(f"🎮 Started new session: {self.current_session_id}")
        
        return self.current_session_id
    
    async def record_ai_cycle(self, decision_data: Dict[str, Any], 
                             action_data: Dict[str, Any],
                             gif_data: Optional[Dict[str, Any]] = None) -> Tuple[str, str, Optional[str]]:
        """
        Record a complete AI decision cycle (decision + action + GIF) in a single transaction.
        Returns (decision_id, action_id, gif_id).
        """
        if not self.current_session_id:
            raise ValueError("No active session. Call start_session() first.")
        
        start_time = time.time()
        
        # Prepare decision data
        self.sequence_counter += 1
        decision_data['session_id'] = self.current_session_id
        decision_data['sequence_number'] = self.sequence_counter
        
        # Prepare action data
        action_data['session_id'] = self.current_session_id
        
        try:
            # Store decision first
            decision_id = await self.db_manager.store_decision(decision_data)
            action_data['decision_id'] = decision_id
            
            # Store action
            action_id = await self.db_manager.store_action(action_data)
            
            # Store GIF if provided
            gif_id = None
            if gif_data:
                gif_data['decision_id'] = decision_id
                gif_data['session_id'] = self.current_session_id
                gif_id = await self.db_manager.store_gif(gif_data)
            
            storage_time = time.time() - start_time
            self.logger.debug(f"📸 AI cycle stored in {storage_time*1000:.1f}ms: decision={decision_id[:8]}, action={action_id[:8]}, gif={gif_id[:8] if gif_id else 'none'}")
            
            return decision_id, action_id, gif_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to record AI cycle: {e}")
            raise
    
    async def store_gif_from_pil(self, decision_id: str, gif_image: PIL.Image.Image,
                                frame_count: int, duration: float, fps: float = 30.0) -> str:
        """Store a PIL Image as GIF with automatic format handling."""
        try:
            # Convert PIL Image to bytes
            gif_buffer = BytesIO()
            
            # Save as GIF with optimization
            if hasattr(gif_image, 'is_animated') and gif_image.is_animated:
                # Animated GIF
                gif_image.save(
                    gif_buffer,
                    format='GIF',
                    save_all=True,
                    optimize=True,
                    quality=85 - (self.compression_level * 5)  # Adjust quality based on compression level
                )
            else:
                # Static image saved as GIF
                gif_image.save(
                    gif_buffer,
                    format='GIF',
                    optimize=True,
                    quality=85 - (self.compression_level * 5)
                )
            
            gif_bytes = gif_buffer.getvalue()
            original_size = len(gif_bytes)
            
            # Create GIF data dictionary
            gif_data = {
                'decision_id': decision_id,
                'session_id': self.current_session_id,
                'frame_count': frame_count,
                'duration_seconds': duration,
                'fps': fps,
                'gif_bytes': gif_bytes,
                'file_size_bytes': original_size,
                'compression_ratio': 1.0,  # Could calculate if we had original
                'visual_summary': f"Game footage: {frame_count} frames over {duration:.2f}s"
            }
            
            # Store using existing method
            gif_id = await self.db_manager.store_gif(gif_data)
            
            storage_type = "BLOB" if original_size < self.gif_threshold_mb * 1024 * 1024 else "FILE"
            self.logger.debug(f"🎥 Stored GIF as {storage_type}: {gif_id[:8]} ({original_size} bytes)")
            
            return gif_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to store PIL GIF: {e}")
            raise
    
    async def update_knowledge_base(self, knowledge_updates: List[Dict[str, Any]]) -> List[str]:
        """Update knowledge base with multiple entries."""
        knowledge_ids = []
        
        for knowledge_data in knowledge_updates:
            if not knowledge_data.get('session_id'):
                knowledge_data['session_id'] = self.current_session_id
            
            knowledge_id = await self.db_manager.store_knowledge(knowledge_data)
            knowledge_ids.append(knowledge_id)
        
        self.logger.debug(f"🧠 Updated knowledge base: {len(knowledge_ids)} entries")
        return knowledge_ids
    
    async def get_gameplay_history(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get gameplay history with optional filters."""
        if not filters:
            filters = {}
        
        session_id = filters.get('session_id', self.current_session_id)
        limit = filters.get('limit', 50)
        
        if not session_id:
            return {'decisions': [], 'session_info': {}}
        
        # Get recent decisions
        decisions = await self.db_manager.get_recent_decisions(session_id, limit)
        
        # Get session analytics
        analytics = await self.db_manager.get_session_analytics(session_id)
        
        return {
            'decisions': decisions,
            'session_info': analytics.get('session_info', {}),
            'decision_stats': analytics.get('decision_stats', {}),
            'button_usage': analytics.get('button_usage', {})
        }
    
    async def export_session_data(self, session_id: str, format: str = 'json') -> Dict[str, Any]:
        """Export complete session data in specified format."""
        if format != 'json':
            raise ValueError(f"Unsupported export format: {format}")
        
        # Get all session data
        history = await self.get_gameplay_history({'session_id': session_id, 'limit': 1000})
        
        # TODO: Add GIF data, knowledge data, metrics
        # For now, return basic structure
        
        export_data = {
            'export_metadata': {
                'session_id': session_id,
                'export_time': datetime.now().isoformat(),
                'format': format,
                'version': '1.0'
            },
            'session_info': history['session_info'],
            'decision_stats': history['decision_stats'],
            'button_usage': history['button_usage'],
            'decisions': history['decisions']
        }
        
        self.logger.info(f"📊 Exported session data: {session_id} ({len(history['decisions'])} decisions)")
        return export_data
    
    async def get_knowledge_by_type(self, knowledge_type: str, category: str = None,
                                   session_id: str = None) -> List[Dict[str, Any]]:
        """Get knowledge data by type and optional category."""
        # This would require additional database queries - implement as needed
        # For now, return empty list
        return []
    
    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up sessions older than specified days."""
        # TODO: Implement cleanup logic
        # This would involve:
        # 1. Find sessions older than days_old
        # 2. Archive or delete session data
        # 3. Clean up associated GIF files
        # 4. Update metrics
        
        self.logger.info(f"🧹 Cleanup completed (placeholder - {days_old} days)")
        return 0
    
    async def get_storage_metrics(self) -> Dict[str, Any]:
        """Get current storage system metrics."""
        try:
            # Get database file size
            db_size_bytes = os.path.getsize(self.db_manager.db_path) if os.path.exists(self.db_manager.db_path) else 0
            
            # Get basic counts (would need additional queries for full metrics)
            metrics = {
                'database_file_size_bytes': db_size_bytes,
                'database_file_size_mb': db_size_bytes / (1024 * 1024),
                'current_session_id': self.current_session_id,
                'sequence_counter': self.sequence_counter,
                'storage_config': {
                    'gif_threshold_mb': self.gif_threshold_mb,
                    'compression_level': self.compression_level,
                    'wal_mode': self.db_manager.enable_wal
                }
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get storage metrics: {e}")
            return {}
    
    async def close_current_session(self, final_status: str = "completed") -> None:
        """Close the current session."""
        if self.current_session_id:
            await self.db_manager.close_session(self.current_session_id, final_status)
            self.logger.info(f"🏁 Closed session: {self.current_session_id}")
            self.current_session_id = None
            self.sequence_counter = 0


# Utility functions for integration

async def create_storage_service_from_config(config: Dict[str, Any]) -> StorageService:
    """Create and initialize a storage service from configuration."""
    service = StorageService(config)
    await service.initialize()
    return service


def prepare_decision_data(llm_response_text: str, llm_reasoning: str, 
                         llm_raw_response: str, processing_time_ms: float,
                         game_state: Optional[Dict[str, Any]] = None,
                         conversation_context: Optional[Dict[str, Any]] = None,
                         memory_context: Optional[Dict[str, Any]] = None,
                         tutorial_step: Optional[str] = None) -> Dict[str, Any]:
    """Prepare decision data dictionary for storage."""
    return {
        'llm_response_text': llm_response_text,
        'llm_reasoning': llm_reasoning,
        'llm_raw_response': llm_raw_response,
        'processing_time_ms': processing_time_ms,
        'game_state': game_state or {},
        'map_name': game_state.get('map_name') if game_state else None,
        'player_x': game_state.get('player_x') if game_state else None,
        'player_y': game_state.get('player_y') if game_state else None,
        'conversation_context': conversation_context or {},
        'memory_context': memory_context or {},
        'tutorial_step': tutorial_step
    }


def prepare_action_data(button_codes: List[int], button_names: List[str],
                       button_durations: List[int], execution_time_ms: float = None,
                       success: bool = True, error_message: str = None) -> Dict[str, Any]:
    """Prepare action data dictionary for storage."""
    return {
        'button_codes': button_codes,
        'button_names': button_names,
        'button_durations': button_durations,
        'execution_time_ms': execution_time_ms,
        'success': success,
        'error_message': error_message
    }


def prepare_gif_data_from_pil(gif_image: PIL.Image.Image, frame_count: int,
                             duration: float, fps: float = 30.0,
                             start_timestamp: float = None,
                             end_timestamp: float = None) -> Dict[str, Any]:
    """Prepare GIF data dictionary from PIL Image."""
    return {
        'gif_image': gif_image,  # Will be processed by storage service
        'frame_count': frame_count,
        'duration_seconds': duration,
        'fps': fps,
        'start_timestamp': start_timestamp,
        'end_timestamp': end_timestamp
    }