# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI GBA Player** is a universal AI gaming framework that enables Large Language Models to play Game Boy Advance games through visual understanding and decision-making. The system features a modern web interface for real-time monitoring and control, and is designed to be game-agnostic and extensible to any GBA title.

**Based on**: [martoast/LLM-Pokemon-Red](https://github.com/martoast/LLM-Pokemon-Red) - Original Pokémon Red AI benchmark

**Key Innovations**: 
- **AI GBA Player Web Interface** - Modern Django-based web interface with real-time monitoring
- **Universal game framework** designed to play any GBA game, not just Pokémon
- **Professional process management** with health monitoring and admin controls
- **WebSocket streaming** for real-time AI decisions, GIFs, and system status
- **Dual-process architecture** with optimized video capture and game control processes
- **Extensible game modules** allowing easy addition of new games and AI behaviors

## Core Architecture

### Four-Layer System with AI GBA Player Web Interface
1. **mGBA Emulator + Lua Script** (`emulator/script.lua`) - Game interface layer
2. **Video Capture Process** (`video_capture_process.py`) - Rolling video buffer with GIF generation
3. **Game Control Process** (`game_control_process.py`) - AI decision-making and emulator communication
4. **AI GBA Player Web Interface** (`ai_gba_player/`) - Django-based web interface with real-time monitoring and process management

### Enhanced Data Flow
```
Emulator → Lua Script → Game Control Process → Knowledge System → Enhanced Context → LLM → Button Commands → Back to Emulator
                ↓                                    ↑
        Video Capture Process ← Screenshot Requests  │
                ↓                                    │
        AI GBA Player Interface ← WebSocket Streaming ───┘
                (GIFs, AI Responses, Actions)
```

The system uses a dual-process architecture with rolling video buffers, real-time web interface integration via WebSocket streaming, and **intelligent context management** that provides the LLM with optimally prioritized information for decision-making.

## Knowledge System Architecture

### Advanced Memory Management
The system includes **8 implemented knowledge features** that dramatically improve AI performance:

**High Priority (Phase 1 - Completed)**:
- **Conversation State Tracking**: Maintains awareness of current NPC conversations
- **Character Identity & Game Phase Tracking**: Consistent character identity (GEMINI) and tutorial progress
- **Context Memory Buffer**: Rolling memory that builds on previous interactions
- **Enhanced Prompt Formatting**: Critical information prominently displayed with visual indicators

**Medium Priority (Phase 2 - Completed)**:
- **Dialogue Recording & Memory**: Complete NPC interaction history with information extraction
- **Conversation Flow Management**: Sophisticated dialogue phase detection and response guidance
- **Smart Context Prioritization**: Dynamic relevance scoring for optimal context delivery
- **Tutorial Progress Tracking**: 12-step Pokemon Red tutorial system with automatic progress detection

### Memory Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge System                          │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Conversation    │ │ Character       │ │ Context Memory  │ │
│ │ State Tracking  │ │ Identity &      │ │ Buffer          │ │
│ │                 │ │ Game Phase      │ │                 │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Dialogue        │ │ Conversation    │ │ Smart Context   │ │
│ │ Recording &     │ │ Flow            │ │ Prioritization  │ │
│ │ Memory          │ │ Management      │ │                 │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│ ┌─────────────────┐ ┌─────────────────┐                     │
│ │ Tutorial        │ │ Enhanced Prompt │                     │
│ │ Progress        │ │ Formatting      │                     │
│ │ Tracking        │ │                 │                     │
│ └─────────────────┘ └─────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

## Key Commands

### Running the AI GBA Player
```bash
# Install dependencies
pip install "google-generativeai>=0.3.0" pillow openai anthropic python-dotenv opencv-python

# Start AI GBA Player (RECOMMENDED)
cd ai_gba_player
python manage.py runserver

# Launch game processes via web interface or command line
python manage.py start_process all --config config_emulator.json

# Alternative: Manual startup for development
python video_capture_process.py --config config_emulator.json
python game_control_process.py --config config_emulator.json
```

### Setup Sequence (CRITICAL ORDER)
1. Start mGBA and load any GBA ROM (currently optimized for Pokémon Red)
2. **Recommended**: Start AI GBA Player: `cd ai_gba_player && python manage.py runserver`
3. **Alternative**: Manual startup: Start video capture, then game control processes
4. Update project path in `emulator/script.lua` if needed
5. In mGBA: Tools > Script Viewer > Load `emulator/script.lua`

### AI GBA Player Access
- **Web Interface**: http://localhost:8000 (main interface)
- **Game Monitor**: http://localhost:8000/ (live gameplay)
- **System Control**: http://localhost:8000/admin-panel/ (process management)
- **Django Admin**: http://localhost:8000/admin/ (system administration)

### Testing Components
```bash
# Test AI GBA Player functionality
cd ai_gba_player
python manage.py test

# Test individual knowledge system features
python tests/test_conversation_tracking.py
python tests/test_dialogue_recording.py
python tests/test_context_prioritization.py
python tests/test_tutorial_progress.py

# Test individual Lua components in mGBA Script Viewer
emulator/test_memory.lua      # Memory address testing
emulator/key_press_test.lua   # Button input testing  
emulator/screenshot_test.lua  # Screenshot capture testing
```

## Project Structure

```
LLM_mGBA/
├── README.md                          # Main documentation
├── CLAUDE.md                          # This file - project guidance
├── ai_gba_player/                     # AI GBA Player web interface (MAIN FEATURE)
│   ├── manage.py                      # Django management commands
│   ├── ai_gba_player/                 # Django project settings
│   │   ├── settings.py                # Django configuration
│   │   ├── urls.py                    # URL routing
│   │   └── wsgi.py                    # WSGI configuration
│   ├── dashboard/                     # Django app for game monitoring
│   │   ├── models.py                  # Data models
│   │   ├── views.py                   # Web views
│   │   ├── templates/dashboard/       # HTML templates
│   │   │   ├── base.html              # Base template with GBA theme
│   │   │   ├── dashboard.html         # Game monitor interface
│   │   │   └── admin_panel.html       # System control interface
│   │   └── static/dashboard/          # Static files
│   │       ├── css/gba-theme.css      # GBA universal theme
│   │       └── js/dashboard.js        # Dashboard JavaScript
│   └── management/                    # Django management commands
│       └── commands/                  # Process control commands
├── video_capture_process.py           # Video capture with rolling buffer
├── game_control_process.py            # AI decision-making process
├── config_emulator.json               # Main configuration file
├── core/                              # Core system components
│   ├── base_knowledge_system.py       # Knowledge management system (80+ methods)
│   ├── base_capture_system.py         # Video capture system
│   ├── screen_capture.py              # Screen capture backends
│   ├── base_game_controller.py        # Main controller logic
│   ├── base_game_engine.py           # Game state handling
│   └── base_prompt_template.py       # Prompt formatting system
├── games/pokemon_red/                 # Pokemon Red implementation (extensible framework)
│   ├── controller.py                  # Pokemon Red controller with knowledge integration
│   ├── knowledge_system.py            # Game-specific knowledge management
│   ├── prompt_template.py            # Pokemon Red prompts with enhanced formatting
│   └── game_engine.py                # Pokemon Red game logic
├── emulator/                          # mGBA Lua scripts
│   └── script.lua                     # Main emulator script with enhanced state tracking
├── tests/                             # Comprehensive test suite
│   ├── test_conversation_tracking.py  # Conversation state tracking tests
│   ├── test_dialogue_recording.py     # Dialogue memory system tests
│   ├── test_context_prioritization.py # Smart context prioritization tests
│   ├── test_tutorial_progress.py      # Tutorial progress tracking tests
│   ├── test_dashboard_websocket.py    # WebSocket integration testing
│   └── test_complete_system.py        # Full system validation
├── data/                              # Data and configuration
│   ├── knowledge_graph.json           # Persistent knowledge storage
│   ├── screenshots/                   # Game screenshots
│   └── prompt_template.txt             # Base AI prompt template
├── knowledge_inspector.py             # Knowledge base inspection tools
├── monitor_knowledge.py               # Real-time knowledge monitoring
└── notepad.txt                        # Long-term game progress memory
```

## Configuration System

### Main Config (`config_emulator.json`)
- **Game Selection**: `"game": "pokemon_red"` (framework supports additional games)
- **API Keys**: Google Gemini API key required (supports multiple LLM providers)
- **Paths**: Screenshot, notepad, and prompt template paths
- **Timing**: `decision_cooldown` controls rate limiting (3-6 seconds recommended)
- **Debug**: `debug_mode` for verbose logging
- **Dual Process**: `dual_process_mode` configuration for video capture and process communication
- **Dashboard**: `dashboard` configuration for WebSocket and admin features

### Dashboard Configuration
```json
{
  "dashboard": {
    "enabled": true,
    "port": 3000,
    "websocket_port": 3001,
    "auto_start_processes": true,
    "theme": "pokemon"
  },
  "dual_process_mode": {
    "enabled": true,
    "video_capture_port": 8889,
    "rolling_window_seconds": 20
  }
}
```

### Dynamic Prompt System
- **Template File**: `data/prompt_template.txt` 
- **Hot Reload**: File changes automatically detected and reloaded
- **Enhanced Variables**: `{critical_summary}`, `{character_context}`, `{conversation_context}`, `{conversation_flow_context}`, `{dialogue_memory_context}`, `{memory_context}`, `{tutorial_guidance}`, `{tutorial_progress}`, `{tutorial_preview}`

## Memory Management Architecture

## Dashboard Architecture

### Real-time Monitoring
- **WebSocket Streaming**: Live GIFs, AI responses, and button actions
- **Process Status**: Real-time health monitoring of all AI processes
- **Connection Management**: Automatic reconnection and error handling

### Admin Panel Features
- **Process Management**: Start, stop, restart individual processes
- **Log Viewing**: Real-time and historical logs for debugging
- **System Monitoring**: Process health, dependencies, and performance metrics
- **Manual Controls**: Force restart, view detailed process information

### Process Management
- **Dependency-aware Startup**: video_capture → game_control → knowledge_system
- **Graceful Failure Handling**: No crash loops, smart auto-restart logic
- **Error Recovery**: Automatic port cleanup, process restart, WebSocket reconnection

### Dual Memory System
- **Short-term**: Rolling context buffer (20 entries) with smart prioritization
- **Long-term**: Persistent dialogue history, character relationships, and tutorial progress
- **Smart Context**: Dynamic relevance scoring ensures most important information reaches LLM

### Knowledge Features
- **Conversation Awareness**: Always knows who it's talking to and conversation history
- **Character Identity**: Maintains consistent identity as "GEMINI" throughout gameplay
- **Dialogue Intelligence**: Complete NPC interaction tracking with information extraction
- **Tutorial Guidance**: Step-by-step progression through Pokemon Red's 12 tutorial steps
- **Context Optimization**: Smart prioritization delivers most relevant information to LLM

### Game State Tracking
- Real-time memory reading: player coordinates, facing direction, map ID
- Position tracking enables spatial reasoning and navigation
- Map ID mapping to human-readable location names
- Enhanced game state context with tutorial progress and conversation flow

## Communication Architecture

### Inter-Process Communication
- **Video Capture ↔ Game Control**: TCP Socket (Port 8889) for GIF requests
- **Game Control ↔ Emulator**: TCP Socket (Port 8888) for button commands
- **All Processes ↔ Dashboard**: WebSocket (Port 3000) for real-time streaming

### WebSocket Protocol
- **Message Format**: JSON with standardized schema
- **Message Types**:
  - `chat_message`: Contains GIFs, AI responses, or actions
  - `ping/pong`: Connection keepalive
  - `process_status`: Process health updates

### Dual-Process GIF System
- **Rolling Buffer**: 20-second window of screenshots at 30 FPS
- **On-demand GIF Generation**: Optimized frame sampling and compression
- **Real-time Streaming**: GIFs sent to dashboard via WebSocket

### Multi-Button Support
- Supports sequences like `["UP", "UP", "A"]` for complex actions
- Button queue system in Lua executes commands sequentially
- Each button held for 2 frames before releasing

## LLM Integration

### Tool-Based Architecture
- **`press_button`**: Execute game controls (accepts button arrays)
- **`update_notepad`**: Update long-term memory

### Enhanced Context Processing Pipeline
1. **Raw Context Collection**: Game state, conversation state, character identity
2. **Smart Prioritization**: Dynamic relevance scoring based on current situation
3. **Visual Formatting**: Structured presentation with priority indicators (🔥, 🗣️, 🧠, 📚)
4. **Length Management**: Intelligent truncation preserving key information
5. **LLM Delivery**: Optimally formatted context for decision-making

### Response Processing
- **Conversation Detection**: Automatic NPC interaction recognition
- **Tutorial Progress**: Step completion detection from AI responses
- **Character Tracking**: Identity consistency monitoring
- **Flow Analysis**: Conversation phase detection and expected action extraction

## Knowledge System Data Structures

### Core State Tracking
```python
@dataclass
class ConversationState:
    current_npc: Optional[str] = None
    npc_role: Optional[str] = None  
    conversation_topic: Optional[str] = None
    conversation_history: List[str] = field(default_factory=list)
    expected_next_action: Optional[str] = None
    conversation_phase: str = "none"

@dataclass
class CharacterState:
    name: str = "GEMINI"
    current_objective: Optional[str] = None
    game_phase: str = "tutorial"
    known_npcs: Dict[str, str] = field(default_factory=dict)
    tutorial_progress: List[str] = field(default_factory=list)

@dataclass
class ContextMemoryEntry:
    timestamp: float
    context_type: str
    content: str
    priority: int = 5  # 1-10 scale
    location_id: Optional[int] = None

@dataclass
class DialogueRecord:
    npc_name: str
    npc_role: str
    dialogue_text: str
    player_response: str
    outcome: str
    timestamp: float
    location_id: int
    important_info: List[str] = field(default_factory=list)
```

## Common Development Patterns

### Knowledge System Integration
```python
# Update conversation state when AI talks to NPCs
controller.knowledge_system.start_conversation(
    npc_name="Mom", npc_role="mom", topic="setting clock", location_id=24
)

# Record complete dialogue interactions
controller.knowledge_system.record_dialogue(
    npc_name="Mom", npc_role="mom", 
    dialogue_text="Welcome home! Set the clock upstairs.",
    player_response="I will go upstairs", 
    outcome="Received clear instruction"
)

# Add important context to memory
controller.knowledge_system.add_context_memory(
    "important", "First conversation with Mom about clock", priority=9
)

# Process tutorial progress
controller.knowledge_system.process_tutorial_step_detection(
    ai_response, action_taken, game_state
)
```

### Error Handling
- Process crash recovery with dependency-aware restart logic
- WebSocket disconnection recovery with automatic reconnection
- Socket disconnection recovery with reconnection logic
- Rate limiting protection with configurable cooldowns
- Graceful degradation when API calls fail
- Knowledge system persistence across restarts

### Testing Pattern
```python
def test_knowledge_feature():
    controller = PokemonRedController(config)
    
    # Test feature functionality
    result = controller.knowledge_system.feature_method()
    assert result == expected_result
    
    # Test integration with other features
    integration_result = test_with_other_features()
    assert integration_result == True
    
    return True
```

## Performance Characteristics

### Memory Efficiency
- Rolling buffers prevent unlimited memory growth
- Smart prioritization ensures optimal context selection
- Automatic context compression for older entries

### Real-time Responsiveness
- Request-based screenshot system prevents timing issues
- Intelligent cooldowns balance performance with API limits
- Context caching optimizes repeated operations

## Debugging

### Knowledge System Monitoring
```bash
# Real-time knowledge base monitoring
python monitor_knowledge.py --monitor

# Current knowledge state inspection
python monitor_knowledge.py --show

# Detailed knowledge inspection
python knowledge_inspector.py
```

### Debug Mode Features
- Verbose logging of all knowledge operations
- Socket communication tracing
- LLM request/response logging with context details
- Game state change notifications
- Conversation flow analysis output
- **Dashboard Logs**: Real-time log viewing in admin panel
- **Process Monitoring**: Live process health and performance metrics

### Common Issues
- **Process crashes**: Use admin panel to view logs and restart processes
- **"Port in use"**: Dashboard automatically handles port conflicts
- **Missing cv2**: Install OpenCV with `pip install opencv-python`
- **Knowledge persistence errors**: Check data directory permissions
- **Context too long**: Smart prioritization automatically manages length
- **Tutorial detection issues**: Check AI response format and game state
- **WebSocket connection failures**: Check AsyncIO event loop threading
- **Missing AI messages in dashboard**: Verify WebSocket connections in admin panel

### Dashboard Troubleshooting
- **Admin Panel**: Access via ⚙️ Admin tab for process management
- **Process Logs**: View real-time stderr/stdout for debugging
- **Manual Controls**: Force restart processes that become unresponsive
- **WebSocket Status**: Monitor connection health and message flow

## Documentation

### Comprehensive Wiki
- **[wiki/README.md](wiki/README.md)** - Documentation hub
- **[wiki/features/completed/](wiki/features/completed/)** - All implemented features
- **[wiki/features/future/](wiki/features/future/)** - Future enhancements
- **[wiki/architecture/](wiki/architecture/)** - System architecture details
- **[wiki/testing/](wiki/testing/)** - Testing guides and results

### Key Documentation Files
- **[wiki/features/completed/knowledge-system-features.md](wiki/features/completed/knowledge-system-features.md)** - Complete knowledge system documentation
- **[wiki/architecture/system-overview.md](wiki/architecture/system-overview.md)** - Technical architecture
- **[wiki/testing/testing-guide.md](wiki/testing/testing-guide.md)** - Testing procedures

## Architecture Considerations

The system is designed as a **sophisticated AI gaming agent** with these key principles:
- **Dual-Process Architecture**: Separate video capture and game control for optimal performance
- **Real-time Dashboard**: Unified monitoring with WebSocket streaming and admin controls
- **Process Management**: Dependency-aware startup, health monitoring, and error recovery
- **Advanced Memory Management**: Comprehensive conversation and character state tracking
- **Intelligent Context Delivery**: Smart prioritization ensures optimal LLM performance
- **Modular Design**: Clear separation between emulator, video, control, knowledge, and dashboard layers
- **Extensible Architecture**: Knowledge system easily adaptable to other games
- **Robust Error Recovery**: Graceful degradation, persistence, and admin controls throughout
- **User-Friendly**: Unified dashboard eliminates complex manual setup procedures
- **Comprehensive Testing**: Full test coverage for all knowledge features and system integration

The system represents a **breakthrough in universal AI gaming**, combining sophisticated LLM capabilities with modern process architecture, real-time monitoring, and extensible game support - providing a complete framework for AI game-playing research across multiple titles and genres.

**Credits**: This framework builds upon the excellent foundational work of [martoast/LLM-Pokemon-Red](https://github.com/martoast/LLM-Pokemon-Red), extending it into a universal GBA gaming platform with enhanced monitoring, process management, and multi-game capabilities.