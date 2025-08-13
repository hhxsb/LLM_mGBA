#!/usr/bin/env python3
"""
Test script to simulate mGBA Lua script communication with AIGameService
"""

import socket
import time
import sys

def test_ai_service():
    """Test the AI service by simulating mGBA connection"""
    
    print("🧪 Testing AI Game Service connection...")
    
    try:
        # Connect to the AI service
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        print("🔌 Connecting to localhost:8888...")
        sock.connect(('127.0.0.1', 8888))
        print("✅ Connected successfully!")
        
        # Send ready message (like mGBA Lua script would)
        print("📤 Sending 'ready' message...")
        sock.send(b"ready\n")
        time.sleep(1)
        
        # Create a fake screenshot file for testing
        import os
        screenshot_dir = "/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Create a simple test image (placeholder)
        screenshot_path = f"{screenshot_dir}/test_screenshot.png"
        if not os.path.exists(screenshot_path):
            # Create a minimal PNG file for testing
            with open(screenshot_path, "wb") as f:
                # PNG header + minimal image data (just for testing)
                f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa')
        
        # Send screenshot data (simulate mGBA sending screenshot info)
        print("📤 Sending screenshot data...")
        screenshot_message = f"screenshot_data|{screenshot_path}|10|15|UP|5\n"
        sock.send(screenshot_message.encode('utf-8'))
        
        print("✅ Test messages sent successfully!")
        print("💭 The AI service should now process this data...")
        print("🔍 Check the Django logs for AI service activity")
        
        # Keep connection alive for a bit to see any responses
        print("⏱️ Waiting 10 seconds for AI processing...")
        time.sleep(10)
        
        sock.close()
        print("🏁 Test completed!")
        
    except socket.timeout:
        print("⏰ Connection timeout - AI service might not be running")
    except ConnectionRefusedError:
        print("🚫 Connection refused - AI service is not listening on port 8888")
        print("💡 Try starting the AI service first via: curl -X POST http://localhost:8000/api/restart-service/")
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        if 'sock' in locals():
            sock.close()

def check_service_status():
    """Check if the AI service is running"""
    try:
        import requests
        response = requests.get("http://localhost:8000/api/chat-messages/")
        data = response.json()
        
        print("📊 Service Status:")
        print(f"   Connected to mGBA: {data.get('connected', False)}")
        print(f"   Decision count: {data.get('decision_count', 0)}")
        print(f"   Service success: {data.get('success', False)}")
        
    except Exception as e:
        print(f"❌ Could not check service status: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_service_status()
    else:
        test_ai_service()