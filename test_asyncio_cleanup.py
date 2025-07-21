#!/usr/bin/env python3
"""
Test AsyncIO task cleanup in dashboard system
"""
import asyncio
import signal
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from dashboard.backend.main import DashboardApp

async def test_dashboard_startup_shutdown():
    """Test dashboard startup and graceful shutdown"""
    print("🧪 Testing Dashboard AsyncIO Task Cleanup")
    print("=" * 50)
    
    # Create dashboard app
    dashboard = DashboardApp("config_emulator.json")
    
    print("🚀 Starting dashboard...")
    await dashboard.startup()
    
    print("✅ Dashboard started, running for 3 seconds...")
    await asyncio.sleep(3)
    
    print("🛑 Shutting down dashboard...")
    await dashboard.shutdown()
    
    print("✅ Dashboard shutdown complete")
    
    # Check for pending tasks
    pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
    if pending_tasks:
        print(f"⚠️ Found {len(pending_tasks)} pending tasks:")
        for task in pending_tasks:
            print(f"   - {task.get_name()}: {task}")
    else:
        print("✅ No pending tasks found!")

def main():
    """Main test function"""
    try:
        # Set up event loop
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Run the test
        asyncio.run(test_dashboard_startup_shutdown())
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1
    
    print("\n🎯 AsyncIO cleanup test completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())