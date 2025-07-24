# SQLite Storage System Specification

## Overview

This specification defines a comprehensive SQLite-based storage system for persisting GIFs, AI messages, actions, and knowledge base data. The system will provide efficient storage, retrieval, and analytics capabilities while maintaining performance during gameplay.

## Objectives

### Primary Goals
- **Persistent Game History**: Store complete gameplay sessions including GIFs, AI decisions, and actions
- **Knowledge Base Persistence**: Replace JSON-based knowledge system with SQLite for better querying
- **Dashboard Analytics**: Enable historical analysis and performance tracking
- **Efficient Retrieval**: Fast queries for recent gameplay and historical analysis
- **Data Integrity**: Ensure consistent data storage across process restarts and failures

### Performance Requirements  
- **Real-time Storage**: < 50ms per GIF/message storage during gameplay
- **Concurrent Access**: Support multiple processes reading/writing simultaneously
- **Storage Efficiency**: Minimize disk space usage through compression and optimization
- **Query Performance**: < 100ms for dashboard queries and analytics

## Database Schema Design

### Core Tables

#### 1. game_sessions
```sql
CREATE TABLE game_sessions (
    session_id TEXT PRIMARY KEY,
    game_name TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NULL,
    player_name TEXT,
    initial_objective TEXT,
    final_status TEXT,
    total_decisions INTEGER DEFAULT 0,
    total_actions INTEGER DEFAULT 0,
    session_metadata JSON
);
```

#### 2. ai_decisions
```sql
CREATE TABLE ai_decisions (
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
    game_state_json JSON,
    map_name TEXT,
    player_x INTEGER,
    player_y INTEGER,
    
    -- Knowledge Context
    conversation_context JSON,
    memory_context JSON,
    tutorial_step TEXT,
    
    FOREIGN KEY (session_id) REFERENCES game_sessions(session_id)
);
```

#### 3. ai_actions
```sql
CREATE TABLE ai_actions (
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
);
```

#### 4. game_gifs
```sql
CREATE TABLE game_gifs (
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
    
    -- Storage
    gif_data BLOB, -- Compressed GIF bytes
    gif_path TEXT, -- Alternative: file system path
    file_size_bytes INTEGER,
    compression_ratio REAL,
    
    -- Visual Analysis
    visual_summary TEXT, -- AI-generated description
    key_events JSON, -- Array of detected events
    
    FOREIGN KEY (decision_id) REFERENCES ai_decisions(decision_id),
    FOREIGN KEY (session_id) REFERENCES game_sessions(session_id)
);
```

#### 5. knowledge_data
```sql
CREATE TABLE knowledge_data (
    knowledge_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Knowledge Categories
    knowledge_type TEXT NOT NULL, -- 'conversation', 'character', 'dialogue', 'tutorial', 'context'
    category TEXT, -- Subcategory within type
    
    -- Content
    data_json JSON NOT NULL,
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
);
```

#### 6. system_metrics
```sql
CREATE TABLE system_metrics (
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
    additional_data JSON,
    
    FOREIGN KEY (session_id) REFERENCES game_sessions(session_id)
);
```

### Indexes for Performance

```sql
-- Core query patterns
CREATE INDEX idx_decisions_session_sequence ON ai_decisions(session_id, sequence_number);
CREATE INDEX idx_actions_decision ON ai_actions(decision_id);
CREATE INDEX idx_gifs_decision ON game_gifs(decision_id);
CREATE INDEX idx_knowledge_session_type ON knowledge_data(session_id, knowledge_type);
CREATE INDEX idx_knowledge_active ON knowledge_data(is_active, knowledge_type);
CREATE INDEX idx_metrics_session_type ON system_metrics(session_id, metric_type);

-- Time-based queries
CREATE INDEX idx_decisions_timestamp ON ai_decisions(timestamp);
CREATE INDEX idx_sessions_start_time ON game_sessions(start_time);

-- Knowledge system queries  
CREATE INDEX idx_knowledge_category ON knowledge_data(knowledge_type, category);
CREATE INDEX idx_knowledge_npc ON knowledge_data(related_npc);
CREATE INDEX idx_knowledge_map ON knowledge_data(related_map_name);
```

## Storage Strategy

### GIF Storage Options

#### Option 1: BLOB Storage (Recommended)
- **Pros**: Single database file, transactional consistency, simple backup
- **Cons**: Larger database size, potential memory usage
- **Implementation**: Compress GIFs before storage, use prepared statements

#### Option 2: File System + Path Reference
- **Pros**: Smaller database, easier to view files directly
- **Cons**: Backup complexity, file system consistency issues
- **Implementation**: Structured directory: `/data/gifs/{session_id}/{decision_id}.gif`

