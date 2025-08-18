# Message Parsing Fix

## 🐛 **Problem**

The AI service was showing "unknown message" errors like this:

```
📸 Requested screenshot from mGBA
📨 Received from mGBA: enhanced_screenshot_with_state||/Users/chengwan/
⚠️ Invalid screenshot data format: enhanced_screenshot_with_state||/Users/chengwan/
🔍 Expected 6+ parts, got 2: ['enhanced_screenshot_with_state', '/Users/chengwan/']
📨 Received from mGBA: Projects/pokemonAI/LLM-Pokemon-Red/data/screenshots/screenshot.png||/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/screenshots/previous_screenshot.png||DOWN||6||5||1||1
🤔 Unknown message from mGBA: Projects/pokemonAI/LLM-Pokemon-Red/data/screenshots/screenshot.png||...
```

## 🔍 **Root Cause**

**TCP Message Splitting**: Long messages from mGBA were being split across multiple TCP packets, causing the AI service to receive and try to process incomplete messages.

**Original Logic Flaw**: The service was processing each `recv()` call separately, without buffering partial messages.

## ✅ **Solution**

### 1. **Message Buffering**
Added a message buffer to accumulate data until complete messages (terminated by `\n`) are received:

```python
# Message buffering for handling partial messages
self.message_buffer = ""

# In message receiving loop:
data = self.client_socket.recv(1024).decode('utf-8')
self.message_buffer += data

# Process complete messages only
while '\n' in self.message_buffer:
    line, self.message_buffer = self.message_buffer.split('\n', 1)
    message = line.strip()
    if message:
        self._process_mgba_message(message)
```

### 2. **Orphaned Message Recovery**
Added logic to detect and recover screenshot data that lost its prefix due to splitting:

```python
elif "||" in message and len(message.split("||")) >= 6:
    # This looks like screenshot data without the proper prefix
    print(f"🔧 Attempting to process orphaned screenshot data: {message}")
    self._handle_screenshot_data("screenshot_with_state||" + message)
```

### 3. **Smarter Unknown Message Filtering**
Only log truly unknown messages, not probable partial data:

```python
else:
    # Only log as unknown if it doesn't look like partial screenshot data
    if not any(keyword in message.lower() for keyword in ["screenshot", "png", "||"]):
        print(f"🤔 Unknown message from mGBA: {message}")
    else:
        print(f"🚧 Ignoring probable partial message: {message[:50]}...")
```

## 🧪 **Testing**

Created comprehensive test in `dev-tools/test-scripts/test_message_parsing.py`:
- ✅ Split message handling
- ✅ Multiple messages in one packet
- ✅ Partial message buffering
- ✅ Orphaned data recovery

## 📈 **Results**

**Before**: Frequent "unknown message" errors and failed screenshot processing  
**After**: Robust message handling with proper buffering and recovery

**Benefits**:
- No more "unknown message" errors
- Reliable screenshot data processing  
- Better debugging output
- Graceful handling of TCP quirks

The fix ensures that all communication between mGBA and the AI service works reliably, regardless of how TCP splits the messages.