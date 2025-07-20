# AI Pokemon Trainer Dashboard - Implementation Plan

## 🎯 **Final Design Specification**

### **Visual Theme**
- **Pokemon-inspired UI** with the provided "AI Pokemon Trainer" banner
- **Chat-based interface** for AI interactions
- **Clean, streaming-friendly** design with blue/green color scheme

### **Core UI Components**

#### **1. AI Interaction Chat Interface**
```
┌─ AI Pokemon Trainer Dashboard ─────────────────────────┐
│ [Pokemon Banner]                               [Status]│
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🎮 GIF Message Bubble                                  │
│  ┌─[GIF-001]────────────────┐                          │
│  │ [Animated GIF Display]   │ 🕒 12:34:56               │
│  │ 150 frames, 5.2s        │                          │
│  └─────────────────────────┘                          │
│                                                         │
│           🤖 AI Response Bubble                         │
│           ┌─────────────────────────────────┐           │
│           │ "I can see the player is facing │ 🕒 12:35:01│
│           │ a wild Pokemon. I should use    │           │
│           │ my Squirtle to battle..."       │           │
│           └─────────────────────────────────┘           │
│                                                         │
│           🎯 Action Bubble                              │
│           ┌─────────────────────────────────┐           │
│           │ Actions: [A, A, DOWN]           │ 🕒 12:35:02│
│           │ Duration: 0.5s each             │           │
│           └─────────────────────────────────┘           │
│                                                         │
│  [Older messages show "GIF no longer available"]       │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Knowledge Base: [Tasks] [Detailed View]                 │
└─────────────────────────────────────────────────────────┘
```

#### **2. Knowledge Base Section**
- **Tasks Tab** (Primary): Current objectives, progress, priorities
- **Detailed Tab** (Expandable): Full knowledge graph, NPCs, locations, items

## 🏗️ **Technical Architecture**

### **Technology Stack Confirmed**
- **Backend**: FastAPI + WebSockets + Python multiprocessing
- **Frontend**: React + TypeScript + WebSocket client
- **Real-time**: WebSocket for live updates
- **Styling**: Tailwind CSS or styled-components
- **Console**: Keep existing logging for debugging

### **Process Architecture**
```
dashboard.py (Main Process)
├── FastAPI Web Server (Port 3000)
│   ├── WebSocket Server (/ws)
│   ├── REST API (/api/*)
│   └── Static File Server (/static/*)
├── Process Manager
│   ├── Video Capture Process (Port 8889)
│   ├── Game Control Process (Port 8888)
│   └── Knowledge System (In-memory)
└── Chat Message Queue (WebSocket broadcasting)
```

### **Data Flow**
```
Video Process → Game Control → LLM Decision → Dashboard → WebSocket → React UI
     ↓              ↓              ↓             ↓
  GIF Data    Game State    AI Response    Chat Messages
```

## 📋 **Implementation Tasks Breakdown**

### **Phase 1: Core Infrastructure (Week 1)**

#### **Task 1.1: Project Structure Setup**
- [ ] Create `dashboard/` directory structure
- [ ] Setup FastAPI project with dependencies
- [ ] Create React frontend scaffolding
- [ ] Configure development environment

**Files to Create:**
```
dashboard/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── process_manager.py   # Process orchestration
│   ├── websocket_handler.py # WebSocket server
│   └── api/
│       ├── routes.py        # REST endpoints
│       └── models.py        # Data models
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── KnowledgeBase.tsx
│   │   │   └── StatusPanel.tsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts
│   │   └── App.tsx
│   ├── package.json
│   └── public/
└── requirements.txt
```

#### **Task 1.2: Process Manager Foundation**
- [ ] Create process lifecycle management
- [ ] Implement process health monitoring
- [ ] Add graceful startup/shutdown sequences
- [ ] Create IPC communication layer

**Example Code Structure:**
```python
class ProcessManager:
    def __init__(self, config):
        self.processes = {}
        self.config = config
    
    async def start_all_processes(self):
        # Start video capture first
        await self.start_video_process()
        # Then game control
        await self.start_game_control()
        # Finally knowledge system
        await self.start_knowledge_system()
    
    async def monitor_health(self):
        # Health check loop
        pass
```

#### **Task 1.3: Basic WebSocket Infrastructure**
- [ ] Setup WebSocket server with FastAPI
- [ ] Create message broadcasting system
- [ ] Implement connection management
- [ ] Add error handling and reconnection

### **Phase 2: Chat Interface (Week 2)**

#### **Task 2.1: GIF Message System**
- [ ] Create GIF message bubble component
- [ ] Implement GIF data streaming from video process
- [ ] Add "no longer available" fallback for old GIFs
- [ ] Include GIF metadata display (frames, duration, timestamp)

**Chat Message Data Model:**
```typescript
interface ChatMessage {
  id: string;
  type: 'gif' | 'response' | 'action';
  timestamp: number;
  content: {
    gif?: {
      data?: string; // base64 or null if purged
      metadata: {
        frameCount: number;
        duration: number;
        size: number;
      };
    };
    response?: {
      text: string;
      reasoning: string;
      confidence?: number;
    };
    action?: {
      buttons: string[];
      durations: number[];
    };
  };
}
```

