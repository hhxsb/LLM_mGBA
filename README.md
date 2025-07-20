# LLM mGBA - Universal AI Game Player

> An extensible AI framework that enables LLMs to play Game Boy Advance games through visual understanding and decision making

## Project Vision

This project aims to create a universal AI gaming framework that can play any GBA game by only seeing the game screen, just like a human would. While initially demonstrated with Pokémon Red, the system is designed to be game-agnostic and extensible to any GBA title. It tests the AI's ability to understand visuals, make decisions, remember context, plan strategies, and adapt to changing game situations - all valuable skills that translate to real-world AI applications.

## Credits & Acknowledgments

**This project is based on and extends the excellent work by [martoast/LLM-Pokemon-Red](https://github.com/martoast/LLM-Pokemon-Red)**

*Original LLM-Pokemon-Red Benchmark by Martoast (MIT License)*

Key enhancements in this fork:
- Unified dashboard with real-time AI monitoring
- Dual-process architecture for improved performance
- Extensible framework for multiple GBA games
- Advanced process management and admin controls
- WebSocket streaming of AI decisions and gameplay

## 🎮 **System Highlights**

- **🎯 Universal Game Framework**: Extensible architecture designed to play any GBA game, not just Pokémon
- **🧠 Advanced AI System**: Sophisticated visual understanding, memory management, and decision-making capabilities
- **🔄 Dual-Process Architecture**: Optimized video capture and game control processes for smooth gameplay
- **📊 Unified Dashboard**: Real-time AI monitoring with admin controls, process management, and WebSocket streaming
- **🎮 Multi-Game Support**: Framework designed to accommodate different game genres and mechanics
- **📡 Real-time Monitoring**: Live AI decision streaming, performance metrics, and process health monitoring
- **🛠️ Developer-Friendly**: Comprehensive admin tools, debugging capabilities, and extensible architecture

## Demo

🎬 [**Watch the Video on Bilibili**](https://www.bilibili.com/video/BV1nPgTzFE8r/?share_source=copy_web&vd_source=61bbacb6c4952260fc1d8cde27cc4ebd)

## How It Works

### **Four-Layer Universal Gaming System**
1. **mGBA Emulator + Lua Script** (`emulator/script.lua`) - Universal game interface layer
2. **Video Capture Process** (`video_capture_process.py`) - Game-agnostic video processing with rolling buffer
3. **Game Control Process** (`game_control_process.py`) - AI decision-making and emulator communication
4. **Unified Dashboard** (`dashboard.py`) - Real-time monitoring, admin controls, and multi-game management

### **Data Flow**
```
Emulator → Lua Script → Game Control Process → LLM → Button Commands → Back to Emulator
                ↓                                    ↑
        Video Capture Process ← Screenshot Requests  │
                ↓                                    │
        Dashboard ← WebSocket Streaming ─────────────┘
                (GIFs, AI Responses, Actions)
```

The system uses dual-process architecture with rolling video buffers and real-time dashboard integration.

## 🚀 **Quick Setup**

### **Install Dependencies**
```bash
pip install "google-generativeai>=0.3.0" pillow openai anthropic python-dotenv opencv-python
```

### **Configuration**
Edit `config_emulator.json` with your Gemini API key:
```json
{
  "game": "pokemon_red",  // Currently supports: pokemon_red (more games coming)
  "providers": {
    "google": {
      "api_key": "YOUR_GEMINI_API_KEY",
      "model_name": "gemini-2.5-pro",
      "max_tokens": 1024
    }
  },
  "dual_process_mode": {
    "enabled": true,
    "video_capture_port": 8889,
    "rolling_window_seconds": 20
  },
  "dashboard": {
    "enabled": true,
    "port": 3000,
    "auto_start_processes": true
  }
}
```

### **Easy Setup with Dashboard**
```bash
# One command to start everything!
python dashboard.py --config config_emulator.json

# For other games, specify game-specific config
python dashboard.py --config config_metroid.json  # Example for future games
```

### **Manual Setup Sequence (Advanced)**
1. Start mGBA and load any GBA ROM
2. Start video capture: `python video_capture_process.py --config config_emulator.json`
3. Start game control: `python game_control_process.py --config config_emulator.json`
4. In mGBA: Tools > Script Viewer > Load `emulator/script.lua`

⚠️ **Important**: Video capture must be started BEFORE game control!

## 🧠 **AI Framework Features**

The system includes sophisticated AI capabilities designed for universal game playing:

### **✅ Core AI Features**:
- **Visual Understanding** - Advanced image processing and game state recognition
- **Memory Management** - Context preservation across gaming sessions
- **Decision Making** - Strategic planning and action selection
- **Game State Tracking** - Real-time monitoring of game variables and progress
- **Adaptive Learning** - Context-aware responses based on game events
- **Multi-Game Support** - Extensible architecture for different game types
- **Performance Optimization** - Efficient processing for real-time gameplay

### **Game-Specific Modules** (Extensible):
**Pokémon Red Module**:
- Conversation state tracking and NPC interaction management
- Character identity management and tutorial progression
- Battle system understanding and strategy development
- Inventory management and item usage optimization

**Framework for Future Games**:
- Modular game-specific knowledge systems
- Configurable AI behavior patterns
- Adaptable memory and context management

## 📁 **Project Structure**

```
LLM_mGBA/
├── README.md                          # Main documentation
├── CLAUDE.md                          # Claude Code assistant instructions
├── dashboard.py                       # Unified dashboard with process management
├── video_capture_process.py           # Video capture with rolling buffer
├── game_control_process.py            # AI decision-making process
├── config_emulator.json               # Main configuration file
├── dashboard/                         # Dashboard implementation
│   ├── backend/                       # FastAPI backend
│   │   ├── main.py                    # Dashboard server
│   │   ├── process_manager.py         # Process lifecycle management
│   │   └── api/                       # REST API endpoints
│   └── frontend/                      # React dashboard UI
│       ├── src/
│       │   ├── App.tsx                # Main dashboard interface
│       │   ├── components/            # UI components
│       │   │   ├── AdminPanel.tsx     # Process management UI
│       │   │   └── Dashboard.tsx      # Main monitoring interface
│       │   └── types/                 # TypeScript definitions
│       └── package.json
├── core/                              # Core system components
│   ├── base_knowledge_system.py       # Knowledge management
│   ├── base_capture_system.py         # Video capture system
│   └── screen_capture.py              # Screen capture backends
├── games/pokemon_red/                 # Pokemon Red specific code
│   ├── controller.py                  # Game controller
│   ├── knowledge_system.py            # Game knowledge
│   └── game_engine.py                 # Game state management
├── emulator/                          # mGBA Lua scripts
│   └── script.lua                     # Main emulator script
└── data/                              # Data and configuration
    ├── knowledge_graph.json           # Knowledge persistence
    ├── screenshots/                   # Game screenshots
    └── prompt_template.txt             # AI prompt template
```

## 🧪 **Testing**

The system includes comprehensive testing for all features:

```bash
# Run individual feature tests
python tests/test_conversation_tracking.py
python tests/test_dialogue_recording.py
python tests/test_context_prioritization.py
python tests/test_tutorial_progress.py

# See wiki/testing/testing-guide.md for complete testing documentation
```

## 📚 **Documentation**

- **[Wiki](wiki/README.md)** - Comprehensive project documentation
- **[System Architecture](wiki/architecture/system-overview.md)** - Technical architecture details
- **[Completed Features](wiki/features/completed/)** - All implemented features
- **[Testing Guide](wiki/testing/testing-guide.md)** - How to run and create tests

## 🎯 **Performance Features**

- **Universal Game Support**: Extensible framework designed for any GBA game
- **Dual-Process Architecture**: Separate video capture and game control for optimal performance
- **Rolling Video Buffer**: 20-second rolling window with on-demand GIF generation
- **Real-time Dashboard**: WebSocket streaming of GIFs, AI responses, and actions
- **Process Management**: Dependency-aware startup, graceful failure handling, auto-restart
- **Game-Agnostic State Tracking**: Configurable monitoring for different game types
- **Rate Limiting**: Configurable cooldowns prevent API overload (3-6 seconds recommended)
- **Memory Management**: Efficient short-term and long-term memory systems
- **Image Enhancement**: Optimized screenshot processing for better AI recognition
- **Modular Architecture**: Easy addition of new games and AI behaviors

## 🔧 **Configuration Options**

Key settings in `config_emulator.json`:
- **`decision_cooldown`**: Time between AI decisions (3-6 seconds recommended)
- **`debug_mode`**: Verbose logging for development
- **`dual_process_mode`**: Video capture and process communication settings
- **`dashboard`**: Dashboard and WebSocket configuration
- **`capture_system`**: Video capture, GIF optimization, and enhancement settings
- **API configuration**: Gemini API key and model settings

### **Dashboard Features**
- **Real-time Monitoring**: Live GIF streams, AI responses, and button actions
- **Admin Panel**: Process management with start/stop/restart controls
- **Process Logs**: View detailed logs for video capture and game control
- **System Status**: Real-time process health and connection monitoring
- **WebSocket Integration**: Live streaming of AI decisions and visual data

## 🤝 **Contributing**

Contributions welcome! Priority areas for contribution:
- **New Game Support**: Add modules for other GBA games (Metroid, Zelda, Fire Emblem, etc.)
- **New LLM Providers**: Add support for other AI models (OpenAI, Anthropic, local models)
- **Game-Specific AI**: Develop specialized AI behaviors for different game genres
- **Performance Optimizations**: Speed and efficiency improvements
- **Documentation**: Help improve guides and examples
- **Testing**: Additional test coverage and scenarios
- **Framework Extensions**: Enhance the universal gaming architecture

### **Roadmap for Game Support**
- 🎮 **Action/Adventure**: Metroid, Zelda series
- ⚔️ **Strategy/RPG**: Fire Emblem, Final Fantasy Tactics
- 🏃 **Platformers**: Mario, Sonic series
- 🏁 **Racing**: Mario Kart, F-Zero

## 📊 **Current Status**

- ✅ **Universal Framework**: Extensible architecture ready for multiple games
- ✅ **Pokémon Red**: Fully functional with advanced AI capabilities
- ✅ **Dashboard System**: Real-time AI monitoring with admin controls
- ✅ **Process Management**: Dependency-aware startup, crash recovery, manual controls
- ✅ **WebSocket Streaming**: Live GIFs, AI responses, and actions to dashboard
- ✅ **Developer Tools**: Comprehensive debugging and monitoring capabilities
- ✅ **Documentation**: Complete setup and development guides
- 🔄 **Multi-Game Support**: Framework ready for additional GBA games
- 🔄 **Active Development**: Adding support for new games and AI improvements

### **Game Support Status**
- ✅ **Pokémon Red**: Complete implementation with advanced features
- 🔄 **Additional Games**: Framework established, games can be added modularly
- 🎯 **Next Target**: Community-driven game selection

## 🚨 **Troubleshooting**

Common issues and solutions:

- **"Port in use"**: Dashboard automatically handles port conflicts
- **Process crashes**: Use admin panel to view logs and restart processes manually
- **Missing cv2**: Install OpenCV with `pip install opencv-python`
- **Socket timeout**: Adjust timeout values in `dual_process_mode` configuration  
- **Rate limiting**: Increase `decision_cooldown` in config
- **Dashboard not loading**: Check that port 5173 (frontend) and 3000 (backend) are available
- **Missing AI messages**: Verify WebSocket connections in admin panel

### **Dashboard Troubleshooting**
- **Access URLs**:
  - Frontend: http://localhost:5173
  - Backend API: http://127.0.0.1:3000
  - Admin Panel: Click ⚙️ Admin tab in dashboard
- **Process Management**: Use admin panel to check process status and logs
- **WebSocket Issues**: Restart processes using admin controls

## 📄 **License**

MIT License - See [LICENSE](LICENSE) for details.

---

**🎮 Ready to watch an AI master GBA games? Start with Pokémon Red and help expand to new games!**

## 🙏 **Acknowledgments**

This project builds upon the foundational work of:
- **[martoast/LLM-Pokemon-Red](https://github.com/martoast/LLM-Pokemon-Red)** - Original Pokémon Red AI benchmark
- **mGBA Development Team** - Excellent emulator with Lua scripting support
- **Google Gemini Team** - Powerful multimodal AI capabilities

Special thanks to the open-source community for making projects like this possible!