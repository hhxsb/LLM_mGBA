# ⚠️ LEGACY CODE - NOT USED BY ACTIVE SYSTEM

## Status: INACTIVE

This directory contains **legacy modular game controller code** that is **NOT used by the current AI GBA Player**.

### Current Active System
The AI GBA Player uses a simplified architecture:
- **AI Service**: `ai_gba_player/dashboard/ai_game_service.py`
- **LLM Client**: `ai_gba_player/dashboard/llm_client.py` (with optimized prompts)
- **No game controllers**: Direct socket communication with mGBA

### Legacy Code Purpose
This modular system was designed for:
- Multiple game support through inheritance
- Abstract base classes for extensibility  
- Complex prompt template management

### Why It's Not Used
Replaced by simpler, more direct architecture that:
- ✅ Works with any GBA game without game-specific code
- ✅ Uses optimized prompts (25% token reduction)
- ✅ Simpler maintenance and deployment
- ✅ Better performance and reliability

### Safe to Ignore
- These files do NOT affect the running AI GBA Player
- Tests may still reference this code
- Kept for git history and reference