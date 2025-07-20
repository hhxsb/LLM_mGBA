#!/usr/bin/env python3
"""
Test script to demonstrate frontend-only dashboard mode
"""
import sys
import time
import requests
from pathlib import Path

# Add dashboard backend to path
dashboard_path = Path(__file__).parent / "dashboard" / "backend"
sys.path.insert(0, str(dashboard_path))

def test_frontend_only_mode():
    """Test that frontend-only mode works correctly"""
    print("🧪 Testing Frontend-Only Mode")
    print("=" * 50)
    
    # Enable debug logging
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    
    # Import after path setup
    from main import DashboardApp
    
    try:
        # Test creating app in frontend-only mode
        app = DashboardApp(config_path="config_emulator.json")
        
        # Set frontend_only BEFORE creating process manager
        app.frontend_only = True
        # Recreate process manager with frontend_only flag
        app.process_manager = app.process_manager.__class__(app.config, frontend_only=True)
        
        print("✅ Dashboard app created in frontend-only mode")
        
        # Check that AI processes are skipped
        ai_processes = ["video_capture", "game_control", "knowledge_system"]
        for process_name in ai_processes:
            if process_name in app.process_manager.processes:
                print(f"❌ {process_name} should be skipped in frontend-only mode")
                return False
            else:
                print(f"✅ {process_name} correctly skipped")
        
        # Check that frontend process is included
        if "frontend" in app.process_manager.processes:
            print("✅ Frontend process correctly included")
        else:
            print("⚠️ Frontend process not found (may be due to npm not available)")
        
        print("\n🎯 Frontend-only mode test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_api_endpoints():
    """Test that API endpoints work"""
    print("\n🌐 Testing API Endpoints")
    print("=" * 30)
    
    base_url = "http://127.0.0.1:3000"
    
    endpoints = [
        "/api/v1/health",
        "/api/v1/status", 
        "/api/v1/knowledge/tasks",
        "/api/v1/knowledge/summary"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"⚠️ {endpoint} - Status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - Error: {e}")

if __name__ == "__main__":
    print("🎮 AI Pokemon Trainer Dashboard - Frontend Test")
    print("=" * 60)
    print("This script tests the dashboard in frontend-only mode")
    print("to verify that AI processes are properly skipped.")
    print("")
    
    # Test frontend-only mode
    if test_frontend_only_mode():
        print("\n✅ All frontend-only tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    
    print("\n💡 To test with a running dashboard, use:")
    print("   python dashboard.py --frontend-only --debug")
    print("   Then run: python test_dashboard_frontend_only.py")