#### **Task 2.2: AI Response Integration**
- [ ] Connect to LLM response stream
- [ ] Parse response text and reasoning
- [ ] Create response message bubbles
- [ ] Add response timing and metadata

#### **Task 2.3: Action Display System**
- [ ] Parse button actions from game control
- [ ] Display action lists in chat bubbles
- [ ] Show action timing and duration
- [ ] Link actions to game state changes

### **Phase 3: Knowledge Integration (Week 3)**

#### **Task 3.1: Knowledge Base UI**
- [ ] Create tabbed interface (Tasks/Detailed)
- [ ] Implement tasks display with priorities
- [ ] Add real-time knowledge updates
- [ ] Create knowledge search and filtering

#### **Task 3.2: Real-time Knowledge Sync**
- [ ] Connect to existing knowledge system
- [ ] Stream knowledge updates via WebSocket
- [ ] Implement knowledge change notifications
- [ ] Add knowledge editing capabilities

#### **Task 3.3: Progress Visualization**
- [ ] Create game progress indicators
- [ ] Add achievement tracking display
- [ ] Implement milestone celebrations
- [ ] Show learning progress metrics

### **Phase 4: Polish & Features (Week 4)**

#### **Task 4.1: Streaming Optimizations**
- [ ] Add full-screen chat mode
- [ ] Implement theme switching (dark/light)
- [ ] Create customizable layout options
- [ ] Add stream-friendly status displays

#### **Task 4.2: Performance & Monitoring**
- [ ] Add system performance metrics
- [ ] Implement error tracking and display
- [ ] Create process restart mechanisms
- [ ] Add configuration management UI

#### **Task 4.3: Polish & Testing**
- [ ] Comprehensive testing of all components
- [ ] Performance optimization
- [ ] UI/UX refinements
- [ ] Documentation completion

## 🔧 **Detailed Architecture Decisions**

### **WebSocket Message Protocol**
```typescript
// Outbound (Dashboard → UI)
interface WebSocketMessage {
  type: 'chat_message' | 'knowledge_update' | 'system_status' | 'process_health';
  timestamp: number;
  data: any;
}

// Chat message broadcasting
{
  type: 'chat_message',
  timestamp: 1703123456789,
  data: {
    message: ChatMessage, // See above
    sequence: 42          // Message ordering
  }
}

// Knowledge updates
{
  type: 'knowledge_update',
  timestamp: 1703123456789,
  data: {
    updateType: 'task_added' | 'task_completed' | 'npc_learned',
    content: { ... }
  }
}
```

### **Process Communication Enhancement**
```python
# Enhanced IPC for dashboard integration
class DashboardIPC:
    def __init__(self, dashboard_port=3001):
        self.dashboard_port = dashboard_port
        self.websocket_url = f"ws://localhost:{dashboard_port}/ws/process"
    
    async def send_gif_update(self, gif_data, metadata):
        # Send to dashboard via WebSocket
        pass
    
    async def send_llm_response(self, response_text, reasoning):
        # Send AI response to dashboard
        pass
    
    async def send_action_update(self, buttons, durations):
        # Send action commands to dashboard
        pass
```

### **File Structure Implementation**
```bash
# Directory creation commands
mkdir -p dashboard/backend/api
mkdir -p dashboard/frontend/src/{components,hooks,utils}
mkdir -p dashboard/frontend/public
mkdir -p static/images
```

### **Configuration Integration**
```json
// Add to config_emulator.json
{
  "dashboard": {
    "enabled": true,
    "port": 3000,
    "websocket_port": 3001,
    "chat_history_limit": 100,
    "gif_retention_minutes": 30,
    "auto_start_processes": true,
    "theme": "pokemon",
    "streaming_mode": false
  }
}
```

### **Development Dependencies**
```txt
# Backend (requirements.txt addition)
fastapi==0.104.1
websockets==12.0
uvicorn==0.24.0
python-multipart==0.0.6

# Frontend (package.json)
{
  "dependencies": {
    "react": "^18.2.0",
    "typescript": "^5.0.0",
    "tailwindcss": "^3.3.0",
    "ws": "^8.14.0"
  }
}
```

## 🚀 **Execution Plan**

### **Immediate Next Steps**
1. **Setup Phase 1.1**: Create directory structure and basic files
2. **Implement Process Manager**: Core process orchestration
3. **Basic WebSocket**: Message broadcasting infrastructure
4. **Simple Chat UI**: Basic React components for chat interface

### **Success Criteria**
- **Single command startup**: `python dashboard.py` starts everything
- **Real-time chat**: GIF → AI Response → Actions flow visible in chat
- **Knowledge integration**: Tasks and progress visible in dashboard
- **Streaming ready**: Clean, professional interface suitable for demos

### **Risk Mitigation**
- **Backward compatibility**: Existing terminal-based workflow remains functional
- **Incremental testing**: Each phase tested independently
- **Performance monitoring**: Track resource usage and optimize
- **Graceful degradation**: Dashboard failures don't break core functionality

This comprehensive plan transforms the Pokemon Red AI into a polished, presentation-ready system with the Pokemon-themed chat interface you envisioned. Ready to start implementation?