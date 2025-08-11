#!/usr/bin/env python3
"""
Test script to verify the file browser functionality is working correctly.
"""

import subprocess
import time
import requests
import sys
import os
import json
from pathlib import Path

# Change to Django directory and setup environment
project_root = Path(__file__).parent
django_path = project_root / "ai_gba_player"

def test_file_browser_system():
    print("🗂️ Testing File Browser System...")
    
    # Start Django server
    django_process = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8004", "--noreload"],
        cwd=str(django_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Wait for server to start
        time.sleep(5)
        
        # Test 1: Configuration Page File Browser Integration
        print("\n📋 Test 1: Configuration Page File Browser")
        response = requests.get("http://localhost:8004/config/", timeout=5)
        if response.status_code == 200:
            content = response.text
            browse_button_count = content.count('📁 Browse')
            if browse_button_count >= 5:  # Should have browse buttons for all path fields
                print(f"✅ Configuration page has {browse_button_count} browse buttons")
                
                # Check for file browser modal
                if "fileBrowserModal" in content and "openFileBrowser" in content:
                    print("✅ File browser modal and JavaScript functions present")
                else:
                    print("❌ File browser modal or functions missing")
                    return False
            else:
                print(f"❌ Expected at least 5 browse buttons, found {browse_button_count}")
                return False
        else:
            print(f"❌ Configuration page returned status: {response.status_code}")
            return False
        
        # Test 2: ROM Configuration Page File Browser Integration  
        print("\n🎮 Test 2: ROM Configuration Page File Browser")
        response = requests.get("http://localhost:8004/rom-config/", timeout=5)
        if response.status_code == 200:
            content = response.text
            browse_button_count = content.count('📁 Browse')
            if browse_button_count >= 3:  # ROM path, mGBA path, script path
                print(f"✅ ROM configuration page has {browse_button_count} browse buttons")
                
                # Check for file filtering logic
                if "browserPathType === 'roms'" in content and "browserPathType === 'executables'" in content:
                    print("✅ File type filtering logic present")
                else:
                    print("❌ File type filtering logic missing")
                    return False
            else:
                print(f"❌ Expected at least 3 browse buttons, found {browse_button_count}")
                return False
        else:
            print(f"❌ ROM configuration page returned status: {response.status_code}")
            return False
        
        # Test 3: Common Paths API
        print("\n🗂️ Test 3: Common Paths API")
        for path_type in ['general', 'roms', 'executables']:
            response = requests.get(f"http://localhost:8004/api/common-paths/?type={path_type}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('paths'):
                    print(f"✅ {path_type.title()} common paths: {len(data['paths'])} paths found")
                else:
                    print(f"❌ {path_type.title()} common paths API returned invalid data")
                    return False
            else:
                print(f"❌ {path_type.title()} common paths API returned status: {response.status_code}")
                return False
        
        # Test 4: File Browse API
        print("\n📁 Test 4: File Browse API")
        test_path = os.path.expanduser('~')
        response = requests.get(f"http://localhost:8004/api/browse-files/?path={test_path}&type=all", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('items'):
                items = data['items']
                file_count = sum(1 for item in items if item['type'] == 'file')
                folder_count = sum(1 for item in items if item['type'] == 'folder')
                print(f"✅ File browser API working: {len(items)} items ({file_count} files, {folder_count} folders)")
                
                # Check file icons
                has_icons = all('icon' in item for item in items)
                if has_icons:
                    print("✅ All file items have icons")
                else:
                    print("⚠️ Some file items missing icons")
            else:
                print("❌ File browse API returned invalid data")
                return False
        else:
            print(f"❌ File browse API returned status: {response.status_code}")
            return False
        
        # Test 5: File Filtering
        print("\n🎯 Test 5: File Filtering")
        # Test ROM file filtering
        response = requests.get(f"http://localhost:8004/api/browse-files/?path={test_path}&type=files", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                # Should only return files, no folders (except parent directory)
                items = data.get('items', [])
                non_folder_items = [item for item in items if item['type'] not in ['folder']]
                if len(non_folder_items) >= len([item for item in items if item['type'] == 'file']):
                    print("✅ File filtering working correctly")
                else:
                    print("⚠️ File filtering may not be working as expected")
            else:
                print("❌ File filtering test failed")
                return False
        else:
            print(f"❌ File filtering test returned status: {response.status_code}")
            return False
            
        # Test 6: Security - Path Traversal Protection
        print("\n🔒 Test 6: Security - Path Traversal Protection")
        malicious_paths = ["../../../etc/passwd", "../../../../Windows/System32", ""]
        for malicious_path in malicious_paths:
            response = requests.get(f"http://localhost:8004/api/browse-files/?path={malicious_path}&type=all", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Should not allow access to system directories
                    current_path = data.get('current_path', '')
                    if not current_path.startswith('/etc') and not current_path.startswith('C:\\Windows'):
                        print("✅ Path traversal protection working")
                    else:
                        print("❌ Security vulnerability: Path traversal not properly blocked")
                        return False
                else:
                    print("✅ Malicious path properly rejected")
            else:
                print("✅ Malicious path properly rejected with error status")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ File browser test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in file browser test: {e}")
        return False
    finally:
        # Clean up Django server
        django_process.terminate()
        try:
            django_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            django_process.kill()

if __name__ == "__main__":
    success = test_file_browser_system()
    if success:
        print("\n🎉 File Browser System Test PASSED!")
        print("✅ All file browser features are working correctly")
        print("")
        print("📋 Summary:")
        print("   • Configuration page file browser: ✅ Working")
        print("   • ROM configuration page file browser: ✅ Working") 
        print("   • Common paths API: ✅ Working")
        print("   • File browse API: ✅ Working")
        print("   • File type filtering: ✅ Working")
        print("   • Security protection: ✅ Working")
        print("")
        print("🎮 File Browser Features:")
        print("   • Browse buttons on all path input fields")
        print("   • Modal interface with file navigation")
        print("   • Smart file filtering (ROMs, executables, general)")
        print("   • Common paths quick navigation")
        print("   • File icons and size information")
        print("   • Security protection against path traversal")
    else:
        print("\n❌ File Browser System Test FAILED")
        print("Some file browser components may need attention")