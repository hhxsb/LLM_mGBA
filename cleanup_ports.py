#!/usr/bin/env python3
"""
Port cleanup utility for dashboard conflicts
"""
import socket
import sys
import time

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is already in use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False

def find_process_using_port(port: int):
    """Find the process using a specific port using lsof"""
    try:
        import subprocess
        result = subprocess.run(['lsof', '-i', f':{port}'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Skip header
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        process_name = parts[0]
                        pid = parts[1]
                        return pid, process_name
    except Exception:
        pass
    return None, None

def cleanup_dashboard_ports():
    """Clean up dashboard-related ports"""
    dashboard_ports = [3000, 5173, 8888, 8889]
    
    print("🧹 AI Pokemon Dashboard Port Cleanup")
    print("=" * 40)
    
    for port in dashboard_ports:
        print(f"\n🔍 Checking port {port}...")
        
        if is_port_in_use(port):
            print(f"⚠️ Port {port} is in use")
            
            pid, process_name = find_process_using_port(port)
            if pid and process_name:
                print(f"   Process: {process_name} (PID: {pid})")
                
                # Ask user for confirmation
                response = input(f"   Kill process {pid}? [y/N]: ").strip().lower()
                if response in ['y', 'yes']:
                    try:
                        import subprocess
                        subprocess.run(['kill', pid], check=True)
                        print(f"✅ Terminated process {pid}")
                        
                        # Wait and check again
                        time.sleep(1)
                        if not is_port_in_use(port):
                            print(f"✅ Port {port} is now free")
                        else:
                            print(f"⚠️ Port {port} still in use, trying force kill...")
                            subprocess.run(['kill', '-9', pid], check=True)
                            time.sleep(1)
                            if not is_port_in_use(port):
                                print(f"✅ Port {port} is now free (force killed)")
                            else:
                                print(f"❌ Port {port} still in use after force kill")
                    except Exception as e:
                        print(f"❌ Error killing process: {e}")
                else:
                    print(f"⏭️ Skipping port {port}")
            else:
                print(f"❌ Could not identify process using port {port}")
        else:
            print(f"✅ Port {port} is free")
    
    print(f"\n🎯 Port cleanup complete")

if __name__ == "__main__":
    try:
        cleanup_dashboard_ports()
    except KeyboardInterrupt:
        print("\n🛑 Cleanup cancelled by user")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        sys.exit(1)