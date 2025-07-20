# Dashboard & Admin Panel Guide

This guide covers the unified dashboard system with real-time monitoring and admin controls for the AI Pokemon Trainer.

## Overview

The dashboard provides a comprehensive interface for monitoring and managing the AI Pokemon system, featuring:
- **Real-time AI monitoring** with WebSocket streaming
- **Process management** with dependency-aware controls
- **Admin panel** for system administration
- **Live log viewing** for debugging
- **System health monitoring** for all processes

## Access URLs

- **Frontend Dashboard**: http://localhost:5173
- **Backend API**: http://127.0.0.1:3000
- **WebSocket**: ws://127.0.0.1:3000/ws

## Main Dashboard Interface

### Real-time Monitoring
The main dashboard displays live AI activity:

#### AI Interaction Chat
- **GIF Streams**: Live video from game capture with optimized compression
- **AI Responses**: Real-time LLM decisions with reasoning and confidence
- **Button Actions**: Game controls with button names and durations
- **Timestamps**: All messages timestamped for analysis

#### System Status
- **Process Health**: Real-time status of all AI processes
- **Connection Status**: WebSocket and IPC connection monitoring
- **Performance Metrics**: Frame rates, processing times, memory usage

### Navigation
- **Dashboard Tab**: Main monitoring interface
- **⚙️ Admin Tab**: Process management and system administration

## Admin Panel Features

Access the admin panel by clicking the ⚙️ Admin tab in the dashboard.

### Process Management

#### Process List
The admin panel shows all AI processes with:
- **Process Name**: video_capture, game_control, knowledge_system, frontend
- **Status**: ✅ Running, ❌ Stopped, 🔄 Starting, ⚠️ Error
- **PID**: Process ID for system monitoring
- **Uptime**: How long the process has been running
- **Health**: Process responsiveness and connection status

#### Process Controls
Each process has individual controls:
- **▶️ Start**: Launch stopped processes
- **⏸️ Stop**: Gracefully shutdown processes
- **🔄 Restart**: Stop and restart processes
- **🚫 Force Restart**: Kill and restart unresponsive processes

#### Dependency Management
The system understands process dependencies:
- **video_capture** → **game_control** → **knowledge_system**
- Starting a process automatically starts its dependencies
- Stopping a process warns about dependent processes

### Log Viewing

#### Real-time Logs
- **Live Streaming**: Logs update in real-time as processes run
- **Error Highlighting**: Errors and warnings are color-coded
- **Auto-scroll**: Latest logs automatically visible
- **Log Levels**: Debug, info, warning, error messages

#### Log Controls
- **Process Selection**: View logs for specific processes
- **Log Level Filter**: Filter by debug, info, warning, error
- **Clear Logs**: Clear current log display
- **Download Logs**: Export logs for external analysis

#### Historical Logs
- **Process History**: View logs from previous runs
- **Error Analysis**: Review crash logs and error patterns
- **Performance Logs**: Analyze timing and performance data

### System Monitoring

#### Process Health
- **CPU Usage**: Per-process CPU consumption
- **Memory Usage**: RAM consumption monitoring
- **Connection Status**: Socket and WebSocket health
- **Response Times**: Process responsiveness metrics

#### AI Performance
- **Decision Times**: How long AI takes to make decisions
- **GIF Generation**: Video processing performance
- **WebSocket Latency**: Real-time streaming performance
- **Error Rates**: Process failure and recovery statistics

## Configuration

### Dashboard Settings
Located in `config_emulator.json`:

```json
{
  "dashboard": {
    "enabled": true,
    "port": 3000,
    "websocket_port": 3001,
    "auto_start_processes": true,
    "theme": "pokemon",
    "chat_history_limit": 100,
    "gif_retention_minutes": 30,
    "streaming_mode": false,
    "auto_restart": true
  }
}
```

#### Key Settings
- **`auto_start_processes`**: Automatically start AI processes on dashboard startup
- **`chat_history_limit`**: Maximum messages shown in chat interface
- **`gif_retention_minutes`**: How long to keep GIF history
- **`auto_restart`**: Enable automatic process restart on failures
- **`theme`**: Dashboard color scheme (pokemon, dark, light)

### Process Configuration
Control individual process behavior:

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

