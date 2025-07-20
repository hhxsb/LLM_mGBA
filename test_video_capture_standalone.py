#!/usr/bin/env python3
"""
Standalone test for video_capture_process to diagnose issues
"""
import subprocess
import sys
import time
from pathlib import Path

def test_video_capture_standalone():
    """Test video capture process in isolation"""
    print("🎥 Testing Video Capture Process")
    print("=" * 40)
    
    project_root = Path(__file__).parent
    video_capture_file = project_root / "video_capture_process.py"
    
    if not video_capture_file.exists():
        print("❌ video_capture_process.py not found!")
        return False
    
    print("✅ video_capture_process.py found")
    print("🔄 Starting video capture process...")
    
    try:
        # Start the process
        process = subprocess.Popen(
            [sys.executable, "video_capture_process.py", "--config", "config_emulator.json"],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        print(f"✅ Process started with PID: {process.pid}")
        print("⏱️ Waiting 10 seconds to see if it runs...")
        
        # Wait for 10 seconds
        for i in range(10):
            if process.poll() is not None:
                print(f"❌ Process exited after {i} seconds")
                break
            print(f"⏳ {i+1}/10 seconds...")
            time.sleep(1)
        
        # Check final status
        if process.poll() is None:
            print("✅ Process is still running - seems healthy!")
            process.terminate()
            process.wait()
        else:
            print(f"❌ Process exited with code: {process.poll()}")
        
        # Get output
        try:
            stdout, stderr = process.communicate(timeout=2)
            
            if stdout:
                print("\n📤 STDOUT:")
                print("-" * 20)
                print(stdout[:1000] + ("..." if len(stdout) > 1000 else ""))
            
            if stderr:
                print("\n📤 STDERR:")
                print("-" * 20)
                print(stderr[:1000] + ("..." if len(stderr) > 1000 else ""))
                
        except subprocess.TimeoutExpired:
            print("⏱️ Output capture timed out")
            
        return process.poll() == 0 if process.poll() is not None else True
        
    except Exception as e:
        print(f"❌ Failed to start process: {e}")
        return False

def check_dependencies():
    """Check common dependencies for video capture"""
    print("\n🔍 Checking Dependencies")
    print("=" * 30)
    
    # Check Python modules
    modules_to_check = ["cv2", "PIL", "numpy", "mss", "pyautogui"]
    
    for module in modules_to_check:
        try:
            __import__(module)
            print(f"✅ {module} available")
        except ImportError:
            print(f"❌ {module} missing")
    
    # Check config file
    config_file = Path("config_emulator.json")
    if config_file.exists():
        print("✅ config_emulator.json found")
    else:
        print("❌ config_emulator.json missing")

def main():
    print("🎮 AI Pokemon Trainer - Video Capture Diagnostic")
    print("=" * 55)
    print("This tool helps diagnose video capture issues.")
    print("")
    
    # Check dependencies first
    check_dependencies()
    
    # Test standalone
    print("")
    success = test_video_capture_standalone()
    
    print("")
    if success:
        print("✅ Video capture process appears to be working!")
        print("💡 The issue may be with the dashboard's process management.")
        print("   Try running the dashboard with: python dashboard.py --debug")
    else:
        print("❌ Video capture process has issues.")
        print("💡 Check the error messages above and:")
        print("   1. Install missing dependencies")
        print("   2. Check config_emulator.json settings")
        print("   3. Ensure mGBA is running if needed")

if __name__ == "__main__":
    main()