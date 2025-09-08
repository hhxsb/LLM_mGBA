# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI GBA Player** is a universal AI gaming framework that enables Large Language Models to play Game Boy Advance games through visual understanding and decision-making. The system features a modern Django web interface with real-time chat monitoring for AI gameplay.

**Based on**: [martoast/LLM-Pokemon-Red](https://github.com/martoast/LLM-Pokemon-Red) - Original Pokémon Red AI benchmark

**Key Innovations**: 
- **Simplified Architecture** - Single Django process with integrated AI service
- **Real-time Chat Interface** - Monitor AI decisions, screenshots, and actions in real-time
- **Universal Game Support** - Works with any GBA game, not just Pokémon
- **Web-based Configuration** - No manual JSON editing, all settings via browser
- **Socket Communication** - Direct TCP connection between mGBA and AI service
- **Database Storage** - SQLite for configuration, no complex file management

## Core Architecture

### Simple Two-Layer System
1. **mGBA Emulator + Lua Script** (`emulator/script.lua`) - Game interface layer
2. **AI GBA Player Web Interface** (`ai_gba_player/`) - Django web app with integrated AI service

### Data Flow
```
mGBA → Lua Script → Socket (Port 8888) → AIGameService → LLM API → Button Commands → Back to mGBA
                                     ↓
                            Real-time Chat Interface
                         (Screenshots, AI Responses, Actions)
```

The system uses a **simplified single-process architecture** with direct socket communication, real-time chat monitoring, and database-driven configuration.

## Key Commands

### Running the AI GBA Player
```bash
# Start the web interface (MAIN COMMAND)
cd ai_gba_player
python manage.py runserver

# Access the web interface
# Open browser to: http://localhost:8000
```

### Setup Sequence (SIMPLE)
1. Start web interface: `cd ai_gba_player && python manage.py runserver`
2. Configure ROM, mGBA, and AI settings at http://localhost:8000
3. Click "Launch mGBA" or start mGBA manually
4. Click "Reset mGBA Connection" to start AI service
5. In mGBA: Tools > Script Viewer > Load `emulator/script.lua`
6. Watch AI play in real-time chat interface

### Testing Components
```bash
# Test AI service communication
python dev-tools/test-scripts/test_ai_service.py

# Test Django app with comprehensive unit tests
cd ai_gba_player
python manage.py test

# Test enhanced memory system
python manage.py test dashboard.tests.test_graphiti_memory
python manage.py test dashboard.tests.test_memory_service

# Test game detection and Sapphire support
python dev-tools/test-scripts/test_game_detection.py
python dev-tools/test-scripts/test_final_sapphire_flow.py

# Test memory system APIs (while Django server is running)
curl -X POST http://localhost:8000/api/restart-service/
curl http://localhost:8000/api/chat-messages/
curl -X POST http://localhost:8000/api/memory-config/test/
curl -X POST http://localhost:8000/api/memory-config/reset/

# Memory debugging tools (load in mGBA Script Viewer)
# Load these files in mGBA Tools > Script Viewer:
# - dev-tools/memory-debugging/simple_sapphire_memory_finder.lua
# - dev-tools/memory-debugging/find_sapphire_direction.lua
```

## Project Structure (Updated)

### Active Components (Used by `python manage.py runserver`)
```
ai_gba_player/                     # Django web application (MAIN)
├── manage.py                      # Django management command entry point
├── ai_gba_player/                 # Django project settings directory
│   ├── settings.py                # Django configuration (apps, database, paths)
│   ├── urls.py                    # Main URL routing (includes API endpoints)
│   ├── simple_views.py            # PRIMARY VIEW LAYER - embedded HTML + API endpoints
│   ├── wsgi.py                    # WSGI application server entry point
│   └── asgi.py                    # ASGI application server entry point (unused)
├── dashboard/                     # Primary Django app - ALL core functionality
│   ├── ai_game_service.py         # CORE: AI service (socket server + LLM integration)
│   ├── llm_client.py              # CORE: Multi-provider LLM API client 
│   ├── game_detector.py           # Game detection and configuration
│   ├── models.py                  # Database models (Configuration, Process, etc.)
│   ├── static/dashboard/          # CSS/JS for web interface
│   │   ├── css/dashboard.css      # Main dashboard styling
│   │   └── js/dashboard.js        # Frontend JavaScript (chat polling)
│   └── migrations/                # Database schema migrations
├── core/                          # Enhanced Memory System (UPDATED)
│   ├── graphiti_memory.py         # Enterprise-grade temporal knowledge graph with:
│   │                              #   - Temporal reasoning & bi-temporal tracking
│   │                              #   - Pokemon/Battle/Location entity relationships
│   │                              #   - Semantic search & hybrid retrieval
│   │                              #   - Multi-provider LLM support (Gemini/OpenAI)
│   └── memory_service.py          # Global memory service with intelligent fallback
├── db.sqlite3                     # SQLite database (configuration + process state)
├── media/uploads/roms/            # ROM file uploads directory
└── staticfiles/                   # Collected static files (Django admin + custom)

emulator/
└── script.lua                     # mGBA Lua script for game control (TCP socket communication)

data/                              # AI memory and game state
├── notepad.txt                    # Simple text-based AI memory log
├── prompt_template.txt            # Optimized LLM prompt template
└── screenshots/                   # Game screenshots for AI analysis
```

### Development/Testing Components (Not part of main program)
```
dev-tools/                         # ⚠️  Development utilities only (not part of main program)
docs/                              # ⚠️  Documentation only  
test_*.py                          # ⚠️  Integration test files (root level)
```

## Actual Architecture (How `python manage.py runserver` Works)

### Django Application Structure
The main program follows a **simplified single-file approach**:

**1. Entry Point**: `ai_gba_player/manage.py`
- Standard Django management command entry point
- Sets `DJANGO_SETTINGS_MODULE = 'ai_gba_player.settings'`

**2. Django Project**: `ai_gba_player/ai_gba_player/`
- `settings.py`: Configures Django apps, database, static files
- `urls.py`: Routes all URLs to views in `simple_views.py` 
- `simple_views.py`: **CORE IMPLEMENTATION** - contains all views and API endpoints

**3. Main App**: `ai_gba_player/dashboard/`
- `ai_game_service.py`: Socket server + AI decision engine
- `llm_client.py`: Multi-provider LLM API wrapper
- `models.py`: Database models for configuration storage

### Key Design Decisions

**Embedded HTML Approach**: 
- All HTML/CSS/JS embedded directly in `simple_views.py`
- No separate template files needed
- Eliminates template loading complexity
- Single-file contains complete UI + API

**File-Based Configuration Fallback**:
- Primary: SQLite database via Django models  
- Secondary: `/tmp/ai_gba_player_config.json` for simple storage
- Auto-updates main `config_emulator.json` when needed

**Direct Socket Communication**:
- AI service runs as daemon thread from Django
- Direct TCP socket on port 8888 for mGBA communication
- No complex message queues or inter-process communication

## Configuration System

### Database Configuration (Primary)
All settings stored in SQLite database via Django models:
- **Configuration model**: LLM provider, API keys, cooldown settings
- **Process model**: Service status tracking
- **Web interface**: Configure everything through browser at http://localhost:8000

### JSON Configuration (Legacy/Auto-updated)
`config_emulator.json` - Automatically updated when saving AI settings through web interface

### No Manual Configuration Required
- ROM path: Set via web interface
- mGBA path: Auto-detected or set via web interface  
- API keys: Entered securely via web interface
- All settings persist in SQLite database

## Graphiti Memory System (ENHANCED)

### Enterprise-Grade AI Memory
The AI GBA Player features an advanced **Graphiti-powered temporal knowledge graph** that provides:

### 🕐 **Temporal Reasoning** (NEW)
- **Bi-temporal Tracking**: Records when events occurred vs. when they were discovered
- **Progression Analysis**: Tracks Pokemon level changes, location visit patterns over time
- **Strategy Evolution**: Monitors how strategy success rates change across gameplay sessions
- **Recency Scoring**: Recent events weighted higher in decision-making
- **Age-aware Context**: "Found Pikachu 2 hours ago at Route 1" vs "Caught Charizard yesterday"

### 🔗 **Rich Entity Relationships** (NEW)
- **Pokemon ↔ Location Mapping**: "Pikachu commonly found at Route 1 (85% encounter rate)"
- **Battle ↔ Strategy Connections**: Links successful battle outcomes to specific button sequences
- **Player ↔ Pokemon Ownership**: Tracks caught Pokemon with capture time and location
- **Location ↔ Item Discovery**: Maps items and NPCs to specific locations
- **Temporal Relationships**: Relationships have validity periods and strength scores

### 🧠 **Semantic Memory Search** (NEW)  
- **Hybrid Search**: Combines semantic embeddings, keyword matching, and graph traversal
- **Contextual Strategy Retrieval**: "Find strategies similar to current battle situation"
- **Location Intelligence**: "What Pokemon are found here? What strategies work?"
- **Pattern Recognition**: Identifies successful gameplay patterns across different contexts
- **Smart Suggestions**: Context-aware discovery recommendations

### 🎮 **Game-Specific Knowledge** (NEW)
- **Pokemon Encounters**: `record_pokemon_encounter()` with species, level, location, catch status
- **Battle Outcomes**: `record_battle_outcome()` with opponent type, strategy used, win/loss
- **Location Insights**: Tracks Pokemon frequency, successful strategies per location
- **Team Composition**: Monitors party changes and battle performance

### 🎯 **Enhanced Objective Discovery**
- **Context-Rich Discovery**: Includes session ID, player level, game time
- **Multi-Category Objectives**: Main story, side quests, exploration, collection
- **Priority-Based Ranking**: Critical (9), High (7), Normal (5) priority levels
- **Temporal Context**: "Discovered 30 minutes ago" vs "Long-term goal"

### 📊 **Advanced Memory Context**
LLM receives comprehensive context in every decision:
```yaml
current_objectives:
  - description: "Find Pokemon Center to heal team"
    priority: 6
    time_since_discovery: "30 minutes ago"
    
relevant_strategies:
  - situation: "navigating to Pokemon Center"
    buttons: ["UP", "UP", "A"]
    success_rate: "92.3%"
    source: "semantic_search"
    
location_insights:
  pokemon_found: ["Rattata", "Pidgey", "Caterpie"]
  success_strategies:
    - situation: "catching wild Pokemon"
      success_rate: 0.85
      
pokemon_knowledge:
  recently_encountered:
    - pokemon: "Pikachu"
      location: "Route 1" 
      time_ago: "2 hours ago"
      
temporal_patterns:
  success_patterns:
    - strategy: "A spam for dialogue"
      usage_frequency: 15
      last_successful: "just now"
```
```
## 🎯 Current Objectives:
  🔥 Defeat Team Rocket leader (Priority: 9)
  ⭐ Find Pokemon Center to heal team (Priority: 6)

## 🧠 Learned Strategies:
  💡 talking to npc: [A, A, B] (Success: 85.7%)
  💡 navigating menu: [START, UP, A] (Success: 92.3%)
```

### Installation & Configuration
```bash
# Enhanced Graphiti with Google Gemini support (v0.20.2+)
pip install "graphiti-core[google-genai]" --upgrade
pip install neo4j>=5.0.0

# Verify installation
python -c "from graphiti_core.llm_client.gemini_client import GeminiClient; print('✅ Graphiti + Gemini ready')"

# Auto-fallback to SimpleMemorySystem if dependencies unavailable
```

### Multi-Provider Configuration
The memory system supports multiple LLM providers:

**Google Gemini (Recommended)**:
- Full native support via `graphiti-core[google-genai]`
- Models: `gemini-2.0-flash`, `embedding-001`, `gemini-2.5-flash-lite-preview-06-17`
- Best performance and cost efficiency

**OpenAI**: 
- Standard support via environment variable
- Models: GPT-4o, text-embedding-3-small
- Requires `OPENAI_API_KEY`

**Configuration via Web Interface**:
1. Navigate to http://localhost:8000
2. Expand "🧠 Memory System Configuration"
3. Choose system type: Auto-detect (recommended), Graphiti, or Simple
4. Configure LLM provider: Inherit from AI Settings or use separate API keys
5. Set Neo4j database connection (bolt://localhost:7687)
6. Test connections and reset memory system

### Architecture Integration
- **Enhanced Discovery**: `ai_gba_player/dashboard/ai_game_service.py` calls `record_pokemon_encounter()`, `record_battle_outcome()`
- **Semantic Context**: `ai_gba_player/core/graphiti_memory.py` provides `get_memory_context()` with temporal analysis
- **Multi-dimensional Memory**: Pokemon knowledge, location insights, temporal patterns, strategy evolution
- **Web Configuration**: Full memory system management via browser interface

### Performance Characteristics
- **P95 Latency**: ~300ms for memory retrieval (following Graphiti benchmarks)
- **Hybrid Search**: Semantic + keyword + graph traversal for comprehensive results
- **Temporal Optimization**: Recent events weighted higher, recency scoring
- **Real-time Updates**: Incremental knowledge graph updates without batch recomputation
- **Graceful Fallback**: Auto-switches to SimpleMemorySystem if Graphiti fails

### Benefits
- **Enterprise-Grade Memory**: Temporal knowledge graphs rival the latest AI agent architectures
- **Self-Improving Gameplay**: AI becomes more skilled through experience and pattern recognition
- **Multi-Session Learning**: Knowledge persists across gameplay sessions
- **Location Intelligence**: Learns optimal strategies for specific game areas
- **Pokemon Expertise**: Builds comprehensive knowledge of species, locations, battle strategies

## Prompt Optimization System

### Optimized LLM Communication
The system uses a **highly optimized prompt template** for efficient LLM communication:

- **Token Reduction**: ~906 tokens (down from ~1,200+ tokens) = **25% reduction**
- **File-based Templates**: `data/prompt_template.txt` with hot-reload capability
- **Dynamic Context**: Spatial awareness and game state injected dynamically
- **Cost Optimization**: Fewer tokens = faster responses and lower API costs

### Template Variables
```
{spatial_context}     - Dynamic location and navigation info
{recent_actions}      - Player's recent button presses  
{direction_guidance}  - Movement suggestions and context
{memory_context}      - Enhanced Graphiti memory context (NEW)
{notepad_content}     - Simple fallback memory and game progress
```

### Enhanced Memory Context Variables (NEW)
```yaml
{memory_context} includes:
  current_objectives:    # Active goals with priorities and temporal context
  recent_achievements:   # Completed objectives with timestamps
  relevant_strategies:   # Context-aware strategy recommendations
  location_insights:     # Pokemon frequency and successful strategies for current area
  pokemon_knowledge:     # Recent encounters and battle patterns
  temporal_patterns:     # Success patterns and usage frequency analysis
  discovery_suggestions: # Context-aware recommendations for next actions
```

### Hot-Reload Support
- Template changes detected automatically
- No service restart required for prompt updates
- Real-time prompt optimization during development

## AI Service Architecture

### AIGameService (`dashboard/ai_game_service.py`)
Single-threaded service that combines:
- **Socket Server**: Listens on port 8888 for mGBA connections
- **AI Decision Processing**: Sends screenshots to LLM and gets decisions
- **Chat Message Storage**: Stores messages for real-time web interface
- **Error Handling**: Graceful fallbacks when LLM calls fail

### LLMClient (`dashboard/llm_client.py`)
Handles API calls to different LLM providers:
- **Google Gemini**: Primary provider with function calling
- **OpenAI**: GPT-4o with vision and tools
- **Anthropic**: Claude models (future support)
- **Error Recovery**: Timeout handling and fallback responses

### Real-time Chat Interface
- **Message Types**: System, screenshot, AI response
- **Polling**: Frontend polls `/api/chat-messages/` every 2 seconds
- **Message Storage**: In-memory buffer with 100 message limit
- **Auto-scroll**: Automatic scrolling to latest messages

## Communication Architecture

### Socket Communication
- **mGBA ↔ AI Service**: TCP Socket (Port 8888)
- **Protocol**: Text-based messages (ready, screenshot_data, button commands)
- **Connection Management**: Automatic reconnection handling

### Web Interface Communication  
- **Frontend ↔ Backend**: HTTP API endpoints
- **Real-time Updates**: Polling-based (foundation for future WebSocket upgrade)
- **Configuration**: POST endpoints for saving settings
- **Status**: GET endpoints for service status and messages

### Message Protocol
```
mGBA → AI Service: "ready"
mGBA → AI Service: "screenshot_data|/path/to/screenshot.png|x|y|direction|mapId"
AI Service → mGBA: "request_screenshot"
AI Service → mGBA: "0,1,4" (button codes: A,B,RIGHT)
```

## LLM Integration

### Tool-Based Architecture
- **`press_button`**: Execute game controls with button arrays
- **Function Calling**: Both Google Gemini and OpenAI support tool calling
- **Error Recovery**: Fallback actions when LLM requests fail

### Context Processing
- **Screenshot Analysis**: LLM analyzes PNG images of game state
- **Game State Context**: Position, direction, map ID provided to LLM
- **Prompt Templates**: Game-specific prompts for better decision-making
- **Response Parsing**: Extract button actions from LLM tool calls

## Common Development Patterns

### Starting the System
```python
# 1. Start Django server
cd ai_gba_player && python manage.py runserver

# 2. Start AI service via web interface
curl -X POST http://localhost:8000/api/restart-service/

# 3. Check service status
curl http://localhost:8000/api/chat-messages/
```

### Configuration Management
```python
# All configuration via Django models
from dashboard.models import Configuration

# Get current config
config = Configuration.get_config()
config_dict = config.to_dict()

# Update config via web interface (saves to database)
# POST to /api/save-ai-config/ with form data
```

### Adding New LLM Providers
```python
# In dashboard/llm_client.py
def _call_new_provider_api(self, screenshot_path, context):
    # Implement new provider
    # Return standardized response format:
    return {
        "text": "AI reasoning",
        "actions": ["UP", "A"],
        "success": True,
        "error": None
    }
```

### Error Handling
- **LLM API Failures**: Automatic fallback to basic exploration actions
- **Socket Disconnections**: Graceful reconnection handling
- **Configuration Errors**: Clear error messages in web interface
- **Service Crashes**: No crash loops, clean restart capability

## Testing
Every function should have unit test coverage.
Every feature should have integration test coverage.

### AI Service Testing
```bash
# Test socket communication
python test_ai_service.py

# Test with real mGBA connection
# 1. Start Django server: python manage.py runserver
# 2. Start AI service via web interface
# 3. Launch mGBA and load script
# 4. Monitor chat interface for real-time activity
```

### Web Interface Testing
```bash
# Test Django app
cd ai_gba_player
python manage.py test

# Test API endpoints
curl -X POST http://localhost:8000/api/restart-service/
curl http://localhost:8000/api/chat-messages/
curl -X POST http://localhost:8000/api/stop-service/
```

## Debugging

### Service Monitoring
- **Web Interface**: Real-time chat shows all AI activity
- **Django Logs**: Console output shows service status
- **API Endpoints**: Check service health via HTTP requests

### Common Issues
- **Port 8888 in use**: Only one AI service can run at a time
- **mGBA not connecting**: Ensure mGBA is running and Lua script loaded
- **API key errors**: Configure correct provider and key via web interface
- **No screenshots**: Verify mGBA has ROM loaded and script is active

### Debug Features
- **Chat Interface**: Shows all screenshots, AI responses, and actions
- **Service Status**: Real-time connection and activity monitoring
- **Error Messages**: Clear error reporting in chat interface

## Architecture Principles

The simplified system is designed with these principles:
- **Single Process**: Django manages everything - no complex multi-process coordination
- **Embedded UI**: All HTML/CSS/JS in simple_views.py - no template complexity
- **Direct Socket**: TCP connection on port 8888 for mGBA communication
- **Database-first**: Configuration stored in SQLite via Django models
- **Real-time Monitoring**: Live chat interface with polling for transparency
- **Error Recovery**: Graceful handling of failures at all levels
- **Minimal Dependencies**: No REST framework, channels, or complex middleware

## Code Organization Status (CLEANED UP)

### ✅ Active Components (Required for main program)
- `ai_gba_player/manage.py` - Django entry point
- `ai_gba_player/ai_gba_player/simple_views.py` - **CORE: All views + API endpoints**
- `ai_gba_player/dashboard/ai_game_service.py` - **CORE: Socket server + AI logic**
- `ai_gba_player/dashboard/llm_client.py` - **CORE: Multi-provider LLM client**
- `ai_gba_player/dashboard/models.py` - Database configuration storage
- `ai_gba_player/core/logging_config.py` - **NEW: Centralized logging system**
- `emulator/script.lua` - mGBA interface script

### 🧹 Recently Cleaned Up (Removed unused legacy code)
- `ai_gba_player/api/` - **REMOVED** - Legacy REST API superseded by simple_views
- `core/` (root level) - **REMOVED** - Legacy base framework classes
- `games/` - **REMOVED** - Game-specific modules (simplified approach used)
- `tests/` (root level) - **REMOVED** - Legacy test files superseded by proper unit tests

### 🔧 Simplified Architecture Benefits
- **90% less code complexity** than original multi-process design
- **Single-file UI approach** eliminates template loading overhead
- **Direct database storage** removes JSON file management complexity
- **Embedded AI service** runs as daemon thread from Django process
- **Centralized logging** replaces scattered print statements with structured logging
- **Zero external dependencies** beyond Django and LLM APIs

The system represents a **major architectural simplification** optimized for reliability and maintainability.

**Quick Start**: `cd ai_gba_player && python manage.py runserver` → http://localhost:8000 🚀

## Coding Conventions

This project follows strict coding standards to ensure maintainability, testability, and clean architecture:

### 1. Object-Oriented Design (OOP)
**Principle**: Proper encapsulation - functions must belong to the right class with clear responsibilities.

**Rules**:
- ✅ **Single Responsibility**: Each class has one clear purpose
- ✅ **Proper Encapsulation**: Private methods use `_` prefix, internal methods use `__` prefix
- ✅ **Method Placement**: Functions must belong to appropriate classes, not scattered as standalone functions
- ✅ **Interface Design**: Public methods provide clear APIs, implementation details are private
- ✅ **Concise Code**: Keep files under 800 lines when possible for maintainability

**Examples**:
```python
# ✅ GOOD: Proper encapsulation
class ScreenshotManager:
    def __init__(self, base_path: str):
        self._base_path = Path(base_path)
        self._current_sequence = 0
        
    def capture_screenshot(self) -> str:
        """Public API for screenshot capture"""
        filename = self._generate_filename()
        return self._save_screenshot(filename)
    
    def _generate_filename(self) -> str:
        """Private method - implementation detail"""
        self._current_sequence += 1
        return f"screenshot_{self._current_sequence:06d}.png"

# ❌ BAD: Scattered functions
def generate_screenshot_filename():  # Should be in ScreenshotManager
    pass

def validate_file_size(path):  # Should be in FileValidator class
    pass
```

### 2. Testing Strategy
**Principle**: Unit tests with mocks > integration test scripts.

**Rules**:
- ✅ **Unit Tests**: Use Django's TestCase with proper mocking
- ✅ **Mock External Dependencies**: Socket connections, file I/O, LLM APIs
- ✅ **Test Coverage**: Each public method must have corresponding tests
- ✅ **Fast Tests**: Tests run in <1 second each, no real network calls

**File Organization**:
```
ai_gba_player/
├── dashboard/
│   ├── tests/                    # ✅ Proper test structure
│   │   ├── __init__.py
│   │   ├── test_ai_game_service.py
│   │   ├── test_llm_client.py
│   │   └── test_models.py
│   ├── ai_game_service.py
│   └── llm_client.py
└── dev-tools/
    └── integration_tests/        # ✅ Separate integration tests
        └── test_end_to_end.py
```

**Examples**:
```python
# ✅ GOOD: Unit test with mocks
class TestAIGameService(TestCase):
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    def test_handle_screenshot_request(self, mock_llm, mock_socket):
        service = AIGameService()
        mock_llm.return_value.analyze_game_state.return_value = {
            'actions': ['UP'], 'success': True
        }
        
        result = service._handle_screenshot_data("test_path")
        
        self.assertEqual(result, "0,0,4")  # UP action
        mock_llm.return_value.analyze_game_state.assert_called_once()

# ❌ BAD: Integration test script
def test_real_mgba_connection():  # Should be mocked unit test
    service = AIGameService()
    service.start()  # Real socket connection
    # Test with real mGBA...
```

### 3. File Size Limits
**Principle**: No single file > 2000 lines for maintainability.

**Rules**:
- ✅ **Hard Limit**: 2000 lines maximum per file
- ✅ **Soft Target**: 500-1000 lines per file
- ✅ **Logical Separation**: Split by functionality, not arbitrarily
- ✅ **Clear Imports**: Related classes can be split across files with clear import structure

**Refactoring Strategy**:
```python
# Before: monolithic llm_client.py (3000+ lines)
# After: Split into focused modules

dashboard/
├── llm/
│   ├── __init__.py
│   ├── client.py           # Core LLMClient (~800 lines)
│   ├── providers.py        # Provider-specific code (~600 lines)
│   ├── image_processing.py # Image enhancement (~400 lines)
│   └── context_builder.py  # Prompt context logic (~500 lines)
```

### 4. Code Quality Standards

**Import Organization**:
```python
# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import django
from django.test import TestCase

# Local application imports
from dashboard.models import Configuration
from dashboard.llm.client import LLMClient
```

**Error Handling**:
```python
# ✅ GOOD: Specific exceptions with context
class ScreenshotNotFoundError(Exception):
    """Raised when screenshot file is not available after timeout"""
    pass

def wait_for_screenshot(self, path: str) -> bool:
    try:
        return self._validate_file(path)
    except FileNotFoundError as e:
        raise ScreenshotNotFoundError(f"Screenshot not ready: {path}") from e
```

**Documentation**:
```python
def analyze_game_state(self, screenshot_path: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze game state from screenshot using LLM.
    
    Args:
        screenshot_path: Absolute path to screenshot file
        context: Game state context (position, direction, etc.)
        
    Returns:
        Dict containing:
            - text: AI reasoning
            - actions: List of button actions
            - success: Boolean success flag
            - error: Error message if failed
            
    Raises:
        ScreenshotNotFoundError: If screenshot is not available after timeout
        LLMAPIError: If LLM API call fails
    """
```

### 5. Refactoring Priorities

**Immediate Actions**:
1. **Split Large Files**: Any file >2000 lines needs immediate refactoring
2. **Extract Service Classes**: Move standalone functions into appropriate service classes
3. **Add Unit Tests**: Replace integration test scripts with proper unit tests
4. **Improve Encapsulation**: Make implementation details private

**File Size Monitoring**:
```bash
# Check current file sizes
find . -name "*.py" -exec wc -l {} + | sort -nr | head -10

# Target files likely >2000 lines:
# - llm_client.py
# - ai_game_service.py  
# - Any generated Django migrations
```

These conventions ensure the codebase remains maintainable, testable, and follows Python/Django best practices.