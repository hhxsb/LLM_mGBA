#!/usr/bin/env python3
"""
Test script to verify main.py starts correctly and then stops gracefully.
"""

import subprocess
import time
import signal
import os

def test_main_startup():
    print("🧪 Testing main.py startup and graceful shutdown...")
    
    # Start main.py
    process = subprocess.Popen(['python', 'main.py'])
    
    try:
        # Wait for 10 seconds to see if it starts
        print("⏳ Waiting 10 seconds for startup...")
        time.sleep(10)
        
        # Send SIGINT (Ctrl+C) to test graceful shutdown
        print("🛑 Sending SIGINT for graceful shutdown...")
        process.send_signal(signal.SIGINT)
        
        # Wait for graceful shutdown
        try:
            process.wait(timeout=15)
            print("✅ Process shut down gracefully")
            return True
        except subprocess.TimeoutExpired:
            print("⚠️ Process didn't shut down gracefully, force killing...")
            process.kill()
            process.wait()
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        if process.poll() is None:
            process.kill()
        return False

if __name__ == "__main__":
    success = test_main_startup()
    if success:
        print("🎉 main.py test completed successfully!")
    else:
        print("❌ main.py test failed")