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

# Test Django app
cd ai_gba_player
python manage.py test

# Test game detection and Sapphire support
python dev-tools/test-scripts/test_game_detection.py
python dev-tools/test-scripts/test_final_sapphire_flow.py

# Test mGBA connection (while Django server is running)
curl -X POST http://localhost:8000/api/restart-service/
curl http://localhost:8000/api/chat-messages/

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
├── core/                          # Memory system integration ONLY
│   ├── graphiti_memory.py         # Graphiti-based autonomous learning system
│   └── memory_service.py          # Memory service abstraction layer
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

### Legacy/Unused Components (NOT used by main program)
```
api/                               # ❌ UNUSED - Legacy REST API superseded by simple_views
core/                              # ❌ UNUSED - Legacy base framework classes  
games/                             # ❌ UNUSED - Game-specific modules (replaced by simple detection)
tests/                             # ❌ UNUSED - Legacy test files
dev-tools/                         # ⚠️  Development utilities only (not part of main program)
docs/                              # ⚠️  Documentation only
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

## Graphiti Memory System (NEW FEATURE)

### Autonomous Learning & Memory
The AI GBA Player now includes an advanced **Graphiti-powered memory system** that enables:

**🎯 Autonomous Objective Discovery**: AI analyzes its own responses to discover new goals
- "I need to find the Pokemon Center" → Creates "find Pokemon Center" objective
- Auto-categorizes as main/side/exploration with priority scoring
- Tracks discovery location and completion status

**🧠 Strategy Learning**: Remembers what button patterns work in different situations
- Records successful button sequences for specific contexts
- Tracks success rates and usage frequency
- Provides learned strategies in future similar situations

**🏆 Achievement Tracking**: Automatically detects and records completed objectives
- "I caught a Pikachu!" → Completes "catch electric Pokemon" objective
- Maintains achievement history with completion times and locations
- Creates prerequisite chains between related objectives

**📊 Memory-Enhanced Prompts**: LLM receives contextual memory in every decision
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
# Full Graphiti support (recommended)
pip install graphiti-ai>=0.3.0 neo4j>=5.0.0

# Auto-fallback if unavailable
# System uses SimpleMemorySystem automatically
```

### Architecture Integration
- **Memory Discovery**: `ai_gba_player/dashboard/ai_game_service.py` analyzes AI responses
- **Context Enhancement**: `ai_gba_player/dashboard/llm_client.py` injects memory into prompts  
- **Knowledge Storage**: `ai_gba_player/core/graphiti_memory.py` manages Graphiti/Neo4j
- **Template Integration**: `data/prompt_template.txt` includes `{memory_context}` variable

### Benefits
- **Self-improving AI**: Gets better at games over time through learning
- **Goal persistence**: Important objectives don't get forgotten
- **Strategy reuse**: Successful patterns are remembered and applied
- **Context awareness**: AI knows what it should be doing at any moment

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
{notepad_content}     - Long-term memory and game progress
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
- `emulator/script.lua` - mGBA interface script

### ❌ Disabled/Unused Components (Safe to ignore)
- `ai_gba_player/api/` - **DISABLED in settings.py** - Legacy REST API superseded
- `core/` (root) - **NOT IMPORTED** - Legacy base framework classes
- `games/` - **NOT USED** - Game-specific modules (simplified approach used)
- `staticfiles/rest_framework/` - **REMOVED** - Unused static files cleaned up

### 🔧 Simplified Architecture Benefits
- **90% less code complexity** than original multi-process design
- **Single-file UI approach** eliminates template loading overhead
- **Direct database storage** removes JSON file management complexity
- **Embedded AI service** runs as daemon thread from Django process
- **Zero external dependencies** beyond Django and LLM APIs

The system represents a **major architectural simplification** optimized for reliability and maintainability.

**Quick Start**: `cd ai_gba_player && python manage.py runserver` → http://localhost:8000 🚀