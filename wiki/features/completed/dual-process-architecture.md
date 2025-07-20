# Pokemon AI Dual-Process Architecture

This document describes the new dual-process architecture for the Pokemon Red AI system.

## Architecture Overview

The system has been redesigned to use two separate processes:

1. **Video Capture Process** (`video_capture_process.py`) - Continuously captures screenshots with a rolling window buffer
2. **Game Control Process** (`game_control_process.py`) - Handles game logic, LLM decisions, and emulator communication

## Process Communication

The processes communicate via TCP sockets (default port 8889):
- Game Control requests GIFs from Video Capture
- Video Capture maintains a 20-second rolling window of frames
- When a GIF is requested, it creates a GIF from the last GIF timestamp to current time

## Rolling Window Logic

### First GIF Request
- Video process starts capturing at 00:00:00
- At 00:00:30, game control requests a GIF
- GIF contains frames from 00:00:10 to 00:00:30 (last 20 seconds)
- Video process resets its "last GIF timestamp" to 00:00:30

### Subsequent GIF Requests  
- At 00:00:35, another GIF is requested
- GIF contains frames from 00:00:30 to 00:00:35 (since last GIF)
- Video process resets its "last GIF timestamp" to 00:00:35

This ensures the LLM sees:
1. All thinking time since the last decision
2. All action execution time
3. No duplicate or missing visual information

## File Structure

```
video_capture_process.py     # Standalone video capture with rolling buffer
game_control_process.py      # Game control inheriting from PokemonRedController  
start_dual_process.py        # Launcher script for both processes
config_emulator.json         # Updated configuration with dual-process settings
README_DUAL_PROCESS.md       # This documentation
```

## Configuration

Add to `config_emulator.json`:

```json
{
  "dual_process_mode": {
    "enabled": true,
    "video_capture_port": 8889,
    "rolling_window_seconds": 20,
    "process_communication_timeout": 10
  }
}
```

## Usage

### Option 1: Use the Launcher Script (Recommended)
```bash
python start_dual_process.py --config config_emulator.json
```

### Option 2: Start Processes Manually
```bash
# Terminal 1: Start video capture process
python video_capture_process.py --config config_emulator.json

# Terminal 2: Start game control process  
python game_control_process.py --config config_emulator.json
```

### Setup Sequence
1. Start the dual-process system using one of the methods above
2. Start mGBA and load Pokemon Red ROM
3. In mGBA: Tools > Script Viewer > Load `emulator/script.lua`
4. The AI will start playing automatically

## Process Details

### Video Capture Process Features
- **Continuous capture** at 30 FPS by default
- **Rolling buffer** of 20 seconds (600 frames at 30 FPS)  
- **Memory management** - automatically discards old frames
- **GIF generation** on request with proper frame timing
- **IPC server** for handling requests from game control
- **Status monitoring** and health checks

### Game Control Process Features
- **Inherits from PokemonRedController** - reuses all game logic
- **External video integration** - requests GIFs instead of capturing internally
- **Emulator communication** - maintains socket connection to mGBA
- **LLM decision making** - sends GIFs to AI for button decisions
- **Action execution** - sends button commands to emulator

## Communication Protocol

### GIF Request
```json
{
  "type": "get_gif"
}
```

### GIF Response
```json
{
  "success": true,
  "gif_data": "base64_encoded_gif_bytes",
  "frame_count": 150,
  "duration": 5.0,
  "start_timestamp": 1234567890.0,
  "end_timestamp": 1234567895.0,
  "fps": 30
}
```

### Status Request
```json
{
  "type": "status"
}
```

### Status Response
```json
{
  "running": true,
  "frame_count": 1500,
  "buffer_frames": 600,
  "buffer_duration": 20.0,
  "capture_fps": 30,
  "last_gif_timestamp": 1234567890.0,
  "uptime": 300.5
}
```

## Benefits

1. **Memory Efficiency** - Rolling window prevents unbounded memory growth
2. **Process Isolation** - Video capture crash doesn't affect game control
3. **Visual Continuity** - LLM sees complete timeline since last decision
4. **Scalability** - Can easily add multiple game control processes
5. **Debugging** - Easier to debug and monitor individual components
6. **Performance** - Dedicated video capture process optimized for speed

## Troubleshooting

### Video Process Won't Start
- Check if port 8889 is available
- Verify mGBA window is visible
- Check capture system configuration

### Game Control Can't Connect
- Ensure video process started first
- Check port configuration matches
- Verify network connectivity

### Poor Performance  
- Reduce capture_fps in config
- Reduce rolling_window_seconds
- Check system resources

### Memory Issues
- Monitor buffer_frames in status
- Reduce rolling window duration
- Check for memory leaks in processes

## Future Enhancements

- Multiple game control processes for parallel games
- Distributed video capture across multiple displays
- Real-time video streaming for monitoring
- Advanced GIF compression and optimization
- Process health monitoring and auto-restart