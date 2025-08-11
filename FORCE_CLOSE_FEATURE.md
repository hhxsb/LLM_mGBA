# Force Close Existing Process Feature

## Overview
Added a new force close feature to `main.py` that automatically detects and terminates any existing AI GBA Player processes using port 8000. This prevents the common "port already in use" error and makes the workflow more robust.

## Usage

### Automatic Force Close (Built-in)
When you run `main.py` normally, it automatically checks for and closes any existing processes using port 8000:

```bash
python main.py
```

### Manual Force Close Only
To only force close existing processes without starting the system:

```bash
python main.py --kill-port
```

### Force Close and Start
To explicitly force close and then start (same as default behavior):

```bash
python main.py --kill-port --start
```

### Custom Port
To check/clean a different port:

```bash
python main.py --kill-port --port 8080
```

## How It Works

### 1. Process Detection
- Scans all running processes for those using the target port (default: 8000)
- Identifies Django/Python processes by checking command line arguments
- Avoids duplicate processing of the same PID

### 2. Graceful Termination
- First attempts graceful termination with `SIGTERM`
- Waits up to 5 seconds for graceful shutdown
- Falls back to force kill (`SIGKILL`) if needed
- Provides clear feedback about each step

### 3. Port Validation
- Double-checks that the port is actually available after cleanup
- Provides additional cleanup attempts if needed
- Only proceeds with startup once port is confirmed available

## Example Output

When existing processes are found and closed:

```
🔍 Checking for existing processes on port 8000...
🔧 Found process using port 8000: PID 8981 (Python)
   Command: /opt/homebrew/Cellar/python@3.11/3.11.13/Frameworks/Python.framework/Versions/3.11/Resources/Python...
✅ Gracefully stopped process 8981
✅ Cleaned up 1 process(es) using port 8000
```

When no conflicting processes are found:

```
🔍 Checking for existing processes on port 8000...
✅ No conflicting processes found on port 8000
```

## Benefits

1. **Eliminates "Port in Use" Errors**: No more manual process hunting and killing
2. **Smooth Development Workflow**: Restart main.py without worrying about cleanup
3. **Safe Process Detection**: Only targets Django/Python processes, not other services
4. **Graceful Shutdown**: Attempts clean termination before force killing
5. **Clear Feedback**: Shows exactly what processes were found and terminated

## Technical Details

- Uses `psutil` library for robust process management
- Implements duplicate PID detection to avoid processing same process multiple times
- Uses `proc.net_connections()` for modern psutil compatibility
- Includes comprehensive error handling for process access and termination
- Validates port availability after cleanup

## Command Line Help

```bash
python main.py --help
```

Shows all available options and usage examples.

## Testing

The feature includes comprehensive tests:

- `test_force_close_feature.py` - End-to-end testing of force close functionality
- Tests graceful termination, port validation, and process cleanup
- Verifies web interface shutdown and port availability

Run tests with:
```bash
python test_force_close_feature.py
```

This feature makes AI GBA Player much more user-friendly by eliminating the need for manual process management!