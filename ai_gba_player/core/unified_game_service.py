#!/usr/bin/env python3
"""
Unified Game Service for AI GBA Player.
Combines video capture and game control into a single threaded Django service.
"""

import threading
import time
import queue
import json
import os
import sys
import signal
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from collections import deque
import base64
from io import BytesIO

# Add project root to path to access core modules and games
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

try:
    from core.base_capture_system import BaseCaptureSystem, VideoSegment, CaptureFrame
    from core.logging_config import configure_logging, get_logger
    from core.message_bus import message_bus, publish_gif_message, publish_response_message, publish_action_message, publish_screenshots_message
    from core.message_types import UnifiedMessage
    from games.pokemon_red.controller import PokemonRedController
except ImportError as e:
    print(f"⚠️ Warning: Could not import project core modules: {e}")
    print("Unified service may not function properly without core modules")
    # Create stub functions to prevent crashes
    def configure_logging(*args, **kwargs): pass
    def get_logger(name): 
        import logging
        return logging.getLogger(name)
    class BaseCaptureSystem: pass
    class VideoSegment: pass  
    class CaptureFrame: pass
    class UnifiedMessage: pass
    class PokemonRedController: pass
    def message_bus(*args, **kwargs): pass
    def publish_gif_message(*args, **kwargs): pass
    def publish_response_message(*args, **kwargs): pass
    def publish_action_message(*args, **kwargs): pass
    def publish_screenshots_message(*args, **kwargs): pass
import PIL.Image


@dataclass
class TimestampedFrame:
    """Frame with timestamp for rolling window."""
    image: PIL.Image.Image
    timestamp: float
    frame_number: int


@dataclass
class ThreadMessage:
    """Message for inter-thread communication."""
    message_type: str
    data: Dict[str, Any]
    response_queue: Optional[queue.Queue] = None