#### Hybrid Approach (Recommended)
- Store small GIFs (< 1MB) as BLOBs for fast access
- Store large GIFs (> 1MB) as files with path references
- Configurable threshold based on performance testing

### Data Compression & Optimization

#### GIF Optimization
- **Pre-storage Compression**: Reduce GIF file size by 30-50%
- **Frame Optimization**: Remove duplicate frames, optimize color palettes
- **Quality Settings**: Configurable compression levels based on storage vs quality needs

#### JSON Data Optimization
- **Schema Validation**: Ensure consistent JSON structure
- **Compression**: Use JSON minification for storage
- **Indexable Fields**: Extract frequently queried JSON fields to separate columns

## Backend Implementation Architecture

### Core Components

#### 1. Database Manager (`core/database_manager.py`)
```python
class DatabaseManager:
    """Central SQLite database management."""
    
    def __init__(self, db_path: str, enable_wal: bool = True)
    async def initialize_database(self)
    async def create_session(self, game_name: str) -> str
    async def store_decision(self, decision_data: dict) -> str
    async def store_action(self, action_data: dict) -> str  
    async def store_gif(self, gif_data: dict) -> str
    async def store_knowledge(self, knowledge_data: dict) -> str
    async def get_recent_decisions(self, session_id: str, limit: int = 10)
    async def get_session_analytics(self, session_id: str)
```

#### 2. Data Access Layer (`core/data_models.py`)
```python
@dataclass
class GameSession:
    session_id: str
    game_name: str
    start_time: datetime
    # ... other fields

@dataclass  
class AIDecision:
    decision_id: str
    session_id: str
    llm_response_text: str
    # ... other fields

# Similar models for Actions, GIFs, Knowledge
```

#### 3. Storage Service (`core/storage_service.py`)
```python
class StorageService:
    """High-level storage operations."""
    
    async def record_ai_cycle(self, decision: AIDecision, actions: List[AIAction], gif: GameGIF)
    async def update_knowledge_base(self, knowledge_updates: List[KnowledgeData])
    async def get_gameplay_history(self, filters: dict)
    async def export_session_data(self, session_id: str, format: str)
```

### Integration Points

#### Game Control Process Integration
```python
# In game_control_process.py
class GameControlProcess:
    def __init__(self):
        self.storage_service = StorageService()
        self.current_session_id = None
    
    async def _make_decision_from_processed_video(self, processed_video):
        # Existing decision logic...
        decision = super()._make_decision_from_processed_video(processed_video)
        
        # 📸 Store complete AI cycle in SQLite
        await self._store_ai_cycle(decision, processed_video)
        
        return decision
    
    async def _store_ai_cycle(self, decision: dict, processed_video: dict):
        # Store decision, actions, and GIF in single transaction
        await self.storage_service.record_ai_cycle(
            decision_data=decision,
            gif_data=processed_video['gif_image'],
            game_state=self.current_game_state
        )
```

#### Knowledge System Integration
```python
# Replace JSON file persistence
class PokemonRedKnowledgeSystem:
    def __init__(self):
        self.storage_service = StorageService()
    
    async def save_conversation_state(self, state: ConversationState):
        await self.storage_service.store_knowledge({
            'knowledge_type': 'conversation',
            'data_json': state.to_dict(),
            'priority_score': 8
        })
    
    async def load_conversation_history(self, npc_name: str):
        return await self.storage_service.get_knowledge_by_category(
            'conversation', 
            related_npc=npc_name
        )
```

## Frontend Changes

### Dashboard Enhancements

#### 1. Separate Analytics Page
```typescript
// src/pages/AnalyticsPage.tsx
interface SessionAnalytics {
  totalDecisions: number;
  averageResponseTime: number;
  buttonUsageStats: Record<string, number>;
  progressOverTime: TimeSeriesData[];
  knowledgeGrowth: TimeSeriesData[];
}

const AnalyticsPage: React.FC = () => {
  const [analytics, setAnalytics] = useState<SessionAnalytics>();
  // Analytics data loaded only when user navigates to /analytics
  // Not loaded during main dashboard operation
};

// src/App.tsx - Add new route
<Route path="/analytics" component={AnalyticsPage} />
```

#### 2. Historical Playback
```typescript
// src/components/PlaybackViewer.tsx
const PlaybackViewer: React.FC = () => {
  const [sessions, setSessions] = useState<GameSession[]>();
  const [selectedDecision, setSelectedDecision] = useState<AIDecision>();
  
  // Timeline scrubber for reviewing past decisions
  // GIF playback with decision context
  // Knowledge state visualization at any point in time
};
```

