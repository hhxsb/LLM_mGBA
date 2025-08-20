# Graphiti Memory System Integration

## Overview

The AI GBA Player now includes an advanced memory system powered by Graphiti that enables autonomous objective discovery, achievement tracking, and strategy learning. The AI learns and remembers as it plays, becoming more effective over time.

## Features

### 🎯 Autonomous Objective Discovery
- **AI-driven goal detection**: Analyzes AI responses to identify new objectives
- **Priority-based organization**: Objectives are automatically prioritized by importance
- **Category classification**: Goals are classified as main, side, exploration, collection, etc.
- **Location tracking**: Remembers where objectives were discovered

### 🏆 Achievement Tracking
- **Completion detection**: Automatically detects when objectives are completed
- **Progress tracking**: Maintains history of completed achievements
- **Prerequisite management**: Understands achievement dependencies

### 🧠 Strategy Learning
- **Pattern recognition**: Learns which button sequences work in specific situations
- **Success rate tracking**: Monitors effectiveness of different strategies
- **Context awareness**: Associates strategies with game situations and locations
- **Adaptive improvement**: Strategies improve with more usage data

### 📊 Memory-Enhanced Decision Making
- **Context-aware prompts**: LLM receives relevant objectives and strategies
- **Real-time updates**: Knowledge graph updated after each AI decision
- **Temporal tracking**: Knows when events occurred and objectives were discovered

## Architecture

### Components

1. **GraphitiMemorySystem** (`ai_gba_player/core/graphiti_memory.py`)
   - Core memory management using Graphiti knowledge graphs
   - Neo4j backend for temporal data storage
   - Fallback to SimpleMemorySystem when Graphiti unavailable

2. **AI Service Integration** (`ai_gba_player/dashboard/ai_game_service.py`)
   - Memory updates after each AI decision
   - Objective discovery from AI text analysis
   - Achievement detection and strategy learning

3. **LLM Client Enhancement** (`ai_gba_player/dashboard/llm_client.py`)
   - Memory context injection into prompts
   - Current objectives and strategies provided to AI
   - Enhanced decision making with learned patterns

4. **Prompt Template** (`data/prompt_template.txt`)
   - Memory context section added
   - Displays current objectives, achievements, and strategies
   - Guides AI toward memory-informed decisions

### Data Flow

```
Game State → AI Decision → Memory Analysis → Knowledge Graph Update
    ↑                                               ↓
LLM Prompt ← Memory Context ← Strategy Retrieval ← Objective Management
```

## Installation

### Requirements

```bash
pip install graphiti-ai>=0.3.0 neo4j>=5.0.0
```

### Neo4j Setup

1. **Local Neo4j**: Install Neo4j Desktop or Docker
2. **Cloud**: Use Neo4j AuraDB free tier
3. **Configuration**: Update connection details in memory system

### Auto-Fallback

If Graphiti/Neo4j unavailable, system automatically falls back to simple in-memory storage.

## Usage

### Automatic Operation

The memory system works automatically once installed:

1. **Start AI GBA Player**: `python manage.py runserver`
2. **Launch game service**: Memory system initializes automatically
3. **Play game**: AI discovers objectives and learns strategies autonomously

### Memory Context in Prompts

The LLM now receives enhanced context including:

```
## 🎯 Current Objectives:
  🔥 Defeat Team Rocket leader (Priority: 9)
     📍 Discovered at: Rocket Hideout (15, 20)
  ⭐ Catch rare Pokemon in Safari Zone (Priority: 7)

## 🏆 Recent Achievements:
  ✅ Obtained HM01 Cut (Completed: 2025-08-18 14:30)
     📍 Completed at: SS Anne (45, 12)

## 🧠 Learned Strategies:
  💡 talking to npc: [A, A, B]
     📊 Success rate: 85.7% (Used 14 times)
```

## API Reference

### Core Methods

```python
# Discover new objective
objective_id = memory_system.discover_objective(
    description="Find the missing Pokemon",
    location="Viridian Forest (25, 30)",
    category="exploration",
    priority=6
)

# Complete objective
success = memory_system.complete_objective(objective_id, location)

# Learn strategy
strategy_id = memory_system.learn_strategy(
    situation="navigating pokemon center",
    button_sequence=["UP", "UP", "A"],
    success=True,
    context={"npc_type": "nurse"}
)

# Get memory context
context = memory_system.get_memory_context("current situation")
```

