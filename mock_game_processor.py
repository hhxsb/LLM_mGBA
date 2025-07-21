#!/usr/bin/env python3
"""
Mock game processor for testing dashboard without real emulator/LLM dependencies.
Completely separate from real game processors to avoid code pollution.
"""

import time
import json
import base64
import asyncio
import websockets
import threading
import signal
import uuid
from pathlib import Path


class MockGameProcessor:
    """Mock game processor that simulates AI gameplay for dashboard testing."""
    
    def __init__(self, dashboard_port: int = 3000, test_gif_path: str = None):
        self.dashboard_port = dashboard_port
        self.test_gif_path = test_gif_path or "/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/test/test.gif"
        self.running = False
        self.dashboard_ws = None
        self.message_counter = 0
        
        # Load test GIF data once
        self.gif_data_b64 = self._load_test_gif()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("🎮 Mock Game Processor initialized")
        print(f"   Dashboard port: {dashboard_port}")
        print(f"   Test GIF: {self.test_gif_path}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down mock processor...")
        self.stop()
    
    def _load_test_gif(self) -> str:
        """Load and encode test GIF file."""
        try:
            gif_path = Path(self.test_gif_path)
            if not gif_path.exists():
                print(f"❌ Test GIF not found: {self.test_gif_path}")
                return self._create_mock_gif_data()
            
            with open(gif_path, 'rb') as f:
                gif_bytes = f.read()
            
            # Check if GIF is too large for WebSocket (>1MB base64 ≈ 750KB binary)
            if len(gif_bytes) > 750000:
                print(f"⚠️ Test GIF too large ({len(gif_bytes)} bytes), using mock data instead")
                return self._create_mock_gif_data()
            
            gif_b64 = base64.b64encode(gif_bytes).decode('utf-8')
            print(f"✅ Loaded test GIF: {len(gif_bytes)} bytes → {len(gif_b64)} base64 chars")
            return gif_b64
            
        except Exception as e:
            print(f"❌ Error loading test GIF: {e}")
            return self._create_mock_gif_data()
    
    def _create_mock_gif_data(self) -> str:
        """Create a small mock GIF data for testing."""
        # This is a minimal GIF header + single pixel animated GIF (base64 encoded)
        # It's tiny but still a valid GIF that browsers can display
        mock_gif_bytes = bytes([
            0x47, 0x49, 0x46, 0x38, 0x39, 0x61,  # GIF89a header
            0x01, 0x00, 0x01, 0x00, 0x80, 0x00, 0x00,  # 1x1 pixel, global color table
            0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00,  # White and black colors
            0x21, 0xFF, 0x0B, 0x4E, 0x45, 0x54, 0x53, 0x43, 0x41, 0x50, 0x45, 0x32, 0x2E, 0x30,  # Netscape extension
            0x03, 0x01, 0x00, 0x00, 0x00, 0x21, 0xF9, 0x04, 0x00, 0x64, 0x00, 0x00, 0x00,  # Graphics control
            0x2C, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00,  # Image descriptor
            0x02, 0x02, 0x04, 0x01, 0x00, 0x3B  # Image data + trailer
        ])
        mock_gif_b64 = base64.b64encode(mock_gif_bytes).decode('utf-8')
        print(f"✅ Created mock GIF: {len(mock_gif_bytes)} bytes → {len(mock_gif_b64)} base64 chars")
        return mock_gif_b64
    
    def start(self):
        """Start the mock game processor."""
        print("🚀 Starting Mock Game Processor...")
        self.running = True
        
        # Create event loop and run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._run_simulation())
        except KeyboardInterrupt:
            print("🛑 Keyboard interrupt received")
        except Exception as e:
            print(f"❌ Mock processor error: {e}")
        finally:
            self.stop()
            loop.close()
    
    def stop(self):
        """Stop the mock game processor."""
        print("🛑 Stopping Mock Game Processor...")
        self.running = False
        if self.dashboard_ws:
            asyncio.create_task(self.dashboard_ws.close())
    
    async def _run_simulation(self):
        """Main simulation loop."""
        # Connect to dashboard
        await self._connect_to_dashboard()
        
        if not self.dashboard_ws:
            print("❌ Could not connect to dashboard, exiting")
            return
        
        print("✅ Mock simulation started - sending test messages every 5 seconds")
        print("   Flow: GIF → AI Response → Action → repeat")
        
        cycle_count = 0
        while self.running:
            try:
                cycle_count += 1
                print(f"🔄 Starting simulation cycle {cycle_count}")
                
                # Send GIF message (represents game footage)
                print("📹 Sending game footage...")
                await self._send_mock_gif()
                await asyncio.sleep(3)  # Realistic processing time
                
                # Send AI response (AI thinking about what it sees)
                print("🤖 Sending AI response...")
                await self._send_mock_response()
                await asyncio.sleep(2)  # Time for AI to decide action
                
                # Send action (AI's decision on what buttons to press)
                print("🎯 Sending AI action...")
                await self._send_mock_action()
                await asyncio.sleep(8)  # Wait before next game cycle (realistic game pace)
                
                print(f"✅ Completed simulation cycle {cycle_count}")
                print()
                
            except Exception as e:
                print(f"❌ Error in simulation loop: {e}")
                await asyncio.sleep(2)
    
    async def _connect_to_dashboard(self):
        """Connect to dashboard WebSocket."""
        dashboard_ws_url = f"ws://localhost:{self.dashboard_port}/ws"
        max_retries = 5
        retry_delay = 3.0
        
        for attempt in range(max_retries):
            try:
                print(f"🔗 Connecting to dashboard: {dashboard_ws_url} (attempt {attempt + 1})")
                self.dashboard_ws = await websockets.connect(dashboard_ws_url)
                print(f"✅ Connected to dashboard WebSocket")
                break
                
            except Exception as e:
                print(f"⚠️ Failed to connect (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    print("❌ Could not connect to dashboard after multiple attempts")
                    self.dashboard_ws = None
    
    async def _send_mock_gif(self):
        """Send mock GIF message to dashboard."""
        if not self.dashboard_ws or not self.gif_data_b64:
            return
        
        self.message_counter += 1
        
        try:
            message = {
                "type": "chat_message",
                "timestamp": time.time(),
                "data": {
                    "message": {
                        "id": f"gif_{uuid.uuid4().hex[:12]}_{self.message_counter}",
                        "type": "gif",
                        "timestamp": time.time(),
                        "sequence": self.message_counter,
                        "content": {
                            "gif": {
                                "data": self.gif_data_b64,
                                "metadata": {
                                    "frameCount": 10,  # Mock frame count
                                    "duration": 2.0,   # Mock duration
                                    "size": len(self.gif_data_b64) // 4 * 3,  # Approximate binary size
                                    "timestamp": time.time()
                                },
                                "available": True
                            }
                        }
                    }
                }
            }
            
            await self.dashboard_ws.send(json.dumps(message))
            print(f"📤 Sent mock GIF message #{self.message_counter}")
            
        except Exception as e:
            print(f"❌ Failed to send GIF message: {e}")
    
    async def _send_mock_response(self):
        """Send mock AI response message to dashboard."""
        if not self.dashboard_ws:
            return
        
        self.message_counter += 1
        
        try:
            test_responses = [
                "I can see the game screen clearly. Let me analyze what's happening.",
                "The character appears to be in a dialogue or menu. I should make a decision.",
                "I can see some text on screen. I need to read it and respond appropriately.",
                "There are options available. Let me choose the best one to progress.",
                "The game state has changed. I'll assess the new situation and act accordingly."
            ]
            
            response_text = test_responses[(self.message_counter - 1) % len(test_responses)]
            
            message = {
                "type": "chat_message",
                "timestamp": time.time(),
                "data": {
                    "message": {
                        "id": f"response_{uuid.uuid4().hex[:12]}_{self.message_counter}",
                        "type": "response",
                        "timestamp": time.time(),
                        "sequence": self.message_counter,
                        "content": {
                            "response": {
                                "text": response_text,
                                "reasoning": f"mock reasoning {self.message_counter}",
                                "confidence": 0.95,
                                "processing_time": 2.1
                            }
                        }
                    }
                }
            }
            
            await self.dashboard_ws.send(json.dumps(message))
            print(f"📤 Sent mock AI response #{self.message_counter}: '{response_text}'")
            
        except Exception as e:
            print(f"❌ Failed to send response message: {e}")
    
    async def _send_mock_action(self):
        """Send mock action message to dashboard."""
        if not self.dashboard_ws:
            return
        
        self.message_counter += 1
        
        try:
            mock_actions = [
                (["0"], [1.0], ["A"]),
                (["4", "0"], [0.5, 1.0], ["RIGHT", "A"]),
                (["6", "6", "0"], [0.5, 0.5, 1.0], ["UP", "UP", "A"]),
                (["5"], [0.5], ["LEFT"]),
                (["7", "0"], [0.5, 1.0], ["DOWN", "A"])
            ]
            
            buttons, durations, button_names = mock_actions[(self.message_counter - 1) % len(mock_actions)]
            
            message = {
                "type": "chat_message",
                "timestamp": time.time(),
                "data": {
                    "message": {
                        "id": f"action_{uuid.uuid4().hex[:12]}_{self.message_counter}",
                        "type": "action",
                        "timestamp": time.time(),
                        "sequence": self.message_counter,
                        "content": {
                            "action": {
                                "buttons": buttons,
                                "button_names": button_names,
                                "durations": durations
                            }
                        }
                    }
                }
            }
            
            await self.dashboard_ws.send(json.dumps(message))
            print(f"📤 Sent mock action #{self.message_counter}: {', '.join(button_names)}")
            
        except Exception as e:
            print(f"❌ Failed to send action message: {e}")


def main():
    """Main entry point for mock game processor."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mock Game Processor for Dashboard Testing')
    parser.add_argument('--dashboard-port', type=int, default=3000, 
                       help='Dashboard WebSocket port (default: 3000)')
    parser.add_argument('--test-gif', default='/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/test/test.gif',
                       help='Path to test GIF file')
    
    args = parser.parse_args()
    
    print("🎮 Mock Game Processor for Dashboard Testing")
    print("=" * 50)
    
    try:
        processor = MockGameProcessor(
            dashboard_port=args.dashboard_port,
            test_gif_path=args.test_gif
        )
        processor.start()
        
    except Exception as e:
        print(f"❌ Failed to start mock processor: {e}")
        exit(1)


if __name__ == '__main__':
    main()