## Startup & Usage

### Easy Startup (Recommended)
```bash
# Start everything with one command
python dashboard.py --config config_emulator.json
```

This automatically:
1. Starts the dashboard backend server
2. Launches the React frontend
3. Starts video capture process
4. Starts game control process
5. Starts knowledge system process

### Manual Startup (Development)
```bash
# Start processes individually
python video_capture_process.py --config config_emulator.json
python game_control_process.py --config config_emulator.json
python dashboard.py --config config_emulator.json
```

### Dashboard Access
1. Open browser to http://localhost:5173
2. Main dashboard shows AI activity in real-time
3. Click ⚙️ Admin tab for process management
4. Use admin controls to start/stop/restart processes

## WebSocket Integration

### Message Types
The dashboard receives real-time messages:

#### GIF Messages
```json
{
  "type": "chat_message",
  "data": {
    "message": {
      "type": "gif",
      "content": {
        "gif": {
          "data": "base64_gif_data",
          "metadata": {
            "frameCount": 30,
            "duration": 1.0,
            "fps": 30
          }
        }
      }
    }
  }
}
```

#### AI Response Messages
```json
{
  "type": "chat_message",
  "data": {
    "message": {
      "type": "response",
      "content": {
        "response": {
          "text": "AI decision text",
          "reasoning": "AI reasoning",
          "confidence": 0.95,
          "processing_time": 2.1
        }
      }
    }
  }
}
```

#### Action Messages
```json
{
  "type": "chat_message",
  "data": {
    "message": {
      "type": "action",
      "content": {
        "action": {
          "buttons": ["6", "0"],
          "button_names": ["UP", "A"],
          "durations": [0.5, 0.3]
        }
      }
    }
  }
}
```

## Troubleshooting

### Common Issues

#### Dashboard Won't Load
- **Check ports**: Ensure 5173 (frontend) and 3000 (backend) are available
- **Browser cache**: Clear cache or try incognito mode
- **Firewall**: Check firewall isn't blocking local connections

#### Process Won't Start
1. Check admin panel for error messages
2. View process logs for detailed error information
3. Verify dependencies are installed (`pip install opencv-python`)
4. Check configuration file for correct paths and API keys

#### Missing AI Messages
1. Verify processes are connected (green status in admin panel)
2. Check WebSocket connection in browser developer tools
3. Restart processes using admin panel controls
4. Review process logs for WebSocket connection errors

#### Process Crashes
1. Use admin panel to view crash logs
2. Check for dependency issues (missing cv2, API keys)
3. Use "Force Restart" for unresponsive processes
4. Review system resources (CPU, memory usage)

### Log Analysis
Common log patterns to look for:

#### Successful Startup
```
✅ Video capture process started successfully
✅ Connected to dashboard WebSocket
📸 Generated GIF: 30 frames, 1.5s
📤 Sent GIF to dashboard: 25000 bytes, 30 frames
```

#### Connection Issues
```
❌ Failed to connect to dashboard (attempt 1): [Errno 61] Connection refused
⚠️ Dashboard connection failed: [Errno 61] Connection refused
```

#### Process Communication
```
🔗 Connecting to video process at 127.0.0.1:8889
✅ GIF received: 30 frames, 1.50s
📤 Sent AI response to dashboard: 45 chars
```

## Advanced Features

### Custom Themes
The dashboard supports custom themes in the configuration:
- `pokemon`: Pokemon-inspired color scheme (default)
- `dark`: Dark mode for low-light environments
- `light`: Light mode for bright environments

### Performance Monitoring
The admin panel tracks:
- **Frame Processing**: Video capture and GIF generation performance
- **AI Decision Times**: How quickly the LLM makes decisions
- **Memory Usage**: RAM consumption by each process
- **Network Latency**: WebSocket message delivery times

### API Integration
The dashboard exposes REST APIs for external integration:
- **`GET /api/v1/processes`**: List all processes and status
- **`POST /api/v1/processes/{name}/start`**: Start a specific process
- **`POST /api/v1/processes/{name}/stop`**: Stop a specific process
- **`GET /api/v1/processes/{name}/logs`**: Get process logs

This allows external tools to integrate with the AI Pokemon system for automated testing, monitoring, and control.