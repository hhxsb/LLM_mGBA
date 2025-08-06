# AI GBA Player 🎮

A universal AI gaming framework that enables Large Language Models to play Game Boy Advance games through visual understanding and decision-making. Features a modern web interface for real-time monitoring and control.

## 🚀 Quick Start

### Start the AI GBA Player
```bash
cd ai_gba_player
python manage.py runserver
```

Visit **http://localhost:8000** to access the AI GBA Player interface.

### Launch Game Processes
```bash
# Start AI game processes
python manage.py start_process all --config config_emulator.json

# View system status  
python manage.py status_process --detailed
```

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

The AI GBA Player uses a sophisticated multi-process architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   mGBA Emulator │ -> │  Game Control    │ -> │   AI GBA Player │
│   + Lua Script  │    │     Process      │    │   Web Interface │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌──────────────────┐              │
         └------------- │  Video Capture   │ -------------┘
                        │     Process      │
                        └──────────────────┘
```

### Core Components

1. **AI GBA Player Web Interface** (`ai_gba_player/`)
   - Django-based web application with real-time WebSocket support
   - Game monitoring, system control, and process management
   - Modern responsive design with GBA theming

2. **Game Control Process** (`game_control_process.py`)
   - LLM-powered decision making and game state analysis
   - Advanced knowledge management and memory systems  
   - Emulator communication via Lua script interface

3. **Video Capture Process** (`video_capture_process.py`)
   - Rolling screenshot buffer and GIF generation
   - Real-time video streaming to web interface
   - On-demand video analysis and processing

4. **Game-Specific Modules** (`games/`)
   - **Pokemon Red**: Fully implemented with advanced AI features
   - **Base Game**: Template for adding new GBA games
   - **Extensible**: Easy addition of new games and AI behaviors

## 📱 Web Interface

### Game Monitor (`/`)
- **Live Gameplay**: Real-time GIF streaming of AI gameplay
- **AI Responses**: Monitor AI decision-making process and reasoning
- **Game Actions**: Track button presses and game state changes
- **System Status**: Process health and performance metrics

### System Control (`/admin-panel/`)
- **Process Management**: Start/stop/restart game processes
- **System Monitoring**: CPU, memory, and connection status
- **Log Viewing**: Real-time system logs and error tracking
- **Quick Actions**: Bulk operations and system utilities

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

# Setup AI GBA Player
cd ai_gba_player
python manage.py setup_django_dashboard --create-processes
```

### Configuration
1. **Configure API Keys**: Add your LLM provider API key to `config_emulator.json`
2. **Setup Emulator**: Load your GBA ROM in mGBA
3. **Load Script**: In mGBA, load `emulator/script.lua` via Tools > Script Viewer
4. **Start System**: Run `python manage.py runserver` and visit http://localhost:8000

## 📊 Management Commands

The AI GBA Player includes comprehensive command-line tools:

```bash
# Process Management
python manage.py start_process <process_name>    # Start specific process
python manage.py stop_process <process_name>     # Stop specific process  
python manage.py restart_process <process_name>  # Restart specific process
python manage.py status_process --detailed       # Check all process status

# System Operations
python manage.py setup_django_dashboard          # Initialize system
python manage.py collectstatic --noinput        # Prepare static files

# Available processes: video_capture, game_control, all
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
cd ai_gba_player && python manage.py runserver
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