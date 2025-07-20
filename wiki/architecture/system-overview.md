# System Architecture Overview

## 🏗️ **High-Level Architecture**

The LLM Pokemon Red AI system uses a **dual-process architecture** with sophisticated knowledge management and context-aware decision making.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   mGBA Emulator │    │ Python Controller│    │  LLM Provider   │
│   + Lua Script  │◄──►│  + Knowledge     │◄──►│  (Gemini AI)    │
│                 │    │    System        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Game State &   │    │  Context Memory │    │  AI Decisions & │
│  Screenshots    │    │  & Dialogue     │    │  Button Commands│
│                 │    │  History        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔄 **Data Flow**

### **Primary Game Loop**:
1. **Emulator** captures game state and screenshot
2. **Lua Script** sends data via TCP socket
3. **Python Controller** receives and processes data
4. **Knowledge System** analyzes context and updates memory
5. **LLM Provider** makes decision based on enhanced context
6. **Controller** sends button commands back to emulator
7. **Process repeats** with updated game state

## 🧠 **Knowledge System Architecture**

### **Core Components**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge System                          │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Conversation    │ │ Character       │ │ Context Memory  │ │
│ │ State Tracking  │ │ Identity &      │ │ Buffer          │ │
│ │                 │ │ Game Phase      │ │                 │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Dialogue        │ │ Conversation    │ │ Smart Context   │ │
│ │ Recording &     │ │ Flow            │ │ Prioritization  │ │
│ │ Memory          │ │ Management      │ │                 │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│ ┌─────────────────┐ ┌─────────────────┐                     │
│ │ Tutorial        │ │ Enhanced Prompt │                     │
│ │ Progress        │ │ Formatting      │                     │
│ │ Tracking        │ │                 │                     │
│ └─────────────────┘ └─────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### **Data Structures**:

#### **Core State Tracking**:
- `ConversationState` - Current NPC, topic, history, expected actions
- `CharacterState` - Player identity, objectives, game phase, known NPCs
- `ContextMemoryEntry` - Timestamped context with type and priority
- `DialogueRecord` - Complete conversation records with metadata

#### **Memory Management**:
- **Short-term**: Rolling buffer (20 entries) with priority-based selection
- **Long-term**: Persistent dialogue history and character relationships
- **Smart Prioritization**: Dynamic relevance scoring based on current situation

## 🎮 **Game Integration**

### **Emulator Layer**:
- **mGBA Emulator**: Runs Pokemon Red ROM
- **Lua Script**: Captures game state, handles button input
- **Memory Reading**: Real-time access to game variables
- **Screenshot Capture**: Visual game state for AI analysis

### **Communication Protocol**:
```
Message Format: message_type||content1||content2||...

Key Messages:
- ready: Emulator signals readiness
- request_screenshot: Controller requests screenshot  
- screenshot_with_state: Screenshot + game data package
- button_commands: Comma-separated button sequences
```

### **Button Control**:
- **Multi-button sequences**: Support for complex actions like ["UP", "UP", "A"]
- **Timing control**: Frame-accurate button timing
- **Queue system**: Sequential execution of button commands

## 🤖 **LLM Integration**

### **Provider Architecture**:
- **Primary**: Google Gemini (with tool support)
- **Abstraction Layer**: Pluggable LLM provider system
- **Tool Integration**: AI can call game control functions

### **Context Enhancement Pipeline**:
1. **Raw Context Collection**: Game state, memory, dialogue history
2. **Smart Prioritization**: Relevance scoring and selection
3. **Visual Formatting**: Structured presentation with priority indicators
4. **Length Management**: Intelligent truncation preserving key information
5. **LLM Delivery**: Optimally formatted context for decision-making

### **Tools Available to LLM**:
- `press_button(buttons)` - Execute game controls
- `update_notepad(content)` - Update long-term memory

## 📁 **File Structure**

### **Core System**:
```
core/
├── base_game_controller.py    # Main controller logic
├── base_knowledge_system.py   # Knowledge management
├── base_game_engine.py        # Game state handling
├── base_prompt_template.py    # Prompt formatting
└── screen_capture.py          # Screenshot handling
```

### **Pokemon Red Specific**:
```
games/pokemon_red/
├── controller.py              # Pokemon Red controller
├── knowledge_system.py        # Game-specific knowledge
├── game_engine.py            # Pokemon Red game logic
├── prompt_template.py        # Pokemon Red prompts
└── llm_client.py             # LLM communication
```

### **Emulator Integration**:
```
emulator/
├── script.lua                # Main Lua script
├── test_memory.lua           # Memory testing
├── key_press_test.lua        # Input testing
└── screenshot_test.lua       # Capture testing
```

## 🔧 **Configuration System**

### **Main Configuration** (`config.json`):
- **API Keys**: LLM provider credentials
- **Paths**: Screenshot, notepad, prompt template locations
- **Timing**: Decision cooldowns and rate limiting
- **Debug**: Verbose logging and debugging options

### **Dynamic Components**:
- **Hot-reload Prompts**: Template changes detected automatically
- **Adaptive Context**: Context selection based on current game state
- **Configurable Priorities**: Adjustable importance weights

## 🚀 **Performance Characteristics**

### **Scalability**:
- **Memory Efficient**: Rolling buffers prevent unlimited growth
- **Context Compression**: Older context automatically summarized
- **Priority-based**: Most relevant information always prioritized

### **Reliability**:
- **Error Recovery**: Socket reconnection and graceful degradation
- **Rate Limiting**: Configurable cooldowns prevent API overuse
- **State Persistence**: Knowledge saved to disk automatically

### **Extensibility**:
- **Modular Design**: Easy to add new games or features
- **Plugin Architecture**: New LLM providers easily integrated
- **Abstract Base Classes**: Clear extension points for customization

This architecture provides a **robust, scalable, and intelligent foundation** for LLM-based game playing with sophisticated memory management and context awareness.