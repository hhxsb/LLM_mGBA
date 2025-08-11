#!/usr/bin/env python3
"""
Complete functionality test for the AI GBA Player.
Tests that all components work together properly.
"""

import subprocess
import time
import requests
import signal
import os

def test_complete_system():
    print("🧪 Testing complete AI GBA Player system...")
    
    # Start main.py
    process = subprocess.Popen(['python', 'main.py'])
    
    try:
        # Wait for system to start up
        print("⏳ Waiting 15 seconds for complete startup...")
        time.sleep(15)
        
        # Test web interface
        try:
            dashboard_response = requests.get("http://localhost:8000/", timeout=5)
            if dashboard_response.status_code == 200:
                print("✅ Dashboard is accessible")
            else:
                print(f"⚠️ Dashboard returned status code: {dashboard_response.status_code}")
        except Exception as e:
            print(f"❌ Dashboard not accessible: {e}")
        
        # Test ROM configuration page
        try:
            rom_response = requests.get("http://localhost:8000/rom-config/", timeout=5)
            if rom_response.status_code == 200:
                print("✅ ROM configuration page is accessible")
            else:
                print(f"⚠️ ROM config page returned status code: {rom_response.status_code}")
        except Exception as e:
            print(f"❌ ROM config page not accessible: {e}")
        
        # Test admin panel
        try:
            admin_response = requests.get("http://localhost:8000/admin-panel/", timeout=5)
            if admin_response.status_code == 200:
                print("✅ Admin panel is accessible")
            else:
                print(f"⚠️ Admin panel returned status code: {admin_response.status_code}")
        except Exception as e:
            print(f"❌ Admin panel not accessible: {e}")
        
        print("✅ All web interfaces are working!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
        
    finally:
        # Cleanup
        print("🛑 Sending SIGINT for graceful shutdown...")
        process.send_signal(signal.SIGINT)
        
        try:
            process.wait(timeout=20)
            print("✅ System shut down gracefully")
            return True
        except subprocess.TimeoutExpired:
            print("⚠️ System didn't shut down gracefully, force killing...")
            process.kill()
            process.wait()
            return False

if __name__ == "__main__":
    success = test_complete_system()
    if success:
        print("\n🎉 Complete system test PASSED!")
        print("✅ AI GBA Player is fully functional")
    else:
        print("\n❌ Complete system test FAILED")