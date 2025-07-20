#!/usr/bin/env python3
"""
AI Pokemon Trainer Dashboard - Single command entry point
Starts the unified dashboard with process management and real-time visualization
"""
import sys
import os
from pathlib import Path

# Add dashboard backend to path
dashboard_path = Path(__file__).parent / "dashboard" / "backend"
sys.path.insert(0, str(dashboard_path))

# Import and run the dashboard
from main import main

if __name__ == "__main__":
    import sys
    
    # Check for frontend-only flag
    frontend_only = "--frontend-only" in sys.argv
    debug_mode = "--debug" in sys.argv
    
    print("🎮 AI Pokemon Trainer Dashboard")
    print("=" * 50)
    
    if frontend_only:
        print("🎯 Frontend-Only Mode: AI processes will be skipped")
    else:
        print("🚀 Starting unified dashboard with frontend...")
    
    print("")
    print("📌 Access URLs:")
    print("   🌐 Frontend Dashboard: http://localhost:5173")
    print("   🔧 Backend API: http://127.0.0.1:3000/api/v1")
    print("   📡 WebSocket: ws://127.0.0.1:3000/ws")
    
    if frontend_only:
        print("")
        print("ℹ️  AI processes disabled - dashboard will show mock data")
    
    print("")
    print("⏱️  Please wait while services start...")
    print("")
    
    main()