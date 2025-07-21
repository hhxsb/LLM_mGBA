#!/usr/bin/env python3
"""
Mock video processor for testing dashboard without real video capture dependencies.
Completely separate from real video processors to avoid code pollution.
"""

import time
import json
import base64
import socket
import threading
import signal
from pathlib import Path


class MockVideoProcessor:
    """Mock video processor that serves test GIF data for dashboard testing."""
    
    def __init__(self, port: int = 8889, test_gif_path: str = None):
        self.port = port
        self.test_gif_path = test_gif_path or "/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/test/test.gif"
        self.running = False
        self.server_socket = None
        
        # Load test GIF data once
        self.gif_data_b64 = self._load_test_gif()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("📹 Mock Video Processor initialized")
        print(f"   Port: {port}")
        print(f"   Test GIF: {self.test_gif_path}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down mock video processor...")
        self.stop()
    
    def _load_test_gif(self) -> str:
        """Load and encode test GIF file."""
        try:
            gif_path = Path(self.test_gif_path)
            if not gif_path.exists():
                print(f"❌ Test GIF not found: {self.test_gif_path}")
                return ""
            
            with open(gif_path, 'rb') as f:
                gif_bytes = f.read()
            
            gif_b64 = base64.b64encode(gif_bytes).decode('utf-8')
            print(f"✅ Loaded test GIF: {len(gif_bytes)} bytes → {len(gif_b64)} base64 chars")
            return gif_b64
            
        except Exception as e:
            print(f"❌ Error loading test GIF: {e}")
            return ""
    
    def start(self):
        """Start the mock video processor server."""
        print("🚀 Starting Mock Video Processor Server...")
        self.running = True
        
        try:
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', self.port))
            self.server_socket.listen(5)
            
            print(f"✅ Mock video server listening on port {self.port}")
            print("🎯 Waiting for game control process connections...")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"🔗 New connection from {client_address}")
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"❌ Error accepting connection: {e}")
        
        except Exception as e:
            print(f"❌ Error starting server: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the mock video processor server."""
        print("🛑 Stopping Mock Video Processor...")
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
    
    def _handle_client(self, client_socket, client_address):
        """Handle requests from game control process."""
        try:
            while self.running:
                # Receive request
                data = client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    request = json.loads(data.decode('utf-8'))
                    request_type = request.get('type')
                    
                    print(f"📥 Received request: {request_type} from {client_address}")
                    
                    if request_type == 'get_gif':
                        response = self._create_gif_response()
                    elif request_type == 'status':
                        response = self._create_status_response()
                    else:
                        response = {
                            'success': False,
                            'error': f'Unknown request type: {request_type}'
                        }
                    
                    # Send response
                    response_data = json.dumps(response).encode('utf-8')
                    client_socket.send(response_data)
                    print(f"📤 Sent response: {len(response_data)} bytes")
                    
                except json.JSONDecodeError:
                    error_response = {
                        'success': False,
                        'error': 'Invalid JSON request'
                    }
                    client_socket.send(json.dumps(error_response).encode('utf-8'))
                
        except Exception as e:
            print(f"❌ Error handling client {client_address}: {e}")
        finally:
            try:
                client_socket.close()
                print(f"🔌 Disconnected from {client_address}")
            except:
                pass
    
    def _create_gif_response(self) -> dict:
        """Create mock GIF response."""
        if not self.gif_data_b64:
            return {
                'success': False,
                'error': 'Test GIF not available'
            }
        
        return {
            'success': True,
            'gif_data': self.gif_data_b64,
            'frame_count': 10,  # Mock frame count
            'duration': 2.0,    # Mock duration
            'start_timestamp': time.time() - 2.0,
            'end_timestamp': time.time(),
            'metadata': {
                'size': len(self.gif_data_b64) // 4 * 3,  # Approximate binary size
                'format': 'gif',
                'source': 'mock_video_processor'
            }
        }
    
    def _create_status_response(self) -> dict:
        """Create mock status response."""
        return {
            'success': True,
            'status': 'running',
            'buffer_frames': 50,  # Mock buffer size
            'buffer_duration': 10.0,  # Mock buffer duration
            'uptime': time.time(),
            'source': 'mock_video_processor'
        }


def main():
    """Main entry point for mock video processor."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mock Video Processor for Dashboard Testing')
    parser.add_argument('--port', type=int, default=8889,
                       help='Server port (default: 8889)')
    parser.add_argument('--test-gif', default='/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/test/test.gif',
                       help='Path to test GIF file')
    
    args = parser.parse_args()
    
    print("📹 Mock Video Processor for Dashboard Testing")
    print("=" * 50)
    
    try:
        processor = MockVideoProcessor(
            port=args.port,
            test_gif_path=args.test_gif
        )
        processor.start()
        
    except Exception as e:
        print(f"❌ Failed to start mock video processor: {e}")
        exit(1)


if __name__ == '__main__':
    main()