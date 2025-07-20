# Process Dependency Solution

## 🔍 Problem Analysis

Based on the detailed error logs, the issue is a **process dependency chain failure**:

```
video_capture_process (fails) → game_control_process (cannot connect) → both fail
```

**Root Cause**: `video_capture_process` is failing to start, which prevents `game_control_process` from connecting to it.

## ✅ Improvements Made

### 1. Enhanced Error Reporting
- **Before**: Silent failures, endless restart loops
- **After**: Clear error messages with full stderr/stdout, no restart loops

**Example Error Output**:
```
❌ Process game_control failed:
Exit code: 1  
STDERR: ❌ Cannot connect to video capture process
STDOUT: 🎮 Starting Pokemon AI Game Control Process
⚠️ Optional process game_control failed - not restarting
```

### 2. Smart Dependency Management
- Added dependency checking before process startup
- Skip dependent processes when prerequisites fail
- Prevent cascade failures

### 3. Admin Panel for Diagnosis
- Real-time process monitoring
- Manual restart controls
- Process log viewing
- Clear status indicators

## 🛠️ Diagnostic Tools

### Tool 1: Standalone Video Capture Test
```bash
python test_video_capture_standalone.py
```
**Purpose**: Test video_capture in isolation to identify the root cause

### Tool 2: Admin Panel
1. Open `http://localhost:5173`
2. Click `⚙️ Admin` tab
3. Select `video_capture` process
4. View logs and error details
5. Try manual restart

### Tool 3: Debug Mode
```bash
python dashboard.py --debug --config config_emulator.json
```
**Purpose**: Get verbose logging for all process operations

## 🎯 Solution Options

### Option A: Fix Video Capture (Recommended)
1. **Diagnose the root cause**:
   ```bash
   python test_video_capture_standalone.py
   ```

2. **Common issues to check**:
   - Missing dependencies (cv2, PIL, mss)
   - mGBA not running or wrong window position
   - Screen capture permissions on macOS
   - Port conflicts (8889)

3. **Fix identified issues** and restart dashboard

### Option B: Use Frontend-Only Mode
```bash
python dashboard.py --frontend-only --config config_emulator.json
```
**Purpose**: Test dashboard functionality without AI processes

### Option C: Manual Process Management
1. Start dashboard normally
2. Use Admin panel to:
   - Check process status
   - View detailed error logs  
   - Manually restart processes after fixing issues

## 📋 Next Steps

### Immediate Actions
1. **Run diagnostic**: `python test_video_capture_standalone.py`
2. **Check dependencies**: Ensure cv2, PIL, mss are installed
3. **Verify mGBA**: Make sure game emulator is running
4. **Review logs**: Use Admin panel to see detailed errors

### If Video Capture Works Standalone
- Issue is with dashboard process management
- Use `--debug` mode to see detailed startup logs
- Check port conflicts or timing issues

### If Video Capture Fails Standalone  
- Install missing Python packages
- Fix screen capture permissions
- Check mGBA window detection
- Review config_emulator.json settings

## 💡 Current Status

**✅ What's Working**:
- Dashboard frontend and backend
- Admin panel with process controls
- Clear error reporting
- No more crash loops
- Graceful failure handling

**🔧 What Needs Fixing**:
- Root cause of video_capture failure
- Process dependency chain once video_capture works

**🎯 Expected Outcome**:
Once video_capture is fixed, game_control should connect successfully and the full AI system will work.

## 🚀 Admin Features Available

### Real-time Monitoring
- Process status dashboard
- Live error logs
- System resource usage
- WebSocket connection status

### Manual Controls
- Start/Stop individual processes
- Force restart with error clearing
- Dependency-aware startup order
- Graceful shutdown handling

### Debug Information
- Full stderr/stdout capture
- Timestamped error logs
- Process lifecycle tracking
- Dependency validation

The dashboard now provides professional-grade process management with clear visibility into what's happening and manual controls to fix issues as they arise.