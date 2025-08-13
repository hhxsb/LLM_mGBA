# 🧹 AI GBA Player Cleanup Plan

## Overview
This document outlines the cleanup of dead code and obsolete files after the successful implementation of the Django-based AI GBA Player system.

## ✅ Current Working System
- **Main Entry Point**: `main.py` (launcher)
- **Core Service**: `ai_gba_player/core/unified_game_service.py`
- **Web Interface**: `ai_gba_player/` (Django app)
- **Configuration**: `config_emulator.json`
- **mGBA Integration**: `emulator/script.lua`

## 🗑️ Files to Remove

### 1. Obsolete Test Scripts (Root Level)
These were development/testing files that are no longer needed:
- `test_complete_functionality.py`
- `test_dashboard_frontend_only.py` 
- `test_dashboard_integration.py`
- `test_dashboard_websocket.py`
- `test_admin_features.py`
- `test_asyncio_cleanup.py`
- `test_storage.py`
- `test_unified_service.py`
- `test_main.py`
- `test_port_cleanup.py`
- `test_force_close_feature.py`
- `test_database_config.py`
- `test_file_browser.py`
- `test_native_file_picker.py`
- `test_file_picker_fixed.py`

### 2. Obsolete Controller Files
- `game_controller.py` (replaced by unified_game_service.py)
- `google_controller.py` (functionality moved to games/pokemon_red/)
- `pokemon_logger.py` (replaced by core/logging_config.py)

### 3. Mock/Debug Files
- `mock_game_processor.py`
- `mock_video_processor.py`
- `run_mock_test.py`
- `debug_file_picker.html`
- `demo_file_picker.html`
- `cleanup_ports.py` (functionality in main.py now)

### 4. Old Configuration Files
- `config.json` (replaced by config_emulator.json)
- `config.template.json` (no longer needed)

### 5. Standalone Scripts
- `dashboard.py` (replaced by Django dashboard)
- `start_system.py` (replaced by main.py)
- `start_unified_service.sh` (replaced by main.py)
- `kill_dashboard.sh` (replaced by main.py cleanup)
- `inspect_videos.py` (development tool)

### 6. Archive Directory
- `archive/react-fastapi-system/` (old React+FastAPI implementation)

### 7. Old Documentation Files
- `README_OLD.md`
- `frontend_implementation_plan.md`
- `debugging_improvements_summary.md`
- `process_dependency_solution.md`
- `DJANGO_MIGRATION_COMPLETE.md`
- `DOCUMENTATION_REORGANIZATION_SUMMARY.md`
- `FORCE_CLOSE_FEATURE.md`

## 📁 Files to Keep

### Core System
- `main.py` - Main launcher
- `ai_gba_player/` - Django web interface
- `core/` - Core modules still used by games
- `games/` - Game implementations
- `emulator/` - mGBA Lua scripts
- `config_emulator.json` - Main configuration

### Data & Storage
- `data/` - Screenshots, videos, knowledge base
- `notepad.txt` - AI memory file
- `requirements.txt` - Python dependencies

### Documentation (Updated)
- `README.md` - Main documentation
- `CLAUDE.md` - System guidance
- `SETUP.md` - Setup instructions
- `tests/` - Proper test suite
- `wiki/` - Comprehensive documentation

## 🔧 Updates Needed

### 1. CLAUDE.md Updates
- Update system architecture description
- Remove references to old dual-process system
- Update commands and usage examples
- Document new Django interface

### 2. README.md Updates  
- Simplify setup instructions
- Update feature list
- Remove outdated screenshots/references
- Add new web interface documentation

### 3. Requirements Cleanup
- Remove unused dependencies
- Ensure all needed packages are listed

## 📈 Benefits of Cleanup
- **Reduced complexity** - Remove confusing obsolete files
- **Clearer documentation** - Updated to match current system
- **Easier maintenance** - Less code to maintain
- **Better onboarding** - Clearer structure for new users
- **Smaller repository** - Faster clones and reduced storage

## 🎯 Next Steps
1. Remove obsolete files
2. Update documentation
3. Test system still works after cleanup
4. Commit clean state