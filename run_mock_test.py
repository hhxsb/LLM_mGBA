#!/usr/bin/env python3
"""
Simple script to run the dashboard in mock mode for testing.
This demonstrates how to test the dashboard without requiring real game processes.
"""

import subprocess
import sys
import time
from pathlib import Path

def main():
    """Run dashboard in mock mode for testing."""
    print("🎭 Starting AI Pokemon Trainer Dashboard in Mock Mode")
    print("=" * 60)
    print()
    print("This will:")
    print("  📹 Start mock video processor (serves test.gif)")
    print("  🎮 Start mock game processor (sends test messages)")
    print("  📊 Start dashboard with frontend")
    print()
    print("Dashboard will be available at: http://localhost:3000")
    print("Frontend will be available at: http://localhost:5173")
    print()
    
    # Get project root
    project_root = Path(__file__).parent
    dashboard_script = project_root / "dashboard" / "backend" / "main.py"
    
    if not dashboard_script.exists():
        print(f"❌ Dashboard script not found: {dashboard_script}")
        return 1
    
    # Run dashboard in mock mode
    try:
        print("🚀 Starting dashboard in mock mode...")
        print("   Use Ctrl+C to stop")
        print()
        
        cmd = [
            sys.executable, 
            str(dashboard_script),
            "--mock",
            "--debug"
        ]
        
        subprocess.run(cmd, cwd=str(project_root))
        
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Error running dashboard: {e}")
        return 1

if __name__ == '__main__':
    exit(main())