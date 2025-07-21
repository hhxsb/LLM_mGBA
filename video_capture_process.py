#!/usr/bin/env python3
"""
Standalone video capture process with rolling window buffer.
Continuously captures screenshots and provides GIF generation on request.
"""

import time
import threading
import queue
import socket
import json
import os
import sys
from collections import deque
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import signal
import asyncio
import websockets

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from core.base_capture_system import BaseCaptureSystem, VideoSegment
from core.logging_config import configure_logging, get_logger, get_timeline_logger
import PIL.Image


@dataclass
class TimestampedFrame:
    """Frame with timestamp for rolling window."""
    image: PIL.Image.Image
    timestamp: float
    frame_number: int


class VideoCaptureProcess:
    """Standalone video capture process with rolling window buffer."""
    
    def __init__(self, config_path: str = "config_emulator.json"):
        self.config = self._load_config(config_path)
        self.capture_config = self.config.get('capture_system', {})
        self.dashboard_config = self.config.get('dashboard', {})
        
        # Capture settings
        self.capture_fps = self.capture_config.get('capture_fps', 30)
        self.rolling_window_seconds = 20  # 20 second rolling window
        self.max_frames = int(self.capture_fps * self.rolling_window_seconds)
        
        # Rolling frame buffer
        self.frame_buffer = deque(maxlen=self.max_frames)
        self.frame_counter = 0
        self.start_time = time.time()
        self.last_gif_timestamp = None
        
        # Capture system
        self.capture_system = None
        self.capture_region = None
        
        # Threading
        self.running = False
        self.capture_thread = None
        self.server_thread = None
        
        # IPC Server
        self.server_socket = None
        self.ipc_port = self.config.get('video_capture_port', 8889)
        
        # Dashboard WebSocket client
        self.dashboard_ws = None
        self.dashboard_enabled = self.dashboard_config.get('enabled', False)
        self.dashboard_port = self.dashboard_config.get('port', 3000)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print(f"🎬 Video Capture Process initialized")
        print(f"   Capture FPS: {self.capture_fps}")
        print(f"   Rolling window: {self.rolling_window_seconds}s ({self.max_frames} frames)")
        print(f"   IPC Port: {self.ipc_port}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down video capture process...")
        self.stop()
    
    def _initialize_capture_system(self):
        """Initialize the capture system."""
        try:
            # Import and initialize capture system
            from core.screen_capture import ScreenCaptureSystem
            
            self.capture_system = ScreenCaptureSystem(self.config)
            
            # Initialize the capture system
            if not self.capture_system.initialize():
                print("❌ Failed to initialize capture backends")
                return False
            
            # The capture region is set internally by the capture system
            if hasattr(self.capture_system, 'capture_region') and self.capture_system.capture_region:
                print(f"🎯 Found mGBA window: {self.capture_system.capture_region}")
            else:
                print("⚠️ mGBA window not found, will capture full screen")
                
        except Exception as e:
            print(f"❌ Failed to initialize capture system: {e}")
            return False
        
        return True
    
    def start(self):
        """Start the video capture process."""
        print("🚀 Starting video capture process...")
        
        if not self._initialize_capture_system():
            print("❌ Failed to initialize capture system")
            return False
        
        self.running = True
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        # Start IPC server thread
        self.server_thread = threading.Thread(target=self._ipc_server_loop, daemon=True)
        self.server_thread.start()
        
        # Connect to dashboard if enabled
        if self.dashboard_enabled:
            # Create a new thread for dashboard connection since this is not in an async context
            dashboard_thread = threading.Thread(target=self._start_dashboard_connection, daemon=True)
            dashboard_thread.start()
        
        print(f"✅ Video capture process started successfully")
        print(f"   Capturing at {self.capture_fps} FPS")
        print(f"   IPC server listening on port {self.ipc_port}")
        if self.dashboard_enabled:
            print(f"   Dashboard integration enabled (port {self.dashboard_port})")
        
        return True
    
    def stop(self):
        """Stop the video capture process."""
        print("🛑 Stopping video capture process...")
        
        self.running = False
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # Wait for threads to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2.0)
        
        print("✅ Video capture process stopped")
    
    def _capture_loop(self):
        """Main capture loop that continuously takes screenshots."""
        frame_interval = 1.0 / self.capture_fps  # Time between frames
        next_capture_time = time.time()
        
        print(f"🎬 Started continuous capture loop at {self.capture_fps} FPS")
        
        while self.running:
            current_time = time.time()
            
            # Check if it's time for next frame
            if current_time >= next_capture_time:
                try:
                    # Capture screenshot
                    if self.capture_system:
                        capture_frame = self.capture_system.capture_frame()
                        if capture_frame and capture_frame.image:
                            # Create timestamped frame
                            timestamped_frame = TimestampedFrame(
                                image=capture_frame.image,
                                timestamp=current_time,
                                frame_number=self.frame_counter
                            )
                            
                            # Add to rolling buffer (automatically removes old frames due to maxlen)
                            self.frame_buffer.append(timestamped_frame)
                            self.frame_counter += 1
                            
                            # Log periodically
                            if self.frame_counter % (self.capture_fps * 5) == 0:  # Every 5 seconds
                                buffer_duration = self._get_buffer_duration()
                                print(f"📊 Captured {self.frame_counter} frames, buffer: {len(self.frame_buffer)} frames ({buffer_duration:.1f}s)")
                
                except Exception as e:
                    print(f"❌ Capture error: {e}")
                
                # Schedule next capture
                next_capture_time += frame_interval
            
            # Small sleep to prevent busy waiting
            time.sleep(0.001)
    
    def _get_buffer_duration(self) -> float:
        """Get current buffer duration in seconds."""
        if len(self.frame_buffer) < 2:
            return 0.0
        return self.frame_buffer[-1].timestamp - self.frame_buffer[0].timestamp
    
    def _ipc_server_loop(self):
        """IPC server loop to handle GIF requests."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', self.ipc_port))
            self.server_socket.listen(5)
            
            print(f"🔗 IPC server listening on port {self.ipc_port}")
            
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)  # Non-blocking accept
                    client_socket, address = self.server_socket.accept()
                    
                    # Handle request in separate thread
                    request_thread = threading.Thread(
                        target=self._handle_gif_request, 
                        args=(client_socket, address),
                        daemon=True
                    )
                    request_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"❌ IPC server error: {e}")
                    break
        
        except Exception as e:
            print(f"❌ Failed to start IPC server: {e}")
    
    def _handle_gif_request(self, client_socket, address):
        """Handle a GIF generation request."""
        try:
            # Receive request
            data = client_socket.recv(1024)
            if not data:
                return
            
            request = json.loads(data.decode('utf-8'))
            request_type = request.get('type', '')
            
            if request_type == 'get_gif':
                response = self._generate_gif_response(request)
            elif request_type == 'status':
                response = self._get_status_response()
            else:
                response = {'error': f'Unknown request type: {request_type}'}
            
            # Send response
            response_data = json.dumps(response).encode('utf-8')
            client_socket.send(response_data)
            
        except Exception as e:
            error_response = {'error': str(e)}
            try:
                response_data = json.dumps(error_response).encode('utf-8')
                client_socket.send(response_data)
            except:
                pass
            print(f"❌ Error handling GIF request: {e}")
        
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def _generate_gif_response(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate GIF from rolling buffer and return response."""
        try:
            current_time = time.time()
            
            # Check if a custom duration is requested
            max_duration = request.get('max_duration', None)
            
            # Determine time range for GIF with performance optimization
            if self.last_gif_timestamp is None:
                # First GIF: use requested duration or last 5 seconds for faster startup
                buffer_duration = self._get_buffer_duration()
                default_duration = 5.0 if max_duration is None else max_duration
                start_time = current_time - min(default_duration, buffer_duration)
                print(f"📸 First GIF request: using {min(default_duration, buffer_duration):.1f}s of history")
            else:
                # Subsequent GIFs: from last GIF timestamp to now
                start_time = self.last_gif_timestamp
                duration_since_last = current_time - self.last_gif_timestamp
                
                # OPTIMIZATION: Limit subsequent GIF duration to prevent huge files
                gif_optimization = self.capture_config.get('gif_optimization', {})
                max_subsequent_duration = gif_optimization.get('max_gif_duration', 10.0)  # Default: 10 seconds max
                if duration_since_last > max_subsequent_duration:
                    start_time = current_time - max_subsequent_duration
                    print(f"📸 Subsequent GIF request: {duration_since_last:.2f}s available, limited to {max_subsequent_duration:.1f}s")
                else:
                    print(f"📸 Subsequent GIF request: {duration_since_last:.2f}s since last GIF")
            
            end_time = current_time
            
            # Extract frames in time range
            gif_frames = []
            for frame in self.frame_buffer:
                if start_time <= frame.timestamp <= end_time:
                    gif_frames.append(frame)
            
            if not gif_frames:
                return {'error': 'No frames available in requested time range'}
            
            # Create GIF
            gif_data = self._create_gif_from_frames(gif_frames)
            if not gif_data:
                return {'error': 'Failed to create GIF'}
            
            # Update last GIF timestamp to reset rolling window
            self.last_gif_timestamp = current_time
            
            # Prepare response with base64 encoded GIF data
            import base64
            gif_data_b64 = base64.b64encode(gif_data).decode('utf-8')
            
            duration = end_time - start_time
            
            # Create metadata for dashboard
            metadata = {
                'frameCount': len(gif_frames),
                'duration': duration,
                'size': len(gif_data),
                'timestamp': current_time,
                'start_timestamp': start_time,
                'end_timestamp': end_time,
                'fps': self.capture_fps
            }
            
            response = {
                'success': True,
                'gif_data': gif_data_b64,
                'frame_count': len(gif_frames),
                'duration': duration,
                'start_timestamp': start_time,
                'end_timestamp': end_time,
                'fps': self.capture_fps
            }
            
            print(f"📸 Generated GIF: {len(gif_frames)} frames, {duration:.2f}s")
            
            # TIMELINE EVENT 2: T+0.1s - Video Capture generates GIF from rolling buffer → sends to dashboard
            timeline_logger = get_timeline_logger("video_capture")
            timeline_logger.log_event(2, "0.1s", "Video Capture generates GIF from rolling buffer → sends to dashboard")
            
            # Send to dashboard if connected
            if self.dashboard_enabled and self.dashboard_ws:
                self._send_gif_to_dashboard_threaded(gif_data_b64, metadata)
            
            return response
            
        except Exception as e:
            return {'error': f'Failed to generate GIF: {e}'}
    
    def _create_gif_from_frames(self, frames: List[TimestampedFrame]) -> Optional[bytes]:
        """Create optimized GIF bytes from list of frames."""
        try:
            if not frames:
                return None
            
            # OPTIMIZATION 1: Limit frame count for performance
            gif_optimization = self.capture_config.get('gif_optimization', {})
            max_frames = gif_optimization.get('max_gif_frames', 150)  # Default: 5s at 30fps
            if len(frames) > max_frames:
                # Sample frames evenly across the duration
                step = len(frames) // max_frames
                frames = [frames[i] for i in range(0, len(frames), step)][:max_frames]
                print(f"🎞️ Frame optimization: reduced to {len(frames)} frames")
            
            # Convert frames to PIL images
            images = [frame.image for frame in frames]
            
            # OPTIMIZATION 2: Resize images for smaller file size
            gif_width = gif_optimization.get('gif_width', 240)  # Default: GBA is 240px in width
            if images and images[0].width > gif_width:
                aspect_ratio = images[0].height / images[0].width
                gif_height = int(gif_width * aspect_ratio)
                images = [img.resize((gif_width, gif_height), PIL.Image.Resampling.LANCZOS) for img in images]
                print(f"🖼️ Image resize: {gif_width}x{gif_height}")
            
            # OPTIMIZATION 3: Adaptive frame duration based on actual frame count
            target_duration = gif_optimization.get('target_gif_duration', 5.0)  # Target 5 seconds
            frame_duration_ms = max(33, int(1000 * target_duration / len(frames)))  # Min 33ms (30fps)
            
            # OPTIMIZATION 4: Optimize GIF settings for smaller file size
            import io
            gif_buffer = io.BytesIO()
            
            # Use optimized GIF settings
            images[0].save(
                gif_buffer,
                format='GIF',
                save_all=True,
                append_images=images[1:],
                duration=frame_duration_ms,
                loop=0,
                optimize=True,  # Enable optimization
                disposal=2  # Dispose previous frame completely
            )
            
            gif_size = len(gif_buffer.getvalue())
            print(f"📊 GIF created: {len(frames)} frames, {gif_size/1024:.1f}KB, {frame_duration_ms}ms/frame")
            
            return gif_buffer.getvalue()
            
        except Exception as e:
            print(f"❌ Error creating GIF: {e}")
            return None
    
    def _get_status_response(self) -> Dict[str, Any]:
        """Get current status of video capture process."""
        buffer_duration = self._get_buffer_duration()
        return {
            'running': self.running,
            'frame_count': self.frame_counter,
            'buffer_frames': len(self.frame_buffer),
            'buffer_duration': buffer_duration,
            'capture_fps': self.capture_fps,
            'last_gif_timestamp': self.last_gif_timestamp,
            'uptime': time.time() - self.start_time,
            'dashboard_connected': self.dashboard_ws is not None
        }
    
    async def _connect_to_dashboard(self):
        """Connect to dashboard WebSocket for real-time GIF streaming"""
        dashboard_ws_url = f"ws://localhost:{self.dashboard_port}/ws"
        max_retries = 5
        retry_delay = 3.0
        
        for attempt in range(max_retries):
            try:
                print(f"🔗 Connecting to dashboard WebSocket: {dashboard_ws_url} (attempt {attempt + 1})")
                self.dashboard_ws = await websockets.connect(dashboard_ws_url)
                print("✅ Connected to dashboard WebSocket")
                
                # Start background task to maintain connection
                asyncio.create_task(self._dashboard_ws_handler())
                break
                
            except Exception as e:
                print(f"⚠️ Failed to connect to dashboard (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    print("❌ Could not connect to dashboard, continuing without dashboard integration")
                    self.dashboard_enabled = False
    
    async def _dashboard_ws_handler(self):
        """Handle dashboard WebSocket connection"""
        try:
            # Keep connection alive and handle any incoming messages
            async for message in self.dashboard_ws:
                # Dashboard may send ping/status requests
                data = json.loads(message)
                if data.get('type') == 'ping':
                    await self.dashboard_ws.send(json.dumps({'type': 'pong', 'timestamp': time.time()}))
                    
        except websockets.exceptions.ConnectionClosed:
            print("📡 Dashboard WebSocket connection closed")
            self.dashboard_ws = None
        except Exception as e:
            print(f"❌ Dashboard WebSocket error: {e}")
            self.dashboard_ws = None
    
    async def _send_gif_to_dashboard(self, gif_data: str, metadata: Dict):
        """Send GIF data to dashboard via WebSocket"""
        if not self.dashboard_ws or not self.dashboard_enabled:
            return
        
        try:
            message = {
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
                                "data": gif_data,
                                "available": True,
                                "metadata": metadata
                            }
                        }
                    }
                }
            }
            
            await self.dashboard_ws.send(json.dumps(message))
            print(f"📤 Sent GIF to dashboard: {len(gif_data)} bytes, {metadata.get('frameCount', 0)} frames")
            
        except Exception as e:
            print(f"❌ Failed to send GIF to dashboard: {e}")
            # Try to reconnect
            self.dashboard_ws = None
            if self.dashboard_enabled:
                # Restart dashboard connection in a separate thread
                dashboard_thread = threading.Thread(target=self._start_dashboard_connection, daemon=True)
                dashboard_thread.start()
    
    def _send_gif_to_dashboard_threaded(self, gif_data: str, metadata: Dict):
        """Send GIF to dashboard in a separate thread to avoid AsyncIO issues"""
        def send_gif():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._send_gif_to_dashboard(gif_data, metadata))
            except Exception as e:
                print(f"❌ Failed to send GIF to dashboard: {e}")
            finally:
                try:
                    loop.close()
                except:
                    pass
        
        gif_thread = threading.Thread(target=send_gif, daemon=True)
        gif_thread.start()
    
    def _start_dashboard_connection(self):
        """Start dashboard connection in a new event loop"""
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._connect_to_dashboard())
        except Exception as e:
            print(f"⚠️ Dashboard connection failed: {e}")
        finally:
            try:
                loop.close()
            except:
                pass
    
    def run_forever(self):
        """Run the video capture process until stopped."""
        if not self.start():
            return False
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        finally:
            self.stop()
        
        return True


def main():
    """Main entry point for video capture process."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Video Capture Process for Pokemon AI')
    parser.add_argument('--config', default='config_emulator.json', 
                       help='Path to configuration file')
    parser.add_argument('--port', type=int, help='IPC port override')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging for video capture process
    configure_logging(debug=args.debug, process_name="video_capture")
    
    # Create and run video capture process
    capture_process = VideoCaptureProcess(args.config)
    
    if args.port:
        capture_process.ipc_port = args.port
    
    print("🎬 Starting Pokemon AI Video Capture Process")
    success = capture_process.run_forever()
    
    if success:
        print("✅ Video capture process completed successfully")
    else:
        print("❌ Video capture process failed")
        sys.exit(1)


if __name__ == '__main__':
    main()