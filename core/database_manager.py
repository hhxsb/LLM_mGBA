#!/usr/bin/env python3
"""
SQLite database manager for Pokemon AI storage system.
Handles database initialization, schema management, and core operations.
"""

import aiosqlite
import asyncio
import json
import os
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import logging

from .logging_config import get_logger


class DatabaseManager:
    """Central SQLite database management for Pokemon AI."""
    
    def __init__(self, db_path: str, enable_wal: bool = True):
        self.db_path = db_path
        self.enable_wal = enable_wal
        self.logger = get_logger("database_manager")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    async def initialize_database(self) -> None:
        """Initialize database with schema and optimizations."""
        self.logger.info(f"🗃️ Initializing SQLite database at {self.db_path}")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrency
            if self.enable_wal:
                await db.execute("PRAGMA journal_mode = WAL")
                self.logger.debug("📝 Enabled WAL mode for better concurrency")
            
            # Performance optimizations
            await db.execute("PRAGMA synchronous = NORMAL")
            await db.execute("PRAGMA cache_size = 10000")
            await db.execute("PRAGMA temp_store = MEMORY")
            await db.execute("PRAGMA mmap_size = 268435456")  # 256MB
            
            # Create tables
            await self._create_tables(db)
            await self._create_indexes(db)
            
            await db.commit()
            
        self.logger.info("✅ Database initialized successfully")
    
    async def _create_tables(self, db: aiosqlite.Connection) -> None:
        """Create all database tables."""
        
        # 1. Game Sessions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                session_id TEXT PRIMARY KEY,
                game_name TEXT NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP NULL,
                player_name TEXT,
                initial_objective TEXT,
                final_status TEXT,
                total_decisions INTEGER DEFAULT 0,
                total_actions INTEGER DEFAULT 0,
                session_metadata TEXT -- JSON
            )
        """)
        
        # 2. AI Decisions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_decisions (
                decision_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sequence_number INTEGER NOT NULL,
                
                -- LLM Response Data
                llm_response_text TEXT,
                llm_reasoning TEXT,
                llm_raw_response TEXT,
                processing_time_ms REAL,
                
                -- Game Context
                game_state_json TEXT, -- JSON
                map_name TEXT,
                player_x INTEGER,
                player_y INTEGER,
                
                -- Knowledge Context
                conversation_context TEXT, -- JSON
                memory_context TEXT, -- JSON
                tutorial_step TEXT,
                
                FOREIGN KEY (session_id) REFERENCES game_sessions(session_id)
            )
        """)
        
        # 3. AI Actions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_actions (
                action_id TEXT PRIMARY KEY,
                decision_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Button Actions
                button_codes TEXT, -- JSON array: [0, 4, 0]
                button_names TEXT, -- JSON array: ["A", "RIGHT", "A"]
                button_durations TEXT, -- JSON array: [2, 2, 2]
                
                -- Execution Details
                execution_time_ms REAL,
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT NULL,
                
                FOREIGN KEY (decision_id) REFERENCES ai_decisions(decision_id),
                FOREIGN KEY (session_id) REFERENCES game_sessions(session_id)
            )
        """)
        
        # 4. Game GIFs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_gifs (
                gif_id TEXT PRIMARY KEY,
                decision_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- GIF Metadata
                frame_count INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                fps REAL DEFAULT 30.0,
                start_timestamp REAL,
                end_timestamp REAL,
                
                -- Storage (hybrid approach)
                gif_data BLOB, -- For small GIFs < 1MB
                gif_path TEXT, -- For large GIFs > 1MB
                file_size_bytes INTEGER,
                compression_ratio REAL,
                
                -- Visual Analysis
                visual_summary TEXT,
                key_events TEXT, -- JSON array
                
                FOREIGN KEY (decision_id) REFERENCES ai_decisions(decision_id),
                FOREIGN KEY (session_id) REFERENCES game_sessions(session_id)
            )
        """)
        
        # 5. Knowledge Data table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_data (
                knowledge_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Knowledge Categories
                knowledge_type TEXT NOT NULL, -- 'conversation', 'character', 'dialogue', 'tutorial', 'context'
                category TEXT, -- Subcategory within type
                
                -- Content
                data_json TEXT NOT NULL, -- JSON content
                priority_score INTEGER DEFAULT 5,
                
                -- Relationships
                related_decision_id TEXT NULL,
                related_map_name TEXT NULL,
                related_npc TEXT NULL,
                
                -- Lifecycle
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                
                FOREIGN KEY (session_id) REFERENCES game_sessions(session_id),
                FOREIGN KEY (related_decision_id) REFERENCES ai_decisions(decision_id)
            )
        """)
        
        # 6. System Metrics table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                metric_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Performance Metrics
                metric_type TEXT NOT NULL, -- 'performance', 'error', 'timeline', 'resource'
                metric_name TEXT NOT NULL,
                metric_value REAL,
                metric_unit TEXT,
                
                -- Context
                process_name TEXT,
                component_name TEXT,
                additional_data TEXT, -- JSON
                
                FOREIGN KEY (session_id) REFERENCES game_sessions(session_id)
            )
        """)
        
        self.logger.debug("📊 Created all database tables")
    
    async def _create_indexes(self, db: aiosqlite.Connection) -> None:
        """Create indexes for query performance."""
        
        indexes = [
            # Core query patterns
            "CREATE INDEX IF NOT EXISTS idx_decisions_session_sequence ON ai_decisions(session_id, sequence_number)",
            "CREATE INDEX IF NOT EXISTS idx_actions_decision ON ai_actions(decision_id)",
            "CREATE INDEX IF NOT EXISTS idx_gifs_decision ON game_gifs(decision_id)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_session_type ON knowledge_data(session_id, knowledge_type)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_active ON knowledge_data(is_active, knowledge_type)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_session_type ON system_metrics(session_id, metric_type)",
            
            # Time-based queries
            "CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON ai_decisions(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON game_sessions(start_time)",
            
            # Knowledge system queries
            "CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_data(knowledge_type, category)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_npc ON knowledge_data(related_npc)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_map ON knowledge_data(related_map_name)",
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)
            
        self.logger.debug("🔍 Created database indexes for performance")
    
    async def create_session(self, game_name: str, player_name: str = None, 
                           initial_objective: str = None) -> str:
        """Create a new game session and return session_id."""
        session_id = f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO game_sessions 
                (session_id, game_name, player_name, initial_objective, session_metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id, 
                game_name, 
                player_name, 
                initial_objective,
                json.dumps({"created_by": "pokemon_ai", "version": "1.0"})
            ))
            await db.commit()
        
        self.logger.info(f"🎮 Created new game session: {session_id}")
        return session_id
    
    async def store_decision(self, decision_data: Dict[str, Any]) -> str:
        """Store an AI decision and return decision_id."""
        decision_id = f"decision_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO ai_decisions (
                    decision_id, session_id, sequence_number, llm_response_text,
                    llm_reasoning, llm_raw_response, processing_time_ms,
                    game_state_json, map_name, player_x, player_y,
                    conversation_context, memory_context, tutorial_step
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision_id,
                decision_data.get('session_id'),
                decision_data.get('sequence_number', 0),
                decision_data.get('llm_response_text'),
                decision_data.get('llm_reasoning'),
                decision_data.get('llm_raw_response'),
                decision_data.get('processing_time_ms'),
                json.dumps(decision_data.get('game_state', {})),
                decision_data.get('map_name'),
                decision_data.get('player_x'),
                decision_data.get('player_y'),
                json.dumps(decision_data.get('conversation_context', {})),
                json.dumps(decision_data.get('memory_context', {})),
                decision_data.get('tutorial_step')
            ))
            
            # Update session decision count
            await db.execute("""
                UPDATE game_sessions 
                SET total_decisions = total_decisions + 1
                WHERE session_id = ?
            """, (decision_data.get('session_id'),))
            
            await db.commit()
        
        self.logger.debug(f"💭 Stored AI decision: {decision_id}")
        return decision_id
    
    async def store_action(self, action_data: Dict[str, Any]) -> str:
        """Store an AI action and return action_id."""
        action_id = f"action_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO ai_actions (
                    action_id, decision_id, session_id, button_codes,
                    button_names, button_durations, execution_time_ms,
                    success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action_id,
                action_data.get('decision_id'),
                action_data.get('session_id'),
                json.dumps(action_data.get('button_codes', [])),
                json.dumps(action_data.get('button_names', [])),
                json.dumps(action_data.get('button_durations', [])),
                action_data.get('execution_time_ms'),
                action_data.get('success', True),
                action_data.get('error_message')
            ))
            
            # Update session action count
            await db.execute("""
                UPDATE game_sessions 
                SET total_actions = total_actions + 1
                WHERE session_id = ?
            """, (action_data.get('session_id'),))
            
            await db.commit()
        
        self.logger.debug(f"🎮 Stored AI action: {action_id}")
        return action_id
    
    async def store_gif(self, gif_data: Dict[str, Any]) -> str:
        """Store a GIF (BLOB or file path) and return gif_id."""
        gif_id = f"gif_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        # Determine storage method based on size (1MB threshold)
        gif_bytes = gif_data.get('gif_bytes')
        file_size = len(gif_bytes) if gif_bytes else 0
        use_blob_storage = file_size < 1024 * 1024  # 1MB threshold
        
        async with aiosqlite.connect(self.db_path) as db:
            if use_blob_storage and gif_bytes:
                # Store as BLOB
                await db.execute("""
                    INSERT INTO game_gifs (
                        gif_id, decision_id, session_id, frame_count, duration_seconds,
                        fps, start_timestamp, end_timestamp, gif_data, gif_path,
                        file_size_bytes, compression_ratio, visual_summary, key_events
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    gif_id,
                    gif_data.get('decision_id'),
                    gif_data.get('session_id'),
                    gif_data.get('frame_count'),
                    gif_data.get('duration_seconds'),
                    gif_data.get('fps', 30.0),
                    gif_data.get('start_timestamp'),
                    gif_data.get('end_timestamp'),
                    gif_bytes,  # Store as BLOB
                    None,  # No file path
                    file_size,
                    gif_data.get('compression_ratio', 1.0),
                    gif_data.get('visual_summary'),
                    json.dumps(gif_data.get('key_events', []))
                ))
                self.logger.debug(f"💾 Stored GIF as BLOB: {gif_id} ({file_size} bytes)")
            else:
                # Store as file path
                gif_path = gif_data.get('gif_path')
                await db.execute("""
                    INSERT INTO game_gifs (
                        gif_id, decision_id, session_id, frame_count, duration_seconds,
                        fps, start_timestamp, end_timestamp, gif_data, gif_path,
                        file_size_bytes, compression_ratio, visual_summary, key_events
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    gif_id,
                    gif_data.get('decision_id'),
                    gif_data.get('session_id'),
                    gif_data.get('frame_count'),
                    gif_data.get('duration_seconds'),
                    gif_data.get('fps', 30.0),
                    gif_data.get('start_timestamp'),
                    gif_data.get('end_timestamp'),
                    None,  # No BLOB data
                    gif_path,  # Store file path
                    file_size,
                    gif_data.get('compression_ratio', 1.0),
                    gif_data.get('visual_summary'),
                    json.dumps(gif_data.get('key_events', []))
                ))
                self.logger.debug(f"📁 Stored GIF as file: {gif_id} ({gif_path})")
            
            await db.commit()
        
        return gif_id
    
    async def store_knowledge(self, knowledge_data: Dict[str, Any]) -> str:
        """Store knowledge data and return knowledge_id."""
        knowledge_id = f"knowledge_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO knowledge_data (
                    knowledge_id, session_id, knowledge_type, category,
                    data_json, priority_score, related_decision_id,
                    related_map_name, related_npc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                knowledge_id,
                knowledge_data.get('session_id'),
                knowledge_data.get('knowledge_type'),
                knowledge_data.get('category'),
                json.dumps(knowledge_data.get('data', {})),
                knowledge_data.get('priority_score', 5),
                knowledge_data.get('related_decision_id'),
                knowledge_data.get('related_map_name'),
                knowledge_data.get('related_npc')
            ))
            await db.commit()
        
        self.logger.debug(f"🧠 Stored knowledge: {knowledge_id} ({knowledge_data.get('knowledge_type')})")
        return knowledge_id
    
    async def get_recent_decisions(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent decisions for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM ai_decisions 
                WHERE session_id = ? 
                ORDER BY sequence_number DESC 
                LIMIT ?
            """, (session_id, limit))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get analytics data for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Basic session info
            cursor = await db.execute("""
                SELECT * FROM game_sessions WHERE session_id = ?
            """, (session_id,))
            session_row = await cursor.fetchone()
            
            if not session_row:
                return {}
            
            # Decision count and timing
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as decision_count,
                    AVG(processing_time_ms) as avg_processing_time,
                    MIN(processing_time_ms) as min_processing_time,
                    MAX(processing_time_ms) as max_processing_time
                FROM ai_decisions 
                WHERE session_id = ?
            """, (session_id,))
            decision_stats = await cursor.fetchone()
            
            # Button usage stats
            cursor = await db.execute("""
                SELECT button_names FROM ai_actions WHERE session_id = ?
            """, (session_id,))
            action_rows = await cursor.fetchall()
            
            button_counts = {}
            for row in action_rows:
                if row[0]:  # button_names JSON
                    buttons = json.loads(row[0])
                    for button in buttons:
                        button_counts[button] = button_counts.get(button, 0) + 1
            
            return {
                'session_info': dict(session_row) if session_row else {},
                'decision_stats': dict(decision_stats) if decision_stats else {},
                'button_usage': button_counts
            }
    
    async def close_session(self, session_id: str, final_status: str = "completed") -> None:
        """Mark a session as completed."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE game_sessions 
                SET end_time = CURRENT_TIMESTAMP, final_status = ?
                WHERE session_id = ?
            """, (final_status, session_id))
            await db.commit()
        
        self.logger.info(f"🏁 Closed session: {session_id} ({final_status})")