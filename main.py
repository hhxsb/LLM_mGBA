#!/usr/bin/env python3
"""
AI GBA Player - Main Entry Point
Simplified launcher that automatically starts Django server and unified service.

Usage:
    python main.py
    
    Then access the dashboard at: http://localhost:8000
"""

import os
import sys
import time
import signal
import threading
import subprocess
import webbrowser
from pathlib import Path
import json
import atexit
import psutil
import socket

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))


class AIGBAPlayerLauncher:
    """Main launcher that manages Django server and unified service."""
    
    def __init__(self):
        self.django_process = None
        self.service_process = None
        self.service_started = False
        self.running = True
        self.django_ready = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self.cleanup)
        
        print("🎮 AI GBA Player - Starting...")
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C and other shutdown signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def start(self):
        """Start the complete AI GBA Player system."""
        try:
            # Step 1: Start Django server
            print("📊 Starting Django web server...")
            if not self._start_django_server():
                print("❌ Failed to start Django server")
                return False
            
            # Step 2: Wait for Django to be ready
            print("⏳ Waiting for Django server to be ready...")
            if not self._wait_for_django():
                print("❌ Django server failed to start properly")
                return False
            
            # Step 3: Initialize database
            print("🗄️ Setting up database...")
            self._setup_database()
            
            # Step 4: Start unified service
            print("🎯 Starting unified game service...")
            if not self._start_unified_service():
                print("❌ Failed to start unified service")
                return False
            
            # Step 5: Open browser
            print("🌐 Opening dashboard in browser...")
            self._open_dashboard()
            
            print("\n🎉 AI GBA Player is running!")
            print("=" * 50)
            print("📊 Dashboard: http://localhost:8000")
            print("⚙️ Admin Panel: http://localhost:8000/admin-panel/")
            print("🎮 Game Monitor: http://localhost:8000/")
            print("=" * 50)
            print("💡 Load a ROM in mGBA and run script.lua to start playing")
            print("🛑 Press Ctrl+C to stop all services")
            print()
            
            # Step 6: Keep main thread alive and monitor
            self._monitor_services()
            
            return True
            
        except Exception as e:
            print(f"❌ Error starting AI GBA Player: {e}")
            self.cleanup()
            return False
    
    def _force_close_port(self, port=8000):
        """Force close any processes using the specified port."""
        print(f"🔍 Checking for existing processes on port {port}...")
        
        processes_killed = []
        processed_pids = set()  # Track already processed PIDs to avoid duplicates
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    pid = proc.info['pid']
                    
                    # Skip if we've already processed this PID
                    if pid in processed_pids:
                        continue
                    processed_pids.add(pid)
                    
                    # Get process connections (prefer net_connections for newer psutil)
                    connections = []
                    try:
                        connections = proc.net_connections()
                    except (AttributeError, psutil.AccessDenied):
                        # Skip if we don't have access or method doesn't exist
                        continue
                    except Exception:
                        # Skip any other connection-related errors
                        continue
                    
                    if connections:
                        port_found = False
                        for conn in connections:
                            if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == port:
                                port_found = True
                                break
                        
                        if port_found:
                            # Found a process using our port
                            name = proc.info['name']
                            cmdline = ' '.join(proc.info['cmdline'] or [])
                            
                            # Check if this is likely our Django process or any Python process
                            if 'manage.py' in cmdline or 'runserver' in cmdline or 'python' in name.lower():
                                print(f"🔧 Found process using port {port}: PID {pid} ({name})")
                                print(f"   Command: {cmdline[:100]}...")
                                
                                # Try graceful termination first
                                try:
                                    proc.terminate()
                                    proc.wait(timeout=5)
                                    print(f"✅ Gracefully stopped process {pid}")
                                    processes_killed.append(pid)
                                except psutil.TimeoutExpired:
                                    # Force kill if graceful termination fails
                                    proc.kill()
                                    proc.wait()
                                    print(f"🔨 Force killed process {pid}")
                                    processes_killed.append(pid)
                                except Exception as e:
                                    print(f"⚠️ Could not stop process {pid}: {e}")
                                
                                break  # Move to next process
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Process might have ended or we don't have access
                    continue
                    
        except Exception as e:
            print(f"⚠️ Error while checking for existing processes: {e}")
        
        if processes_killed:
            print(f"✅ Cleaned up {len(processes_killed)} process(es) using port {port}")
            time.sleep(2)  # Give processes time to fully close
        else:
            print(f"✅ No conflicting processes found on port {port}")
            
        return len(processes_killed) > 0
    
    def _is_port_available(self, port=8000):
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return True
        except socket.error:
            return False
    
    def _start_django_server(self):
        """Start the Django development server."""
        try:
            # First, force close any existing processes using port 8000
            self._force_close_port(8000)
            
            # Double-check that port is now available
            if not self._is_port_available(8000):
                print("⚠️ Port 8000 still not available, attempting additional cleanup...")
                time.sleep(3)
                if not self._is_port_available(8000):
                    print("❌ Port 8000 is still in use after cleanup attempts")
                    return False
            
            django_dir = project_root / "ai_gba_player"
            manage_py = django_dir / "manage.py"
            
            if not manage_py.exists():
                print(f"❌ Django manage.py not found at {manage_py}")
                return False
            
            # Start Django server in background
            self.django_process = subprocess.Popen(
                [sys.executable, str(manage_py), "runserver", "127.0.0.1:8000"],
                cwd=str(django_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Check if process started successfully
            time.sleep(1)
            if self.django_process.poll() is not None:
                stdout, stderr = self.django_process.communicate()
                print(f"❌ Django failed to start: {stderr}")
                return False
            
            print(f"✅ Django server started (PID: {self.django_process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Error starting Django server: {e}")
            return False
    
    def _wait_for_django(self, max_wait=30):
        """Wait for Django server to be ready."""
        import requests
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = requests.get("http://127.0.0.1:8000", timeout=2)
                if response.status_code == 200:
                    self.django_ready = True
                    print("✅ Django server is ready")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
            print("⏳ Waiting for Django server...")
        
        print("❌ Django server did not respond within timeout")
        return False
    
    def _setup_database(self):
        """Setup the database with initial data."""
        try:
            django_dir = project_root / "ai_gba_player"
            manage_py = django_dir / "manage.py"
            
            # Run migrations
            result = subprocess.run(
                [sys.executable, str(manage_py), "migrate"],
                cwd=str(django_dir),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"⚠️ Database migration issues: {result.stderr}")
            else:
                print("✅ Database migrations completed")
            
            # Skip custom database setup commands (they don't exist in simplified Django)
            print("✅ Database setup completed")
                
        except Exception as e:
            print(f"⚠️ Database setup error: {e}")
    
    def _start_unified_service(self):
        """Start the unified service directly."""
        try:
            service_script = project_root / "ai_gba_player" / "core" / "unified_game_service.py"
            config_path = project_root / "config_emulator.json"
            
            if not service_script.exists():
                print(f"❌ Service script not found: {service_script}")
                return False
                
            if not config_path.exists():
                print(f"❌ Config file not found: {config_path}")
                return False
            
            # Start unified service directly in background
            self.service_process = subprocess.Popen([
                sys.executable, str(service_script), 
                '--config', str(config_path),
                '--debug'
            ], 
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )
            
            # Give it a moment to start
            time.sleep(3)
            
            # Check if it's running
            if self.service_process.poll() is None:
                print("✅ Unified service started successfully")
                self.service_started = True
                return True
            else:
                stdout, stderr = self.service_process.communicate()
                print(f"❌ Unified service failed to start: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting unified service: {e}")
            return False
    
    def _open_dashboard(self):
        """Open the dashboard in the default web browser."""
        try:
            # Wait a moment for everything to be ready
            time.sleep(2)
            webbrowser.open("http://localhost:8000")
            print("✅ Dashboard opened in browser")
        except Exception as e:
            print(f"⚠️ Could not open browser: {e}")
    
    def _monitor_services(self):
        """Monitor services and keep main thread alive."""
        try:
            while self.running:
                # Check Django server
                if self.django_process and self.django_process.poll() is not None:
                    print("❌ Django server stopped unexpectedly")
                    break
                
                # Check unified service
                if self.service_process and self.service_process.poll() is not None:
                    print("❌ Unified service stopped unexpectedly")
                    # Could restart it here if needed
                
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Received keyboard interrupt")
        except Exception as e:
            print(f"❌ Error monitoring services: {e}")
        finally:
            self.cleanup()
    
    def _check_service_status(self):
        """Check the status of the unified service."""
        # Service status is now checked directly in _monitor_services
        # by checking if self.service_process.poll() returns None
        pass
    
    def restart_service(self):
        """Restart the unified service."""
        print("🔄 Restarting unified service...")
        try:
            # Stop current service
            if self.service_process:
                self.service_process.terminate()
                try:
                    self.service_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.service_process.kill()
                    self.service_process.wait()
            
            # Start new service
            time.sleep(2)
            return self._start_unified_service()
                
        except Exception as e:
            print(f"❌ Error restarting service: {e}")
            return False
    
    def cleanup(self):
        """Clean up all running processes."""
        if not self.running:
            return
        
        print("\n🧹 Cleaning up services...")
        self.running = False
        
        # Stop unified service
        if self.service_process:
            try:
                print("🛑 Stopping unified service...")
                self.service_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.service_process.wait(timeout=10)
                    print("✅ Unified service stopped gracefully")
                except subprocess.TimeoutExpired:
                    print("⚠️ Unified service didn't stop gracefully, force killing...")
                    self.service_process.kill()
                    self.service_process.wait()
                    print("✅ Unified service force stopped")
                    
            except Exception as e:
                print(f"⚠️ Error stopping unified service: {e}")
        
        # Stop Django server
        if self.django_process:
            try:
                print("🛑 Stopping Django server...")
                self.django_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.django_process.wait(timeout=10)
                    print("✅ Django server stopped gracefully")
                except subprocess.TimeoutExpired:
                    print("⚠️ Django server didn't stop gracefully, force killing...")
                    self.django_process.kill()
                    self.django_process.wait()
                    print("✅ Django server force stopped")
                    
            except Exception as e:
                print(f"⚠️ Error stopping Django: {e}")
        
        print("✅ Cleanup completed")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AI GBA Player - Universal AI gaming framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Start AI GBA Player
  python main.py --kill-port        # Force close processes on port 8000
  python main.py --kill-port --start  # Force close and then start
        """
    )
    parser.add_argument(
        '--kill-port',
        action='store_true',
        help='Force close any processes using port 8000'
    )
    parser.add_argument(
        '--start',
        action='store_true',
        help='Start AI GBA Player (default behavior, use with --kill-port to force close first)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port number to check/clean (default: 8000)'
    )
    
    args = parser.parse_args()
    
    print("🎮 AI GBA Player Launcher")
    print("=" * 40)
    
    # Handle kill-port command
    if args.kill_port:
        print(f"🧹 Force closing processes on port {args.port}...")
        launcher = AIGBAPlayerLauncher()
        killed_any = launcher._force_close_port(args.port)
        
        if killed_any:
            print(f"✅ Successfully cleaned up port {args.port}")
        else:
            print(f"✅ No processes found on port {args.port}")
        
        # If --start wasn't specified, just exit after cleanup
        if not args.start:
            print("💡 Use --start to launch AI GBA Player after cleanup")
            return
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    # Check if config exists
    config_path = project_root / "config_emulator.json"
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("Please ensure config_emulator.json exists in the project root")
        sys.exit(1)
    
    # Check if ai_gba_player directory exists
    django_dir = project_root / "ai_gba_player"
    if not django_dir.exists():
        print(f"❌ Django application not found: {django_dir}")
        sys.exit(1)
    
    try:
        launcher = AIGBAPlayerLauncher()
        success = launcher.start()
        
        if not success:
            print("❌ Failed to start AI GBA Player")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()