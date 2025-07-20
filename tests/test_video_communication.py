#!/usr/bin/env python3
"""
Test script to verify communication with video capture process.
"""

import socket
import json
import time


def test_video_process_communication():
    """Test communication with video capture process."""
    try:
        print("🔗 Connecting to video process at 127.0.0.1:8889")
        
        # Connect to video process
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect(('127.0.0.1', 8889))
        
        print("✅ Connected successfully")
        
        # Test status request first
        print("📤 Requesting status...")
        status_request = {'type': 'status'}
        request_data = json.dumps(status_request).encode('utf-8')
        sock.send(request_data)
        
        # Receive status response
        response_data = sock.recv(4096)
        status_response = json.loads(response_data.decode('utf-8'))
        
        print(f"📊 Status: {status_response}")
        sock.close()
        
        # Test GIF request
        print("\n📤 Requesting GIF...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15.0)  # Longer timeout for GIF
        sock.connect(('127.0.0.1', 8889))
        
        gif_request = {'type': 'get_gif'}
        request_data = json.dumps(gif_request).encode('utf-8')
        sock.send(request_data)
        
        print("⏳ Waiting for GIF response...")
        
        # Receive GIF response
        response_data = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_data += chunk
            try:
                gif_response = json.loads(response_data.decode('utf-8'))
                break
            except json.JSONDecodeError:
                continue
        
        print(f"📥 Received response: {len(response_data)} bytes")
        
        if gif_response.get('success'):
            frame_count = gif_response.get('frame_count', 0)
            duration = gif_response.get('duration', 0.0)
            gif_data_size = len(gif_response.get('gif_data', ''))
            print(f"✅ GIF received: {frame_count} frames, {duration:.2f}s, {gif_data_size} bytes (base64)")
        else:
            error = gif_response.get('error', 'Unknown error')
            print(f"❌ GIF request failed: {error}")
        
        sock.close()
        
    except Exception as e:
        print(f"❌ Error testing video process: {e}")


if __name__ == '__main__':
    print("🧪 Testing Video Process Communication")
    print("=" * 40)
    test_video_process_communication()