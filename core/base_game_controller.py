#!/usr/bin/env python3
"""
Abstract base controller for game-agnostic LLM game playing.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional
import socket
import time
import threading
import signal
import sys
import atexit
import os
import queue
import PIL.Image
from collections import deque

from .base_game_engine import BaseGameEngine, GameState
from .base_knowledge_system import BaseKnowledgeSystem
from .base_prompt_template import BasePromptTemplate, Tool
from .base_capture_system import BaseCaptureSystem, CaptureSystemFactory
from .video_analyzer import VideoAnalyzer


class ToolCall:
    """Represents a tool call from the LLM"""
    def __init__(self, id: str, name: str, arguments: Dict[str, Any]):
        self.id = id
        self.name = name
        self.arguments = arguments


class BaseGameController(ABC):
    """Abstract base controller for LLM-driven game playing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._cleanup_done = False
        self._cleanup_lock = threading.Lock()
        
        # Settings
        self.decision_cooldown = config.get('decision_cooldown', 5)
        self.debug_mode = config.get('debug_mode', False)
        
        # Initialize logger first (needed by other components)
        self.logger = self._create_logger()
        
        # Game state tracking
        self.current_game_state = GameState()
        
        # Action history (short-term memory)
        self.recent_actions = deque(maxlen=10)
        
        # Paths
        self.notepad_path = self._get_absolute_path(config['notepad_path'])
        self.screenshot_path = self._get_absolute_path(config['screenshot_path'])
        self.video_path = self._get_absolute_path(config.get('video_path', 'data/videos/video.mp4'))
        
        # Initialize game-specific components (implemented by subclasses)
        self.game_engine = self._create_game_engine()
        self.knowledge_system = self._create_knowledge_system()
        self.prompt_template = self._create_prompt_template()
        
        # Initialize capture system
        self.capture_system = self._create_capture_system()
        self.video_analyzer = VideoAnalyzer(config.get('capture_system', {}).get('video_analysis', {}))
        
        # Continuous recording system
        self.video_queue = queue.Queue()
        self.processing_lock = threading.Lock()
        self.current_recording_id = 0
        self.processed_videos = {}
        self.capture_fps = config.get('capture_system', {}).get('capture_fps', 30)
        self.continuous_recording = config.get('capture_system', {}).get('type') == 'screen'
        
        # Core components
        self.llm_client = self._create_llm_client()
        self.server_socket = None
        self.current_client = None
        self.running = True
        self.client_threads = []
        
        # Processing state
        self.is_processing = False
        self.emulator_ready = False
        self.last_decision_time = 0
        
        # Create directories
        self._create_directories()
        
        # Setup networking
        self.setup_socket()
        
        # Signal handling
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        atexit.register(self.cleanup)
    
    def _get_absolute_path(self, path: str) -> str:
        """Convert relative path to absolute path."""
        if not os.path.isabs(path):
            return os.path.abspath(path)
        return path
    
    def _create_directories(self):
        """Create necessary directories."""
        os.makedirs(os.path.dirname(self.notepad_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.screenshot_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.video_path), exist_ok=True)
    
    @abstractmethod
    def _create_game_engine(self) -> BaseGameEngine:
        """Create game-specific engine instance."""
        pass
    
    @abstractmethod
    def _create_knowledge_system(self) -> BaseKnowledgeSystem:
        """Create game-specific knowledge system instance."""
        pass
    
    @abstractmethod
    def _create_prompt_template(self) -> BasePromptTemplate:
        """Create game-specific prompt template instance."""
        pass
    
    @abstractmethod
    def _create_llm_client(self):
        """Create LLM client instance."""
        pass
    
    def _create_logger(self):
        """Create logger instance."""
        try:
            # Try to import the Pokemon logger
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from pokemon_logger import PokemonLogger
            return PokemonLogger(debug_mode=self.debug_mode)
        except ImportError:
            # Fallback to basic logging
            import logging
            logging.basicConfig(level=logging.INFO, format='%(message)s')
            return logging.getLogger(self.__class__.__name__)
    
    def _create_capture_system(self) -> BaseCaptureSystem:
        """Create capture system instance based on configuration."""
        capture_config = self.config.get('capture_system', {})
        capture_type = capture_config.get('type', 'emulator')
        
        # Import capture implementations
        from .screen_capture import ScreenCaptureSystem, EmulatorCaptureSystem
        
        try:
            capture_system = CaptureSystemFactory.create_system(capture_type, capture_config)
            if capture_system.initialize():
                self.logger.success(f"Initialized {capture_type} capture system")
                return capture_system
            else:
                self.logger.error(f"Failed to initialize {capture_type} capture system")
        except Exception as e:
            self.logger.error(f"Error creating {capture_type} capture system: {e}")
        
        # Fallback to emulator capture
        self.logger.info("Falling back to emulator capture system")
        fallback_system = EmulatorCaptureSystem(self.config)
        fallback_system.initialize()
        return fallback_system
    
    def setup_socket(self):
        """Set up the socket server for emulator communication."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            try:
                self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
            except (AttributeError, OSError):
                pass  # TCP keepalive options not fully supported
            
            host = self.config.get('host', '127.0.0.1')
            port = self.config.get('port', 8888)
            
            try:
                self.server_socket.bind((host, port))
            except socket.error:
                self.logger.warning(f"Port {port} in use. Attempting to free it...")
                os.system(f"lsof -ti:{port} | xargs kill -9")
                time.sleep(1)
                self.server_socket.bind((host, port))
            
            self.server_socket.listen(1)
            self.server_socket.settimeout(1)
            self.logger.success(f"Socket server set up on {host}:{port}")
            
        except socket.error as e:
            self.logger.error(f"Socket setup error: {e}")
            sys.exit(1)
    
    def signal_handler(self, sig, _frame):
        """Handle termination signals"""
        self.logger.warning(f"Received signal {sig}. Shutting down server...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Clean up resources"""
        with self._cleanup_lock:
            if self._cleanup_done:
                return
            self._cleanup_done = True
            
            self.logger.section("Cleaning up resources...")
            if self.current_client:
                try:
                    self.current_client.close()
                    self.current_client = None
                except:
                    pass
            if self.server_socket:
                try:
                    self.server_socket.close()
                    self.server_socket = None
                except:
                    pass
            self.logger.success("Cleanup complete")
            time.sleep(0.5)
    
    def process_screenshot(self, screenshot_path: str = None) -> Optional[Dict[str, Any]]:
        """Process a game screenshot or capture frame and return button decision."""
        if self.is_processing:
            return None
        
        self.is_processing = True
        try:
            # Check for prompt template updates
            self.prompt_template.check_for_updates()
            
            # Update knowledge system
            current_map = self.game_engine.get_map_name(self.current_game_state.map_id)
            self.knowledge_system.update_location(self.current_game_state, current_map)
            
            # Get frame from capture system or file
            if screenshot_path and os.path.exists(screenshot_path):
                # Use provided screenshot file (legacy mode)
                image = PIL.Image.open(screenshot_path)
                capture_frame = None
            else:
                # Use capture system
                capture_frame = self.capture_system.capture_frame()
                if not capture_frame:
                    self.logger.error("Failed to capture frame")
                    return None
                image = capture_frame.image
            
            # Enhance image
            if capture_frame:
                enhanced_frame = self.capture_system.enhance_frame(capture_frame)
                image = enhanced_frame.image
            else:
                image = self._enhance_image(image)
            
            # Get context for prompt
            context = self._build_prompt_context()
            
            # Format prompt
            prompt = self.prompt_template.format_template(
                self.current_game_state,
                **context
            )
            
            # Call LLM
            tools = self.prompt_template.get_available_tools()
            tool_objects = [Tool(t['name'], t['description'], t['parameters']) for t in tools]
            
            # Log what we're sending to the AI
            self.logger.info(f"📸 Sending single screenshot to AI for analysis")
            
            # Save screenshot sent to AI for inspection if debug mode is enabled
            if self.debug_mode:
                self._save_ai_frames_for_inspection([image], ["Single screenshot"], 0.0)
            
            response, tool_calls, text = self.llm_client.call_with_tools(
                message=prompt,
                tools=tool_objects,
                images=[image]
            )
            
            self.logger.ai_response(text)
            
            # Process tool calls
            return self._process_tool_calls(tool_calls, text)
            
        except Exception as e:
            self.logger.error(f"Error processing screenshot: {e}")
            if self.debug_mode:
                import traceback
                self.logger.debug(traceback.format_exc())
        finally:
            self.is_processing = False
        
        return None
    
    def process_video_sequence(self, action_duration: float = 2.0) -> Optional[Dict[str, Any]]:
        """Process a video sequence showing the result of recent actions."""
        if self.is_processing:
            return None
        
        self.is_processing = True
        try:
            # Check if this is an initial state analysis or action result analysis
            if action_duration <= 1.5:  # Initial state analysis
                self.logger.section(f"Starting initial video capture for {action_duration}s")
                
                # Stop any ongoing recording first
                if hasattr(self.capture_system, 'is_recording') and self.capture_system.is_recording:
                    self.logger.debug("Stopping previous recording before starting new one")
                    self.capture_system.stop_recording()
                
                # Start recording for initial state
                if not self.capture_system.start_recording():
                    self.logger.error("Failed to start video recording")
                    return self.process_screenshot()  # Fallback to screenshot
                
                # Wait for the short duration
                time.sleep(action_duration)
                
                # Stop recording and get video segment
                video_segment = self.capture_system.stop_recording()
                if not video_segment:
                    self.logger.error("Failed to get video segment")
                    return self.process_screenshot()  # Fallback to screenshot
            else:
                # This is action result analysis - recording should already be in progress
                self.logger.section(f"Analyzing action video sequence ({action_duration}s)")
                
                # Check if recording is actually in progress
                if not hasattr(self.capture_system, 'is_recording') or not self.capture_system.is_recording:
                    self.logger.warning("Recording not in progress, starting now...")
                    if not self.capture_system.start_recording():
                        self.logger.error("Failed to start video recording")
                        return self.process_screenshot()
                    # Wait for the action to complete
                    time.sleep(action_duration)
                else:
                    # Recording already in progress, just wait for completion
                    time.sleep(action_duration)
                
                # Stop recording and get video segment
                video_segment = self.capture_system.stop_recording()
                if not video_segment:
                    self.logger.error("Failed to get action video segment")
                    return self.process_screenshot()  # Fallback to screenshot
            
            # Save video segment for inspection if debug mode is enabled
            # Only save video segments if explicitly requested to reduce disk usage
            save_videos = self.config.get('capture_system', {}).get('auto_cleanup', {}).get('save_video_segments', False)
            if self.debug_mode and save_videos:
                self._save_video_segment_for_inspection(video_segment)
            
            # Analyze video segment
            analysis = self.video_analyzer.analyze_video_segment(video_segment)
            self.logger.debug(f"Video analysis: {analysis['segment_info']['frame_count']} frames, {analysis['segment_info']['duration']:.2f}s")
            
            # Get recommended frames for LLM analysis
            recommended_frames = analysis.get('recommended_frames', [])
            if not recommended_frames:
                self.logger.warning("No frames recommended from video analysis")
                return self.process_screenshot()  # Fallback to screenshot
            
            # For 24 FPS GIF creation, use ALL available frames, not just keyframes
            all_frames = video_segment.frames
            segment_duration = analysis['segment_info']['duration']
            
            # Create GIF from all frames if we have multiple frames
            if len(all_frames) > 1:
                # Sample frames to achieve approximately 24 FPS for the GIF
                target_gif_fps = 24
                target_frame_count = max(int(segment_duration * target_gif_fps), len(all_frames))
                
                # If we have more frames than needed, subsample evenly
                if len(all_frames) > target_frame_count:
                    step = len(all_frames) / target_frame_count
                    selected_indices = [int(i * step) for i in range(target_frame_count)]
                    selected_frames = [all_frames[i] for i in selected_indices]
                else:
                    # Use all frames if we have fewer than target
                    selected_frames = all_frames
                
                # Enhance all selected frames for GIF
                enhanced_images = []
                for frame in selected_frames:
                    enhanced_frame = self.capture_system.enhance_frame(frame)
                    enhanced_images.append(enhanced_frame.image)
                
                gif_image = self._create_gif_from_frames(enhanced_images, total_duration=segment_duration)
                if gif_image:
                    # Use the GIF as primary content
                    images = [gif_image]
                    frame_descriptions = [f"Animated GIF: {len(selected_frames)} frames over {segment_duration:.1f}s"]
                    self.logger.debug(f"🎬 Created animated GIF from {len(selected_frames)} frames (target {target_gif_fps} FPS)")
                else:
                    # Fallback to keyframes if GIF creation failed
                    images = []
                    frame_descriptions = []
                    for recommendation in recommended_frames[:3]:
                        frame = recommendation['frame']
                        reason = recommendation['reason']
                        enhanced_frame = self.capture_system.enhance_frame(frame)
                        images.append(enhanced_frame.image)
                        frame_descriptions.append(f"{reason} (t={frame.timestamp - video_segment.start_time:.2f}s)")
            else:
                # Single frame case - use keyframe analysis
                images = []
                frame_descriptions = []
                for recommendation in recommended_frames[:3]:
                    frame = recommendation['frame']
                    reason = recommendation['reason']
                    enhanced_frame = self.capture_system.enhance_frame(frame)
                    images.append(enhanced_frame.image)
                    frame_descriptions.append(f"{reason} (t={frame.timestamp - video_segment.start_time:.2f}s)")
            
            # Update knowledge system
            current_map = self.game_engine.get_map_name(self.current_game_state.map_id)
            self.knowledge_system.update_location(self.current_game_state, current_map)
            
            # Build context with video information
            context = self._build_prompt_context()
            context['video_analysis'] = self._format_video_context(analysis, frame_descriptions)
            
            # Format prompt
            prompt = self.prompt_template.format_template(
                self.current_game_state,
                **context
            )
            
            # Call LLM with video frames
            tools = self.prompt_template.get_available_tools()
            tool_objects = [Tool(t['name'], t['description'], t['parameters']) for t in tools]
            
            # Log what we're sending to the AI
            if len(images) == 1 and "Animated GIF" in frame_descriptions[0]:
                self.logger.info(f"🎬 Sending animated GIF from {action_duration}s video sequence to AI for analysis")
            else:
                self.logger.info(f"🎥 Sending {len(images)} video frames from {action_duration}s sequence to AI for analysis")
            
            for i, desc in enumerate(frame_descriptions):
                self.logger.debug(f"   Content {i+1}: {desc}")
            
            # Save frames sent to AI for inspection if debug mode is enabled
            save_ai_frames = self.config.get('capture_system', {}).get('auto_cleanup', {}).get('save_ai_frames', True)
            if self.debug_mode and save_ai_frames:
                self._save_ai_frames_for_inspection(images, frame_descriptions, action_duration)
            
            try:
                response, tool_calls, text = self.llm_client.call_with_tools(
                    message=prompt,
                    tools=tool_objects,
                    images=images
                )
            except Exception as llm_error:
                # If LLM call fails (e.g., MALFORMED_FUNCTION_CALL with GIF), try with fallback frames
                error_msg = str(llm_error)
                if ("MALFORMED_FUNCTION_CALL" in error_msg or "finish_reason" in error_msg) and len(all_frames) > 1:
                    self.logger.warning(f"LLM call failed with GIF, trying with static frames: {error_msg}")
                    
                    # Use first and last frames as static images instead of GIF
                    fallback_images = []
                    fallback_descriptions = []
                    
                    # First frame
                    first_frame = self.capture_system.enhance_frame(all_frames[0])
                    fallback_images.append(first_frame.image)
                    fallback_descriptions.append(f"Initial state (t=0.0s)")
                    
                    # Last frame if different
                    if len(all_frames) > 1:
                        last_frame = self.capture_system.enhance_frame(all_frames[-1])
                        fallback_images.append(last_frame.image)
                        fallback_descriptions.append(f"Final state (t={segment_duration:.1f}s)")
                    
                    # Update images and descriptions for fallback
                    images = fallback_images
                    frame_descriptions = fallback_descriptions
                    
                    self.logger.debug(f"Using fallback static frames: {len(images)} frames")
                    
                    # Re-save for inspection with fallback frames
                    if self.debug_mode and save_ai_frames:
                        self._save_ai_frames_for_inspection(images, frame_descriptions, action_duration)
                    
                    response, tool_calls, text = self.llm_client.call_with_tools(
                        message=prompt,
                        tools=tool_objects,
                        images=images
                    )
                    self.logger.ai_decision(f"AI decision (fallback): {text}")
                else:
                    # Re-raise if it's not a GIF-related issue or we can't fallback
                    raise
            
            self.logger.ai_response(text)
            
            # Process tool calls
            return self._process_tool_calls(tool_calls, text)
            
        except Exception as e:
            self.logger.error(f"Error processing video sequence: {e}")
            if self.debug_mode:
                import traceback
                self.logger.debug(traceback.format_exc())
            # Fallback to screenshot processing
            return self.process_screenshot()
        finally:
            self.is_processing = False
    
    def _save_video_segment_for_inspection(self, video_segment):
        """Save video segment frames for inspection (debug mode only)."""
        try:
            import os
            import time
            
            # Create inspection directory
            inspection_dir = os.path.join(os.path.dirname(self.video_path), 'inspection')
            os.makedirs(inspection_dir, exist_ok=True)
            
            # Create timestamped folder for this video segment
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            segment_dir = os.path.join(inspection_dir, f"video_segment_{timestamp}")
            os.makedirs(segment_dir, exist_ok=True)
            
            # Save individual frames
            frame_count = 0
            for frame in video_segment.frames:
                frame_path = os.path.join(segment_dir, f"frame_{frame_count:03d}_{frame.timestamp:.2f}s.png")
                frame.image.save(frame_path)
                frame_count += 1
            
            # Save metadata
            metadata_path = os.path.join(segment_dir, "metadata.txt")
            with open(metadata_path, 'w') as f:
                f.write(f"Video Segment Metadata\n")
                f.write(f"======================\n")
                f.write(f"Start Time: {video_segment.start_time}\n")
                f.write(f"End Time: {video_segment.end_time}\n")
                f.write(f"Duration: {video_segment.end_time - video_segment.start_time:.2f}s\n")
                f.write(f"Frame Count: {len(video_segment.frames)}\n")
                f.write(f"FPS: {len(video_segment.frames) / (video_segment.end_time - video_segment.start_time):.1f}\n")
                f.write(f"\nFrame Details:\n")
                for i, frame in enumerate(video_segment.frames):
                    f.write(f"Frame {i:03d}: {frame.timestamp:.2f}s - Size: {frame.image.size}\n")
            
            self.logger.success(f"💾 Saved {frame_count} frames to {segment_dir}")
            
            # Clean up old captures to prevent disk space growth
            cleanup_config = self.config.get('capture_system', {}).get('auto_cleanup', {})
            if cleanup_config.get('enabled', True):
                keep_recent = cleanup_config.get('keep_recent_captures', 3)
                self._cleanup_old_captures(keep_recent=keep_recent)
            
        except Exception as e:
            self.logger.error(f"Failed to save video segment for inspection: {e}")
    
    def _cleanup_old_captures(self, keep_recent: int = 3):
        """Clean up old video captures and AI frames to prevent disk space growth."""
        try:
            import shutil
            import glob
            
            base_videos_dir = os.path.dirname(self.video_path)
            
            # Clean up video segments
            inspection_dir = os.path.join(base_videos_dir, 'inspection')
            if os.path.exists(inspection_dir):
                segments = []
                for item in os.listdir(inspection_dir):
                    item_path = os.path.join(inspection_dir, item)
                    if os.path.isdir(item_path) and item.startswith("video_segment_"):
                        segments.append((item, item_path, os.path.getctime(item_path)))
                
                # Sort by creation time (newest first) and remove old ones
                segments.sort(key=lambda x: x[2], reverse=True)
                for i, (name, path, _) in enumerate(segments):
                    if i >= keep_recent:
                        shutil.rmtree(path)
                        self.logger.debug(f"🗑️ Removed old video segment: {name}")
            
            # Clean up AI frames
            ai_frames_dir = os.path.join(base_videos_dir, 'ai_frames')
            if os.path.exists(ai_frames_dir):
                requests = []
                for item in os.listdir(ai_frames_dir):
                    item_path = os.path.join(ai_frames_dir, item)
                    if os.path.isdir(item_path) and item.startswith("ai_request_"):
                        requests.append((item, item_path, os.path.getctime(item_path)))
                
                # Sort by creation time (newest first) and remove old ones
                requests.sort(key=lambda x: x[2], reverse=True)
                for i, (name, path, _) in enumerate(requests):
                    if i >= keep_recent:
                        shutil.rmtree(path)
                        self.logger.debug(f"🗑️ Removed old AI request: {name}")
                        
        except Exception as e:
            self.logger.error(f"Failed to cleanup old captures: {e}")
    
    def _save_ai_frames_for_inspection(self, images: List[PIL.Image.Image], frame_descriptions: List[str], duration: float):
        """Save frames sent to AI for inspection (debug mode only)."""
        try:
            import os
            import time
            
            # Create AI frames directory
            ai_frames_dir = os.path.join(os.path.dirname(self.video_path), 'ai_frames')
            os.makedirs(ai_frames_dir, exist_ok=True)
            
            # Create timestamped folder for this AI request
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            ai_request_dir = os.path.join(ai_frames_dir, f"ai_request_{timestamp}")
            os.makedirs(ai_request_dir, exist_ok=True)
            
            # Save frames sent to AI
            for i, (image, description) in enumerate(zip(images, frame_descriptions)):
                # Create safe filename from description
                safe_desc = description.replace(" ", "_").replace("(", "").replace(")", "").replace("=", "").replace(".", "").replace(":", "")
                
                # Check if this is a GIF
                if "Animated GIF" in description:
                    frame_path = os.path.join(ai_request_dir, f"ai_content_{i+1:02d}_{safe_desc}.gif")
                    # Save as GIF
                    image.save(frame_path, format='GIF', save_all=True)
                else:
                    frame_path = os.path.join(ai_request_dir, f"ai_frame_{i+1:02d}_{safe_desc}.png")
                    image.save(frame_path)
            
            # Save metadata
            metadata_path = os.path.join(ai_request_dir, "ai_request_metadata.txt")
            with open(metadata_path, 'w') as f:
                f.write(f"AI Request Metadata\n")
                f.write(f"==================\n")
                f.write(f"Duration: {duration:.2f}s\n")
                f.write(f"Frames Sent: {len(images)}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"\nFrame Details:\n")
                for i, description in enumerate(frame_descriptions):
                    f.write(f"Frame {i+1:02d}: {description}\n")
            
            self.logger.success(f"🤖 Saved {len(images)} AI frames to {ai_request_dir}")
            
            # Clean up old captures to prevent disk space growth
            cleanup_config = self.config.get('capture_system', {}).get('auto_cleanup', {})
            if cleanup_config.get('enabled', True):
                keep_recent = cleanup_config.get('keep_recent_captures', 3)
                self._cleanup_old_captures(keep_recent=keep_recent)
            
        except Exception as e:
            self.logger.error(f"Failed to save AI frames for inspection: {e}")
    
    def _format_video_context(self, analysis: Dict[str, Any], frame_descriptions: List[str]) -> str:
        """Format video analysis results for prompt context."""
        segment_info = analysis.get('segment_info', {})
        motion_analysis = analysis.get('motion_analysis', {})
        
        context = f"\n## Video Analysis Results\n"
        context += f"- Duration: {segment_info.get('duration', 0):.2f} seconds\n"
        context += f"- Frame count: {segment_info.get('frame_count', 0)}\n"
        context += f"- Motion detected: {'Yes' if motion_analysis.get('motion_detected', False) else 'No'}\n"
        
        if frame_descriptions:
            context += f"- Frames being analyzed: {', '.join(frame_descriptions)}\n"
        
        content_changes = analysis.get('content_changes', [])
        if content_changes:
            change_times = [f"{c.get('relative_time', 0):.1f}s" for c in content_changes[:3]]
            context += f"- Content changes detected at: {', '.join(change_times)}\n"
        
        context += "\n**Instructions**: The images show the sequence of events during your action. Compare them to understand what happened and decide your next move.\n"
        
        return context
    
    def _enhance_image(self, image: PIL.Image.Image) -> PIL.Image.Image:
        """Enhance image for better LLM processing."""
        # Scale the image to 3x its original size for better detail recognition
        scale_factor = 3
        scaled_width = image.width * scale_factor
        scaled_height = image.height * scale_factor
        scaled_image = image.resize((scaled_width, scaled_height), PIL.Image.LANCZOS)
        
        # Enhance contrast, saturation, and brightness
        from PIL import ImageEnhance
        
        contrast_enhancer = ImageEnhance.Contrast(scaled_image)
        contrast_image = contrast_enhancer.enhance(1.5)  # Increase contrast by 50%
        
        saturation_enhancer = ImageEnhance.Color(contrast_image)
        enhanced_image = saturation_enhancer.enhance(1.8)  # Increase saturation by 80%
        
        brightness_enhancer = ImageEnhance.Brightness(enhanced_image)
        final_image = brightness_enhancer.enhance(1.1)  # Increase brightness by 10%
        
        return final_image
    
    def _build_prompt_context(self) -> Dict[str, str]:
        """Build context dictionary for prompt formatting."""
        current_map = self.game_engine.get_map_name(self.current_game_state.map_id)
        
        context = {
            'current_map': current_map,
            'player_x': str(self.current_game_state.player_x),
            'player_y': str(self.current_game_state.player_y),
            'player_direction': self.current_game_state.player_direction,
            'recent_actions': self._get_recent_actions_text(),
            'direction_guidance': self.game_engine.get_navigation_guidance(self.current_game_state),
            'notepad_content': self._read_notepad(),
        }
        
        # Add knowledge system context
        context['knowledge_context'] = self.knowledge_system.generate_context_summary()
        context['location_context'] = self.knowledge_system.get_location_context(self.current_game_state.map_id)
        context['navigation_advice'] = self.knowledge_system.get_navigation_advice(self.current_game_state.map_id)
        
        # Add conversation context (HIGH PRIORITY)
        conversation_context = self.knowledge_system.get_conversation_context()
        if conversation_context:
            context['conversation_context'] = conversation_context
        
        # Add character identity context (HIGH PRIORITY)
        character_context = self.knowledge_system.get_character_context()
        if character_context:
            context['character_context'] = character_context
        
        # Add game phase guidance
        phase_guidance = self.knowledge_system.get_game_phase_guidance()
        if phase_guidance:
            context['game_phase_guidance'] = phase_guidance
        
        # Add context memory buffer (HIGH PRIORITY)
        memory_context = self.knowledge_system.get_relevant_context_memory(max_entries=8)
        if memory_context:
            context['memory_context'] = memory_context
        
        # Add conversation flow context (MEDIUM PRIORITY)
        flow_context = self.knowledge_system.get_conversation_flow_context()
        if flow_context:
            context['conversation_flow_context'] = flow_context
        
        # Add dialogue memory context (MEDIUM PRIORITY)
        dialogue_memory = self.knowledge_system.get_dialogue_memory_context()
        if dialogue_memory:
            context['dialogue_memory_context'] = dialogue_memory
        
        # Add tutorial progress context (MEDIUM PRIORITY)
        if self.knowledge_system.character_state.game_phase == "tutorial":
            # Initialize tutorial system if needed
            if not hasattr(self.knowledge_system, 'tutorial_steps'):
                self.knowledge_system.initialize_tutorial_system()
            
            tutorial_guidance = self.knowledge_system.get_current_tutorial_guidance()
            if tutorial_guidance:
                context['tutorial_guidance'] = tutorial_guidance
                
            tutorial_summary = self.knowledge_system.get_tutorial_progress_summary()
            if tutorial_summary:
                context['tutorial_progress'] = tutorial_summary
                
            next_steps = self.knowledge_system.get_next_tutorial_steps_preview(2)
            if next_steps:
                context['tutorial_preview'] = next_steps
        
        # Enhanced prompt formatting
        context = self._enhance_prompt_formatting(context)
        
        return context
    
    def _get_recent_actions_text(self) -> str:
        """Get formatted text of recent actions."""
        if not self.recent_actions:
            return "No recent actions."
        
        text = "## Short-term Memory (Recent Actions):\n"
        for i, (timestamp, buttons, reasoning, game_state) in enumerate(self.recent_actions, 1):
            map_name = self.game_engine.get_map_name(game_state.map_id)
            text += f"{i}. [{timestamp}] Pressed {buttons} at {map_name} ({game_state.player_x}, {game_state.player_y})\n"
            text += f"   Reasoning: {reasoning.strip()}\n\n"
        return text
    
    def _read_notepad(self) -> str:
        """Read notepad content."""
        try:
            if os.path.exists(self.notepad_path):
                with open(self.notepad_path, 'r') as f:
                    return f.read()
        except Exception as e:
            self.logger.error(f"Error reading notepad: {e}")
        return "No notepad content available."
    
    def _enhance_prompt_formatting(self, context: Dict[str, str]) -> Dict[str, str]:
        """Enhance context formatting for optimal LLM comprehension."""
        enhanced_context = context.copy()
        
        # Format character context with urgency if conversation active
        if 'character_context' in enhanced_context:
            char_context = enhanced_context['character_context']
            
            # Add conversation urgency if talking to someone
            if 'conversation_context' in enhanced_context and enhanced_context['conversation_context']:
                char_context = f"🔥 **ACTIVE CONVERSATION** 🔥\n{char_context}"
            
            enhanced_context['character_context'] = char_context
        
        # Format conversation context with high visibility
        if 'conversation_context' in enhanced_context and enhanced_context['conversation_context']:
            conv_context = enhanced_context['conversation_context']
            enhanced_context['conversation_context'] = f"🗣️ **CONVERSATION IN PROGRESS**\n{conv_context}\n⚠️ **Remember: Stay consistent with who you're talking to!**"
        
        # Format memory context with priority indicators
        if 'memory_context' in enhanced_context and enhanced_context['memory_context']:
            memory_context = enhanced_context['memory_context']
            enhanced_context['memory_context'] = f"🧠 **RECENT MEMORY & CONTEXT**\n{memory_context}"
        
        # Format game phase guidance with appropriate urgency
        if 'game_phase_guidance' in enhanced_context and enhanced_context['game_phase_guidance']:
            phase_guidance = enhanced_context['game_phase_guidance']
            enhanced_context['game_phase_guidance'] = f"📚 **CURRENT GAME PHASE**\n{phase_guidance}"
        
        # Add critical context summary at the top level
        critical_summary = self._generate_critical_context_summary(enhanced_context)
        if critical_summary:
            enhanced_context['critical_summary'] = critical_summary
        
        return enhanced_context
    
    def _generate_critical_context_summary(self, context: Dict[str, str]) -> str:
        """Generate a critical context summary for immediate awareness."""
        summary_parts = []
        
        # Character identity reminder
        if hasattr(self.knowledge_system, 'character_state'):
            char_state = self.knowledge_system.character_state
            summary_parts.append(f"🎭 You are: **{char_state.name}**")
            
            if char_state.current_objective:
                summary_parts.append(f"🎯 Current Goal: **{char_state.current_objective}**")
        
        # Active conversation reminder
        if hasattr(self.knowledge_system, 'conversation_state') and self.knowledge_system.conversation_state.current_npc:
            conv_state = self.knowledge_system.conversation_state
            summary_parts.append(f"💬 Currently talking to: **{conv_state.current_npc}** ({conv_state.npc_role})")
            
            if conv_state.conversation_topic:
                summary_parts.append(f"📝 About: **{conv_state.conversation_topic}**")
        
        # Location reminder
        current_map = self.game_engine.get_map_name(self.current_game_state.map_id)
        summary_parts.append(f"📍 Location: **{current_map}**")
        
        if summary_parts:
            return "🚨 **IMMEDIATE CONTEXT SUMMARY**\n" + "\n".join(f"   {part}" for part in summary_parts)
        
        return ""
    
    def _process_tool_calls(self, tool_calls: List[ToolCall], response_text: str) -> Optional[Dict[str, Any]]:
        """Process tool calls from LLM response."""
        button_decision = None
        
        for call in tool_calls:
            if call.name == "press_button":
                button_decision = self._handle_press_button(call, response_text)
            elif call.name == "update_notepad":
                self._handle_update_notepad(call)
            else:
                # Let game-specific controller handle other tools
                self._handle_game_specific_tool_call(call)
        
        return button_decision
    
    def _handle_press_button(self, call: ToolCall, response_text: str) -> Dict[str, Any]:
        """Handle press_button tool call."""
        buttons = call.arguments.get("buttons", [])
        durations = call.arguments.get("durations", [])
        
        if not buttons:
            return None
        
        # Validate buttons using game engine
        valid_buttons = self.game_engine.validate_button_sequence(buttons)
        button_codes = self.game_engine.convert_buttons_to_codes(valid_buttons)
        
        # Handle durations
        button_durations = []
        for i, button in enumerate(valid_buttons):
            if durations and i < len(durations):
                try:
                    duration = max(1, min(180, int(float(durations[i]))))
                    button_durations.append(duration)
                except (ValueError, TypeError):
                    button_durations.append(2)  # Default
            else:
                button_durations.append(2)  # Default
        
        if button_codes:
            buttons_str = ", ".join(valid_buttons)
            self.logger.ai_action(f"Pressing buttons: {buttons_str}")
            
            # Calculate total action duration for video recording
            action_duration = self._calculate_action_duration(button_codes, button_durations)
            
            # Store action timing for video capture
            self.last_action_time = time.time()
            self.pending_action_duration = action_duration
            
            # Note: Video recording will be started by the next state request automatically
            # We just store the timing information here
            
            # Record action
            timestamp = time.strftime("%H:%M:%S")
            self.recent_actions.append((
                timestamp, buttons_str, response_text, 
                GameState(
                    player_x=self.current_game_state.player_x,
                    player_y=self.current_game_state.player_y,
                    player_direction=self.current_game_state.player_direction,
                    map_id=self.current_game_state.map_id
                )
            ))
            
            # Record in knowledge system
            self.knowledge_system.record_action(
                action=buttons_str,
                result=response_text[:200],
                location=self.current_game_state.map_id,
                success=True
            )
            
            return {'buttons': button_codes, 'durations': button_durations}
        
        return None
    
    def _handle_update_notepad(self, call: ToolCall):
        """Handle update_notepad tool call."""
        content = call.arguments.get("content", "")
        if content:
            self._update_notepad(content)
            self.logger.notepad(content)
    
    def _update_notepad(self, content: str):
        """Update the notepad file."""
        try:
            current_content = self._read_notepad()
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            updated_content = current_content + f"\n## Update {timestamp}\n{content}\n"
            
            with open(self.notepad_path, 'w') as f:
                f.write(updated_content)
            
            # Summarize if too long
            if len(updated_content) > 10000:
                self._summarize_notepad()
                
        except Exception as e:
            self.logger.error(f"Error updating notepad: {e}")
    
    def _summarize_notepad(self):
        """Summarize notepad when it gets too long."""
        # This would use the LLM to summarize the notepad content
        # Implementation depends on specific LLM client
        pass
    
    def _calculate_action_duration(self, button_codes: List[int], button_durations: List[int]) -> float:
        """Calculate total duration for button sequence in seconds."""
        if not button_codes:
            return 0.0
        
        # Constants from Lua script (at 60 FPS)
        DEFAULT_BUTTON_FRAMES = 2
        SEPARATION_FRAMES = 58  # Wait between buttons
        POST_SEQUENCE_WAIT_FRAMES = 60  # Wait after last button
        FPS = 60.0
        
        total_frames = 0
        
        # Calculate duration for each button
        for i, button_code in enumerate(button_codes):
            # Button press duration
            if i < len(button_durations):
                button_frame_duration = button_durations[i]
            else:
                button_frame_duration = DEFAULT_BUTTON_FRAMES
            
            total_frames += button_frame_duration
            
            # Add separation time (except for last button)
            if i < len(button_codes) - 1:
                total_frames += SEPARATION_FRAMES
        
        # Add post-sequence wait
        total_frames += POST_SEQUENCE_WAIT_FRAMES
        
        # Convert frames to seconds
        duration_seconds = total_frames / FPS
        
        self.logger.debug(f"🕐 Calculated action duration: {len(button_codes)} buttons = {total_frames} frames = {duration_seconds:.2f}s")
        
        return duration_seconds
    
    def _create_gif_from_frames(self, images: List[PIL.Image.Image], total_duration: float = 1.0) -> PIL.Image.Image:
        """Create an animated GIF from a list of images with 24 FPS target."""
        if not images:
            return None
        
        if len(images) == 1:
            return images[0]  # Single frame, return as-is
        
        # Resize images for efficiency but keep good quality (max 800px width for 24fps)
        max_width = 800
        processed_images = []
        
        for img in images:
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), PIL.Image.LANCZOS)
            processed_images.append(img)
        
        # Calculate frame duration to match the actual recorded duration
        # This ensures the GIF plays back at the same speed as the original recording
        duration_per_frame_ms = int((total_duration * 1000) / len(processed_images))
        
        # Ensure reasonable bounds for GIF playback
        min_duration_ms = 42   # 24 FPS maximum
        max_duration_ms = 500  # 2 FPS minimum (for very slow actions)
        
        # Use the calculated duration but clamp to reasonable bounds
        duration_ms = max(min_duration_ms, min(max_duration_ms, duration_per_frame_ms))
        
        # If the calculated duration is very different from actual, log it
        actual_total_duration = (duration_ms * len(processed_images)) / 1000.0
        if abs(actual_total_duration - total_duration) > 0.5:  # More than 0.5s difference
            self.logger.debug(f"⚠️ GIF duration adjusted: {total_duration:.2f}s → {actual_total_duration:.2f}s (due to frame rate limits)")
        
        # Create a new image that will hold the GIF data
        gif_image = processed_images[0]
        
        # Save as animated GIF in memory with better quality
        import io
        gif_buffer = io.BytesIO()
        gif_image.save(
            gif_buffer,
            format='GIF',
            save_all=True,
            append_images=processed_images[1:],
            duration=duration_ms,
            loop=0,
            optimize=True,
            disposal=2  # Clear frame before next one for smoother animation
        )
        gif_buffer.seek(0)
        
        # Load the GIF back as PIL Image for consistency
        gif_result = PIL.Image.open(gif_buffer)
        
        actual_fps = 1000 / duration_ms
        actual_total_duration = (duration_ms * len(processed_images)) / 1000.0
        self.logger.debug(f"🎬 Created GIF: {len(processed_images)} frames, {duration_ms}ms per frame ({actual_fps:.1f} FPS), total duration: {actual_total_duration:.2f}s")
        
        return gif_result
    
    def process_video_segment(self, video_segment, thinking_segment=None):
        """Process a video segment directly (for actions that were already recorded)."""
        if not video_segment or not video_segment.frames:
            self.logger.warning("No video segment to process")
            return None
        
        # Combine thinking and action segments if both are available
        if thinking_segment and thinking_segment.frames:
            self.logger.debug(f"🎬 Processing combined video: thinking ({thinking_segment.duration:.2f}s) + action ({video_segment.duration:.2f}s)")
            combined_frames = thinking_segment.frames + video_segment.frames
            combined_duration = thinking_segment.duration + video_segment.duration
            
            # Create a new combined video segment
            from .base_capture_system import VideoSegment
            video_segment = VideoSegment(
                frames=combined_frames,
                start_time=thinking_segment.start_time,
                end_time=video_segment.end_time,
                duration=combined_duration,
                metadata={
                    'type': 'combined',
                    'thinking_duration': thinking_segment.duration,
                    'action_duration': video_segment.duration,
                    'thinking_frames': len(thinking_segment.frames),
                    'action_frames': len(video_segment.frames)
                }
            )
        
        self.logger.debug(f"🎬 Processing video segment: {len(video_segment.frames)} frames, {video_segment.duration:.2f}s")
        
        # Analyze video segment
        analysis = self.video_analyzer.analyze_video_segment(video_segment)
        self.logger.debug(f"Video analysis: {analysis['segment_info']['frame_count']} frames, {analysis['segment_info']['duration']:.2f}s")
        
        # Get recommended frames for LLM analysis
        recommended_frames = analysis.get('recommended_frames', [])
        if not recommended_frames:
            self.logger.warning("No frames recommended from video analysis")
            return self.process_screenshot()  # Fallback to screenshot
        
        # For 24 FPS GIF creation, use ALL available frames, not just keyframes
        all_frames = video_segment.frames
        segment_duration = analysis['segment_info']['duration']
        
        # Create GIF from all frames if we have multiple frames
        if len(all_frames) > 1:
            # Sample frames to achieve approximately 24 FPS for the GIF
            target_gif_fps = 24
            target_frame_count = max(int(segment_duration * target_gif_fps), len(all_frames))
            
            # If we have more frames than needed, subsample evenly
            if len(all_frames) > target_frame_count:
                step = len(all_frames) / target_frame_count
                selected_indices = [int(i * step) for i in range(target_frame_count)]
                selected_frames = [all_frames[i] for i in selected_indices]
            else:
                # Use all frames if we have fewer than target
                selected_frames = all_frames
            
            # Enhance all selected frames for GIF
            enhanced_images = []
            for frame in selected_frames:
                enhanced_frame = self.capture_system.enhance_frame(frame)
                enhanced_images.append(enhanced_frame.image)
            
            gif_image = self._create_gif_from_frames(enhanced_images, total_duration=segment_duration)
            if gif_image:
                # Use the GIF as primary content
                images = [gif_image]
                
                # Create descriptive frame description based on video type
                if hasattr(video_segment, 'metadata') and video_segment.metadata.get('type') == 'combined':
                    thinking_duration = video_segment.metadata.get('thinking_duration', 0)
                    action_duration = video_segment.metadata.get('action_duration', 0)
                    thinking_frames = video_segment.metadata.get('thinking_frames', 0)
                    action_frames = video_segment.metadata.get('action_frames', 0)
                    frame_descriptions = [f"Combined video: {thinking_frames} thinking frames ({thinking_duration:.1f}s) + {action_frames} action frames ({action_duration:.1f}s) = {len(selected_frames)} total frames over {segment_duration:.1f}s"]
                else:
                    frame_descriptions = [f"Action video: {len(selected_frames)} frames over {segment_duration:.1f}s"]
                
                self.logger.debug(f"🎬 Created animated GIF from {len(selected_frames)} frames (target {target_gif_fps} FPS)")
            else:
                # Fallback to keyframes if GIF creation failed
                images = []
                frame_descriptions = []
                for recommendation in recommended_frames[:3]:
                    frame = recommendation['frame']
                    reason = recommendation['reason']
                    enhanced_frame = self.capture_system.enhance_frame(frame)
                    images.append(enhanced_frame.image)
                    frame_descriptions.append(f"{reason} (t={frame.timestamp - video_segment.start_time:.2f}s)")
        else:
            # Single frame case - use keyframe analysis
            images = []
            frame_descriptions = []
            for recommendation in recommended_frames[:3]:
                frame = recommendation['frame']
                reason = recommendation['reason']
                enhanced_frame = self.capture_system.enhance_frame(frame)
                images.append(enhanced_frame.image)
                frame_descriptions.append(f"{reason} (t={frame.timestamp - video_segment.start_time:.2f}s)")
        
        # Update knowledge system
        current_map = self.game_engine.get_map_name(self.current_game_state.map_id)
        self.knowledge_system.update_location(self.current_game_state, current_map)
        
        # Build context with video information
        context = self._build_prompt_context()
        context['video_analysis'] = self._format_video_context(analysis, frame_descriptions)
        
        # Format prompt
        prompt = self.prompt_template.format_template(
            game_state=self.current_game_state,
            **context
        )
        
        # Create tool objects
        tool_objects = self.prompt_template.create_tool_objects()
        
        for i, desc in enumerate(frame_descriptions):
            self.logger.debug(f"   Content {i+1}: {desc}")
        
        # Save frames sent to AI for inspection if debug mode is enabled
        save_ai_frames = self.config.get('capture_system', {}).get('auto_cleanup', {}).get('save_ai_frames', True)
        action_duration = segment_duration
        if self.debug_mode and save_ai_frames:
            self._save_ai_frames_for_inspection(images, frame_descriptions, action_duration)
        
        try:
            response, tool_calls, text = self.llm_client.call_with_tools(
                message=prompt,
                tools=tool_objects,
                images=images
            )
        except Exception as llm_error:
            # If LLM call fails (e.g., MALFORMED_FUNCTION_CALL with GIF), try with fallback frames
            error_msg = str(llm_error)
            if ("MALFORMED_FUNCTION_CALL" in error_msg or "finish_reason" in error_msg) and len(all_frames) > 1:
                self.logger.warning(f"LLM call failed with GIF, trying with static frames: {error_msg}")
                
                # Use first and last frames as static images instead of GIF
                fallback_images = []
                fallback_descriptions = []
                
                # First frame
                first_frame = self.capture_system.enhance_frame(all_frames[0])
                fallback_images.append(first_frame.image)
                fallback_descriptions.append(f"Initial state (t=0.0s)")
                
                # Last frame if different
                if len(all_frames) > 1:
                    last_frame = self.capture_system.enhance_frame(all_frames[-1])
                    fallback_images.append(last_frame.image)
                    fallback_descriptions.append(f"Final state (t={segment_duration:.1f}s)")
                
                # Update images and descriptions for fallback
                images = fallback_images
                frame_descriptions = fallback_descriptions
                
                self.logger.debug(f"Using fallback static frames: {len(images)} frames")
                
                # Re-save for inspection with fallback frames
                if self.debug_mode and save_ai_frames:
                    self._save_ai_frames_for_inspection(images, frame_descriptions, action_duration)
                
                response, tool_calls, text = self.llm_client.call_with_tools(
                    message=prompt,
                    tools=tool_objects,
                    images=images
                )
                self.logger.ai_decision(f"AI decision (fallback): {text}")
            else:
                # Re-raise if it's not a GIF-related issue or we can't fallback
                raise
        
        self.logger.ai_response(text)
        
        # Process tool calls
        button_codes = None
        button_durations = []
        
        for call in tool_calls:
            if call.name == 'press_button':
                buttons = call.arguments.get('buttons', [])
                durations = call.arguments.get('durations', [])
                
                # Convert button names to codes
                button_codes = self.game_engine.convert_button_names_to_codes(buttons)
                
                # Convert durations to integers if provided
                if durations:
                    try:
                        button_durations = [int(d) for d in durations]
                        # Ensure durations list matches buttons list length
                        while len(button_durations) < len(button_codes):
                            button_durations.append(2)  # Default duration
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid durations provided: {durations}")
                        button_durations = [2] * len(button_codes)  # Use defaults
                else:
                    button_durations = [2] * len(button_codes)  # Default durations
                
                break
            else:
                self._handle_game_specific_tool_call(call)
        
        return {'text': text, 'buttons': button_codes, 'durations': button_durations}
    
    def start_continuous_recording(self):
        """Start continuous recording and return recording ID."""
        if not self.continuous_recording:
            return None
        
        recording_id = self.current_recording_id
        self.current_recording_id += 1
        
        if hasattr(self.capture_system, 'start_recording'):
            success = self.capture_system.start_recording()
            if success:
                self.logger.debug(f"🎬 Started continuous recording #{recording_id} at {self.capture_fps} FPS")
                return recording_id
            else:
                self.logger.warning(f"⚠️ Failed to start recording #{recording_id}")
        return None
    
    def stop_and_queue_recording(self, recording_id):
        """Stop current recording and queue it for processing."""
        if not self.continuous_recording or recording_id is None:
            return None
        
        if hasattr(self.capture_system, 'stop_recording'):
            video_segment = self.capture_system.stop_recording()
            if video_segment:
                self.logger.debug(f"🎬 Stopped recording #{recording_id}: {len(video_segment.frames)} frames, {video_segment.duration:.2f}s")
                
                # Queue for processing
                self.video_queue.put((recording_id, video_segment))
                
                # Immediately start next recording
                next_recording_id = self.start_continuous_recording()
                return next_recording_id
            else:
                self.logger.warning(f"⚠️ No video segment from recording #{recording_id}")
        return None
    
    def process_video_async(self, recording_id):
        """Process a video segment asynchronously and store result."""
        try:
            # Get video from queue
            try:
                queued_id, video_segment = self.video_queue.get_nowait()
            except queue.Empty:
                self.logger.warning(f"No video in queue for recording #{recording_id}")
                return
            
            if queued_id != recording_id:
                self.logger.warning(f"Recording ID mismatch: expected {recording_id}, got {queued_id}")
                # Put it back in queue for correct processing
                self.video_queue.put((queued_id, video_segment))
                return
            
            with self.processing_lock:
                # Create GIF with ALL frames at capture FPS
                gif_image = self._create_all_frames_gif(video_segment)
                
                # Store processed result
                self.processed_videos[recording_id] = {
                    'video_segment': video_segment,
                    'gif_image': gif_image,
                    'frame_count': len(video_segment.frames),
                    'duration': video_segment.duration,
                    'processed_at': time.time()
                }
                
                self.logger.debug(f"📊 Processed recording #{recording_id}: {len(video_segment.frames)} frames → GIF")
                
        except Exception as e:
            self.logger.error(f"Error processing recording #{recording_id}: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def get_processed_video(self, recording_id):
        """Get processed video result by ID."""
        return self.processed_videos.get(recording_id)
    
    def cleanup_processed_video(self, recording_id):
        """Remove processed video from memory."""
        if recording_id in self.processed_videos:
            del self.processed_videos[recording_id]
    
    def _create_all_frames_gif(self, video_segment) -> PIL.Image.Image:
        """Create GIF using ALL frames at the original capture FPS."""
        if not video_segment or not video_segment.frames:
            return None
        
        frames = video_segment.frames
        if len(frames) == 1:
            enhanced_frame = self.capture_system.enhance_frame(frames[0])
            return enhanced_frame.image
        
        # Enhance all frames
        enhanced_images = []
        for frame in frames:
            enhanced_frame = self.capture_system.enhance_frame(frame)
            enhanced_images.append(enhanced_frame.image)
        
        # Use original capture FPS for GIF playback
        frame_duration_ms = int(1000 / self.capture_fps)  # e.g., 33ms for 30 FPS
        
        # Resize for efficiency but maintain quality
        max_width = 800
        processed_images = []
        for img in enhanced_images:
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), PIL.Image.LANCZOS)
            processed_images.append(img)
        
        # Create animated GIF
        import io
        gif_buffer = io.BytesIO()
        processed_images[0].save(
            gif_buffer,
            format='GIF',
            save_all=True,
            append_images=processed_images[1:],
            duration=frame_duration_ms,
            loop=0,
            optimize=True,
            disposal=2
        )
        gif_buffer.seek(0)
        
        gif_result = PIL.Image.open(gif_buffer)
        
        actual_duration = (frame_duration_ms * len(processed_images)) / 1000.0
        self.logger.debug(f"🎬 Created {self.capture_fps} FPS GIF: {len(processed_images)} frames, {frame_duration_ms}ms per frame, {actual_duration:.2f}s total")
        
        return gif_result
    
    @abstractmethod
    def _handle_game_specific_tool_call(self, call: ToolCall):
        """Handle game-specific tool calls."""
        pass
    
    @abstractmethod
    def handle_client(self, client_socket, client_address):
        """Handle communication with emulator client."""
        pass
    
    def start(self):
        """Start the controller server."""
        self.logger.header(f"Starting {self.game_engine.__class__.__name__} Controller")
        
        # Track connection state to reduce repetitive messages
        waiting_logged = False
        
        try:
            while self.running:
                try:
                    if not waiting_logged:
                        self.logger.section("Waiting for emulator connection...")
                        waiting_logged = True
                    
                    client_socket, client_address = self.server_socket.accept()
                    waiting_logged = False  # Reset for next connection
                    
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    
                    try:
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
                    except (AttributeError, OSError):
                        pass
                    
                    client_socket.setblocking(0)
                    client_thread = threading.Thread(
                        target=self._handle_client_connection,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    self.client_threads.append(client_thread)
                    
                except socket.timeout:
                    continue
                except KeyboardInterrupt:
                    self.logger.warning("Keyboard interrupt detected. Shutting down...")
                    break
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error in main loop: {e}")
                        if self.debug_mode:
                            import traceback
                            self.logger.debug(traceback.format_exc())
                        time.sleep(1)
        finally:
            self.running = False
            self.logger.section("Closing all client connections...")
            for t in self.client_threads:
                try:
                    t.join(timeout=1)
                except:
                    pass
            self.cleanup()
            self.logger.success("Server shut down cleanly")
    
    def _handle_client_connection(self, client_socket, client_address):
        """Wrapper around handle_client with error handling."""
        try:
            self.handle_client(client_socket, client_address)
        except Exception as e:
            self.logger.error(f"Client connection error: {e}")
        finally:
            if client_socket:
                try:
                    client_socket.close()
                except:
                    pass
            if self.current_client == client_socket:
                self.current_client = None