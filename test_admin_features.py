#!/usr/bin/env python3
"""
Test the new admin features and debug improvements
"""
import time
import json
import requests
from pathlib import Path

def test_api_endpoints():
    """Test the new admin API endpoints"""
    base_url = "http://127.0.0.1:3000"
    
    print("🧪 Testing Admin API Endpoints")
    print("=" * 40)
    
    # Test basic health
    try:
        response = requests.get(f"{base_url}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"⚠️ Health endpoint returned {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
        return False
    
    # Test system status
    try:
        response = requests.get(f"{base_url}/api/v1/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            processes = data.get("system", {}).get("processes", {})
            print(f"✅ System status - {len(processes)} processes found")
            
            # Test process logs for each process
            for process_name in processes.keys():
                try:
                    log_response = requests.get(f"{base_url}/api/v1/processes/{process_name}/logs", timeout=5)
                    if log_response.status_code == 200:
                        log_data = log_response.json()
                        print(f"  ✅ {process_name} logs - {log_data.get('total_lines', 0)} lines")
                    else:
                        print(f"  ⚠️ {process_name} logs returned {log_response.status_code}")
                except Exception as e:
                    print(f"  ❌ {process_name} logs failed: {e}")
            
        else:
            print(f"⚠️ System status returned {response.status_code}")
    except Exception as e:
        print(f"❌ System status failed: {e}")
    
    # Test knowledge endpoints
    try:
        response = requests.get(f"{base_url}/api/v1/knowledge/summary", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Knowledge summary - Available: {data.get('knowledge_available', False)}")
        else:
            print(f"⚠️ Knowledge summary returned {response.status_code}")
    except Exception as e:
        print(f"❌ Knowledge summary failed: {e}")

    return True

def print_usage_instructions():
    """Print usage instructions for the new features"""
    print("\n🎯 New Admin Features Available!")
    print("=" * 50)
    print("")
    print("1. 📊 Dashboard View (Default):")
    print("   - Chat interface with AI interactions")
    print("   - System status monitoring") 
    print("   - Knowledge base with tasks")
    print("")
    print("2. ⚙️ Admin Panel (New!):")
    print("   - Process management controls")
    print("   - Real-time process logs")
    print("   - Manual restart/start/stop buttons")
    print("   - Error diagnosis tools")
    print("")
    print("🚀 How to Access:")
    print("   1. Start dashboard: python dashboard.py --config config_emulator.json")
    print("   2. Open browser: http://localhost:5173")
    print("   3. Click '⚙️ Admin' tab in the header")
    print("")
    print("🐛 Debug Options:")
    print("   - Debug mode: python dashboard.py --debug")
    print("   - Frontend only: python dashboard.py --frontend-only")
    print("   - Combined: python dashboard.py --frontend-only --debug")
    print("")
    print("✨ Fixed Issues:")
    print("   ✅ No more process crash loops")
    print("   ✅ Clear error messages with stderr/stdout")
    print("   ✅ Optional processes fail gracefully") 
    print("   ✅ Admin controls for manual management")
    print("   ✅ Real-time log viewing")

if __name__ == "__main__":
    print("🎮 AI Pokemon Trainer Dashboard - Admin Features Test")
    print("=" * 65)
    print("This script tests the new admin features and API endpoints.")
    print("")
    
    # Test if dashboard is running
    try:
        response = requests.get("http://127.0.0.1:3000/api/v1/health", timeout=3)
        if response.status_code == 200:
            print("🌐 Dashboard is running! Testing API endpoints...")
            test_api_endpoints()
        else:
            print("⚠️ Dashboard is running but health check failed")
    except requests.exceptions.ConnectionError:
        print("🔌 Dashboard is not running. Start it with:")
        print("   python dashboard.py --config config_emulator.json")
        print("")
    except Exception as e:
        print(f"❌ Error connecting to dashboard: {e}")
    
    print_usage_instructions()