#!/usr/bin/env python3
"""
Test script for dashboard integration
Simulates the flow of GIF → AI Response → Actions
"""
import asyncio
import websockets
import json
import time
import base64
from PIL import Image, ImageDraw
import io

async def create_test_gif():
    """Create a simple test GIF"""
    frames = []
    for i in range(5):
        # Create a simple image with changing colors
        img = Image.new('RGB', (160, 144), color=(50 + i*40, 100, 150))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"Frame {i+1}", fill=(255, 255, 255))
        frames.append(img)
    
    # Save as GIF to bytes
    gif_buffer = io.BytesIO()
    frames[0].save(
        gif_buffer,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=500,  # 500ms per frame
        loop=0
    )
    
    return base64.b64encode(gif_buffer.getvalue()).decode('utf-8')

async def test_dashboard_flow():
    """Test the complete dashboard flow"""
    dashboard_url = "ws://localhost:3000/ws"
    
    try:
        print("🔗 Connecting to dashboard...")
        async with websockets.connect(dashboard_url) as websocket:
            print("✅ Connected to dashboard")
            
            # Test 1: Send a GIF message
            print("\n📸 Testing GIF message...")
            gif_data = await create_test_gif()
            gif_message = {
                'type': 'gif_message',
                'timestamp': time.time(),
                'data': {
                    'gif_data': gif_data,
                    'metadata': {
                        'frameCount': 5,
                        'duration': 2.5,
                        'size': len(gif_data),
                        'timestamp': time.time(),
                        'start_timestamp': time.time() - 2.5,
                        'end_timestamp': time.time(),
                        'fps': 2
                    }
                }
            }
            
            await websocket.send(json.dumps(gif_message))
            print("✅ Sent test GIF message")
            
            # Wait a bit
            await asyncio.sleep(1)
            
            # Test 2: Send an AI response
            print("\n🤖 Testing AI response message...")
            response_message = {
                'type': 'response_message',
                'timestamp': time.time(),
                'data': {
                    'response_text': "I can see the player is in Pallet Town. I should head north towards Route 1 to begin my Pokemon journey!",
                    'reasoning': "The screenshot shows the starting area of Pokemon Red. The optimal strategy is to move north to begin catching Pokemon and progressing through the game.",
                    'processing_time': 1.23
                }
            }
            
            await websocket.send(json.dumps(response_message))
            print("✅ Sent test AI response message")
            
            # Wait a bit
            await asyncio.sleep(1)
            
            # Test 3: Send action buttons
            print("\n🎯 Testing action message...")
            action_message = {
                'type': 'action_message',
                'timestamp': time.time(),
                'data': {
                    'buttons': ['6', '6', '0'],  # UP, UP, A
                    'durations': [2.0, 2.0, 1.0],
                    'button_names': ['UP', 'UP', 'A']
                }
            }
            
            await websocket.send(json.dumps(action_message))
            print("✅ Sent test action message")
            
            # Listen for any responses
            print("\n👂 Listening for dashboard responses...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received: {response[:100]}...")
            except asyncio.TimeoutError:
                print("⏰ No response received (timeout)")
            
            print("\n🎉 Dashboard integration test completed!")
            
    except ConnectionRefusedError:
        print("❌ Could not connect to dashboard. Make sure it's running with:")
        print("   python dashboard.py --config config_emulator.json")
    except Exception as e:
        print(f"❌ Error testing dashboard: {e}")

if __name__ == "__main__":
    print("🧪 AI Pokemon Trainer Dashboard Integration Test")
    print("=" * 50)
    asyncio.run(test_dashboard_flow())