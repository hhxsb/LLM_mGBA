# Child Process Logging Architecture

## Overview

Implements a clean multi-process logging architecture where child processes (game_control, video_capture) log to individual files while the main dashboard process remains clean. Logs are forwarded to the existing admin panel for real-time monitoring.

## Architecture Specifications

### 1. Child Process Logging Architecture

**Individual Log Files:**
- Each child process writes to its own persistent log file
- File naming: `/tmp/pokemon_ai_logs/{process_name}.log` (no PID, overwrite existing)
- Examples: 
  - `/tmp/pokemon_ai_logs/game_control.log`
  - `/tmp/pokemon_ai_logs/video_capture.log`
- File behavior: Overwrite existing file on process start (not append)
- Persistence: Files remain after process exit for debugging

**Child Process Behavior:**
- Log to both console (their own stdout) AND their individual log file
- Use same formatter as main process for consistency
- Camera emoji logs at INFO level (always visible)
- Debug logs at DEBUG level (when debug flag enabled)

### 2. Main Process Logging Behavior

**Clean Main Console:**
- Dashboard process logs only its own events
- Show log file paths at startup for easy access
- No child process log content in main console
- Clean, professional output for production use

**Log File Path Broadcasting:**
- When child process starts: Log the path to its log file
- Format: `📁 Process {process_name} logging to: {log_file_path}`
- Users can `tail -f` these files manually if needed

### 3. Admin Panel Log Forwarding

**WebSocket Log Streaming:**
- New WebSocket message type: `log_stream`
- Fire-and-forget: No backend storage, immediate forward to frontend
- Stream both main process logs AND child process logs
- Message format:
```typescript
{
  type: "log_stream",
  data: {
    source: "dashboard" | "game_control" | "video_capture",
    level: "DEBUG" | "INFO" | "WARNING" | "ERROR", 
    message: string,
    timestamp: number,
    process_id: string
  }
}
```

**Log Capture Mechanism:**
- Custom logging handler that forwards to WebSocket
- Captures logs from all processes via individual log file monitoring
- Rate limiting: Max 100 logs/second per process (prevent spam)
- Filter: Only forward INFO+ level logs (unless debug mode)

### 4. Frontend Admin Panel Integration

**Leverage Existing Design:**
- Extend existing admin panel's process-specific log sections
- Each process card shows its own logs in real-time
- Maintain existing UI/UX patterns and styling
- Add log file path display in process status

**Enhanced Process Cards:**
```
┌─────────────────────────────────────────────────────────┐
│ Game Control Process                        [Restart]   │
├─────────────────────────────────────────────────────────┤
│ Status: ✅ Running (PID: 12345)                         │
│ Log file: /tmp/pokemon_ai_logs/game_control.log         │
├─────────────────────────────────────────────────────────┤
│ Recent logs:                              [View All]    │
│ 17:30:16 INFO: 📸 TIMELINE T+0.0s: Game Control...     │
│ 17:30:17 INFO: 📸 TIMELINE T+0.3s: Receives GIF...     │
│ 17:30:18 INFO: 📸 TIMELINE T+6.0s: Sends AI response   │
└─────────────────────────────────────────────────────────┘
```

**Frontend Memory Management:**
- Keep max 100 log entries per process in memory
- FIFO queue: Remove oldest when limit exceeded
- No persistence: Logs lost on page refresh (intentional)
- Performance: Efficient React rendering with process isolation

### 5. Implementation Components

**Backend Changes:**
1. `core/logging_config.py` - Individual log files per process (overwrite mode)
2. `core/log_forwarder.py` - WebSocket log forwarding handler  
3. `dashboard/backend/websocket_handler.py` - Add log_stream message type
4. `dashboard/backend/process_manager.py` - Log child process file paths

**Frontend Changes:**
1. `dashboard/frontend/src/components/AdminPanel.tsx` - Enhance existing process cards
2. `dashboard/frontend/src/hooks/useWebSocket.ts` - Handle log_stream messages
3. `dashboard/frontend/src/types/` - TypeScript definitions for log messages

### 6. Performance & Resource Management

**Backend:**
- Non-blocking log file tailing using asyncio
- Rate limiting to prevent WebSocket flooding  
- Graceful error handling if log files are rotated/deleted
- Clean shutdown: Stop all log monitoring tasks

**Frontend:**
- Efficient React rendering with process-specific state
- Memory-conscious log entry pruning per process
- Smooth auto-scroll within process log sections
- Leverage existing admin panel performance patterns

### 7. Error Handling & Edge Cases

**File System Issues:**
- Log directory creation failure → Fallback to console only
- Log file permission issues → Log warning, continue
- Disk space full → Truncate old logs, continue

**Process Lifecycle:**
- Child process crash → Keep log file, mark as "disconnected"
- Process restart → Overwrite existing log file (clean start)
- Dashboard restart → Discover existing child log files

**WebSocket Issues:**
- Connection lost → Buffer logs, replay on reconnect
- Slow client → Drop old logs, keep recent ones
- Multiple clients → Broadcast to all, each manages own memory

## Implementation Phases

### Phase 1: Individual Log Files + Path Broadcasting
- Modify `core/logging_config.py` for individual process log files
- Update process manager to log child process file paths
- Test file creation and overwrite behavior

### Phase 2: WebSocket Log Forwarding Infrastructure  
- Create `core/log_forwarder.py` for real-time log streaming
- Add log_stream message type to WebSocket handler
- Implement rate limiting and error handling

### Phase 3: Admin Panel Integration
- Enhance existing process cards with log display
- Add log file path information to process status
- Implement real-time log streaming in existing UI

### Phase 4: Performance Optimization
- Add filtering and search within process log sections
- Optimize memory usage and rendering performance
- Polish UX for production use

## Benefits

- ✅ **Clean main console** - Professional dashboard output
- ✅ **Individual debugging** - Easy to debug specific processes
- ✅ **Real-time monitoring** - Live logs in familiar admin interface
- ✅ **No memory bloat** - Fire-and-forget architecture
- ✅ **Persistent logs** - Debug files remain after process exit
- ✅ **Consistent UX** - Leverages existing admin panel design

## Usage

**For Users:**
- Main dashboard console shows only dashboard events
- Admin panel provides real-time process-specific logs
- Log files available for manual inspection with `tail -f`

**For Developers:**
- Debug individual processes with dedicated log files
- Monitor all processes simultaneously in admin panel
- Clean separation of concerns between processes

---

**Implementation Status**: Planned  
**Priority**: High  
**Dependencies**: Existing admin panel infrastructure  
**Estimated Effort**: 2-3 development cycles