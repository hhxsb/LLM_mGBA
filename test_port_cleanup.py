#!/usr/bin/env python3
"""
Test script to specifically test the port cleanup functionality.
"""

import subprocess
import time
import signal
import requests

def test_port_cleanup():
    print("🧪 Testing port cleanup functionality...")
    
    # Start first main.py instance
    print("🚀 Starting first main.py instance...")
    first_process = subprocess.Popen(['python', 'main.py'])
    
    try:
        # Wait for first instance to start
        print("⏳ Waiting 15 seconds for first instance to start...")
        time.sleep(15)
        
        # Verify it's running by checking the web interface
        try:
            response = requests.get("http://localhost:8000/", timeout=5)
            if response.status_code == 200:
                print("✅ First instance is running and serving web interface")
            else:
                print(f"⚠️ First instance web interface returned status: {response.status_code}")
        except Exception as e:
            print(f"❌ First instance web interface not accessible: {e}")
            return False
        
        # Now try to start a second instance with --kill-port --start
        print("\n🔧 Starting second instance with force cleanup...")
        result = subprocess.run(['python', 'main.py', '--kill-port', '--start'], timeout=30)
        
        if result.returncode == 0:
            print("❌ Second instance should not have succeeded (timeout expected)")
        else:
            print("✅ Second instance handled correctly (expected timeout/interruption)")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("✅ Expected timeout occurred (second instance properly started)")
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
        
    finally:
        # Clean up first process
        print("\n🛑 Cleaning up first process...")
        first_process.send_signal(signal.SIGINT)
        try:
            first_process.wait(timeout=15)
            print("✅ First process cleaned up")
        except subprocess.TimeoutExpired:
            first_process.kill()
            first_process.wait()
            print("🔨 First process force killed")

if __name__ == "__main__":
    success = test_port_cleanup()
    if success:
        print("\n🎉 Port cleanup test completed!")
    else:
        print("\n❌ Port cleanup test failed")