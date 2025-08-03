# Message System Architecture

## Overview

The AI Pokemon Trainer Dashboard implements a sophisticated real-time message system that enables live streaming of game footage, AI responses, and system actions from the AI processes to a web-based dashboard interface. This document provides a comprehensive analysis of how messages flow through the system, how they're stored, and how the frontend displays them.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AI Pokemon Trainer Message System                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────────┐ │
│  │ Video Capture   │     │ Game Control    │     │ Knowledge System           │ │
│  │ Process         │────▶│ Process         │────▶│ (Pokemon Red)              │ │
│  │                 │     │                 │     │                            │ │
│  │ • Screenshots   │     │ • AI Decisions  │     │ • Dialogue Memory          │ │
│  │ • GIF Generation│     │ • Button Actions│     │ • Context Memory           │ │
│  │ • Rolling Buffer│     │ • LLM Responses │     │ • JSON Persistence         │ │
│  └─────────────────┘     └─────────────────┘     └─────────────────────────────┘ │
│           │                        │                         │                   │
│           │ TCP Socket             │ WebSocket               │ File I/O          │
│           │ (Port 8889)            │ (Port 3000/ws)          │ (.json)           │
│           ▼                        ▼                         ▼                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                      Dashboard Backend (FastAPI)                           │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │ │
│  │  │ WebSocket       │  │ Connection      │  │ Process Manager             │  │ │
│  │  │ Handler         │  │ Manager         │  │                             │  │ │
│  │  │                 │  │                 │  │ • Lifecycle Management      │  │ │
│  │  │ • Message       │  │ • Active        │  │ • Health Monitoring         │  │ │
│  │  │   Routing       │  │   Connections   │  │ • Auto-restart Logic        │  │ │
│  │  │ • History       │  │ • Broadcasting  │  │                             │  │ │
│  │  │   Storage       │  │ • Keepalive     │  │                             │  │ │
│  │  │ • GIF Caching   │  │                 │  │                             │  │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                           │
│                                      │ WebSocket (ws://localhost:3000/ws)        │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                     Dashboard Frontend (React + TypeScript)                │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │ │
│  │  │ useWebSocket    │  │ ChatInterface   │  │ StatusPanel /               │  │ │
│  │  │ Hook            │  │ Component       │  │ AdminPanel                  │  │ │
│  │  │                 │  │                 │  │                             │  │ │
│  │  │ • Connection    │  │ • Message       │  │ • Process Status            │  │ │
│  │  │   Management    │  │   Rendering     │  │ • System Health             │  │ │
│  │  │ • Message       │  │ • Auto-scroll   │  │ • Real-time Monitoring      │  │ │
│  │  │   State         │  │ • Type-specific │  │                             │  │ │
│  │  │ • Reconnection  │  │   Display       │  │                             │  │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Complete Message Lifecycle Diagram

The following diagram shows one complete cycle of how a GIF is captured, processed by AI, and results in actions - and how each step creates messages that flow to the frontend:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          COMPLETE MESSAGE LIFECYCLE                             │
│                         (One AI Decision Cycle)                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ STEP 1: GAME FOOTAGE CAPTURE                                                   │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Video Capture Process (video_capture_process.py)                           │ │
│ │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │ │
│ │ │ Continuous   │ │ Rolling      │ │ GIF Request  │ │ GIF Generation      │ │ │
│ │ │ Screenshot   │→│ Frame Buffer │→│ (TCP 8889)   │→│ & Base64 Encoding   │ │ │
│ │ │ (30 FPS)     │ │ (20 seconds) │ │ from Game    │ │ + Metadata          │ │ │
│ │ │              │ │ 600 frames   │ │ Control      │ │                     │ │ │
│ │ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                         │
│                                      │ TCP Response                            │
│                                      ▼                                         │
│ STEP 2: AI DECISION MAKING                                                     │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Game Control Process (game_control_process.py)                             │ │
│ │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │ │
│ │ │ Receive GIF  │ │ Convert to   │ │ Send to LLM  │ │ Parse LLM Response  │ │ │
│ │ │ Data + Meta  │→│ PIL Image    │→│ (Gemini API) │→│ Extract Buttons     │ │ │
│ │ │              │ │              │ │ + Context    │ │ + Reasoning         │ │ │
│ │ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                         │
│                                      │ WebSocket Messages                      │
│                                      ▼                                         │
│ STEP 3: MESSAGE CREATION & ROUTING                                             │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Dashboard Backend (websocket_handler.py)                                   │ │
│ │                                                                             │ │
│ │ Message 1: GIF MESSAGE                                                     │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │ │
│ │ │ Video       │ │ Create      │ │ Store in    │ │ Broadcast to All       │ │ │
│ │ │ Process     │→│ ChatMessage │→│ History     │→│ WebSocket Clients      │ │ │
│ │ │ Sends GIF   │ │ type="gif"  │ │ (deque 100) │ │                        │ │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ └────────────────────────┘ │ │
│ │                                                                             │ │
│ │ Message 2: AI RESPONSE MESSAGE                                             │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │ │
│ │ │ Game        │ │ Create      │ │ Store in    │ │ Broadcast to All       │ │ │
│ │ │ Control     │→│ ChatMessage │→│ History     │→│ WebSocket Clients      │ │ │
│ │ │ Sends AI    │ │ type="resp" │ │ (deque 100) │ │                        │ │ │
│ │ │ Response    │ │             │ │             │ │                        │ │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ └────────────────────────┘ │ │
│ │                                                                             │ │
│ │ Message 3: ACTION MESSAGE                                                  │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │ │
│ │ │ Game        │ │ Create      │ │ Store in    │ │ Broadcast to All       │ │ │
│ │ │ Control     │→│ ChatMessage │→│ History     │→│ WebSocket Clients      │ │ │
│ │ │ Sends       │ │ type="act"  │ │ (deque 100) │ │                        │ │ │
│ │ │ Button Acts │ │             │ │             │ │                        │ │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ └────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                         │
│                                      │ WebSocket (ws://localhost:3000/ws)      │
│                                      ▼                                         │
│ STEP 4: FRONTEND MESSAGE DISPLAY                                               │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Dashboard Frontend (React)                                                  │ │
│ │                                                                             │ │
│ │ useWebSocket Hook Receives Messages:                                        │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │ │
│ │ │ WebSocket   │ │ Parse JSON  │ │ Update      │ │ Trigger React          │ │ │
│ │ │ Message     │→│ Extract     │→│ Messages    │→│ Component Re-render    │ │ │
│ │ │ Received    │ │ ChatMessage │ │ State Array │ │                        │ │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ └────────────────────────┘ │ │
│ │                                                                             │ │
│ │ ChatInterface Component Renders:                                            │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │ │
│ │ │ Type-Based  │ │ GIF: Show   │ │ Response:   │ │ Action: Show Button    │ │ │
│ │ │ Message     │→│ Image +     │→│ Show Text + │→│ Pills + Durations      │ │ │
│ │ │ Routing     │ │ Metadata    │ │ Reasoning   │ │ Auto-scroll to Bottom  │ │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ └────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ TIMING: Complete cycle takes ~3-8 seconds depending on AI processing time      │
│         Each message appears in frontend within 100-200ms of creation          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Message Creation Sequence

### Timeline of One Complete AI Decision Cycle

1. **T+0.0s**: Game Control requests GIF from Video Capture (TCP socket)
2. **T+0.1s**: Video Capture generates GIF from rolling buffer → sends to dashboard
3. **T+0.2s**: **GIF MESSAGE** appears in frontend chat
4. **T+0.3s**: Game Control receives GIF data → processes with LLM
5. **T+2-6s**: LLM processing time (varies by complexity)
6. **T+6.0s**: Game Control sends AI response → dashboard
7. **T+6.1s**: **AI RESPONSE MESSAGE** appears in frontend chat
8. **T+6.2s**: Game Control sends button actions → dashboard
9. **T+6.3s**: **ACTION MESSAGE** appears in frontend chat
10. **T+6.4s**: Actions executed in emulator → cycle repeats after cooldown

### Message Data Flow Details

#### 1. GIF Message Creation Flow
```python
# video_capture_process.py - Line 372-373
if self.dashboard_enabled and self.dashboard_ws:
    self._send_gif_to_dashboard_threaded(gif_data_b64, metadata)

# websocket_handler.py - Lines 336-361
async def send_gif_message(self, gif_data: str, metadata: Dict):
    gif_obj = GifData(data=gif_data, metadata=metadata, available=True)
    chat_message = ChatMessage.create_gif_message(gif_obj, 0)
    await self.connection_manager.broadcast_chat_message(chat_message)
```

#### 2. AI Response Message Creation Flow
```python
# game_control_process.py - Lines 226-228
if response_text:
    self._send_dashboard_message_threaded('response', response_text, reasoning, processing_time)

# websocket_handler.py - Lines 366-382
async def send_response_message(self, response_text: str, reasoning: Optional[str], processing_time: Optional[float]):
    response_data = ResponseData(text=response_text, reasoning=reasoning, processing_time=processing_time)
    chat_message = ChatMessage.create_response_message(response_data, 0)
    await self.connection_manager.broadcast_chat_message(chat_message)
```

#### 3. Action Message Creation Flow
```python
# game_control_process.py - Lines 241-246
if button_codes:
    self._send_dashboard_message_threaded('action', 
        [str(code) for code in button_codes], 
        [float(d) for d in button_durations], 
        button_names)

# websocket_handler.py - Lines 384-396
async def send_action_message(self, buttons: List[str], durations: List[float], button_names: List[str]):
    action_data = ActionData(buttons=buttons, durations=durations, button_names=button_names)
    chat_message = ChatMessage.create_action_message(action_data, 0)
    await self.connection_manager.broadcast_chat_message(chat_message)
```

## Message Flow Architecture

### 1. Message Generation Sources

#### A. Video Capture Process (`video_capture_process.py`)
- **Function**: Generates game footage GIFs on demand
- **Communication**: TCP Socket (Port 8889)
- **Message Types**: 
  - GIF data with metadata (frame count, duration, size)
  - Status responses
- **Data Flow**: 
  ```
  Game Screenshots → Rolling Buffer → GIF Generation → Base64 Encoding → TCP Socket
  ```

#### B. Game Control Process (`game_control_process.py`)
- **Function**: AI decision-making and game interaction
- **Communication**: WebSocket (Port 3000/ws)
- **Message Types**:
  - AI text responses with reasoning
  - Button action commands
  - System status updates
- **Integration**: Requests GIFs from video capture, processes with LLM

#### C. Knowledge System (`games/pokemon_red/knowledge_system.py`)
- **Function**: Game state persistence and learning
- **Communication**: File I/O + Memory
- **Storage**: JSON files for dialogue history, context memory
- **Scope**: Separate from chat interface, focused on AI learning

### 2. Message Processing Pipeline

#### Backend Message Handling (`dashboard/backend/`)

**WebSocket Handler** (`websocket_handler.py`):
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.message_history: deque = deque(maxlen=100)  # FIFO message storage
        self.message_sequence = 0

class DashboardWebSocketHandler:
    def __init__(self):
        self.gif_cache: Dict[str, Dict] = {}  # 30-minute GIF retention
        self.gif_retention_time = 30 * 60  # seconds
```

**Message Types** (`models.py`):
- `GIF`: Game footage with base64 data and metadata
- `RESPONSE`: AI text responses with optional reasoning/timing
- `ACTION`: Button commands with durations
- `SYSTEM`: Status updates and errors

**Message Broadcasting Flow**:
```
Incoming Message → Type Detection → Message Validation → History Storage → 
Client Broadcasting → GIF Caching (if applicable) → Cleanup Management
```

### 3. Frontend Message Display (`dashboard/frontend/`)

#### WebSocket Hook (`hooks/useWebSocket.ts`)
```typescript
export const useWebSocket = (): UseWebSocketReturn => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
```

**Connection Management**:
- Multi-port fallback: tries ports 3001, 3000 (Update 7/23/2025, deprecating 3001 in code so we don't try that anymore)
- Automatic reconnection with exponential backoff
- Ping/pong keepalive mechanism
- Historical message retrieval for new connections

#### Chat Interface (`components/ChatInterface.tsx`)

**Message Rendering Pipeline**:
```typescript
const renderMessage = (message: ChatMessage) => {
  switch (message.type) {
    case 'gif': return renderGifMessage(message);
    case 'response': return renderResponseMessage(message);
    case 'action': return renderActionMessage(message);
    case 'system': return renderSystemMessage(message);
  }
};
```

**Display Features**:
- Type-specific message styling and icons
- Auto-scroll to newest messages
- GIF expiration handling
- Timestamp formatting
- Metadata display (processing time, confidence, etc.)

## Message Storage and Persistence

### 1. In-Memory Storage

#### Backend Storage (WebSocket Handler)
```python
# Primary message storage
self.message_history: deque = deque(maxlen=100)

# GIF binary data cache
self.gif_cache: Dict[str, Dict] = {
    "gif_id": {
        "data": "base64_string",
        "timestamp": float
    }
}
```

**Characteristics**:
- **Capacity**: 100 messages maximum (FIFO rotation)
- **Persistence**: Lost on server restart
- **New Client Behavior**: Receives recent message history on connection

#### Frontend Storage (React State)
```typescript
const [messages, setMessages] = useState<ChatMessage[]>([]);
```

**Characteristics**:
- **Capacity**: No limit during session
- **Persistence**: Lost on page refresh
- **Update Mechanism**: Real-time via WebSocket

### 2. Retention Policies

#### Chat Messages
- **Backend**: 100 message limit with FIFO rotation
- **Frontend**: Session-only storage
- **Historical Access**: New connections receive recent history

#### GIF Data
- **Retention Time**: 30 minutes configurable
- **Cleanup Frequency**: Every 5 minutes
- **Post-Expiration**: Metadata retained, binary data purged
- **UI Behavior**: Shows "GIF no longer available" placeholder

#### Knowledge System (Separate)
```python
# Persistent storage to JSON files
dialogue_history: Last 20 dialogues
context_memory: In-memory deque(maxlen=20)
action_history: Last 50-100 actions
conversation_state: Current NPC interactions
```

## WebSocket Communication Protocol

### 1. Connection Management

**URL Resolution**:
```typescript
const getWebSocketURL = () => {
  if (window.location.host.includes(':5173')) {
    // Development: try multiple ports
    return ['ws://localhost:3001/ws', 'ws://localhost:3000/ws'];
  } else {
    // Production: same host
    return [`ws://${window.location.host}/ws`];
  }
};
```

**Connection Lifecycle**:
1. **Initial Connection**: Try ports in order
2. **Authentication**: None required (local system)
3. **Keepalive**: Ping/pong every 30 seconds
4. **Reconnection**: Automatic with exponential backoff
5. **History Sync**: New clients receive recent messages

### 2. Message Format

**WebSocket Message Structure**:
```typescript
interface WebSocketMessage {
  type: string;           // "chat_message", "system_status", "message_history"
  timestamp: number;      // Unix timestamp
  data: {
    message?: ChatMessage;  // For chat_message type
    sequence?: number;      // Message sequence number
    // ... other type-specific data
  };
}
```

**Chat Message Structure**:
```typescript
interface ChatMessage {
  id: string;            // "gif_1234567890", "response_1234567890"
  type: 'gif' | 'response' | 'action' | 'system';
  timestamp: number;     // Unix timestamp
  sequence: number;      // Auto-incrementing sequence
  content: {
    gif?: GifData;       // For GIF messages
    response?: ResponseData;  // For AI responses
    action?: ActionData;      // For button actions
    system?: SystemData;      // For system messages
  };
}
```

### 3. Message Types and Data Structures

#### GIF Messages
```typescript
content: {
  gif: {
    data?: string;       // Base64 encoded GIF (null if expired)
    metadata: {
      frameCount: number;
      duration: number;   // seconds
      size: number;      // bytes
      timestamp: number;
    };
    available: boolean;  // false after retention period
  }
}
```

#### Response Messages
```typescript
content: {
  response: {
    text: string;           // AI response text
    reasoning?: string;     // Optional AI reasoning
    confidence?: number;    // 0-1 confidence score
    processing_time?: number; // seconds
  }
}
```

#### Action Messages
```typescript
content: {
  action: {
    buttons: string[];      // ["UP", "A"]
    durations: number[];    // [0.5, 0.2] seconds
    button_names: string[]; // Human-readable names
  }
}
```

## Performance and Optimization

### 1. Memory Management

**Message History Limits**:
- Backend: 100 messages maximum prevents unbounded growth
- GIF Cache: 30-minute TTL with automatic cleanup
- Frontend: Session-only, no persistence across refreshes

**GIF Optimization**:
- Base64 encoding for WebSocket compatibility
- Adaptive timeouts for large GIF transfers (20+ seconds)
- Metadata preservation after binary data expiration

### 2. Real-time Performance

**Connection Management**:
- WebSocket for low-latency bidirectional communication
- Connection pooling and automatic reconnection
- Ping/pong keepalive prevents idle disconnections

**Broadcasting Efficiency**:
- Single message → all connected clients
- Timeout protection (5 seconds) for slow clients
- Automatic cleanup of failed connections

## Configuration and Customization

### 1. Dashboard Configuration (`config_emulator.json`)
```json
{
  "dashboard": {
    "enabled": true,
    "port": 3000,
    "websocket_port": 3001,
    "auto_start_processes": true,
    "theme": "pokemon"
  },
  "dual_process_mode": {
    "enabled": true,
    "video_capture_port": 8889,
    "rolling_window_seconds": 20
  }
}
```

### 2. Message Retention Settings (`models.py`)
```python
class DashboardConfig(BaseModel):
    chat_history_limit: int = 100
    gif_retention_minutes: int = 30
    auto_start_processes: bool = True
    streaming_mode: bool = False
```

## Error Handling and Resilience

### 1. Connection Failures

**Backend Resilience**:
- Process manager handles AI process failures
- WebSocket connection cleanup on client disconnect
- Graceful degradation when video capture unavailable

**Frontend Recovery**:
- Automatic reconnection with exponential backoff
- Multi-port connection attempts
- Connection status indicators for users

### 2. Message Delivery

**Delivery Guarantees**:
- Best-effort delivery (WebSocket limitations)
- No persistence across server restarts
- Historical message recovery for new connections

**Error Scenarios**:
- Large message timeouts (5-second client timeout)
- JSON parsing errors logged but don't crash system
- Malformed messages filtered and logged

## Security Considerations

### 1. Local System Design
- **Network Scope**: localhost-only communication
- **Authentication**: None required (local system)
- **Data Exposure**: Game data only, no sensitive information

### 2. Input Validation
- JSON message validation at WebSocket layer
- Type checking for message structures
- Graceful handling of malformed data

## Future Enhancements

### 1. Persistence Improvements
- Optional database storage for long-term message history
- Message export functionality
- User-configurable retention policies

### 2. Advanced Features
- Message search and filtering
- Performance metrics and analytics
- Multi-game support with game-specific message types

---

**File Location**: `/wiki/architecture/message-system-architecture.md`  
**Last Updated**: 2025-07-20  
**Version**: 1.0.0