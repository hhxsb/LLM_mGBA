#!/usr/bin/env python3
"""
Game control process for Pokemon Red AI.
Handles game logic, LLM decisions, and communicates with video capture process.
"""

import time
import socket
import json
import os
import sys
import threading
import signal
from typing import Dict, List, Any, Optional
import base64
from io import BytesIO
import asyncio
import websockets

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from games.pokemon_red.controller import PokemonRedController
from core.logging_config import configure_logging, get_logger, get_timeline_logger
from core.storage_service import StorageService, prepare_decision_data, prepare_action_data
from core.message_bus import message_bus, publish_response_message, publish_action_message
from core.message_types import UnifiedMessage
import PIL.Image


class VideoProcessClient:
    """Client for communicating with video capture process."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 8889, config: Dict[str, Any] = None):
        self.host = host
        self.port = port
        self.config = config or {}
        
    def request_gif(self) -> Optional[Dict[str, Any]]:
        """Request a GIF from the video capture process."""
        try:
            logger = get_logger("game_control.video_client")
            logger.debug(f"🔗 Connecting to video process at {self.host}:{self.port}")
            
            # Connect to video process
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # OPTIMIZATION: Adaptive timeout for large GIF transfers
            dual_process_config = self.config.get('dual_process_mode', {})
            base_timeout = dual_process_config.get('process_communication_timeout', 10.0)
            adaptive_timeout = max(base_timeout, 20.0)
            sock.settimeout(adaptive_timeout)
            logger.debug(f"🕒 Using adaptive timeout: {adaptive_timeout:.1f}s for GIF transfer")
            sock.connect((self.host, self.port))
            
            # Send request
            request = {'type': 'get_gif'}
            request_data = json.dumps(request).encode('utf-8')
            logger.debug(f"📤 Sending GIF request")
            sock.send(request_data)
            
            # Receive response - handle potentially large messages
            response_data = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                # Check if we have a complete JSON message
                try:
                    response = json.loads(response_data.decode('utf-8'))
                    break
                except json.JSONDecodeError:
                    # Message not complete yet, continue receiving
                    continue
            
            if not response_data:
                raise Exception("No response received from video process")
            
            logger.debug(f"📥 Received response: {len(response_data)} bytes")
            if response.get('success'):
                frame_count = response.get('frame_count', 0)
                duration = response.get('duration', 0.0)
                logger.info(f"✅ GIF received: {frame_count} frames, {duration:.2f}s")
            else:
                error = response.get('error', 'Unknown error')
                logger.error(f"❌ GIF request failed: {error}")
            
            sock.close()
            return response
            
        except Exception as e:
            logger.error(f"❌ Error requesting GIF from video process: {e}")
            return None
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """Get status from video capture process."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.host, self.port))
            
            request = {'type': 'status'}
            request_data = json.dumps(request).encode('utf-8')
            sock.send(request_data)
            
            response_data = sock.recv(4096)
            response = json.loads(response_data.decode('utf-8'))
            
            sock.close()
            return response
            
        except Exception as e:
            logger = get_logger("game_control.video_client")
            logger.error(f"❌ Error getting status from video process: {e}")
            return None
    
    def gif_data_to_image(self, gif_data: str) -> Optional[PIL.Image.Image]:
        """Convert base64 GIF data to PIL Image."""
        try:
            # Decode base64 GIF data
            gif_bytes = base64.b64decode(gif_data)
            
            # Load as PIL Image and keep the BytesIO buffer open
            gif_buffer = BytesIO(gif_bytes)
            image = PIL.Image.open(gif_buffer)
            
            # Force load the image data to prevent buffer issues
            image.load()
            
            # For animated GIFs, we need to preserve the animation
            logger = get_logger("game_control.video_client")
            if hasattr(image, 'is_animated') and image.is_animated:
                logger.debug(f"✅ Loaded animated GIF: {image.n_frames} frames, format={image.format}")
            else:
                logger.debug(f"⚠️ Loaded static image: format={image.format}")
            
            return image
            
        except Exception as e:
            logger = get_logger("game_control.video_client")
            logger.error(f"❌ Error converting GIF data to image: {e}")
            return None


