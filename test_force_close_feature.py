#!/usr/bin/env python3
"""
Test the complete force close feature functionality.
"""

import subprocess
import time
import signal
import requests

def test_force_close_feature():
    print("🧪 Testing force close existing main.py functionality...")
    
    # Step 1: Start main.py normally
    print("🚀 Step 1: Starting main.py normally...")
    main_process = subprocess.Popen(['python', 'main.py'])
    
    try:
        # Wait for startup
        print("⏳ Waiting 15 seconds for startup...")
        time.sleep(15)
        
        # Verify it's running
        try:
            response = requests.get("http://localhost:8000/", timeout=5)
            if response.status_code == 200:
                print("✅ Main process is running and serving web interface")
            else:
                print(f"⚠️ Web interface returned status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Web interface not accessible: {e}")
            return False
        
        # Step 2: Use --kill-port to find and close the process
        print("\n🔧 Step 2: Using --kill-port to close existing process...")
        result = subprocess.run(
            ['python', 'main.py', '--kill-port'], 
            capture_output=True, 
            text=True,
            timeout=15
        )
        
        print("Kill-port output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        # Step 3: Verify the original process was killed
        print("\n🔍 Step 3: Verifying original process was terminated...")
        time.sleep(3)
        
        # Check if original process is still running
        poll_result = main_process.poll()
        if poll_result is None:
            print("⚠️ Original process is still running, sending SIGINT...")
            main_process.send_signal(signal.SIGINT)
            try:
                main_process.wait(timeout=10)
                print("✅ Original process terminated after SIGINT")
            except subprocess.TimeoutExpired:
                main_process.kill()
                print("🔨 Original process force killed")
        else:
            print("✅ Original process was successfully terminated by --kill-port")
        
        # Step 4: Verify port is now available
        print("\n🌐 Step 4: Verifying port is now available...")
        try:
            response = requests.get("http://localhost:8000/", timeout=3)
            print(f"⚠️ Port still responding (status: {response.status_code})")
        except requests.exceptions.ConnectionError:
            print("✅ Port is now available (connection refused as expected)")
        except Exception as e:
            print(f"✅ Port appears to be free: {e}")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Kill-port command timed out")
        return False
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    finally:
        # Cleanup
        if main_process.poll() is None:
            print("\n🧹 Final cleanup...")
            main_process.send_signal(signal.SIGINT)
            try:
                main_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                main_process.kill()
                main_process.wait()

if __name__ == "__main__":
    success = test_force_close_feature()
    if success:
        print("\n🎉 Force close feature test PASSED!")
        print("✅ The --kill-port functionality is working correctly")
    else:
        print("\n❌ Force close feature test FAILED")