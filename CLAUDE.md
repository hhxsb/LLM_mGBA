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

## Project Structure

```
ai_gba_player/                     # Django web application (MAIN)
├── manage.py                      # Django management
├── ai_gba_player/                 # Django project settings
│   ├── settings.py                # Django configuration
│   ├── urls.py                    # URL routing
│   └── simple_views.py            # Web views and API endpoints
├── dashboard/                     # Main Django app
│   ├── ai_game_service.py         # AI service (socket server + LLM)
│   ├── llm_client.py              # LLM API client (Google/OpenAI/Anthropic)
│   ├── models.py                  # Database models (Configuration, Process)
│   └── templates/dashboard/       # HTML templates
│       ├── base.html              # Base template
│       └── dashboard.html         # Main interface (chat + config)
├── db.sqlite3                     # SQLite database
└── static/                        # CSS/JS assets

emulator/
└── script.lua                     # mGBA Lua script for game control

data/
├── screenshots/                   # Game screenshots
└── knowledge_graph.json           # AI memory system (legacy)

core/                              # Shared utilities
├── base_knowledge_system.py       # Knowledge management
├── base_game_controller.py        # Game controller base
└── screen_capture.py              # Screenshot utilities

games/pokemon_red/                 # Game-specific modules (extensible)
├── controller.py                  # Pokemon Red controller
├── knowledge_system.py            # Game-specific knowledge
└── prompt_template.py             # Pokemon Red prompts

dev-tools/                         # Development & debugging tools
├── memory-debugging/              # Memory address debugging scripts
│   ├── simple_sapphire_memory_finder.lua
│   └── find_sapphire_direction.lua
└── test-scripts/                  # System validation tests
    ├── test_game_detection.py
    └── test_final_sapphire_flow.py

docs/                              # Documentation
├── QUICKSTART.md                  # Quick setup guide
├── POKEMON_SAPPHIRE_SETUP.md      # Sapphire-specific setup
└── SAPPHIRE_MEMORY_DEBUG_GUIDE.md # Memory debugging guide

config_emulator.json               # Configuration file (auto-updated)
```

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
- **Single Process**: No complex multi-process coordination
- **Web-based**: Everything manageable through browser interface
- **Database-driven**: Configuration stored in SQLite, not files
- **Socket Communication**: Direct TCP for reliable mGBA connection
- **Real-time Monitoring**: Live chat interface for transparency
- **Error Recovery**: Graceful handling of failures at all levels
- **Extensible**: Easy to add new games and LLM providers

The system represents a **major simplification** from the original complex multi-process architecture while maintaining all core functionality and improving user experience significantly.

**Quick Start**: `cd ai_gba_player && python manage.py runserver` → http://localhost:8000 🚀