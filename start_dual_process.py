#!/usr/bin/env python3
"""
Launcher script for dual-process Pokemon AI system.
Starts both video capture process and game control process.
"""

import subprocess
import time
import sys
import os
import signal
import json
import argparse
from typing import List, Optional


class DualProcessLauncher:
    """Launcher for dual-process Pokemon AI system."""
    
    def __init__(self, config_path: str = "config_emulator.json"):
        self.config_path = config_path
        self.processes: List[subprocess.Popen] = []
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down all processes...")
        self.stop_all()
        sys.exit(0)
    
    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}
    
    def start_video_capture_process(self, show_output: bool = False) -> Optional[subprocess.Popen]:
        """Start the video capture process."""
        print("🎬 Starting video capture process...")
        
        try:
            cmd = [sys.executable, "video_capture_process.py", "--config", self.config_path]
            
            if show_output:
                # Show live output
                process = subprocess.Popen(cmd)
            else:
                # Capture output for monitoring
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
            
            # Give it a moment to start
            time.sleep(2.0)
            
            # Check if process is still running
            if process.poll() is None:
                print("✅ Video capture process started successfully")
                return process
            else:
                print(f"❌ Video capture process failed to start (exit code: {process.returncode})")
                return None
                
        except Exception as e:
            print(f"❌ Error starting video capture process: {e}")
            return None
    
    def start_game_control_process(self, show_output: bool = False) -> Optional[subprocess.Popen]:
        """Start the game control process."""
        print("🎮 Starting game control process...")
        
        try:
            cmd = [sys.executable, "game_control_process.py", "--config", self.config_path]
            
            if show_output:
                # Show live output
                process = subprocess.Popen(cmd)
            else:
                # Capture output for monitoring
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
            
            # Give it a moment to start
            time.sleep(2.0)
            
            # Check if process is still running
            if process.poll() is None:
                print("✅ Game control process started successfully")
                return process
            else:
                print(f"❌ Game control process failed to start (exit code: {process.returncode})")
                return None
                
        except Exception as e:
            print(f"❌ Error starting game control process: {e}")
            return None
    
    def start_all(self, show_output: bool = False) -> bool:
        """Start both processes in the correct order."""
        print("🚀 Starting Pokemon AI Dual-Process System")
        print("=" * 50)
        
        # Load and validate config
        config = self._load_config()
        if not config:
            return False
        
        dual_process_config = config.get('dual_process_mode', {})
        if not dual_process_config.get('enabled', False):
            print("❌ Dual process mode is not enabled in config")
            print("   Set 'dual_process_mode.enabled' to true in config_emulator.json")
            return False
        
        print(f"📋 Configuration loaded:")
        print(f"   Video capture port: {dual_process_config.get('video_capture_port', 8889)}")
        print(f"   Rolling window: {dual_process_config.get('rolling_window_seconds', 20)}s")
        print(f"   Capture FPS: {config.get('capture_system', {}).get('capture_fps', 30)}")
        print()
        
        # Start video capture process first
        video_process = self.start_video_capture_process(show_output)
        if not video_process:
            return False
        
        self.processes.append(video_process)
        
        # Wait a bit for video process to initialize
        print("⏳ Waiting for video capture process to initialize...")
        time.sleep(3.0)
        
        # Start game control process
        game_process = self.start_game_control_process(show_output)
        if not game_process:
            self.stop_all()
            return False
        
        self.processes.append(game_process)
        
        self.running = True
        self.start_time = time.time()
        
        print("=" * 50)
        print("✅ Both processes started successfully!")
        print()
        print("📖 Next steps:")
        print("1. Start mGBA and load Pokemon Red ROM")
        print("2. In mGBA: Tools > Script Viewer > Load 'emulator/script.lua'")
        print("3. The AI will start playing automatically")
        print()
        print("🛑 Press Ctrl+C to stop all processes")
        print("=" * 50)
        
        return True
    
    def monitor_processes(self):
        """Monitor both processes and restart if they crash."""
        print("👁️  Monitoring processes...")
        print("    (Both processes are running in background)")
        print("    (Use Ctrl+C to stop when ready)")
        print()
        
        # Show periodic status updates
        last_status_time = time.time()
        status_interval = 30.0  # Show status every 30 seconds
        
        while self.running:
            time.sleep(1.0)
            
            # Check if any process has died
            for i, process in enumerate(self.processes):
                if process.poll() is not None:
                    process_name = "Video Capture" if i == 0 else "Game Control"
                    print(f"❌ {process_name} process died (exit code: {process.returncode})")
                    
                    # Read any remaining output
                    try:
                        output, _ = process.communicate(timeout=1.0)
                        if output:
                            print(f"Last output from {process_name}:")
                            print(output)
                    except:
                        pass
                    
                    self.running = False
                    break
            
            # Show periodic status updates
            current_time = time.time()
            if current_time - last_status_time >= status_interval:
                print(f"📊 Status: Both processes running for {current_time - self.start_time:.0f}s")
                print("    🎬 Video Capture: Continuously recording at 30 FPS")
                print("    🎮 Game Control: Waiting for mGBA connection")
                print("    💡 Connect mGBA with script.lua to start AI gameplay")
                print()
                last_status_time = current_time
    
    def stop_all(self):
        """Stop all processes gracefully."""
        print("🛑 Stopping all processes...")
        
        self.running = False
        
        for i, process in enumerate(self.processes):
            if process.poll() is None:  # Process is still running
                process_name = "Video Capture" if i == 0 else "Game Control"
                print(f"   Stopping {process_name} process...")
                
                try:
                    # Try graceful shutdown first
                    process.terminate()
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    print(f"   Force killing {process_name} process...")
                    process.kill()
                    process.wait()
                
                print(f"   ✅ {process_name} process stopped")
        
        self.processes.clear()
        print("✅ All processes stopped")
    
    def run(self, show_output: bool = False) -> bool:
        """Run the dual-process system."""
        if not self.start_all(show_output):
            return False
        
        try:
            self.monitor_processes()
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        finally:
            self.stop_all()
        
        return True


def main():
    """Main entry point for dual-process launcher."""
    parser = argparse.ArgumentParser(description='Pokemon AI Dual-Process System Launcher')
    parser.add_argument('--config', default='config_emulator.json', 
                       help='Path to configuration file')
    parser.add_argument('--show-output', action='store_true',
                       help='Show live output from subprocesses (verbose mode)')
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"❌ Configuration file not found: {args.config}")
        sys.exit(1)
    
    # Create and run launcher
    launcher = DualProcessLauncher(args.config)
    
    print("🎮 Pokemon AI Dual-Process System Launcher")
    print("=" * 50)
    
    if args.show_output:
        print("📢 Verbose mode: Showing live output from subprocesses")
        print()
    
    success = launcher.run(show_output=args.show_output)
    
    if success:
        print("\n✅ Dual-process system completed successfully")
    else:
        print("\n❌ Dual-process system failed")
        sys.exit(1)


if __name__ == '__main__':
    main()