class GameControlProcess(PokemonRedController):
    """Game control process that uses video capture process for visual input."""
    
    def __init__(self, config: Dict[str, Any]):
        # Initialize parent controller but override video capture behavior
        super().__init__(config)
        
        # Video process client
        dual_process_config = config.get('dual_process_mode', {})
        video_port = dual_process_config.get('video_capture_port', 8889)
        self.video_client = VideoProcessClient(port=video_port, config=config)
        
        # Override capture system behavior
        self.use_external_video_process = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # On-demand GIF timing
        self.last_action_complete_time = None
        self.pending_gif_request = False
        self.action_delay_seconds = 0.5  # Wait 0.5s after action completion
        
        # Dashboard integration via message bus
        self.dashboard_config = config.get('dashboard', {})
        self.dashboard_enabled = self.dashboard_config.get('enabled', False)
        
        # Storage service for SQLite persistence
        self.storage_service = None
        self.storage_enabled = config.get('storage', {}).get('enabled', True)
        if self.storage_enabled:
            self.storage_service = StorageService(config)
            self.logger.info("🗃️ SQLite storage service initialized")
        
        self.logger.section("Game Control Process Initialized")
        self.logger.info(f"   Video process port: {video_port}")
        self.logger.info(f"   Game: {config.get('game', 'Unknown')}")
        self.logger.info(f"   Dual-process mode: ENABLED")
        self.logger.info(f"   On-demand GIF requests: {self.action_delay_seconds}s after action completion")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"\n🛑 Received signal {signum}, shutting down game control process...")
        self.stop()
    
    def start(self):
        """Start the game control process."""
        self.logger.section("Starting Game Control Process")
        
        # Check video process connection
        self.logger.debug("🔗 Connecting to video capture process...")
        status = self.video_client.get_status()
        if not status:
            self.logger.error("Cannot connect to video capture process")
            self.logger.error("Make sure video_capture_process.py is running first")
            return False
        
        buffer_frames = status.get('buffer_frames', 0)
        buffer_duration = status.get('buffer_duration', 0.0)
        self.logger.success(f"Connected to video process: {buffer_frames} frames ({buffer_duration:.1f}s) in buffer")
        
        # Initialize storage service if enabled
        if self.storage_enabled and self.storage_service:
            try:
                # Initialize storage in a separate thread since we're not in async context
                storage_thread = threading.Thread(target=self._initialize_storage_service, daemon=True)
                storage_thread.start()
                storage_thread.join(timeout=5.0)  # Wait up to 5 seconds for initialization
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize storage service: {e}")
                self.storage_enabled = False
        
        # Start the base controller (socket server for emulator)
        self.logger.debug("🎮 Starting socket server for emulator connection...")
        result = super().start()
        
        if result:
            self.logger.success("Game control process started successfully")
            self.logger.info("🎯 Waiting for mGBA emulator connection...")
            
            # Start new game session if storage is enabled
            if self.storage_enabled and self.storage_service:
                try:
                    session_thread = threading.Thread(target=self._start_storage_session, daemon=True)
                    session_thread.start()
                except Exception as e:
                    self.logger.error(f"❌ Failed to start storage session: {e}")
            
            # Dashboard integration enabled via message bus
            if self.dashboard_enabled:
                self.logger.info("📊 Dashboard integration enabled via message bus")
        
        return result
    
    def _initialize_storage_service(self):
        """Initialize storage service in async context."""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.storage_service.initialize())
            self.logger.success("✅ Storage service initialized")
        except Exception as e:
            self.logger.error(f"❌ Storage service initialization failed: {e}")
            self.storage_enabled = False
        finally:
            try:
                loop.close()
            except:
                pass
    
    def _start_storage_session(self):
        """Start a new storage session."""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            session_id = loop.run_until_complete(self.storage_service.start_session())
            self.logger.success(f"🎮 Started storage session: {session_id}")
        except Exception as e:
            self.logger.error(f"❌ Failed to start storage session: {e}")
        finally:
            try:
                loop.close()
            except:
                pass
    
    def _make_decision_from_processed_video(self, processed_video):
        """Override to add dashboard integration for AI responses and actions."""
        start_time = time.time()
        
        # Call parent method to get the decision
        decision = super()._make_decision_from_processed_video(processed_video)
        
        # 📸 Add detailed LLM response and decision reasoning logging (missing from dual process mode)
        if decision:
            # Extract and log detailed LLM response content
            response_text = decision.get('text', '')
            raw_response = decision.get('raw_response', '')
            reasoning = decision.get('reasoning', '')
            
            self.logger.info(f"📸 LLM RESPONSE CONTENT: {response_text}")
            if reasoning:
                self.logger.info(f"📸 LLM DECISION REASONING: {reasoning}")
            if raw_response and raw_response != response_text:
                self.logger.debug(f"📸 LLM RAW RESPONSE: {raw_response}")
            
            # Log button decision reasoning
            button_codes = decision.get('buttons', [])
            if button_codes:
                button_names = []
                button_code_to_name = {0: 'A', 1: 'B', 2: 'SELECT', 3: 'START', 4: 'RIGHT', 5: 'LEFT', 6: 'UP', 7: 'DOWN'}
                for code in button_codes:
                    button_names.append(button_code_to_name.get(code, f'BUTTON_{code}'))
                self.logger.info(f"📸 LLM BUTTON DECISION: Chose {len(button_codes)} buttons: {', '.join(button_names)}")
            
        else:
            self.logger.warning("📸 LLM RESPONSE: No decision made by LLM")
        
        processing_time = time.time() - start_time
        
        # 🗃️ Store complete AI cycle in SQLite if storage is enabled
        if decision and self.storage_enabled and self.storage_service:
            self._store_ai_cycle_async(decision, processed_video, processing_time)
        
        # Send AI response and actions to dashboard using unified message bus
        if decision:
            # Extract response text and reasoning
            response_text = decision.get('text', '')
            reasoning = decision.get('reasoning')  # Extract reasoning if available
            
            # TIMELINE EVENT 7: T+6.0s - Game Control sends AI response → dashboard  
            if response_text:
                timeline_logger = get_timeline_logger("game_control")
                timeline_logger.log_event(7, f"{processing_time + 6.0:.1f}s", "Game Control sends AI response → dashboard")
                
                # Use message bus to publish response
                publish_response_message(
                    text=response_text,
                    reasoning=reasoning,
                    processing_time=processing_time,
                    source="game_control"
                )
                self.logger.info(f"📤 Published AI response to message bus: {len(response_text)} chars")
            
            # Extract button information
            button_codes = decision.get('buttons', [])
            button_durations = decision.get('durations', [])
            
            # Convert button codes to names for display
            button_names = []
            button_code_to_name = {0: 'A', 1: 'B', 2: 'SELECT', 3: 'START', 4: 'RIGHT', 5: 'LEFT', 6: 'UP', 7: 'DOWN'}
            for code in button_codes:
                button_names.append(button_code_to_name.get(code, f'BUTTON_{code}'))
            
            # TIMELINE EVENT 8: T+6.2s - Game Control sends button actions → dashboard
            if button_codes:
                timeline_logger.log_event(8, f"{processing_time + 6.2:.1f}s", "Game Control sends button actions → dashboard")
                
                # Use message bus to publish action
                publish_action_message(
                    buttons=[str(code) for code in button_codes],
                    durations=[float(d) for d in button_durations],
                    button_names=button_names,
                    source="game_control"
                )
                self.logger.info(f"📤 Published action to message bus: {len(button_codes)} buttons")
        
        return decision
    
    # Old dashboard WebSocket methods removed - now using message bus
    
    def _store_ai_cycle_async(self, decision: Dict[str, Any], processed_video: Dict[str, Any], processing_time: float):
        """Store complete AI cycle in SQLite asynchronously."""
        def store_cycle():
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Prepare decision data
                decision_data = prepare_decision_data(
                    llm_response_text=decision.get('text', ''),
                    llm_reasoning=decision.get('reasoning', ''),
                    llm_raw_response=decision.get('raw_response', ''),
                    processing_time_ms=processing_time * 1000,
                    game_state=getattr(self, 'current_game_state', None).__dict__ if hasattr(self, 'current_game_state') else {},
                    conversation_context={},  # Could extract from knowledge system
                    memory_context={},       # Could extract from knowledge system
                    tutorial_step=None       # Could extract from knowledge system
                )
                
                # Prepare action data
                button_codes = decision.get('buttons', [])
                button_durations = decision.get('durations', [])
                button_names = []
                button_code_to_name = {0: 'A', 1: 'B', 2: 'SELECT', 3: 'START', 4: 'RIGHT', 5: 'LEFT', 6: 'UP', 7: 'DOWN'}
                for code in button_codes:
                    button_names.append(button_code_to_name.get(code, f'BUTTON_{code}'))
                
                action_data = prepare_action_data(
                    button_codes=button_codes,
                    button_names=button_names,
                    button_durations=button_durations,
                    execution_time_ms=None,  # Will be updated when action executes
                    success=True
                )
                
                # Store complete AI cycle
                decision_id, action_id, gif_id = loop.run_until_complete(
                    self.storage_service.record_ai_cycle(decision_data, action_data)
                )
                
                # Store GIF separately if available
                gif_image = processed_video.get('gif_image')
                if gif_image and decision_id:
                    frame_count = processed_video.get('frame_count', 0)
                    duration = processed_video.get('duration', 0.0)
                    
                    gif_id = loop.run_until_complete(
                        self.storage_service.store_gif_from_pil(
                            decision_id=decision_id,
                            gif_image=gif_image,
                            frame_count=frame_count,
                            duration=duration
                        )
                    )
                
                self.logger.debug(f"🗃️ Stored AI cycle: decision={decision_id[:8]}, action={action_id[:8]}, gif={gif_id[:8] if gif_id else 'none'}")
                
            except Exception as e:
                self.logger.error(f"❌ Failed to store AI cycle: {e}")
            finally:
                try:
                    loop.close()
                except:
                    pass
        
        # Run storage in background thread
        storage_thread = threading.Thread(target=store_cycle, daemon=True)
        storage_thread.start()
    
    def stop(self):
        """Stop the game control process."""
        self.logger.section("Stopping Game Control Process")
        # Set running flag to false to stop server loop
        self.running = False
        
        # Call parent stop method if it exists
        if hasattr(super(), 'stop'):
            super().stop()
        else:
            # Basic cleanup
            if hasattr(self, 'server_socket') and self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
    
    def _handle_continuous_recording_workflow(self, client_socket):
        """Override to use external video process instead of internal recording."""
        # Always make decision using current video from external process
        decision = self._make_decision_from_video_process()
        return decision
    
    def _make_decision_from_video_process(self):
        """Make AI decision using GIF from external video process."""
        try:
            # TIMELINE EVENT 1: T+0.0s - Game Control requests GIF from Video Capture
            cycle_start_time = time.time()
            timeline_logger = get_timeline_logger("game_control")
            timeline_logger.log_event(1, "0.0s", "Game Control requests GIF from Video Capture (TCP socket)")
            self.logger.debug("📹 Requesting GIF from video process...")
            gif_response = self.video_client.request_gif()
            
            if not gif_response or not gif_response.get('success'):
                error = gif_response.get('error', 'Unknown error') if gif_response else 'No response'
                self.logger.error(f"Failed to get GIF from video process: {error}")
                return None
            
            # Extract GIF data
            gif_data = gif_response.get('gif_data')
            frame_count = gif_response.get('frame_count', 0)
            duration = gif_response.get('duration', 0.0)
            start_timestamp = gif_response.get('start_timestamp', 0.0)
            end_timestamp = gif_response.get('end_timestamp', 0.0)
            
            if not gif_data:
                self.logger.error("No GIF data received from video process")
                return None
            
            # TIMELINE EVENT 4: T+0.3s - Game Control receives GIF data 
            elapsed_time = time.time() - cycle_start_time
            timeline_logger.log_event(4, f"{elapsed_time:.1f}s", "Game Control receives GIF data → processes with LLM")
            
            # Convert GIF data to PIL Image
            gif_image = self.video_client.gif_data_to_image(gif_data)
            if not gif_image:
                self.logger.error("Failed to convert GIF data to image")
                return None
            
            # Check if GIF is animated
            is_animated = getattr(gif_image, 'is_animated', False)
            n_frames = getattr(gif_image, 'n_frames', 1) if is_animated else 1
            
            self.logger.info(f"🎥 Received GIF: {frame_count} frames, {duration:.2f}s")
            self.logger.debug(f"   Time range: {start_timestamp:.2f} → {end_timestamp:.2f}")
            self.logger.debug(f"   GIF size: {len(gif_data)} bytes (base64)")
            self.logger.debug(f"   PIL Image: Animated={is_animated}, PIL_frames={n_frames}, Format={gif_image.format}")
            
            # Create a mock video segment object for compatibility
            class MockVideoSegment:
                def __init__(self, frame_count, duration, start_timestamp, end_timestamp):
                    self.frames = [None] * frame_count  # Mock frames list
                    self.duration = duration
                    self.start_time = start_timestamp
                    self.end_time = end_timestamp
            
            mock_video_segment = MockVideoSegment(frame_count, duration, start_timestamp, end_timestamp)
            
            # Create processed video object for decision making
            processed_video = {
                'gif_image': gif_image,
                'video_segment': mock_video_segment,  # Add missing video_segment
                'frame_count': frame_count,
                'duration': duration,
                'processed_at': time.time()
            }
            
            # TIMELINE EVENT 5: T+2-6s - LLM processing time
            llm_start_time = time.time()
            elapsed_time = llm_start_time - cycle_start_time
            timeline_logger.log_event(5, f"{elapsed_time:.1f}s", "LLM processing begins (varies by complexity)")
            self.logger.debug("🧠 Making AI decision from received GIF...")
            
            decision = self._make_decision_from_processed_video(processed_video)
            
            # Log LLM completion
            llm_end_time = time.time()
            llm_duration = llm_end_time - llm_start_time
            total_elapsed = llm_end_time - cycle_start_time
            timeline_logger.log_event(6, f"{total_elapsed:.1f}s", f"LLM processing complete (took {llm_duration:.1f}s)")
            
            if decision:
                button_count = len(decision.get('buttons', []))
                self.logger.ai_action(f"Decision made: {button_count} buttons")
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error making decision from video process: {e}")
            return None
    
    def _should_request_gif_now(self, current_time: float) -> bool:
        """Determine if it's time to request a GIF based on action completion timing."""
        # First request: always allow (but video process will handle initial timing)
        if self.last_action_complete_time is None:
            return True
        
        # Subsequent requests: wait for action_delay_seconds after last action completion
        time_since_action = current_time - self.last_action_complete_time
        return time_since_action >= self.action_delay_seconds
    
    def _get_remaining_delay(self, current_time: float) -> float:
        """Get remaining delay time before next GIF request."""
        if self.last_action_complete_time is None:
            return 0.0
        
        time_since_action = current_time - self.last_action_complete_time
        remaining = self.action_delay_seconds - time_since_action
        return max(0.0, remaining)
    
    def _send_button_decision_with_timing(self, client_socket, decision, request_time: float):
        """Send button decision and track timing for next GIF request."""
        if decision and decision.get('buttons') is not None:
            button_codes = decision['buttons']
            button_durations = decision.get('durations', [])
            
            # Calculate action duration
            action_duration_seconds = self._calculate_action_duration(button_codes, button_durations)
            
            # TIMELINE EVENT 10: T+6.4s - Actions executed in emulator → cycle repeats after cooldown
            timeline_logger = get_timeline_logger("game_control")
            timeline_logger.log_event(10, "6.4s", "Actions executed in emulator → cycle repeats after cooldown")
            
            # Send the decision
            self._send_button_decision(client_socket, decision)
            
            # Schedule action completion time tracking
            self._schedule_action_completion_tracking(action_duration_seconds)
            
            self.logger.debug(f"🎮 Action duration: {action_duration_seconds:.2f}s, next GIF in {action_duration_seconds + self.action_delay_seconds:.2f}s")
        else:
            # No decision, just acknowledge
            self._send_button_decision(client_socket, decision)
    
    def _schedule_action_completion_tracking(self, action_duration_seconds: float):
        """Schedule tracking of when the action completes."""
        def track_action_completion():
            time.sleep(action_duration_seconds)
            self.last_action_complete_time = time.time()
            self.logger.debug(f"🎮 Action completed at T={self.last_action_complete_time:.2f}, next GIF available in {self.action_delay_seconds}s")
        
        completion_thread = threading.Thread(target=track_action_completion, daemon=True)
        completion_thread.start()
    
    def _handle_state_message(self, client_socket, content):
        """Override state message handling for dual-process architecture with on-demand timing."""
        self.logger.game_state("Received game state for dual-process mode")
        self.logger.debug(f"🎮 Received state message with {len(content)} parts: {content}")
        
        if len(content) >= 4:
            # Parse game state using game engine
            state_data = content[0:4]  # direction, x, y, mapId
            self.current_game_state = self.game_engine.parse_game_state(state_data)
            
            self.logger.debug(f"Game State: {self.current_game_state}")
            self.logger.debug(f"🎮 Parsed game state - Map: {self.current_game_state.map_id}, Pos: ({self.current_game_state.player_x}, {self.current_game_state.player_y})")
            
            # Check if this is the right time to request a GIF
            current_time = time.time()
            should_request_gif = self._should_request_gif_now(current_time)
            
            if should_request_gif:
                self.logger.debug("🎮 Making on-demand decision from video process...")
                decision = self._make_decision_from_video_process()
                if decision:
                    self.logger.debug(f"🎮 Decision received, sending buttons: {decision.get('buttons', [])}")
                    self._send_button_decision_with_timing(client_socket, decision, current_time)
                else:
                    # Fallback if video process fails
                    self.logger.warning("⚠️ Video process failed, using fallback decision")
                    decision = self.process_video_sequence(1.0)
                    self._send_button_decision_with_timing(client_socket, decision, current_time)
            else:
                # Not time yet, just acknowledge the state
                delay_remaining = self._get_remaining_delay(current_time)
                self.logger.debug(f"🎮 Waiting {delay_remaining:.2f}s more before next GIF request")
                # Send a simple acknowledgment or wait
                time.sleep(0.1)  # Small delay before next state check
        else:
            self.logger.error(f"State message too short: {len(content)} parts")
    
    def _handle_enhanced_screenshot_with_state(self, client_socket, content):
        """Override enhanced screenshot handling for dual-process architecture."""
        self.logger.game_state("Received enhanced screenshot with game state")
        
        if len(content) >= 7:
            screenshot_path = content[0]
            previous_screenshot_path = content[1]
            
            # Parse game state
            state_data = content[2:6]  # direction, x, y, mapId
            self.current_game_state = self.game_engine.parse_game_state(state_data)
            button_count = int(content[6])
            
            self.logger.debug(f"Enhanced Game State: {self.current_game_state}, Button Count: {button_count}")
            self.logger.debug(f"   Screenshot: {screenshot_path}")
            self.logger.debug(f"   Previous screenshot: {previous_screenshot_path}")
            
            # Always use external video process for decisions in dual-process mode
            self.logger.debug("🎥 Using dual-process video system for enhanced screenshot")
            decision = self._make_decision_from_video_process()
            if decision:
                self.logger.debug("✅ Decision received, sending button commands")
                self._send_button_decision(client_socket, decision)
            else:
                self.logger.warning("⚠️ No decision received from video process")
                # Send a simple fallback decision to prevent hanging
                self.logger.debug("🔄 Requesting new state from emulator")
                try:
                    client_socket.send(b'request_state\n')
                except Exception as e:
                    self.logger.error(f"Failed to request new state: {e}")
        else:
            self.logger.error(f"Enhanced screenshot content too short: {len(content)} items")
    
    def _send_button_decision(self, client_socket, decision):
        """Override to remove continuous recording logic and add detailed logging."""
        if decision and decision.get('buttons') is not None:
            try:
                button_codes = decision['buttons']
                button_durations = decision.get('durations', [])
                
                # Log the decision details
                button_names = [name for name, code in [('A', 0), ('B', 1), ('SELECT', 2), ('START', 3), 
                                                      ('RIGHT', 4), ('LEFT', 5), ('UP', 6), ('DOWN', 7)] 
                               if code in button_codes]
                
                self.logger.ai_action(f"Decision: Press {len(button_codes)} buttons: {', '.join(button_names)}")
                
                # Format message for emulator
                button_codes_str = ','.join(str(code) for code in button_codes)
                if button_durations:
                    durations_str = ','.join(str(d) for d in button_durations)
                    message = f"{button_codes_str}|{durations_str}"
                    self.logger.debug(f"   Button codes with durations: {button_codes_str} | {durations_str}")
                else:
                    message = button_codes_str
                    self.logger.debug(f"   Button codes: {button_codes_str}")
                
                self.logger.debug(f"📡 Sending to emulator: {message}")
                
                # Send button commands
                client_socket.send(message.encode('utf-8') + b'\n')
                self.emulator_ready = False
                self.last_decision_time = time.time()
                
                self.logger.ai_action(f"✅ Button commands sent to emulator")
                
            except Exception as e:
                self.logger.error(f"Failed to send button commands: {e}")
        else:
            # No decision made, respect cooldown and request another screenshot
            self.logger.warning("⚠️ No decision made, requesting new screenshot")
            self.last_decision_time = time.time()
            try:
                time.sleep(0.5)
                client_socket.send(b'request_screenshot\n')
                self.logger.debug("📡 Requested new screenshot from emulator")
            except Exception as e:
                self.logger.error(f"Failed to request another screenshot: {e}")
    
    # Old WebSocket dashboard methods removed - now using message bus for all communication


def main():
    """Main entry point for game control process."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Game Control Process for Pokemon AI')
    parser.add_argument('--config', default='config_emulator.json', 
                       help='Path to configuration file')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging for game control process
    configure_logging(debug=args.debug, process_name="game_control")
    
    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)
    
    # Create and run game control process
    game_controller = GameControlProcess(config)
    
    print("🎮 Starting Pokemon AI Game Control Process")
    
    try:
        success = game_controller.start()
        if not success:
            print("❌ Failed to start game control process")
            sys.exit(1)
        
        print("✅ Game control process started successfully")
        print("🎯 Waiting for emulator connection...")
        
        # The start() method contains the main server loop - no need for run()
        # Just wait for keyboard interrupt or process termination
        while True:
            time.sleep(1.0)
        
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
    except Exception as e:
        print(f"❌ Game control process error: {e}")
        sys.exit(1)
    finally:
        game_controller.stop()
        print("✅ Game control process stopped")


if __name__ == '__main__':
    main()