### Memory Context Structure

```python
{
    "current_objectives": [
        {
            "description": "objective text",
            "priority": 1-10,
            "category": "main|side|exploration|etc",
            "location_discovered": "location name"
        }
    ],
    "recent_achievements": [
        {
            "title": "achievement name",
            "completed_at": "timestamp",
            "location": "completion location"
        }
    ],
    "relevant_strategies": [
        {
            "situation": "situation description",
            "buttons": ["A", "B"],
            "success_rate": "85.7%",
            "times_used": 12
        }
    ],
    "discovery_suggestions": ["tip1", "tip2"]
}
```

## Examples

### Objective Discovery

When AI says: "I need to find the Pokemon Center to heal my Pokemon"
- **System detects**: "need to" keyword + context
- **Creates objective**: "find the Pokemon Center to heal my Pokemon"
- **Categorizes**: "maintenance" priority 6
- **Tracks location**: Current game location

### Strategy Learning

When AI uses buttons `["UP", "A", "A"]` and mentions "talking to nurse"
- **Situation**: "talking to npc in pokemon center"
- **Actions**: `["UP", "A", "A"]`
- **Success**: Based on AI not mentioning failure
- **Context**: Location, NPC type, etc.

### Achievement Detection

When AI says: "I caught a Pikachu!"
- **Scans objectives**: Looking for "catch" related goals
- **Finds match**: "Catch electric-type Pokemon"
- **Completes objective**: Moves to achievements
- **Notifies**: "🏆 Achievement unlocked: Catch electric-type Pokemon"

## Configuration

### Memory System Settings

```python
# Neo4j connection (default: localhost)
memory_system = create_memory_system(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j", 
    neo4j_password="password"
)
```

### Objective Categories

- **main**: Primary story objectives (priority 8-10)
- **combat**: Battle-related goals (priority 7-8)
- **collection**: Catching/finding items (priority 6-7)
- **exploration**: Area discovery (priority 5-6)
- **social**: NPC interactions (priority 4-5)
- **maintenance**: Healing, shopping (priority 2-4)

## Benefits

### For AI Performance
- **Contextual awareness**: AI knows what it should be doing
- **Pattern reuse**: Successful strategies are remembered and reused
- **Goal persistence**: Important objectives don't get forgotten
- **Learning improvement**: AI gets better at the game over time

### For Development
- **Debugging insight**: See what the AI is trying to accomplish
- **Behavior analysis**: Track strategy effectiveness and learning
- **Progress monitoring**: Observe objective completion rates
- **Performance optimization**: Identify successful patterns

## Troubleshooting

### Common Issues

1. **Neo4j Connection Failed**
   - System falls back to simple memory
   - Check Neo4j service is running
   - Verify connection credentials

2. **No Objectives Discovered**
   - AI text analysis may need tuning
   - Check keyword matching in `_discover_objectives_from_ai_text`
   - Verify AI is providing descriptive responses

3. **Strategies Not Learning**
   - Check button sequence format
   - Verify success detection logic
   - Monitor AI text for failure keywords

### Debug Commands

```bash
# Test memory system
python test_graphiti_integration.py

# Check memory stats (in Django shell)
from ai_gba_player.core.graphiti_memory import create_memory_system
memory = create_memory_system()
print(memory.get_stats())
```

## Future Enhancements

- **NLP-based objective extraction**: Use embeddings for better text analysis
- **Multi-game support**: Adapt memory system for different GBA games
- **Memory visualization**: Web interface for exploring knowledge graph
- **Social learning**: Share strategies between AI instances
- **Advanced reasoning**: Query knowledge graph for complex relationships

## Technical Notes

- **Thread-safe**: Memory operations are safe for concurrent access
- **Performance**: Memory context generation is optimized for low latency
- **Scalability**: Graphiti handles large knowledge graphs efficiently
- **Backup**: Knowledge graph persists across system restarts