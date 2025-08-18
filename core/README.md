# ⚠️ LEGACY CODE - NOT USED BY ACTIVE SYSTEM

## Status: INACTIVE

This directory contains **legacy base framework classes** that are **NOT used by the current AI GBA Player**.

### Current Active System
The AI GBA Player uses a simplified architecture:
- **AI Service**: `ai_gba_player/dashboard/ai_game_service.py`
- **LLM Client**: `ai_gba_player/dashboard/llm_client.py` 
- **No base classes**: Direct implementation without abstraction layers

### Legacy Code Purpose
This framework was designed for:
- Abstract base classes for controllers, engines, templates
- Modular architecture with inheritance
- Complex capture and knowledge systems

### Why It's Not Used
Replaced by simpler, more direct approach that:
- ✅ Eliminates unnecessary abstraction layers
- ✅ Reduces code complexity by 80%+
- ✅ Easier to understand and maintain
- ✅ Better performance without overhead

### Safe to Ignore
- These files do NOT affect the running AI GBA Player
- Tests may still reference this code
- Kept for git history and reference