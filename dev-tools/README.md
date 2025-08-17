# Development Tools

This folder contains development and debugging tools for the AI GBA Player project.

## 📁 Folder Structure

### `/memory-debugging/`
Lua scripts for debugging Pokemon game memory addresses:

- **`simple_sapphire_memory_finder.lua`** - Basic memory address finder
- **`debug_sapphire_memory_realtime.lua`** - Real-time memory monitoring  
- **`find_sapphire_direction.lua`** - Find direction address near working base
- **`debug_sapphire_memory.lua`** - Advanced memory debugging

**Usage**: Load any of these in mGBA Script Viewer to debug memory addresses

### `/test-scripts/`
Python test scripts for system validation:

- **`test_final_sapphire_flow.py`** - Complete Sapphire detection flow test
- **`test_game_detection.py`** - Game detection system tests
- **`test_sapphire_detection.py`** - Sapphire-specific detection tests
- **`test_ai_service.py`** - AI service integration tests
- **`test_enhanced_ai_control.py`** - Enhanced AI control tests
- **`test_end_to_end_sapphire.py`** - End-to-end Sapphire tests
- **`test_fixes.py`** - Bug fix validation tests

**Usage**: Run with `python dev-tools/test-scripts/test_name.py`

## 🛠️ How to Use

### Memory Debugging
1. Load ROM in mGBA
2. Tools > Script Viewer  
3. Load any script from `memory-debugging/`
4. Follow script instructions

### System Testing
```bash
# Test game detection
python dev-tools/test-scripts/test_game_detection.py

# Test Sapphire support
python dev-tools/test-scripts/test_final_sapphire_flow.py
```

## 📋 Common Tasks

- **Find memory addresses**: Use `simple_sapphire_memory_finder.lua`
- **Test game detection**: Use `test_game_detection.py` 
- **Validate fixes**: Use `test_fixes.py`
- **End-to-end testing**: Use `test_end_to_end_sapphire.py`

These tools are kept separate from the main codebase to maintain clean organization.