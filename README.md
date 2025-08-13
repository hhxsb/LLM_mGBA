# AI GBA Player 🎮

A universal AI gaming framework that enables Large Language Models to play Game Boy Advance games through visual understanding and decision-making. Features a modern web interface for real-time monitoring and control.

## 🚀 Quick Start

### Simple Setup
```bash
# Launch AI GBA Player
python main.py
```

This starts the web interface at **http://localhost:8000** where you can:
- Configure your ROM and mGBA paths
- Launch mGBA automatically 
- Start the AI gaming service
- Monitor AI gameplay in real-time

## ✨ Features

### 🎯 **Game Monitor**
- **Real-time Gameplay**: Watch AI play GBA games live via WebSocket streaming
- **Game Footage**: Rolling video buffer with GIF generation and playback
- **AI Decision Tracking**: Monitor AI reasoning and button press decisions
- **Multi-game Support**: Designed to work with any GBA game

### ⚙️ **System Control**
- **Process Management**: Start, stop, restart game processes via web interface
- **Health Monitoring**: Real-time CPU, memory, and system metrics
- **Error Handling**: Comprehensive logging and error recovery
- **Command Line Tools**: Full automation support via Django management commands

### 🎨 **Modern Interface** 
- **GBA-Themed Design**: Retro color scheme inspired by Game Boy Advance hardware
- **Responsive Layout**: Works on desktop, tablet, and mobile devices
- **Real-time Updates**: WebSocket-powered live updates throughout the interface
- **Professional Admin Panel**: Complete system control and monitoring

## 🏗️ Architecture

The AI GBA Player uses a unified threaded architecture for optimal performance:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   mGBA Emulator │ -> │ Unified Game     │ -> │   AI GBA Player │
│   + Lua Script  │    │ Service          │    │   Web Interface │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌──────────────────┐              │
         └------------- │ Video Capture    │ -------------┘
                        │ Thread           │
                        └──────────────────┘
```

### Core Components

1. **AI GBA Player Web Interface** (`ai_gba_player/`)
   - Django-based chat interface for real-time AI monitoring
   - Configuration management for ROM, mGBA, and AI settings
   - Simple message-based UI: images/videos sent, AI responses received

2. **Unified Game Service** (`ai_gba_player/core/unified_game_service.py`)
   - Integrated video capture and AI decision-making in threaded architecture
   - LLM-powered game analysis with advanced knowledge management
   - Direct emulator communication via Lua script interface

3. **Game-Specific Modules** (`games/`)
   - **Pokemon Red**: Fully implemented with advanced AI features
   - **Extensible**: Easy addition of new games and AI behaviors

## 📱 Web Interface

### Chat-Based AI Monitor (`/`)
- **Chat Interface**: Simple messaging interface for AI interaction
- **Sent Messages**: Images and videos sent to AI for analysis
- **Received Messages**: AI text responses with button action lists
- **Configuration Panel**: Easy setup of ROM path, mGBA path, and AI settings
- **Service Controls**: Start/stop AI gaming service with one click
- **mGBA Integration**: Launch mGBA directly from the interface

## 🎮 Supported Games

### Currently Implemented
- **Pokemon Red**: Complete implementation with advanced AI features
  - Sophisticated knowledge management system
  - NPC conversation tracking and tutorial progression
  - Battle strategies and exploration algorithms

### Easy to Add
The framework is designed for easy game addition:
1. Create game module in `games/your_game/`
2. Implement game-specific controller and prompts
3. Configure game detection and state management
4. Launch with existing AI infrastructure

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.11+
- mGBA Emulator
- Game Boy Advance ROM files

### Installation
```bash
# Clone repository
git clone <repository-url>
cd LLM-Pokemon-Red