#### 3. Enhanced Chat Interface
```typescript
// Update existing ChatInterface.tsx
interface ChatMessage {
  // Existing fields...
  decisionId?: string;
  sessionId?: string;
  knowledgeContext?: KnowledgeSnapshot;
  relatedGifId?: string;
}

// Add features:
// - Click GIF to see related decisions
// - Show knowledge state changes
// - Link to historical context
```

### API Extensions

#### New REST Endpoints
```python
# dashboard/backend/api/storage.py
@router.get("/sessions")
async def get_sessions(limit: int = 50):
    """Get recent gameplay sessions."""

@router.get("/sessions/{session_id}/analytics")  
async def get_session_analytics(session_id: str):
    """Get detailed analytics for a session."""

@router.get("/decisions/{decision_id}")
async def get_decision_detail(decision_id: str):
    """Get complete decision context including GIF and knowledge."""

@router.get("/knowledge/search")
async def search_knowledge(query: str, knowledge_type: str = None):
    """Search knowledge base with full-text capabilities."""

@router.post("/export")
async def export_data(request: ExportRequest):
    """Export session data in various formats (JSON, CSV, etc.)."""
```

#### WebSocket Extensions
```python
# Real-time storage status updates
@websocket.on("storage_status")
async def storage_status():
    """Stream storage metrics and database size."""

@websocket.on("knowledge_updates")  
async def knowledge_updates():
    """Stream real-time knowledge base changes."""
```

## Configuration & Settings

### Database Configuration
```json
{
  "storage": {
    "enabled": true,
    "database_path": "data/pokemon_ai.db",
    "wal_mode": true,
    "auto_vacuum": "incremental",
    "cache_size": 10000,
    "gif_storage_threshold_mb": 1,
    "compression_level": 6,
    "retention_policy": {
      "keep_sessions_days": 30,
      "archive_old_sessions": true,
      "max_database_size_gb": 5
    }
  }
}
```

### Performance Tuning
```python
# SQLite optimizations
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;  
PRAGMA cache_size = 10000;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456; # 256MB
```

## Migration & Deployment

### Phase 1: Database Setup
1. Create database schema and indexes
2. Implement core DatabaseManager with basic CRUD operations
3. Add configuration options and initialization

### Phase 2: Backend Integration  
1. Integrate storage service with game control process
2. Migrate knowledge system from JSON to SQLite
3. Clean up old JSON knowledge files (`data/knowledge_graph.json`)
4. Remove deprecated knowledge management Python files:
   - `knowledge_system.py` (replaced by games/pokemon_red/knowledge_system.py)
   - `knowledge_web_viewer.py` (web interface no longer needed)
   - `knowledge_web_manager.py` (web management no longer needed)  
   - `knowledge_manager.py` (replaced by SQLite storage)
   - `knowledge_inspector.py` (replaced by analytics page)
   - `monitor_knowledge.py` (replaced by real-time dashboard)
   - `fix_knowledge.py` (cleanup utility no longer needed)
   - `dashboard/backend/knowledge_integration.py` (replaced by storage service)
5. Add WebSocket events for storage status

### Phase 3: Frontend Features
1. Build separate analytics page at `/analytics` route
2. Add historical session viewer on analytics page
3. Enhance chat interface with storage integration

### Phase 4: Final Features
1. Data export tools for sessions
2. Performance optimization and monitoring
3. Automated cleanup and archival of old sessions

## Testing Strategy

### Unit Tests
- Database operations and transactions
- Data model validation and serialization
- Storage service methods with mocked database

### Integration Tests
- Complete AI cycle storage (decision → action → GIF)
- Knowledge system persistence and retrieval
- Dashboard API endpoints with real database

### Performance Tests
- Concurrent read/write operations
- Large GIF storage and retrieval
- Database size growth over extended gameplay sessions
- Query performance with thousands of records

### Data Integrity Tests
- Transaction rollback on failures
- Concurrent process access
- Database corruption recovery
- Migration between schema versions

## Monitoring & Maintenance

### Storage Metrics
- Database file size and growth rate
- Query execution times and performance
- Storage success/failure rates
- Knowledge base size and complexity

### Automated Maintenance
- Periodic VACUUM operations for space reclamation
- Old session archival based on retention policy
- Backup strategies for critical game progress
- Index optimization and statistics updates

---

This specification provides a comprehensive foundation for implementing persistent storage while maintaining the system's real-time performance requirements. The phased approach ensures incremental value delivery focused on core Pokemon AI gameplay enhancement and historical analysis capabilities.