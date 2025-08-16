# AI GBA Player 🎮

A universal AI gaming framework that enables Large Language Models to play Game Boy Advance games through visual understanding and decision-making. Features a modern web interface with real-time chat monitoring.

## 🚀 Quick Start

### Simple Setup
```bash
# 1. Start the web interface
cd ai_gba_player
python manage.py runserver

# 2. Open browser to http://localhost:8000
# 3. Configure ROM path, mGBA path, and AI settings
# 4. Click "Launch mGBA" or start mGBA manually
# 5. Click "Reset mGBA Connection" 
# 6. In mGBA: Tools > Script Viewer > Load "emulator/script.lua"
# 7. Watch the AI play in real-time!
```

## ✨ Features

### 💬 **Real-time Chat Interface**
- **Screenshot Monitoring**: See exactly what the AI sees from the game
- **AI Reasoning**: Read the AI's analysis and decision-making process
- **Action Tracking**: Watch button commands being sent to the game
- **System Status**: Live connection and service health monitoring

### 🎯 **Universal Game Support**
- **Game Agnostic**: Works with any GBA game, not just Pokémon
- **Visual Understanding**: AI analyzes screenshots to make decisions
- **Flexible Controls**: Supports all GBA controller inputs
- **Easy ROM Management**: Simple file-based ROM configuration

### ⚙️ **Simple Configuration**
- **Web-based Setup**: Configure everything through the browser interface
- **Multiple LLM Providers**: Google Gemini, OpenAI, or Anthropic
- **Database Storage**: Settings saved automatically in SQLite
- **Auto mGBA Launch**: One-click emulator startup

### 🔧 **Developer Friendly**
- **Django Framework**: Modern Python web application
- **Single Process**: No complex multi-process architecture
- **Socket Communication**: Direct TCP connection with mGBA
- **Extensible**: Easy to add new games and AI behaviors

## 🏗️ Architecture

### Simple Two-Layer System
1. **mGBA Emulator + Lua Script** (`emulator/script.lua`) - Game interface
2. **AI GBA Player Web Interface** (`ai_gba_player/`) - Django web app with AI service

### Data Flow
```
mGBA → Lua Script → Socket (Port 8888) → AIGameService → LLM API → Button Commands → Back to mGBA
                                     ↓
                            Real-time Chat Interface
                         (Screenshots, AI Responses, Actions)
```

## 📦 Installation

### Requirements
- Python 3.11+
- mGBA emulator
- LLM API key (Google Gemini, OpenAI, or Anthropic)

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
cd ai_gba_player
python manage.py migrate

# Start the web interface
python manage.py runserver
```

## 🎮 Usage

### Configuration
1. **ROM Setup**: Set path to your GBA ROM file
2. **mGBA Setup**: Configure mGBA executable location
3. **AI Settings**: Choose LLM provider and enter API key
4. **Timing**: Set decision cooldown (3-6 seconds recommended)

### Running
1. Start the web interface: `python manage.py runserver`
2. Configure settings at http://localhost:8000
3. Launch mGBA (manually or via "Launch mGBA" button)
4. Start AI connection ("Reset mGBA Connection")
5. Load Lua script in mGBA: `Tools > Script Viewer > Load emulator/script.lua`

### Monitoring
- **Chat Interface**: Real-time AI decisions and game state
- **Service Status**: Connection health and activity monitoring
- **Message History**: Scroll through AI conversation history

## 🗂️ Project Structure

```
ai_gba_player/              # Django web application (MAIN)
├── manage.py              # Django management
├── ai_gba_player/         # Django project settings
├── dashboard/             # Main Django app
│   ├── ai_game_service.py # AI service (socket server + LLM)
│   ├── llm_client.py      # LLM API client
│   ├── models.py          # Database models
│   └── templates/         # Web interface templates
└── static/                # CSS/JS assets

emulator/
└── script.lua             # mGBA Lua script for game control

data/
├── screenshots/           # Game screenshots
└── knowledge_graph.json   # AI memory system

core/                      # Shared utilities
├── base_knowledge_system.py
├── base_game_controller.py
└── screen_capture.py

games/pokemon_red/         # Game-specific modules (extensible)
├── controller.py
├── knowledge_system.py
└── prompt_template.py
```

## 🔧 Configuration Files

### Database Configuration (Primary)
All settings are stored in SQLite database and configured via web interface:
- ROM paths and game settings
- LLM provider and API keys
- Timing and behavior settings

### JSON Configuration (Legacy/Optional)
`config_emulator.json` - Automatically updated when saving AI settings through web interface.

## 🤖 LLM Integration

### Supported Providers
- **Google Gemini** (recommended): `gemini-2.0-flash-exp`
- **OpenAI**: `gpt-4o` or `gpt-4o-mini`
- **Anthropic**: Claude models

### AI Capabilities
- **Visual Analysis**: Analyzes game screenshots to understand current state
- **Decision Making**: Chooses appropriate button actions based on game state
- **Tool Calling**: Uses `press_button` function to send commands to mGBA
- **Error Recovery**: Fallback actions when AI requests fail

## 🧪 Testing

```bash
# Test AI service communication
python test_ai_service.py

# Run Django tests
cd ai_gba_player
python manage.py test
```

## 🛠️ Troubleshooting

### Common Issues
- **mGBA Connection Failed**: Check if mGBA is running and Lua script is loaded
- **AI Service Won't Start**: Verify API key is configured correctly
- **No Screenshots**: Ensure mGBA has ROM loaded and script is active
- **Port Conflicts**: AI service uses port 8888 for mGBA communication

### Debug Mode
Enable verbose logging by adding `--debug` flag or checking Django logs for detailed error information.

## 🎯 Key Features

### Real-time Monitoring
- Live screenshot feed showing what AI sees
- AI reasoning and decision explanations
- Button action confirmations
- Connection status indicators

### Easy Configuration
- Browser-based setup (no manual config file editing)
- Auto-detection of common mGBA installation paths
- One-click ROM loading and emulator launch

### Developer Features
- Clean Django architecture
- Simple socket-based communication
- Extensible game module system
- Comprehensive error handling

## 📚 Documentation

- **Setup Guide**: Complete installation and configuration instructions
- **API Reference**: Django models and service interfaces
- **Game Integration**: How to add support for new GBA games
- **Troubleshooting**: Common issues and solutions

## 🤝 Contributing

Contributions welcome! The simplified architecture makes it easy to:
- Add new LLM providers
- Implement game-specific behaviors
- Enhance the web interface
- Improve AI decision-making

## 📄 License

Based on [martoast/LLM-Pokemon-Red](https://github.com/martoast/LLM-Pokemon-Red) - Extended into a universal GBA gaming platform.

---

**Get started in 2 minutes**: `cd ai_gba_player && python manage.py runserver` → Open http://localhost:8000 🚀