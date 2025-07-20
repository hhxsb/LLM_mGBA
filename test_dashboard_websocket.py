#!/usr/bin/env python3
"""
Test dashboard WebSocket integration for AI processes
"""
import asyncio
import websockets
import json
import time

async def test_dashboard_websocket():
    """Test connecting to dashboard WebSocket and sending messages"""
    dashboard_ws_url = "ws://localhost:3000/ws"
    
    try:
        print(f"🔗 Connecting to dashboard WebSocket: {dashboard_ws_url}")
        
        async with websockets.connect(dashboard_ws_url) as websocket:
            print("✅ Connected to dashboard WebSocket!")
            
            # Test sending a GIF message (matching video_capture format)
            gif_message = {
                "type": "chat_message",
                "timestamp": time.time(),
                "data": {
                    "message": {
                        "id": f"gif_{int(time.time() * 1000)}",
                        "type": "gif",
                        "timestamp": time.time(),
                        "sequence": int(time.time() % 10000),
                        "content": {
                            "gif": {
                                "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                                "available": True,
                                "metadata": {
                                    "frameCount": 30,
                                    "duration": 1.0,
                                    "size": 1024,
                                    "timestamp": time.time(),
                                    "fps": 30
                                }
                            }
                        }
                    }
                }
            }
            
            print("📤 Sending test GIF message...")
            await websocket.send(json.dumps(gif_message))
            print("✅ GIF message sent!")
            
            # Test sending an AI response message (matching game_control format)
            response_message = {
                "type": "chat_message",
                "timestamp": time.time(),
                "data": {
                    "message": {
                        "id": f"response_{int(time.time() * 1000)}",
                        "type": "response",
                        "timestamp": time.time(),
                        "sequence": int(time.time() % 10000),
                        "content": {
                            "response": {
                                "text": "I can see the Pokemon Red game screen. The player is in Pallet Town.",
                                "reasoning": "Based on the visual analysis, I can identify this as the starting area.",
                                "confidence": 0.95,
                                "processing_time": 2.1
                            }
                        }
                    }
                }
            }
            
            print("📤 Sending test AI response message...")
            await websocket.send(json.dumps(response_message))
            print("✅ AI response message sent!")
            
            # Test sending an action message (matching game_control format)
            action_message = {
                "type": "chat_message", 
                "timestamp": time.time(),
                "data": {
                    "message": {
                        "id": f"action_{int(time.time() * 1000)}",
                        "type": "action",
                        "timestamp": time.time(),
                        "sequence": int(time.time() % 10000),
                        "content": {
                            "action": {
                                "buttons": ["6", "0"],
                                "button_names": ["UP", "A"], 
                                "durations": [0.5, 0.3]
                            }
                        }
                    }
                }
            }
            
            print("📤 Sending test action message...")
            await websocket.send(json.dumps(action_message))
            print("✅ Action message sent!")
            
            print("🎯 All test messages sent successfully!")
            print("💡 Check the dashboard at http://localhost:5173 to see if messages appear")
            
            # Wait a moment to ensure messages are processed
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"❌ Dashboard WebSocket test failed: {e}")
        return False
    
    return True

async def main():
    print("🎮 AI Pokemon Trainer - Dashboard WebSocket Test")
    print("=" * 50)
    print("This script tests sending messages to the dashboard WebSocket.")
    print("")
    
    success = await test_dashboard_websocket()
    
    print("")
    if success:
        print("✅ Dashboard WebSocket test completed!")
        print("📋 Next steps:")
        print("   1. Check dashboard UI for new messages")
        print("   2. Restart AI processes to use fixed WebSocket connection")
        print("   3. Verify real AI messages appear during gameplay")
    else:
        print("❌ Dashboard WebSocket test failed!")
        print("💡 Make sure dashboard is running: python dashboard.py")

if __name__ == "__main__":
    asyncio.run(main())