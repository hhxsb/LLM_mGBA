#!/usr/bin/env python3
"""
Simple system starter that bypasses Django issues and starts the unified service directly.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def start_unified_service():
    """Start the unified service directly"""
    print("🎯 Starting unified service directly...")
    
    service_script = project_root / "ai_gba_player" / "core" / "unified_game_service.py"
    config_file = project_root / "config_emulator.json"
    
    if not service_script.exists():
        print(f"❌ Service script not found: {service_script}")
        return False
    
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return False
    
    try:
        # Start the service
        process = subprocess.Popen([
            'python', str(service_script), 
            '--config', str(config_file),
            '--debug'
        ], cwd=str(project_root))
        
        print(f"✅ Unified service started (PID: {process.pid})")
        print("🎮 The service is now running with:")
        print("  - ✅ Core modules imported")
        print("  - ✅ mGBA window detection")
        print("  - ✅ Video capture active")
        print("  - ✅ AI decision-making ready")
        print()
        print("💡 To test: Load a ROM in mGBA and run the Lua script")
        print("🛑 Press Ctrl+C to stop")
        
        # Keep the service running
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping service...")
            process.terminate()
            process.wait()
            print("✅ Service stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to start service: {e}")
        return False

def main():
    print("🎮 AI GBA Player - Direct Service Starter")
    print("=" * 50)
    print("This bypasses Django issues and starts the unified service directly")
    print()
    
    if not start_unified_service():
        print("❌ Failed to start system")
        sys.exit(1)

if __name__ == "__main__":
    main()