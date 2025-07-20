# Setup Guide - AI Pokemon Trainer

Complete setup guide for the AI Pokemon Red benchmark system with unified dashboard.

## Quick Start (Recommended)

### 1. Install Dependencies
```bash
pip install "google-generativeai>=0.3.0" pillow openai anthropic python-dotenv opencv-python
```

### 2. Configure API Key
Edit `config_emulator.json` and add your Gemini API key:
```json
{
  "providers": {
    "google": {
      "api_key": "YOUR_GEMINI_API_KEY_HERE",
      "model_name": "gemini-2.5-pro",
      "max_tokens": 1024
    }
  }
}
```

### 3. Setup Game Emulator
1. Download and install [mGBA emulator](https://mgba.io/downloads.html)
2. Obtain Pokemon Red ROM (not provided)
3. Start mGBA and load Pokemon Red ROM

### 4. Start the System
```bash
# One command to start everything!
python dashboard.py --config config_emulator.json
```

### 5. Update Lua Script Path
Edit `emulator/script.lua` and update the project root path:
```lua
local projectRoot = "/path/to/your/LLM_mGBA"  -- Change this to your project path
```

### 6. Load Lua Script
In mGBA:
1. Go to Tools > Script Viewer
2. Click "Load" and select `emulator/script.lua`
3. The AI will now control the game automatically

### 7. Monitor with Dashboard
Open your browser to http://localhost:5173 to see:
- Real-time AI decisions and responses
- Live video feed from the game
- Process management controls
- System logs and health monitoring

## Detailed Setup

### Prerequisites

#### System Requirements
- **Python 3.8+** (recommended: Python 3.10+)
- **mGBA Emulator** (latest version)
- **Pokemon Red ROM** (Game Boy)
- **Internet connection** (for LLM API calls)

#### API Requirements
- **Google Gemini API key** (required)
  - Sign up at [Google AI Studio](https://makersuite.google.com/)
  - Generate API key for Gemini Pro
  - Free tier available with rate limits

#### Operating System
- **Windows**: Supported with some screen capture limitations
- **macOS**: Fully supported (recommended)
- **Linux**: Fully supported

### Installation Steps

#### 1. Clone Repository
```bash
git clone https://github.com/hhxsb/LLM_mGBA.git
cd LLM_mGBA
```

#### 2. Python Dependencies
```bash
# Install required packages
pip install -r requirements.txt

# Or install manually:
pip install "google-generativeai>=0.3.0" pillow openai anthropic python-dotenv opencv-python
```

#### 3. Configuration File
Create/edit `config_emulator.json`:
```json
{
  "game": "pokemon_red",
  "llm_provider": "google",
  "providers": {
    "google": {
      "api_key": "YOUR_GEMINI_API_KEY",
      "model_name": "gemini-2.5-pro",
      "max_tokens": 1024
    }
  },
  "host": "127.0.0.1",
  "port": 8888,
  "decision_cooldown": 5,
  "debug_mode": true,
  "dual_process_mode": {
    "enabled": true,
    "video_capture_port": 8889,
    "rolling_window_seconds": 20,
    "process_communication_timeout": 25
  },
  "dashboard": {
    "enabled": true,
    "port": 3000,
    "auto_start_processes": true,
    "theme": "pokemon"
  },
  "capture_system": {
    "type": "screen",
    "capture_fps": 30,
    "gif_optimization": {
      "max_gif_frames": 150,
      "gif_width": 320,
      "target_gif_duration": 5.0
    }
  }
}
```

#### 4. mGBA Emulator Setup
1. **Download mGBA**: Get latest version from [mgba.io](https://mgba.io/downloads.html)
2. **Install mGBA**: Follow platform-specific installation instructions
3. **Configure mGBA**:
   - Enable Tools > Script Viewer
   - Set window size to reasonable resolution (recommended: 3x scale)
   - Configure input controls (keyboard recommended)

#### 5. Pokemon Red ROM
- Obtain Pokemon Red ROM file (`.gb` format)
- Place in accessible location
- Load in mGBA: File > Load ROM

### Startup Methods

#### Method 1: Easy Startup (Recommended)
```bash
# Start everything with unified dashboard
python dashboard.py --config config_emulator.json
```

This will:
- Start dashboard backend (port 3000)
- Launch React frontend (port 5173)
- Start video capture process
- Start game control process
- Start knowledge system process
- Display all URLs for access

#### Method 2: Manual Startup (Development)
```bash
# Terminal 1: Video capture
python video_capture_process.py --config config_emulator.json

# Terminal 2: Game control
python game_control_process.py --config config_emulator.json

# Terminal 3: Dashboard (optional)
python dashboard.py --config config_emulator.json
```

#### Method 3: Individual Process Testing
```bash
# Test video capture only
python video_capture_process.py --config config_emulator.json

# Test WebSocket integration
python test_dashboard_websocket.py

# Test complete system
python test_complete_system.py
```

### Startup Sequence

#### Critical Order
1. **Start mGBA** and load Pokemon Red ROM
2. **Start AI processes** (dashboard handles this automatically)
3. **Load Lua script** in mGBA: Tools > Script Viewer > Load `emulator/script.lua`
4. **Access dashboard** at http://localhost:5173

#### Verification Steps
1. **Check process status** in admin panel (⚙️ Admin tab)
2. **Verify connections**:
   - All processes show ✅ Running status
   - WebSocket connected (visible in dashboard)
   - Game control connected to emulator
3. **Test AI control**:
   - Move character in game manually
   - Load Lua script
   - AI should take control within 5-10 seconds

## Configuration Options

### Essential Settings

#### API Configuration
```json
{
  "providers": {
    "google": {
      "api_key": "your-api-key-here",
      "model_name": "gemini-2.5-pro",
      "max_tokens": 1024
    }
  }
}
```

#### Performance Settings
```json
{
  "decision_cooldown": 5,          // Seconds between AI decisions
  "capture_fps": 30,               // Video capture frame rate
  "rolling_window_seconds": 20,    // Video buffer duration
  "debug_mode": true               // Verbose logging
}
```

#### Dashboard Settings
```json
{
  "dashboard": {
    "enabled": true,
    "port": 3000,
    "auto_start_processes": true,
    "chat_history_limit": 100,
    "gif_retention_minutes": 30,
    "theme": "pokemon"
  }
}
```

### Advanced Configuration

#### Video Capture Optimization
```json
{
  "capture_system": {
    "capture_fps": 30,
    "gif_optimization": {
      "max_gif_frames": 150,
      "gif_width": 320,
      "target_gif_duration": 5.0,
      "max_gif_duration": 10.0
    },
    "frame_enhancement": {
      "scale_factor": 3,
      "contrast": 1.5,
      "saturation": 1.8,
      "brightness": 1.1
    }
  }
}
```

#### Process Communication
```json
{
  "dual_process_mode": {
    "enabled": true,
    "video_capture_port": 8889,
    "rolling_window_seconds": 20,
    "process_communication_timeout": 25
  }
}
```

## Troubleshooting

### Common Setup Issues

#### 1. Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'cv2'`
**Solution**: 
```bash
pip install opencv-python
```

#### 2. API Key Issues
**Error**: API authentication failures
**Solution**:
- Verify API key is correct in `config_emulator.json`
- Check Gemini API quota and billing
- Test API key with simple request

#### 3. Port Conflicts
**Error**: `Address already in use`
**Solution**:
- Dashboard automatically handles port conflicts
- Manually kill processes on ports 3000, 5173, 8888, 8889
- Use different ports in configuration

#### 4. mGBA Connection
**Error**: `Cannot connect to emulator`
**Solution**:
- Ensure mGBA is running with Pokemon Red loaded
- Load Lua script AFTER starting AI processes
- Check firewall isn't blocking local connections

#### 5. Process Crashes
**Error**: Processes repeatedly crash
**Solution**:
- Check admin panel logs for detailed errors
- Verify all dependencies installed
- Use force restart in admin panel
- Check system resources (CPU, memory)

### Performance Issues

#### Slow AI Decisions
- Increase `decision_cooldown` to reduce API pressure
- Check internet connection speed
- Verify Gemini API isn't rate limited
- Monitor CPU usage during decision making

#### Video Capture Problems
- Reduce `capture_fps` if system is overloaded
- Adjust `gif_optimization` settings for smaller files
- Check screen capture permissions on macOS
- Verify mGBA window is visible and focused

#### Dashboard Not Loading
- Clear browser cache
- Try incognito/private mode
- Check browser console for errors
- Verify ports 3000 and 5173 are accessible

### Debug Mode

Enable detailed logging:
```json
{
  "debug_mode": true
}
```

This provides:
- Verbose process communication logs
- AI decision reasoning details
- WebSocket message tracing
- Performance timing information

### Getting Help

#### Log Analysis
1. **Enable debug mode** in configuration
2. **Use admin panel** to view real-time logs
3. **Check process status** in admin panel
4. **Export logs** for analysis

#### System Information
Useful information for troubleshooting:
- Operating system and version
- Python version (`python --version`)
- mGBA version
- Configuration file contents (remove API key)
- Error messages from logs

#### Test Scripts
Run diagnostic tests:
```bash
# Test complete system
python test_complete_system.py

# Test WebSocket integration
python test_dashboard_websocket.py

# Test video capture
python test_video_capture_standalone.py
```

## Advanced Setup

### Development Environment

#### Frontend Development
```bash
cd dashboard/frontend
npm install
npm run dev  # Start development server
```

#### Backend Development
```bash
# Run dashboard backend only
python dashboard/backend/main.py
```

#### Custom Configuration
Create environment-specific configs:
```bash
cp config_emulator.json config_development.json
# Edit config_development.json for development settings
python dashboard.py --config config_development.json
```

### Production Deployment

#### Docker Setup (Optional)
```bash
# Build Docker image
docker build -t pokemon-ai .

# Run with Docker
docker run -p 3000:3000 -p 5173:5173 -p 8888:8888 -p 8889:8889 pokemon-ai
```

#### System Service (Linux)
Create systemd service for automatic startup:
```ini
[Unit]
Description=Pokemon AI Dashboard
After=network.target

[Service]
Type=simple
User=pokemon
WorkingDirectory=/opt/pokemon-ai
ExecStart=/usr/bin/python dashboard.py --config config_emulator.json
Restart=always

[Install]
WantedBy=multi-user.target
```

This setup guide should get you running with the AI Pokemon system quickly and help troubleshoot any issues that arise during setup.