class VideoCaptureThread(threading.Thread):
    """Video capture thread with rolling window buffer."""
    
    def __init__(self, config: Dict[str, Any], message_queue: queue.Queue):
        super().__init__(daemon=True, name="VideoCaptureThread")
        self.config = config
        self.message_queue = message_queue
        self.capture_config = config.get('capture_system', {})
        
        # Capture settings
        self.capture_fps = self.capture_config.get('capture_fps', 30)
        self.rolling_window_seconds = 20
        self.max_frames = int(self.capture_fps * self.rolling_window_seconds)
        
        # Rolling frame buffer
        self.frame_buffer = deque(maxlen=self.max_frames)
        self.frame_counter = 0
        self.last_gif_timestamp = None
        
        # Thread control
        self.running = False
        self.capture_system = None
        
        self.logger = get_logger("video_capture_thread")
        self.logger.info(f"🎬 Video Capture Thread initialized (FPS: {self.capture_fps}, Buffer: {self.rolling_window_seconds}s)")
    
    def run(self):
        """Main thread execution."""
        self.logger.info("🚀 Starting video capture thread...")
        self.running = True
        
        if not self._initialize_capture_system():
            self.logger.error("❌ Failed to initialize capture system")
            return
        
        # Start capture loop
        self._capture_loop()
        
        self.logger.info("✅ Video capture thread stopped")
    
    def stop(self):
        """Stop the video capture thread."""
        self.logger.info("🛑 Stopping video capture thread...")
        self.running = False
    
    def _initialize_capture_system(self):
        """Initialize the capture system."""
        try:
            from core.screen_capture import ScreenCaptureSystem
            
            self.capture_system = ScreenCaptureSystem(self.config)
            
            if not self.capture_system.initialize():
                self.logger.error("❌ Failed to initialize capture backends")
                return False
            
            if hasattr(self.capture_system, 'capture_region') and self.capture_system.capture_region:
                self.logger.info(f"🎯 Found mGBA window: {self.capture_system.capture_region}")
            else:
                self.logger.warning("⚠️ mGBA window not found, will capture full screen")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize capture system: {e}")
            return False
        
        return True
    
    def _capture_loop(self):
        """Main capture loop that continuously takes screenshots."""
        frame_interval = 1.0 / self.capture_fps
        next_capture_time = time.time()
        
        while self.running:
            current_time = time.time()
            
            # Handle messages from other threads
            self._process_messages()
            
            # Check if it's time for next frame
            if current_time >= next_capture_time:
                try:
                    if self.capture_system:
                        capture_frame = self.capture_system.capture_frame()
                        if capture_frame and capture_frame.image:
                            timestamped_frame = TimestampedFrame(
                                image=capture_frame.image,
                                timestamp=current_time,
                                frame_number=self.frame_counter
                            )
                            
                            self.frame_buffer.append(timestamped_frame)
                            self.frame_counter += 1
                            
                            # Log periodically
                            if self.frame_counter % (self.capture_fps * 5) == 0:
                                buffer_duration = self._get_buffer_duration()
                                self.logger.debug(f"📊 Captured {self.frame_counter} frames, buffer: {len(self.frame_buffer)} frames ({buffer_duration:.1f}s)")
                
                except Exception as e:
                    self.logger.error(f"❌ Capture error: {e}")
                
                next_capture_time += frame_interval
            
            # Small sleep to prevent busy waiting
            time.sleep(0.001)
    
    def _process_messages(self):
        """Process messages from other threads."""
        try:
            while True:
                message = self.message_queue.get_nowait()
                if message.message_type == 'get_gif':
                    response = self._generate_gif_response(message.data)
                    if message.response_queue:
                        message.response_queue.put(response)
                elif message.message_type == 'get_status':
                    response = self._get_status_response()
                    if message.response_queue:
                        message.response_queue.put(response)
        except queue.Empty:
            pass
        except Exception as e:
            self.logger.error(f"❌ Error processing message: {e}")
    
    def _generate_gif_response(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate GIF from rolling buffer."""
        try:
            current_time = time.time()
            max_duration = request_data.get('max_duration', None)
            
            # Determine time range for GIF
            if self.last_gif_timestamp is None:
                buffer_duration = self._get_buffer_duration()
                default_duration = 5.0 if max_duration is None else max_duration
                start_time = current_time - min(default_duration, buffer_duration)
            else:
                start_time = self.last_gif_timestamp
                duration_since_last = current_time - self.last_gif_timestamp
                
                gif_optimization = self.capture_config.get('gif_optimization', {})
                max_subsequent_duration = gif_optimization.get('max_gif_duration', 10.0)
                if duration_since_last > max_subsequent_duration:
                    start_time = current_time - max_subsequent_duration
            
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
            
            self.last_gif_timestamp = current_time
            
            gif_data_b64 = base64.b64encode(gif_data).decode('utf-8')
            duration = end_time - start_time
            
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
            
            self.logger.info(f"📸 Generated GIF: {len(gif_frames)} frames, {duration:.2f}s")
            
            # Send to dashboard via message bus
            dashboard_config = self.config.get('dashboard', {})
            if dashboard_config.get('enabled', False):
                publish_gif_message(gif_data_b64, metadata, source="video_capture_thread")
            
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Error generating GIF: {e}")
            return {'error': f'Failed to generate GIF: {e}'}
    
    def _create_gif_from_frames(self, frames: List[TimestampedFrame]) -> Optional[bytes]:
        """Create optimized GIF bytes from list of frames."""
        try:
            if not frames:
                return None
            
            gif_optimization = self.capture_config.get('gif_optimization', {})
            max_frames = gif_optimization.get('max_gif_frames', 150)
            
            if len(frames) > max_frames:
                step = len(frames) // max_frames
                frames = [frames[i] for i in range(0, len(frames), step)][:max_frames]
            
            images = [frame.image for frame in frames]
            
            # Resize images for smaller file size
            gif_width = gif_optimization.get('gif_width', 240)
            if images and images[0].width > gif_width:
                aspect_ratio = images[0].height / images[0].width
                gif_height = int(gif_width * aspect_ratio)
                images = [img.resize((gif_width, gif_height), PIL.Image.Resampling.LANCZOS) for img in images]
            
            # Calculate frame duration
            target_duration = gif_optimization.get('target_gif_duration', 5.0)
            frame_duration_ms = max(33, int(1000 * target_duration / len(frames)))
            
            # Create GIF
            gif_buffer = BytesIO()
            images[0].save(
                gif_buffer,
                format='GIF',
                save_all=True,
                append_images=images[1:],
                duration=frame_duration_ms,
                loop=0,
                optimize=True,
                disposal=2
            )
            
            return gif_buffer.getvalue()
            
        except Exception as e:
            self.logger.error(f"❌ Error creating GIF: {e}")
            return None
    
    def _get_buffer_duration(self) -> float:
        """Get current buffer duration in seconds."""
        if len(self.frame_buffer) < 2:
            return 0.0
        return self.frame_buffer[-1].timestamp - self.frame_buffer[0].timestamp
    
    def _get_status_response(self) -> Dict[str, Any]:
        """Get current status of video capture thread."""
        buffer_duration = self._get_buffer_duration()
        return {
            'running': self.running,
            'frame_count': self.frame_counter,
            'buffer_frames': len(self.frame_buffer),
            'buffer_duration': buffer_duration,
            'capture_fps': self.capture_fps,
            'last_gif_timestamp': self.last_gif_timestamp
        }


class GameControlThread(threading.Thread):
    """Game control thread that handles AI decisions and emulator communication."""
    
    def __init__(self, config: Dict[str, Any], video_queue: queue.Queue):
        super().__init__(daemon=True, name="GameControlThread")
        self.config = config
        self.video_queue = video_queue
        
        # Initialize Pokemon Red controller
        self.controller = PokemonRedController(config)
        
        # Thread control
        self.running = False
        
        self.logger = get_logger("game_control_thread")
        self.logger.info("🎮 Game Control Thread initialized")
    
    def run(self):
        """Main thread execution."""
        self.logger.info("🚀 Starting game control thread...")
        self.running = True
        
        # Start the controller (socket server for emulator)
        if not self.controller.start():
            self.logger.error("❌ Failed to start game controller")
            return
        
        self.logger.info("✅ Game control thread started successfully")
        
        # The controller.start() method contains the main server loop
        # No additional loop needed here
    
    def stop(self):
        """Stop the game control thread."""
        self.logger.info("🛑 Stopping game control thread...")
        self.running = False
        
        if hasattr(self.controller, 'stop'):
            self.controller.stop()
    
    def request_gif_from_video_thread(self, max_duration: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Request GIF from video capture thread."""
        try:
            response_queue = queue.Queue()
            message = ThreadMessage(
                message_type='get_gif',
                data={'max_duration': max_duration},
                response_queue=response_queue
            )
            
            self.video_queue.put(message)
            
            # Wait for response with timeout
            response = response_queue.get(timeout=30)
            return response
            
        except queue.Empty:
            self.logger.error("❌ Timeout waiting for GIF from video thread")
            return None
        except Exception as e:
            self.logger.error(f"❌ Error requesting GIF from video thread: {e}")
            return None


class UnifiedGameService:
    """Unified service that manages both video capture and game control threads."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config_emulator.json')
        
        self.config = self._load_config(config_path)
        self.logger = get_logger("unified_game_service")
        
        # Thread communication
        self.video_message_queue = queue.Queue()
        
        # Thread instances
        self.video_thread = None
        self.game_thread = None
        
        # Service state
        self.running = False
        
        self.logger.info("🎯 Unified Game Service initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Force single process mode
            if 'dual_process_mode' not in config:
                config['dual_process_mode'] = {}
            config['dual_process_mode']['enabled'] = False
            
            return config
        except Exception as e:
            self.logger.error(f"❌ Error loading config: {e}")
            return {}
    
    def start(self):
        """Start the unified service."""
        if self.running:
            self.logger.warning("⚠️ Service is already running")
            return False
        
        self.logger.info("🚀 Starting Unified Game Service...")
        
        # Configure logging
        configure_logging(debug=self.config.get('debug_mode', False), process_name="unified_service")
        
        try:
            # Start video capture thread
            self.video_thread = VideoCaptureThread(self.config, self.video_message_queue)
            self.video_thread.start()
            
            # Wait a moment for video thread to initialize
            time.sleep(2)
            
            # Start game control thread
            self.game_thread = GameControlThread(self.config, self.video_message_queue)
            
            # Modify controller to use threaded video capture
            self._integrate_threaded_video_capture()
            
            self.game_thread.start()
            
            self.running = True
            self.logger.info("✅ Unified Game Service started successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start service: {e}")
            self.stop()
            return False
    
    def stop(self):
        """Stop the unified service."""
        if not self.running:
            return
        
        self.logger.info("🛑 Stopping Unified Game Service...")
        self.running = False
        
        # Stop threads
        if self.game_thread:
            self.game_thread.stop()
        
        if self.video_thread:
            self.video_thread.stop()
        
        # Wait for threads to finish
        if self.game_thread and self.game_thread.is_alive():
            self.game_thread.join(timeout=5)
        
        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.join(timeout=5)
        
        self.logger.info("✅ Unified Game Service stopped")
    
    def _integrate_threaded_video_capture(self):
        """Integrate threaded video capture with game controller."""
        # Store original method if it exists  
        original_make_decision = getattr(self.game_thread.controller, '_make_decision_from_video_process', None)
        
        def threaded_make_decision():
            """Make AI decision using GIF from video thread."""
            try:
                self.logger.debug("📹 Requesting GIF from video thread...")
                gif_response = self.game_thread.request_gif_from_video_thread()
                
                if not gif_response or not gif_response.get('success'):
                    error = gif_response.get('error', 'Unknown error') if gif_response else 'No response'
                    self.logger.error(f"Failed to get GIF from video thread: {error}")
                    return None
                
                # Convert to format expected by controller
                gif_data = gif_response.get('gif_data')
                frame_count = gif_response.get('frame_count', 0)
                duration = gif_response.get('duration', 0.0)
                start_timestamp = gif_response.get('start_timestamp', 0.0)
                end_timestamp = gif_response.get('end_timestamp', 0.0)
                
                if not gif_data:
                    self.logger.error("No GIF data received from video thread")
                    return None
                
                # Convert GIF data to PIL Image
                gif_bytes = base64.b64decode(gif_data)
                gif_buffer = BytesIO(gif_bytes)
                gif_image = PIL.Image.open(gif_buffer)
                gif_image.load()
                
                self.logger.info(f"🎥 Received GIF: {frame_count} frames, {duration:.2f}s")
                
                # Create mock video segment for compatibility
                class MockVideoSegment:
                    def __init__(self, frame_count, duration, start_timestamp, end_timestamp):
                        self.frames = [None] * frame_count
                        self.duration = duration
                        self.start_time = start_timestamp
                        self.end_time = end_timestamp
                
                mock_video_segment = MockVideoSegment(frame_count, duration, start_timestamp, end_timestamp)
                
                processed_video = {
                    'gif_image': gif_image,
                    'video_segment': mock_video_segment,
                    'frame_count': frame_count,
                    'duration': duration,
                    'processed_at': time.time()
                }
                
                # Make decision using processed video
                decision = self.game_thread.controller._make_decision_from_processed_video(processed_video)
                
                if decision:
                    button_count = len(decision.get('buttons', []))
                    self.logger.info(f"Decision made: {button_count} buttons")
                
                return decision
                
            except Exception as e:
                self.logger.error(f"Error making decision from video thread: {e}")
                return None
        
        # Add the method to the controller
        self.game_thread.controller._make_decision_from_video_process = threaded_make_decision
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of the unified service."""
        status = {
            'service_running': self.running,
            'video_thread_alive': self.video_thread.is_alive() if self.video_thread else False,
            'game_thread_alive': self.game_thread.is_alive() if self.game_thread else False,
        }
        
        # Get video thread status
        if self.video_thread and self.video_thread.is_alive():
            try:
                response_queue = queue.Queue()
                message = ThreadMessage(
                    message_type='get_status',
                    data={},
                    response_queue=response_queue
                )
                self.video_message_queue.put(message)
                video_status = response_queue.get(timeout=5)
                status['video_capture'] = video_status
            except:
                status['video_capture'] = {'error': 'Failed to get status'}
        
        return status


# Global service instance
_service_instance = None


def get_unified_service() -> UnifiedGameService:
    """Get the global unified service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = UnifiedGameService()
    return _service_instance


def start_unified_service(config: Union[str, Dict] = None) -> bool:
    """Start the global unified service.
    
    Args:
        config: Either a config file path (str) or config dictionary (Dict)
    """
    service = get_unified_service()
    if config:
        if isinstance(config, str):
            # Config is a file path
            service.config = service._load_config(config)
        elif isinstance(config, dict):
            # Config is a dictionary from database
            service.config = config
        else:
            raise ValueError(f"Config must be a string (file path) or dict, got {type(config)}")
    return service.start()


def stop_unified_service():
    """Stop the global unified service."""
    service = get_unified_service()
    service.stop()


def main():
    """Main entry point for testing the unified service."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified Game Service for AI GBA Player')
    parser.add_argument('--config', default='config_emulator.json', 
                       help='Path to configuration file')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging
    configure_logging(debug=args.debug, process_name="unified_service")
    
    # Create and start service
    service = UnifiedGameService(args.config)
    
    try:
        success = service.start()
        if not success:
            print("❌ Failed to start unified service")
            sys.exit(1)
        
        print("✅ Unified service started successfully")
        print("🎯 Service running... Press Ctrl+C to stop")
        
        # Keep service running
        while service.running:
            time.sleep(1.0)
        
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
    except Exception as e:
        print(f"❌ Service error: {e}")
        sys.exit(1)
    finally:
        service.stop()
        print("✅ Unified service stopped")


if __name__ == '__main__':
    main()