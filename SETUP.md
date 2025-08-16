# Setup Guide - AI GBA Player

Complete setup guide for the AI GBA Player universal gaming framework.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database
```bash
cd ai_gba_player
python manage.py migrate
```

### 3. Start the Web Interface
```bash
python manage.py runserver
```

Open your browser to: **http://localhost:8000**

### 4. Configure Through Web Interface
1. **ROM Configuration**: Set path to your GBA ROM file
2. **mGBA Configuration**: Set path to mGBA executable (auto-detected on macOS)
3. **AI Settings**: Choose LLM provider and enter API key
4. **Save Settings**: Click "Save Config" for each section

### 5. Launch and Connect
1. Click **"Launch mGBA"** (or start mGBA manually)
2. Click **"Reset mGBA Connection"** to start AI service
3. In mGBA: **Tools > Script Viewer > Load** `emulator/script.lua`
4. Watch the AI play in the real-time chat interface!

## 📋 Detailed Setup

### System Requirements
- **Python 3.11+**
- **mGBA emulator** (latest version recommended)
- **GBA ROM file** (legally obtained)
- **LLM API key** (Google Gemini, OpenAI, or Anthropic)

### Installation Steps

#### 1. Clone Repository
```bash
git clone <repository-url>
cd LLM-Pokemon-Red
```

#### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Install mGBA
**macOS (Homebrew):**
```bash
brew install mgba
```

**macOS (Manual):**
Download from [mgba.io](https://mgba.io/downloads.html) and install to `/Applications/mGBA.app`

**Linux:**
```bash
sudo apt-get install mgba-qt  # Ubuntu/Debian
sudo dnf install mgba         # Fedora
```

#### 4. Prepare ROM File
- Obtain a legal GBA ROM file (e.g., Pokémon Ruby, Sapphire, Emerald)
- Place it in an accessible location
- Note the full file path for configuration

### Configuration

#### Web Interface Configuration (Recommended)
1. Start the web interface: `cd ai_gba_player && python manage.py runserver`
2. Open http://localhost:8000 in your browser
3. Configure all settings through the web interface:

**ROM Configuration:**
- ROM File Path: `/path/to/your/pokemon.gba`
- Display Name: Pokemon Ruby (optional)

**mGBA Configuration:**
- mGBA Executable: Auto-detected or set manually
- Common paths:
  - macOS: `/Applications/mGBA.app/Contents/MacOS/mGBA`
  - Linux: `/usr/bin/mgba-qt`

**AI Settings:**
- LLM Provider: Google Gemini (recommended)
- API Key: Your provider's API key
- Decision Cooldown: 3-6 seconds (recommended)

#### Manual Configuration (Optional)
If needed, you can also edit `config_emulator.json`:
```json
{
  "llm_provider": "google",
  "decision_cooldown": 3,
  "providers": {
    "google": {
      "api_key": "YOUR_API_KEY_HERE",
      "model_name": "gemini-2.0-flash-exp"
    }
  }
}
```

### LLM API Setup

#### Google Gemini (Recommended)
1. Visit [AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Enter the key in the web interface under "AI Settings"

#### OpenAI
1. Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Choose OpenAI as provider and enter the key

#### Anthropic
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Generate an API key
3. Choose Anthropic as provider and enter the key

### Testing the Setup

#### 1. Test Web Interface
```bash
cd ai_gba_player
python manage.py runserver
```
Visit http://localhost:8000 and verify the interface loads

#### 2. Test AI Service
```bash
# In one terminal: start Django server
cd ai_gba_player && python manage.py runserver

# In another terminal: test AI service
python test_ai_service.py
```

#### 3. Test Full Integration
1. Start web interface
2. Configure all settings
3. Click "Launch mGBA"
4. Load a ROM in mGBA
5. Click "Reset mGBA Connection"
6. Load `emulator/script.lua` in mGBA Script Viewer
7. Watch real-time AI gameplay in chat interface

## 🛠️ Troubleshooting

### Common Issues

#### mGBA Won't Launch
- **Issue**: "mGBA executable not found"
- **Solution**: Set correct path in mGBA Configuration, or install mGBA

#### AI Service Connection Failed
- **Issue**: "Connection refused on port 8888"
- **Solution**: 
  1. Ensure AI service is started via "Reset mGBA Connection"
  2. Check no other process is using port 8888
  3. Restart the AI service

#### No Screenshots in Chat
- **Issue**: No images appearing in chat interface
- **Solution**:
  1. Ensure ROM is loaded in mGBA
  2. Verify Lua script is loaded and running
  3. Check mGBA console for script errors

#### LLM API Errors
- **Issue**: "AI API failed" or fallback mode
- **Solution**:
  1. Verify API key is correct
  2. Check internet connection
  3. Ensure API quota is not exceeded
  4. Try a different LLM provider

#### Port Conflicts
- **Issue**: "Port already in use"
- **Solution**:
  1. Stop other Django servers: `pkill -f runserver`
  2. Kill processes on port 8888: `lsof -ti:8888 | xargs kill`
  3. Restart the services

### Debug Mode
Enable verbose logging by checking Django console output when running `python manage.py runserver`

### Configuration Verification
Check your configuration is working:
```bash
# Test API endpoints
curl http://localhost:8000/api/chat-messages/
curl -X POST http://localhost:8000/api/restart-service/
```

## 🎯 Advanced Configuration

### Custom Game Support
To add support for new GBA games:
1. Create game-specific controller in `games/your_game/`
2. Implement game-specific prompts and knowledge
3. Update configuration to recognize new game

### Performance Tuning
- **Decision Cooldown**: Increase for slower, more thoughtful decisions
- **Model Selection**: Use faster models (gemini-2.0-flash-exp) for real-time play
- **Screenshot Quality**: Adjust in mGBA settings for clearer AI vision

### Multiple ROM Support
- Configure different ROM paths for different games
- Use web interface to switch between games easily
- Each game maintains separate AI context

## 📚 Next Steps

After successful setup:
1. **Monitor AI Gameplay**: Watch real-time chat interface
2. **Experiment with Settings**: Try different cooldowns and models
3. **Add New Games**: Extend support to other GBA titles
4. **Customize Prompts**: Modify AI behavior for specific games

## 🤝 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Django console logs for detailed errors
3. Test individual components (web interface, AI service, mGBA)
4. Ensure all dependencies are correctly installed

**Quick Start Reminder**: `cd ai_gba_player && python manage.py runserver` → http://localhost:8000 🚀