# Install dependencies
pip install -r requirements.txt
```

### Configuration
1. **Start AI GBA Player**: Run `python main.py`
2. **Visit Interface**: Go to http://localhost:8000
3. **Configure Settings**: Set ROM path, mGBA path, and API key via web interface
4. **Launch mGBA**: Click "Launch mGBA" to start emulator with your ROM
5. **Load Script**: In mGBA, load `emulator/script.lua` via Tools > Script Viewer
6. **Start AI Service**: Click "Start Service" to begin AI gameplay

## 📊 Management

### Web Interface Controls
All system management is available through the web interface:
- **Service Control**: Start/stop AI gaming service
- **Configuration**: Update ROM, mGBA, and AI settings
- **mGBA Launch**: Automatically launch mGBA with configured ROM
- **Real-time Monitoring**: Chat interface shows AI decisions and actions

### Alternative Command Line
```bash
# Django management commands (if needed)
cd ai_gba_player
python manage.py runserver                       # Start web interface only
python manage.py start_process unified_service   # Start AI service directly
```

## 🌐 API & Integration

### REST API
- **Process Control**: `/api/processes/` - Start, stop, restart processes
- **System Status**: `/api/status/` - Get real-time system information
- **Message History**: `/api/messages/` - Retrieve gameplay chat history

### WebSocket API
- **Live Updates**: Real-time game footage, AI responses, and system status
- **Bi-directional**: Send commands and receive live data streams
- **Auto-reconnect**: Robust connection handling with exponential backoff

## 🎯 Use Cases

### AI Research
- **Game AI Development**: Test and develop game-playing AI algorithms
- **Multimodal AI**: Combine vision, language, and decision-making models
- **Transfer Learning**: Study AI performance across different game genres

### Entertainment
- **AI Streaming**: Watch AI play games with real-time commentary
- **Game Completion**: Let AI complete games while you monitor progress
- **Challenge Runs**: Set up AI to attempt specific game challenges

### Education
- **AI Demonstration**: Show how modern AI systems make decisions
- **Game Analysis**: Study game mechanics through AI perspective  
- **Programming Education**: Learn about web development, AI, and system architecture

## 🔧 Customization

### Adding New Games
1. Create game directory: `games/your_game/`
2. Implement required modules:
   - `controller.py` - Game-specific AI controller
   - `game_engine.py` - Game state management
   - `prompt_template.py` - LLM prompts for the game
3. Register game in system configuration
4. Test with existing infrastructure

### Extending AI Capabilities
- **Knowledge Systems**: Add game-specific memory and learning
- **Decision Algorithms**: Implement custom AI strategies
- **Multi-agent**: Coordinate multiple AI systems
- **Real-time Learning**: Adapt AI behavior during gameplay

## 📚 Documentation

- **Architecture Guide**: `wiki/architecture/system-overview.md`
- **Feature Documentation**: `wiki/features/completed/`
- **Setup Instructions**: `SETUP.md`
- **Contributing Guide**: `CONTRIBUTING.md`

## 🏆 Key Features

### Technical Excellence
- ✅ **Production-Ready**: Django web framework with comprehensive error handling
- ✅ **Real-time Performance**: WebSocket streaming with optimized video processing
- ✅ **Scalable Architecture**: Multi-process design with clean separation of concerns
- ✅ **Modern UI/UX**: Responsive design with professional admin interface

### AI Capabilities  
- ✅ **Visual Understanding**: AI analyzes game screenshots for decision-making
- ✅ **Memory Management**: Sophisticated context and conversation tracking
- ✅ **Strategic Planning**: Advanced reasoning for complex game scenarios
- ✅ **Multi-game Support**: Framework designed for any GBA game

### User Experience
- ✅ **One-Command Setup**: Simple installation and startup process
- ✅ **Web-based Interface**: No desktop app installation required
- ✅ **Mobile-Friendly**: Full functionality on phones and tablets
- ✅ **Real-time Monitoring**: Live gameplay with system health tracking

## 🎮 Ready to Play!

The AI GBA Player transforms your Game Boy Advance games into an interactive AI showcase. Watch as artificial intelligence navigates complex game worlds, makes strategic decisions, and learns from gameplay - all through a beautiful, modern web interface.

**Get started now:**
```bash
python main.py
```

Visit **http://localhost:8000** and experience the future of AI gaming! 🚀

## Credits & Acknowledgments

**This project is based on and extends the excellent work by [martoast/LLM-Pokemon-Red](https://github.com/martoast/LLM-Pokemon-Red)**

*Original LLM-Pokemon-Red Benchmark by Martoast (MIT License)*

Key enhancements in this fork:
- Unified web interface with Django and real-time monitoring
- Multi-process architecture for improved performance
- Universal framework designed for multiple GBA games
- Modern responsive design with GBA theming
- Professional process management and admin controls