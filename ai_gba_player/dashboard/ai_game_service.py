#!/usr/bin/env python3
"""
Simplified AI Game Service for AI GBA Player.
Single-threaded service that combines socket server + AI decision making.
"""

import threading
import socket
import time
import json
import os
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
import base64
from pathlib import Path

from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Configuration
from .llm_client import LLMClient
from .game_detector import get_game_detector

# Memory service will be imported when Django is ready
MEMORY_SERVICE_AVAILABLE = False
_memory_service_functions = {}


class AIGameService(threading.Thread):
    """Single-threaded service combining socket server + AI decisions"""
    
    def __init__(self):
        super().__init__(daemon=True, name="AIGameService")
        
        # Socket server for mGBA communication
        self.socket = None
        self.client_socket = None
        self.running = False
        
        # Configuration
        self.config = None
        self.host = "127.0.0.1"
        self.port = 8888
        
        # WebSocket channel layer for frontend updates
        self.channel_layer = get_channel_layer()
        
        # State tracking
        self.mgba_connected = False
        self.last_screenshot = None
        self.decision_count = 0
        
        # Screenshot tracking with sorted map and storage optimization
        self.screenshot_map = {}  # {filename: creation_time}
        self.max_screenshots = 10  # Keep only 10 most recent screenshots
        self.screenshot_dir = Path("/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/screenshots")
        self.current_screenshot_path = None
        self._initialize_screenshot_tracking()
        
        # Message buffering for handling partial messages
        self.message_buffer = ""
        
        # Chat message storage (simple in-memory for now)
        self.chat_messages = []
        self.max_messages = 500  # Keep last 500 messages for longer history
        self.message_counter = 0  # Track total messages sent
        
        # LLM client
        self.llm_client = None
        
        # Game detection
        self.game_detector = get_game_detector()
        self.current_game_id = None
        self.game_config_sent = False
        
        # Memory system
        self.notepad_path = Path("/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/notepad.txt")
        self.recent_actions = []
        self.max_recent_actions = 10
        
        # Memory system (initialize when needed)
        self.memory_system = None
        
        # Screenshot timing configuration (AI service controls timing)
        self.timing_config = self._load_timing_config()
        self._initialize_memory_system()
        
        # Game state tracking
        self.player_direction = "UNKNOWN"
        self.player_x = 0
        self.player_y = 0
        self.map_id = 0
        
        # Enhanced position tracking
        self.position_history = []  # Last 10 positions
        self.movement_patterns = {}  # Track repeated movement attempts
        
        # Dynamic address validation
        self.address_validation_failures = 0
        self.last_valid_data_time = None
        self.recalibration_needed = False
        
        # Initialize notepad
        self._initialize_notepad()
        
        print(f"🎮 AIGameService initialized - will listen on {self.host}:{self.port}")
    
    def _initialize_memory_system(self):
        """Initialize memory system when Django apps are ready"""
        try:
            from django.apps import apps
            if apps.ready:
                from core.memory_service import get_global_memory_system
                self.memory_system = get_global_memory_system()
                if self.memory_system:
                    print("🧠 AI Service: Connected to global memory system")
                else:
                    print("⚠️ AI Service: Global memory system unavailable")
                global MEMORY_SERVICE_AVAILABLE, _memory_service_functions
                MEMORY_SERVICE_AVAILABLE = True
                # Import memory functions
                from core.memory_service import (
                    discover_objective, complete_objective, learn_strategy, get_memory_context
                )
                _memory_service_functions.update({
                    'discover_objective': discover_objective,
                    'complete_objective': complete_objective,
                    'learn_strategy': learn_strategy,
                    'get_memory_context': get_memory_context
                })
            else:
                print("⚠️ AI Service: Django apps not ready yet, memory system unavailable")
        except Exception as e:
            print(f"⚠️ AI Service: Memory system initialization failed: {e}")
            self.memory_system = None
    
    def _initialize_screenshot_tracking(self):
        """Initialize screenshot tracking by scanning existing files"""
        try:
            if not self.screenshot_dir.exists():
                self.screenshot_dir.mkdir(parents=True, exist_ok=True)
                print(f"📁 Created screenshot directory: {self.screenshot_dir}")
                return
            
            # Scan existing screenshot files and build the map
            screenshot_files = list(self.screenshot_dir.glob("screenshot*.png"))
            
            for file_path in screenshot_files:
                try:
                    creation_time = file_path.stat().st_mtime
                    self.screenshot_map[str(file_path)] = creation_time
                except Exception as e:
                    print(f"⚠️ Error reading file stats for {file_path}: {e}")
            
            print(f"📊 Found {len(self.screenshot_map)} existing screenshots")
            
            # Clean up excess screenshots immediately
            self._cleanup_old_screenshots()
            
        except Exception as e:
            print(f"❌ Error initializing screenshot tracking: {e}")
    
    def _cleanup_old_screenshots(self):
        """Remove old screenshots, keeping only the most recent ones"""
        try:
            if len(self.screenshot_map) <= self.max_screenshots:
                return
            
            # Sort by creation time (newest first)
            sorted_screenshots = sorted(
                self.screenshot_map.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Keep only the newest screenshots
            to_keep = sorted_screenshots[:self.max_screenshots]
            to_remove = sorted_screenshots[self.max_screenshots:]
            
            # Remove old files
            for file_path, _ in to_remove:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"🗑️ Removed old screenshot: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"⚠️ Error removing {file_path}: {e}")
            
            # Update the map to only include kept files
            self.screenshot_map = dict(to_keep)
            
            print(f"✅ Screenshot cleanup: kept {len(self.screenshot_map)}, removed {len(to_remove)}")
            
        except Exception as e:
            print(f"❌ Error during screenshot cleanup: {e}")
    
    def _register_new_screenshot(self, screenshot_path: str):
        """Register a new screenshot in the tracking map and clean up if needed"""
        try:
            if os.path.exists(screenshot_path):
                creation_time = os.path.getmtime(screenshot_path)
                self.screenshot_map[screenshot_path] = creation_time
                
                # Update current screenshot
                self.current_screenshot_path = screenshot_path
                
                # Clean up old screenshots if we exceed the limit
                if len(self.screenshot_map) > self.max_screenshots:
                    self._cleanup_old_screenshots()
                
                print(f"📸 Registered: {os.path.basename(screenshot_path)} (total: {len(self.screenshot_map)})")
                
        except Exception as e:
            print(f"❌ Error registering screenshot: {e}")
    
    def _get_latest_screenshots(self) -> tuple[str, str]:
        """Get the two most recent screenshots for before/after comparison"""
        try:
            if len(self.screenshot_map) < 1:
                return None, None
            elif len(self.screenshot_map) == 1:
                # Only one screenshot available - use it for both
                latest_path = list(self.screenshot_map.keys())[0]
                return latest_path, latest_path
            
            # Sort by creation time (newest first)
            sorted_screenshots = sorted(
                self.screenshot_map.items(),
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Get the two most recent
            current_path = sorted_screenshots[0][0]    # Most recent (current)
            previous_path = sorted_screenshots[1][0]   # Second most recent (previous)
            
            print(f"📸 Screenshot pair - Previous: {os.path.basename(previous_path)}, Current: {os.path.basename(current_path)}")
            
            return previous_path, current_path
            
        except Exception as e:
            print(f"❌ Error getting latest screenshots: {e}")
            return None, None
    
    def run(self):
        """Main thread execution - start socket server and handle connections"""
        print("🚀 Starting AI Game Service...")
        self.running = True
        
        try:
            self._setup_socket_server()
            self._send_chat_message("system", "🔗 AI Service started - waiting for mGBA connection...")
            self._accept_connections()
        except Exception as e:
            print(f"❌ AI Game Service error: {e}")
            traceback.print_exc()
            self._send_chat_message("system", f"❌ Service error: {str(e)}")
        finally:
            self._cleanup()
    
    def stop(self):
        """Stop the AI Game Service"""
        print("🛑 Stopping AI Game Service...")
        self.running = False
        self.mgba_connected = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        self._send_chat_message("system", "⏸️ AI Service stopped")
    
    def reset_llm_session(self):
        """Reset the LLM session to clear any conversation history"""
        print("🔄 Resetting LLM session...")
        
        if self.llm_client:
            self.llm_client.reset_session()
            self._send_chat_message("system", "🔄 LLM session reset - starting fresh!")
        else:
            print("⚠️ No LLM client to reset")
            self._send_chat_message("system", "⚠️ No LLM client active to reset")
        
        # Also clear recent actions to start fresh
        self.recent_actions = []
        self.decision_count = 0
        
        print("✅ LLM session reset completed")
    
    def _load_timing_config(self) -> dict:
        """Load timing configuration from Django settings or config file"""
        try:
            # Try to load from Django configuration first (if available)
            try:
                from pathlib import Path
                import json
                
                # Load from the same config file used by the web interface
                config_file = Path('/tmp/ai_gba_player_config.json')
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        
                    return {
                        'base_stabilization': config.get('base_stabilization', 0.5),
                        'movement_multiplier': config.get('movement_multiplier', 0.8),
                        'interaction_multiplier': config.get('interaction_multiplier', 0.6),
                        'menu_multiplier': config.get('menu_multiplier', 0.4),
                        'max_wait_time': config.get('max_wait_time', 10.0)
                    }
            except Exception as e:
                print(f"⚠️ Could not load timing config from file: {e}")
                
        except Exception as e:
            print(f"⚠️ Error loading timing configuration: {e}")
        
        # Fallback to default values
        return {
            'base_stabilization': 0.5,      # Base time for game state to settle
            'movement_multiplier': 0.8,     # Extra seconds per movement action
            'interaction_multiplier': 0.6,  # Extra seconds per interaction  
            'menu_multiplier': 0.4,         # Extra seconds per menu action
            'max_wait_time': 10.0           # Maximum wait time safety cap
        }
    
    def reload_timing_config(self):
        """Reload timing configuration from updated settings"""
        old_config = self.timing_config.copy()
        self.timing_config = self._load_timing_config()
        print(f"⚙️ Timing configuration reloaded: {self.timing_config}")
        
        # Log changes
        for key, new_value in self.timing_config.items():
            if key in old_config and old_config[key] != new_value:
                print(f"   {key}: {old_config[key]} → {new_value}")
    
    def _calculate_screenshot_delay(self, actions: list, durations: list = None) -> float:
        """Calculate optimal delay before taking screenshot based on action complexity"""
        if not actions:
            return self.timing_config['base_stabilization']
        
        # Start with base stabilization time
        total_delay = self.timing_config['base_stabilization']
        
        # Add timing for each action based on type
        for i, action in enumerate(actions):
            # Get duration for this action (convert frames to seconds)
            if durations and i < len(durations):
                action_duration = durations[i] / 60.0  # Convert frames to seconds at 60fps
            else:
                action_duration = 2 / 60.0  # Default 2 frames = ~0.033 seconds
            
            # Add action-specific timing
            if action in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
                # Movement actions need time for character to move and position to update
                total_delay += action_duration + self.timing_config['movement_multiplier']
            elif action in ['A', 'B']:
                # Interaction actions may trigger dialogs, battles, or state changes
                total_delay += action_duration + self.timing_config['interaction_multiplier']
            elif action in ['START', 'SELECT']:
                # Menu actions need time for UI to render and stabilize
                total_delay += action_duration + self.timing_config['menu_multiplier']
            else:
                # Default timing for other actions
                total_delay += action_duration + 0.3
        
        # Apply safety cap
        final_delay = min(total_delay, self.timing_config['max_wait_time'])
        
        print(f"⏱️ Calculated screenshot delay: {final_delay:.2f}s for {len(actions)} actions")
        return final_delay
    
    def _setup_socket_server(self):
        """Set up the socket server for mGBA communication"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.socket.settimeout(1.0)  # Non-blocking accept with timeout
            print(f"✅ Socket server listening on {self.host}:{self.port}")
        except Exception as e:
            raise Exception(f"Failed to setup socket server: {e}")
    
    def _accept_connections(self):
        """Accept and handle mGBA connections"""
        while self.running:
            try:
                client_socket, client_address = self.socket.accept()
                print(f"🔗 mGBA connected from {client_address}")
                
                # Close any existing connection
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except:
                        pass
                
                self.client_socket = client_socket
                self.mgba_connected = True
                self._send_chat_message("system", "🎮 mGBA connected successfully!")
                
                # Handle this connection
                self._handle_mgba_connection()
                
            except socket.timeout:
                # Normal timeout, continue loop
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ Connection error: {e}")
                    self._send_chat_message("system", f"⚠️ Connection error: {str(e)}")
    
    def _handle_mgba_connection(self):
        """Handle communication with connected mGBA instance"""
        try:
            self.client_socket.settimeout(0.1)  # Short timeout for non-blocking recv
            
            while self.running and self.mgba_connected:
                try:
                    data = self.client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    # Add to message buffer
                    self.message_buffer += data
                    
                    # Debug: Show if we received partial data
                    if len(self.message_buffer) > 100 and '\n' not in self.message_buffer:
                        print(f"🔄 Buffering large message: {len(self.message_buffer)} chars")
                    
                    # Process complete messages (terminated by newlines)
                    while '\n' in self.message_buffer:
                        line, self.message_buffer = self.message_buffer.split('\n', 1)
                        message = line.strip()
                        
                        if message:  # Only process non-empty messages
                            print(f"📨 Received from mGBA: {message}")
                            self._process_mgba_message(message)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"⚠️ Error receiving data: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Connection handling error: {e}")
        finally:
            self.mgba_connected = False
            self._send_chat_message("system", "🔌 mGBA disconnected")
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
    
    def _process_mgba_message(self, message: str):
        """Process messages received from mGBA Lua script"""
        try:
            if message.startswith("ready"):
                self._handle_ready_message()
            elif message.startswith("config_loaded"):
                self._handle_config_loaded_message()
            elif message.startswith("config_error"):
                self._handle_config_error_message(message)
            elif message.startswith("screenshot_with_state") or message.startswith("enhanced_screenshot_with_state"):
                self._handle_screenshot_data(message)
            elif "||" in message and len(message.split("||")) >= 6:
                # This looks like screenshot data without the proper prefix (probably due to message splitting)
                # Try to process it as screenshot_with_state
                print(f"🔧 Attempting to process orphaned screenshot data: {message}")
                self._handle_screenshot_data("screenshot_with_state||" + message)
            else:
                # Only log as unknown if it doesn't look like partial screenshot data
                if not any(keyword in message.lower() for keyword in ["screenshot", "png", "||"]):
                    print(f"🤔 Unknown message from mGBA: {message}")
                else:
                    print(f"🚧 Ignoring probable partial message: {message[:50]}...")
        except Exception as e:
            print(f"❌ Error processing mGBA message: {e}")
            self._send_chat_message("system", f"❌ Error processing message: {str(e)}")
    
    def _handle_ready_message(self):
        """Handle 'ready' message from mGBA"""
        print("✅ mGBA is ready for gameplay")
        
        # Only detect and configure game on first connection
        if not self.game_config_sent:
            self._send_chat_message("system", "✅ mGBA ready - detecting game and sending config...")
            self._detect_and_configure_game()
            
            # Wait a moment for config to be processed before requesting screenshot
            time.sleep(0.5)
        else:
            self._send_chat_message("system", "✅ mGBA ready - resuming gameplay")
        
        # Request screenshot
        self._request_screenshot()
    
    def _handle_config_loaded_message(self):
        """Handle confirmation that Lua script loaded the game config"""
        print("✅ Game configuration loaded by mGBA")
        self._send_chat_message("system", "✅ Game configuration loaded successfully")
        self.game_config_sent = True
    
    def _handle_config_error_message(self, message: str):
        """Handle config error from Lua script"""
        error_msg = message.replace("config_error||", "") if "||" in message else "Unknown config error"
        print(f"❌ Game configuration error: {error_msg}")
        self._send_chat_message("system", f"❌ Config error: {error_msg}")
        self.game_config_sent = False
    
    def _detect_and_configure_game(self):
        """Detect game and send configuration to mGBA Lua script"""
        try:
            # Load configuration to get ROM info
            config = self._load_config()
            if not config:
                self._send_chat_message("system", "❌ No configuration found")
                return
            
            # Get ROM information for detection
            rom_path = config.get('rom_path', '')
            rom_display_name = config.get('rom_display_name', '')
            
            print(f"🔍 ROM detection info: path='{rom_path}', display_name='{rom_display_name}'")
            
            # Check if there's already a manual override
            print(f"🔍 Game detector manual override: {self.game_detector.manual_override}")
            
            # Test individual detection methods for debugging
            name_detection = self.game_detector.detect_game_from_rom_name(rom_display_name) if rom_display_name else None
            path_detection = self.game_detector.detect_game_from_path(rom_path) if rom_path else None
            print(f"🔍 Name detection result: {name_detection}")
            print(f"🔍 Path detection result: {path_detection}")
            
            # Detect game using the game detector
            detected_game_id, detection_source = self.game_detector.get_current_game(
                rom_name=rom_display_name,
                rom_path=rom_path
            )
            
            print(f"🔍 Final detection result: {detected_game_id} (source: {detection_source})")
            
            self.current_game_id = detected_game_id
            game_config = self.game_detector.get_game_config(detected_game_id)
            
            if not game_config:
                self._send_chat_message("system", f"❌ Unknown game: {detected_game_id}")
                return
            
            print(f"🎮 Detected game: {game_config.name} (source: {detection_source})")
            self._send_chat_message("system", f"🎮 Game detected: {game_config.name}")
            
            # Update configuration with detection results
            self._update_configuration_with_detection(detected_game_id, detection_source, config)
            
            # Send game configuration to Lua script
            lua_config = self.game_detector.format_game_config_for_lua(detected_game_id)
            if lua_config:
                self._send_game_config_to_lua(lua_config)
                self.game_config_sent = True
            else:
                self._send_chat_message("system", "❌ Failed to format game config for Lua")
                
        except Exception as e:
            print(f"❌ Game detection error: {e}")
            self._send_chat_message("system", f"❌ Game detection failed: {str(e)}")
    
    def _update_configuration_with_detection(self, game_id: str, detection_source: str, config: Dict[str, Any]):
        """Update database configuration with game detection results"""
        try:
            # Update the database configuration
            from .models import Configuration
            db_config = Configuration.get_config()
            
            # Only update if detection source is not manual override
            if detection_source != "manual":
                db_config.detected_game = game_id
                db_config.detection_source = detection_source
                
                # If no manual override, update the active game
                if not db_config.game_override:
                    db_config.game = game_id
            
            db_config.save()
            print(f"📝 Updated configuration: game={game_id}, source={detection_source}")
            
        except Exception as e:
            print(f"⚠️ Failed to update configuration: {e}")
    
    def _send_game_config_to_lua(self, lua_config: str):
        """Send game configuration to mGBA Lua script"""
        try:
            if not self.mgba_connected or not self.client_socket:
                print("⚠️ Cannot send config: mGBA not connected")
                return False
            
            # Send config command to Lua
            config_message = f"game_config||{lua_config}"
            self.client_socket.settimeout(5.0)
            self.client_socket.send(f"{config_message}\n".encode('utf-8'))
            self.client_socket.settimeout(0.1)
            
            print("📤 Game configuration sent to mGBA")
            self._send_chat_message("system", "📤 Game configuration sent to mGBA")
            return True
            
        except Exception as e:
            print(f"❌ Error sending game config: {e}")
            self._send_chat_message("system", f"❌ Failed to send game config: {str(e)}")
            return False
    
    def _handle_screenshot_data(self, message: str):
        """Handle screenshot data from mGBA and process through AI"""
        try:
            # Parse different message formats:
            # "screenshot_with_state||path||direction||x||y||mapId" (6 parts)
            # "enhanced_screenshot_with_state||path||previousPath||direction||x||y||mapId||buttonCount" (8 parts)
            parts = message.split("||")
            
            # Validate message format
            if len(parts) < 6:
                print(f"⚠️ Invalid screenshot data format: {message}")
                print(f"🔍 Expected 6+ parts, got {len(parts)}: {parts}")
                return
            
            message_type = parts[0]
            
            # Parse based on message type
            if message_type == "screenshot_with_state" and len(parts) >= 6:
                screenshot_path = parts[1]
                direction = parts[2]
                x_str, y_str, map_id_str = parts[3], parts[4], parts[5]
            elif message_type == "enhanced_screenshot_with_state" and len(parts) >= 8:
                screenshot_path = parts[1]
                # parts[2] is previousPath (not used for AI processing)
                direction = parts[3]
                x_str, y_str, map_id_str = parts[4], parts[5], parts[6]
                # parts[7] is buttonCount (not used for AI processing)
            else:
                print(f"⚠️ Unknown message format: {message_type} with {len(parts)} parts")
                return
            
            # Safely parse coordinates with improved validation
            try:
                # Clean any trailing characters or whitespace
                x = int(x_str.strip())
                y = int(y_str.strip()) 
                map_id = int(map_id_str.strip())
            except ValueError as ve:
                print(f"⚠️ Error parsing coordinates: {ve}")
                print(f"🔍 Raw coordinate strings: x='{x_str}', y='{y_str}', map_id='{map_id_str}'")
                print(f"🔍 Full message: {message}")
                # Use fallback values
                x, y, map_id = 0, 0, 0
            
            # Normalize direction to handle UNKNOWN values
            normalized_direction = self._normalize_direction(direction)
            
            game_state = {
                "position": {"x": x, "y": y},
                "direction": normalized_direction,
                "direction_raw": direction,  # Keep original for debugging
                "map_id": map_id
            }
            
            print(f"📷 Processing {message_type}: {screenshot_path}")
            print(f"🎮 Game state: Position({x}, {y}), Direction={direction}, Map={map_id}")
            self._process_ai_decision(screenshot_path, game_state)
            
        except Exception as e:
            print(f"❌ Error handling screenshot data: {e}")
            print(f"🔍 Raw message: {message}")
            self._send_chat_message("system", f"❌ Screenshot processing error: {str(e)}")
    
    def _process_ai_decision(self, screenshot_path: str, game_state: Dict[str, Any]):
        """Process screenshot through AI and send commands back to mGBA"""
        try:
            # Update game state tracking
            new_x = game_state.get('position', {}).get('x', 0)
            new_y = game_state.get('position', {}).get('y', 0)
            new_direction = game_state.get('direction', 'UNKNOWN')
            new_map_id = game_state.get('map_id', 0)
            
            # Track position changes for movement analysis
            self._update_position_tracking(new_x, new_y, new_direction, new_map_id)
            
            # Update current state
            self.player_x = new_x
            self.player_y = new_y
            self.player_direction = new_direction
            self.map_id = new_map_id
            
            # Get the previous screenshot (most recent in map) BEFORE registering the new one
            previous_path = None
            if len(self.screenshot_map) > 0:
                # Get the most recent screenshot as "previous"
                sorted_screenshots = sorted(
                    self.screenshot_map.items(),
                    key=lambda x: x[1], 
                    reverse=True
                )
                previous_path = sorted_screenshots[0][0]
            
            # Now register the new screenshot as "current"
            self._register_new_screenshot(screenshot_path)
            current_path = screenshot_path
            
            # Display screenshots being sent to AI
            if previous_path and current_path and previous_path != current_path:
                # Subsequent cycle: Show both previous and current screenshots
                self._send_screenshot_comparison_message(previous_path, current_path, game_state)
            else:
                # Initial cycle or only one screenshot: Show current screenshot only
                self._send_single_screenshot_message(screenshot_path, game_state)
            
            # Load current configuration from database
            config = self._load_config()
            if not config:
                self._send_chat_message("system", "❌ No AI configuration found")
                return
            
            # Get recent actions text for enhanced context
            recent_actions_text = self._get_recent_actions_text()
            
            # Add movement analysis to context
            movement_analysis = self._get_movement_analysis_text()
            
            # Call AI with latest screenshots for LLM-based analysis
            ai_response = self._call_ai_api_with_comparison(
                current_screenshot=current_path,
                previous_screenshot=previous_path if previous_path != current_path else None,
                game_state=game_state,
                config=config,
                enhanced_context=recent_actions_text + "\n" + movement_analysis
            )
            
            # Show AI response in chat (includes both decision and analysis)
            self._send_ai_response_message(ai_response)
            
            # Check if this is an error response first
            is_error_response = not ai_response.get("success", True)
            actions_to_send = ai_response.get("actions", [])
            durations_to_send = ai_response.get("durations", [])
            
            if is_error_response:
                # Error occurred - don't send any actions
                print("🚫 Error response detected - not sending any button actions")
                actions_to_send = []
            else:
                # Normal response - validate and process actions
                if not actions_to_send:
                    # Only add fallback "A" for successful responses with missing actions
                    actions_to_send = ["A"]
                    print("⚠️ No actions provided in successful response - using fallback 'A'")
                
                # Validate actions
                valid_buttons = ["A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L"]
                actions_to_send = [action for action in actions_to_send if action in valid_buttons]
                if not actions_to_send:
                    actions_to_send = ["A"]  # Final fallback for successful responses
            
            # Add to recent actions history
            reasoning = ai_response.get("text", "No reasoning provided")
            if actions_to_send:
                sequence_description = f"{len(actions_to_send)} actions: {', '.join(actions_to_send)}"
            else:
                sequence_description = "0 actions: (error - no actions sent)"
            self._add_recent_action(sequence_description, reasoning, game_state)
            
            # Only send button sequences and calculate delays if we have actions
            if actions_to_send:
                # Send button sequence to mGBA  
                self._send_button_sequence(actions_to_send, durations_to_send)
                
                # Calculate delay for actions + cooldown
                action_delay = self._calculate_screenshot_delay(actions_to_send, durations_to_send)
                cooldown = config.get('decision_cooldown', 3)
                total_delay = action_delay + cooldown
                
                print(f"⏳ Waiting {total_delay:.2f}s (actions: {action_delay:.2f}s + cooldown: {cooldown}s)")
                time.sleep(total_delay)
            else:
                # Error case - just wait minimal cooldown and continue
                cooldown = config.get('decision_cooldown', 3)
                print(f"⏳ Error occurred - waiting minimal {cooldown}s cooldown before continuing")
                time.sleep(cooldown)
            
            # Request next screenshot to continue cycle
            if self.mgba_connected:
                self._request_screenshot()
            
            # Process memory system updates
            if self.memory_system:
                self._process_memory_updates(ai_response, game_state, actions_to_send)
            
            self.decision_count += 1
            
        except Exception as e:
            print(f"❌ AI decision error: {e}")
            traceback.print_exc()
            self._handle_ai_processing_error(e, screenshot_path, game_state)
    
    def _send_single_screenshot_message(self, screenshot_path: str, game_state: Dict[str, Any]):
        """Send single screenshot message for initial cycle"""
        try:
            if os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                
                position_text = f"📍 Position: ({game_state['position']['x']}, {game_state['position']['y']}) facing {game_state['direction']}"
                
                self.message_counter += 1
                message = {
                    "type": "screenshot",
                    "image_data": f"data:image/png;base64,{image_data}",
                    "game_state": f"📤 Screenshot sent to AI for analysis... {position_text}",
                    "timestamp": datetime.now().isoformat(),
                    "id": self.message_counter
                }
                
                self.chat_messages.append(message)
                if len(self.chat_messages) > self.max_messages:
                    self.chat_messages.pop(0)
                    
        except Exception as e:
            print(f"❌ Error sending single screenshot message: {e}")
    
    def _send_screenshot_comparison_message(self, previous_path: str, current_path: str, game_state: Dict[str, Any]):
        """Send screenshot comparison message for subsequent cycles"""
        try:
            previous_image_data = ""
            current_image_data = ""
            
            if os.path.exists(previous_path):
                with open(previous_path, 'rb') as f:
                    previous_image_data = base64.b64encode(f.read()).decode('utf-8')
                    
            if os.path.exists(current_path):
                with open(current_path, 'rb') as f:
                    current_image_data = base64.b64encode(f.read()).decode('utf-8')
            
            position_text = f"📍 Position: ({game_state['position']['x']}, {game_state['position']['y']}) facing {game_state['direction']}"
            
            self.message_counter += 1
            message = {
                "type": "screenshot_comparison",
                "previous_image_data": f"data:image/png;base64,{previous_image_data}",
                "current_image_data": f"data:image/png;base64,{current_image_data}",
                "game_state": f"📤 Previous and current screenshots sent to AI for analysis... {position_text}",
                "timestamp": datetime.now().isoformat(),
                "id": self.message_counter
            }
            
            self.chat_messages.append(message)
            if len(self.chat_messages) > self.max_messages:
                self.chat_messages.pop(0)
                
        except Exception as e:
            print(f"❌ Error sending screenshot comparison message: {e}")
    
    def _call_ai_api_with_comparison(self, current_screenshot: str, previous_screenshot: Optional[str], 
                                   game_state: Dict[str, Any], config: Dict[str, Any], enhanced_context: str) -> Dict[str, Any]:
        """Call AI API with optional previous screenshot for comparison"""
        try:
            # Initialize LLM client if needed
            if not self.llm_client:
                self.llm_client = LLMClient(config)
            
            # Call LLM with both screenshots if previous exists
            if previous_screenshot and os.path.exists(previous_screenshot):
                return self.llm_client.analyze_game_state_with_comparison(
                    current_screenshot=current_screenshot,
                    previous_screenshot=previous_screenshot,
                    game_state=game_state,
                    recent_actions_text=enhanced_context
                )
            else:
                # Initial cycle - single screenshot analysis
                return self.llm_client.analyze_game_state(
                    screenshot_path=current_screenshot,
                    game_state=game_state,
                    recent_actions_text=enhanced_context
                )
                
        except Exception as e:
            print(f"❌ AI API call error: {e}")
            return {
                "text": f"AI call failed: {str(e)}",
                "actions": ["A"],
                "success": False,
                "error": str(e)
            }
    
    def _load_config(self) -> Optional[Dict[str, Any]]:
        """Load configuration from SQLite database"""
        try:
            config = Configuration.get_config()
            return config.to_dict()
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return None
    
    def _call_ai_api(self, screenshot_path: str, game_state: Dict[str, Any], config: Dict[str, Any], recent_actions_text: str = "", before_after_analysis: str = "") -> Dict[str, Any]:
        """Call AI API with screenshot and game state"""
        try:
            # Initialize LLM client if needed
            if not self.llm_client:
                self.llm_client = LLMClient(config)
            
            # Call LLM with error handling and timeout
            print(f"🤖 Calling {config.get('llm_provider', 'unknown')} API...")
            start_time = time.time()
            
            result = self.llm_client.analyze_game_state(screenshot_path, game_state, recent_actions_text, before_after_analysis)
            
            elapsed = time.time() - start_time
            print(f"⏱️ AI response received in {elapsed:.1f}s")
            
            return result
            
        except Exception as e:
            print(f"❌ AI API call failed: {e}")
            traceback.print_exc()
            
            # Intelligent fallback based on game state
            fallback_action = self._get_intelligent_fallback_action(game_state)
            
            return {
                "text": f"AI API failed: {str(e)}. Using intelligent fallback: {fallback_action}",
                "actions": [fallback_action],
                "durations": [],  # Use default durations
                "success": False,
                "error": str(e)
            }
    
    def _request_screenshot(self):
        """Request a screenshot from mGBA with retry logic"""
        if not self.mgba_connected or not self.client_socket:
            print("⚠️ Cannot request screenshot: mGBA not connected")
            return False
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.client_socket.settimeout(5.0)  # 5 second timeout
                self.client_socket.send("request_screenshot\n".encode('utf-8'))
                self.client_socket.settimeout(0.1)  # Reset timeout
                print("📸 Requested screenshot from mGBA")
                return True
            except socket.timeout:
                print(f"⚠️ Screenshot request timeout (attempt {attempt + 1}/{max_retries})")
            except Exception as e:
                print(f"❌ Error requesting screenshot (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retry
        
        print("❌ Failed to request screenshot after all retries")
        self._send_chat_message("system", "❌ Failed to request screenshot - connection may be lost")
        return False
    
    def _send_button_sequence(self, actions: list, durations: list = None):
        """Send button sequence to mGBA with optional custom durations"""
        if not self.mgba_connected or not self.client_socket:
            print("⚠️ Cannot send sequence: mGBA not connected")
            self._send_chat_message("system", "⚠️ Cannot send sequence: mGBA not connected")
            return False
        
        try:
            # Convert action names to button codes
            button_map = {
                "A": "0", "B": "1", "SELECT": "2", "START": "3",
                "RIGHT": "4", "LEFT": "5", "UP": "6", "DOWN": "7", "R": "8", "L": "9"
            }
            
            # Check for empty actions list (error condition - don't press anything)
            if not actions:
                print("🛑 Empty actions list - not pressing any buttons (error occurred)")
                self._send_chat_message("system", "🛑 No button actions sent due to error")
                return True  # Return success without sending buttons
            
            # Validate actions
            valid_actions = [action for action in actions if action in button_map]
            if not valid_actions:
                print(f"⚠️ No valid actions in: {actions}")
                print("🛑 Not pressing any buttons due to invalid action list")
                self._send_chat_message("system", "🛑 No valid button actions - skipping button press")
                return True  # Return success without sending buttons
            
            # Process durations
            if durations:
                # Validate and limit durations (1-180 frames at 60fps = 1-3 seconds)
                processed_durations = []
                for i, duration in enumerate(durations):
                    if i < len(valid_actions):
                        validated_duration = max(1, min(180, int(duration)))
                        processed_durations.append(validated_duration)
                    
                # Pad with default duration (2 frames) if needed
                while len(processed_durations) < len(valid_actions):
                    processed_durations.append(2)
                    
                durations_to_use = processed_durations[:len(valid_actions)]
            else:
                # Use default duration for all actions
                durations_to_use = [2] * len(valid_actions)
            
            # Create button codes and durations
            button_codes = [button_map[action] for action in valid_actions]
            
            # Format command as "button_codes|durations" for Lua script
            button_codes_str = ",".join(button_codes)
            durations_str = ",".join(map(str, durations_to_use))
            command = f"{button_codes_str}|{durations_str}"
            
            # Send with timeout protection
            self.client_socket.settimeout(5.0)  # 5 second timeout
            self.client_socket.send(f"{command}\n".encode('utf-8'))
            self.client_socket.settimeout(0.1)  # Reset to original timeout
            
            # Create user-friendly message
            action_descriptions = []
            for i, action in enumerate(valid_actions):
                duration_frames = durations_to_use[i]
                duration_ms = round(duration_frames * 16.67)  # Convert frames to milliseconds
                action_descriptions.append(f"{action} ({duration_ms}ms)")
            
            sequence_description = " → ".join(action_descriptions)
            self._send_chat_message("system", f"✅ Sequence sent: {sequence_description}")
            return True
            
        except socket.timeout:
            print("❌ Button sequence timeout")
            self._send_chat_message("system", "❌ Sequence sending timed out")
            return False
        except Exception as e:
            print(f"❌ Error sending button sequence: {e}")
            self._send_chat_message("system", f"❌ Error sending sequence: {str(e)}")
            return False
    
    def _send_button_commands(self, actions: list):
        """Legacy method - redirect to sequence method for compatibility"""
        return self._send_button_sequence(actions)
    
    def _send_chat_message(self, message_type: str, content: str):
        """Send a message to the frontend chat interface"""
        try:
            self.message_counter += 1
            message = {
                "type": "system",
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "id": self.message_counter  # Add unique ID for tracking
            }
            
            # Store in local message buffer
            self.chat_messages.append(message)
            if len(self.chat_messages) > self.max_messages:
                self.chat_messages.pop(0)
            
            # Also try WebSocket if available
            if self.channel_layer:
                async_to_sync(self.channel_layer.group_send)(
                    "ai_chat",
                    {
                        "type": "chat_message",
                        "message_type": message_type,
                        "content": content,
                        "timestamp": datetime.now().isoformat()
                    }
                )
        except Exception as e:
            print(f"⚠️ Error sending chat message: {e}")
    
    def _send_screenshot_message(self, screenshot_path: str, game_state: Dict[str, Any]):
        """Send screenshot as a sent message in chat"""
        try:
            # Read and encode screenshot
            if os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                
                position_text = f"📍 Position: ({game_state['position']['x']}, {game_state['position']['y']}) facing {game_state['direction']}"
                
                self.message_counter += 1
                message = {
                    "type": "screenshot",
                    "image_data": f"data:image/png;base64,{image_data}",
                    "game_state": position_text,
                    "timestamp": datetime.now().isoformat(),
                    "id": self.message_counter  # Add unique ID for tracking
                }
                
                # Store in local message buffer
                self.chat_messages.append(message)
                if len(self.chat_messages) > self.max_messages:
                    self.chat_messages.pop(0)
                
                # Also try WebSocket if available
                if self.channel_layer:
                    async_to_sync(self.channel_layer.group_send)(
                        "ai_chat",
                        {
                            "type": "screenshot_message",
                            "image_data": image_data,
                            "game_state": position_text,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
            else:
                print(f"⚠️ Screenshot file not found: {screenshot_path}")
        except Exception as e:
            print(f"❌ Error sending screenshot message: {e}")
    
    def _send_ai_response_message(self, ai_response: Dict[str, Any]):
        """Send AI response as a received message in chat"""
        try:
            self.message_counter += 1
            message = {
                "type": "ai_response",
                "text": ai_response.get("text", ""),
                "actions": ai_response.get("actions", []),
                "success": ai_response.get("success", True),
                "error_details": ai_response.get("error_details", None),  # Add error details for expandable UI
                "timestamp": datetime.now().isoformat(),
                "id": self.message_counter  # Add unique ID for tracking
            }
            
            # Store in local message buffer
            self.chat_messages.append(message)
            if len(self.chat_messages) > self.max_messages:
                self.chat_messages.pop(0)
            
            # Also try WebSocket if available
            if self.channel_layer:
                async_to_sync(self.channel_layer.group_send)(
                    "ai_chat",
                    {
                        "type": "ai_response_message",
                        "text": ai_response.get("text", ""),
                        "actions": ai_response.get("actions", []),
                        "timestamp": datetime.now().isoformat()
                    }
                )
        except Exception as e:
            print(f"❌ Error sending AI response message: {e}")
    
    def _initialize_notepad(self):
        """Initialize the notepad file with clear game objectives"""
        if not self.notepad_path.exists():
            self.notepad_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.notepad_path, 'w') as f:
                f.write("# Pokémon Red Game Progress\n\n")
                f.write(f"Game started: {timestamp}\n\n")
                f.write("## Current Objectives\n- Enter my name 'GEMINI' and give my rival a name.\n\n")
                f.write("## Exit my house\n\n")
                f.write("## Current Objectives\n- Find Professor Oak to get first Pokémon\n- Start Pokémon journey\n\n")
                f.write("## Current Location\n- Starting in player's house in Pallet Town\n\n")
                f.write("## Game Progress\n- Just beginning the adventure\n\n")
                f.write("## Items\n- None yet\n\n")
                f.write("## Pokémon Team\n- None yet\n\n")
    
    def _read_notepad(self):
        """Read the current notepad content"""
        try:
            with open(self.notepad_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading notepad: {e}")
            return "Error reading notepad"
    
    def _update_notepad(self, new_content):
        """Update the notepad"""
        try:
            current_content = self._read_notepad()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated_content = current_content + f"\n## Update {timestamp}\n{new_content}\n"
            with open(self.notepad_path, 'w') as f:
                f.write(updated_content)
            print("📝 Notepad updated")
        except Exception as e:
            print(f"❌ Error updating notepad: {e}")
    
    def _get_recent_actions_text(self):
        """Get formatted text of recent actions with reasoning"""
        if not self.recent_actions:
            return "No recent actions."
        
        recent_actions_text = "## Short-term Memory (Recent Actions and Reasoning):\n"
        for i, action in enumerate(self.recent_actions, 1):
            timestamp = action.get('timestamp', 'unknown')
            button = action.get('button', 'unknown')
            reasoning = action.get('reasoning', 'no reasoning available')
            direction = action.get('direction', 'unknown')
            x, y = action.get('x', 0), action.get('y', 0)
            map_id = action.get('map_id', 0)
            
            recent_actions_text += f"{i}. [{timestamp}] Pressed {button} while facing {direction} at position ({x}, {y}) on map {map_id}\n"
            recent_actions_text += f"   Reasoning: {reasoning.strip()}\n\n"
        return recent_actions_text
    
    def _get_map_name(self, map_id):
        """Get map name from ID, with fallback for unknown maps"""
        # Pokémon Red/Blue map IDs (incomplete, add more as needed)
        map_names = {
            0: "Pallet Town",
            1: "Viridian City", 
            2: "Pewter City",
            3: "Cerulean City",
            12: "Route 1",
            13: "Route 2",
            14: "Route 3",
            15: "Route 4",
            37: "Red's House 1F",
            38: "Red's House 2F", 
            39: "Blue's House",
            40: "Oak's Lab",
        }
        
        return map_names.get(map_id, f"Unknown Area (Map ID: {map_id})")
    
    def _add_recent_action(self, button: str, reasoning: str, game_state: Dict[str, Any]):
        """Add an action to recent actions history"""
        action = {
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'button': button,
            'reasoning': reasoning,
            'direction': game_state.get('direction', 'UNKNOWN'),
            'x': game_state.get('position', {}).get('x', 0),
            'y': game_state.get('position', {}).get('y', 0),
            'map_id': game_state.get('map_id', 0)
        }
        
        self.recent_actions.append(action)
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions.pop(0)
    
    def _normalize_direction(self, direction_str: str) -> str:
        """Enhanced direction normalization supporting both standard and TBL encodings"""
        if not direction_str:
            return "UNKNOWN"
        
        # Handle "UNKNOWN (XX)" format
        if direction_str.startswith("UNKNOWN"):
            return "UNKNOWN"
        
        # Handle numeric direction values (both standard and TBL)
        if direction_str.isdigit():
            direction_value = int(direction_str)
            
            # Standard GBA encoding (1-4)
            standard_directions = {1: "DOWN", 2: "UP", 3: "LEFT", 4: "RIGHT"}
            if direction_value in standard_directions:
                return standard_directions[direction_value]
            
            # TBL hex encoding (0x79-0x7C = 121-124 decimal)
            tbl_directions = {121: "UP", 122: "DOWN", 123: "LEFT", 124: "RIGHT"}
            if direction_value in tbl_directions:
                return tbl_directions[direction_value]
            
            # Log unknown numeric values for debugging
            print(f"⚠️ Unknown numeric direction value: {direction_value} (not standard 1-4 or TBL 121-124)")
            return "UNKNOWN"
        
        # Normalize to uppercase and validate known directions
        direction = direction_str.upper().strip()
        valid_directions = ["UP", "DOWN", "LEFT", "RIGHT"]
        
        if direction in valid_directions:
            return direction
        else:
            print(f"⚠️ Unknown direction value: '{direction_str}' -> normalized to 'UNKNOWN'")
            return "UNKNOWN"
    
    def _get_intelligent_fallback_action(self, game_state: Dict[str, Any]) -> str:
        """Get intelligent fallback action based on game state"""
        map_id = game_state.get('map_id', 0)
        direction_raw = game_state.get('direction', 'UNKNOWN')
        direction = self._normalize_direction(direction_raw)
        x, y = game_state.get('position', {}).get('x', 0), game_state.get('position', {}).get('y', 0)
        
        # If we've been in the same position for too long, try moving
        if hasattr(self, '_last_position'):
            if self._last_position == (x, y, map_id) and hasattr(self, '_stuck_count'):
                self._stuck_count += 1
                if self._stuck_count > 3:
                    # Try different directions when stuck
                    fallback_moves = ["UP", "DOWN", "LEFT", "RIGHT"]
                    if direction in fallback_moves:
                        current_dir_index = fallback_moves.index(direction)
                        next_direction = fallback_moves[(current_dir_index + 1) % len(fallback_moves)]
                    else:
                        # If direction is UNKNOWN, start with UP
                        next_direction = "UP"
                    print(f"⚠️ Stuck detected (direction: {direction_raw}), trying: {next_direction}")
                    return next_direction
            else:
                self._stuck_count = 0
        else:
            self._stuck_count = 0
        
        self._last_position = (x, y, map_id)
        
        # Default fallback based on context
        if map_id == 0:  # Pallet Town - likely need to explore
            return "UP"
        elif map_id in [37, 38]:  # Player's house - try to exit
            return "DOWN"
        elif map_id == 40:  # Oak's lab - interact
            return "A"
        else:
            # General exploration - if direction is unknown, try to move
            if direction == "UNKNOWN":
                return "UP"  # Safe default movement
            else:
                return "A"  # Try to interact
    
    def _handle_ai_processing_error(self, error: Exception, screenshot_path: str, game_state: Dict[str, Any]):
        """Handle AI processing errors with graceful recovery"""
        error_msg = str(error)
        
        # Log the error with context
        print(f"❌ AI Processing Error: {error_msg}")
        print(f"📍 Context: Screenshot={screenshot_path}, GameState={game_state}")
        
        # Send error message to chat
        self._send_chat_message("system", f"⚠️ AI processing error: {error_msg}")
        
        # Try to recover by using fallback
        fallback_action = self._get_intelligent_fallback_action(game_state)
        self._send_button_commands([fallback_action])
        
        # Request next screenshot after a delay
        time.sleep(2)
        self._request_screenshot()
    
    def _process_memory_updates(self, ai_response: Dict[str, Any], game_state: Dict[str, Any], actions_taken: list):
        """Process AI response for autonomous objective discovery and strategy learning"""
        if not self.memory_system:
            return
        
        try:
            ai_text = ai_response.get("text", "").lower()
            current_location = self._get_current_location_description(game_state)
            
            # 1. OBJECTIVE DISCOVERY - Look for AI mentioning goals or tasks
            self._discover_objectives_from_ai_text(ai_text, current_location)
            
            # 2. ACHIEVEMENT DETECTION - Check if AI completed something important
            self._detect_achievements_from_ai_text(ai_text, current_location)
            
            # 3. STRATEGY LEARNING - Record what button patterns work
            self._learn_strategy_from_actions(ai_text, actions_taken, game_state)
            
        except Exception as e:
            print(f"⚠️ Memory system update error: {e}")
    
    def _discover_objectives_from_ai_text(self, ai_text: str, location: str):
        """Analyze AI text for new objective discovery"""
        objective_keywords = [
            # Discovery patterns
            ("i need to", "task"),
            ("i should", "task"), 
            ("my goal is", "main"),
            ("i want to", "goal"),
            ("let me", "action"),
            # Pokemon-specific objectives
            ("catch", "collection"),
            ("find", "exploration"),
            ("battle", "combat"),
            ("heal", "maintenance"),
            ("explore", "exploration"),
            ("gym", "main"),
            ("pokecenter", "maintenance"),
            ("pokemart", "shopping"),
            # NPC interactions
            ("talk to", "social"),
            ("speak with", "social"),
            ("visit", "exploration")
        ]
        
        for keyword, category in objective_keywords:
            if keyword in ai_text and len(ai_text.split(keyword)[1]) > 5:  # Make sure there's context after keyword
                objective_text = ai_text.split(keyword)[1].split('.')[0]  # Get text until next sentence
                if len(objective_text.strip()) > 10:  # Ensure meaningful objective
                    full_objective = f"{keyword}{objective_text}".strip()
                    
                    # Determine priority based on category
                    priority_map = {"main": 9, "combat": 8, "collection": 7, "task": 6, "goal": 6, 
                                  "exploration": 5, "social": 4, "maintenance": 3, "shopping": 2, "action": 5}
                    priority = priority_map.get(category, 5)
                    
                    objective_id = ""
                    if MEMORY_SERVICE_AVAILABLE and 'discover_objective' in _memory_service_functions:
                        objective_id = _memory_service_functions['discover_objective'](
                            description=full_objective,
                            location=location,
                            category=category,
                            priority=priority
                        )
                    
                    if objective_id:
                        print(f"🎯 Discovered objective: {full_objective}")
                        self._send_chat_message("system", f"🧠 Discovered new objective: {full_objective}")
                        break  # Only discover one objective per AI response
    
    def _detect_achievements_from_ai_text(self, ai_text: str, location: str):
        """Detect completed achievements from AI text"""
        completion_keywords = [
            "caught", "defeated", "completed", "finished", "won", "obtained", 
            "got", "found", "reached", "arrived", "healed", "bought"
        ]
        
        for keyword in completion_keywords:
            if keyword in ai_text:
                # Look for objectives that might be completed
                if MEMORY_SERVICE_AVAILABLE and self.memory_system:
                    current_objectives = self.memory_system.get_current_objectives()
                    for objective in current_objectives:
                        # Simple keyword matching - could be enhanced with NLP
                        if any(word in objective.description.lower() for word in ai_text.split() if len(word) > 3):
                            success = False
                            if MEMORY_SERVICE_AVAILABLE and 'complete_objective' in _memory_service_functions:
                                success = _memory_service_functions['complete_objective'](objective.id, location)
                            if success:
                                print(f"✅ Completed objective: {objective.description}")
                                self._send_chat_message("system", f"🏆 Achievement unlocked: {objective.description}")
                                break
    
    def _learn_strategy_from_actions(self, ai_text: str, actions: list, game_state: Dict[str, Any]):
        """Learn strategies from successful action patterns"""
        if not actions:
            return
        
        # Determine situation context
        situation_context = self._get_situation_context(ai_text, game_state)
        
        # Assume success if AI didn't mention failure
        success = not any(fail_word in ai_text for fail_word in ['stuck', 'failed', 'error', 'wrong', 'mistake'])
        
        # Record strategy
        strategy_id = ""
        if MEMORY_SERVICE_AVAILABLE and 'learn_strategy' in _memory_service_functions:
            strategy_id = _memory_service_functions['learn_strategy'](
                situation=situation_context,
                button_sequence=actions,
                success=success,
                context={
                    "location": self._get_current_location_description(game_state),
                    "direction": game_state.get("direction", "UNKNOWN"),
                    "map_id": game_state.get("position", {}).get("map_id", 0)
                }
            )
        
        if strategy_id and success:
            print(f"🧠 Learned strategy: {situation_context} → {actions}")
    
    def _get_situation_context(self, ai_text: str, game_state: Dict[str, Any]) -> str:
        """Extract situation context from AI text and game state"""
        # Simple context extraction based on common game situations
        context_patterns = {
            "talking to npc": ["talk", "speak", "npc", "person"],
            "in battle": ["battle", "fight", "attack", "pokemon"],
            "navigating menu": ["menu", "select", "choose", "option"],
            "moving around": ["move", "go", "walk", "explore"],
            "interacting with object": ["interact", "examine", "use", "press a"],
            "in pokemon center": ["heal", "pokemon center", "pokecenter"],
            "shopping": ["buy", "shop", "mart", "pokemart"]
        }
        
        for situation, keywords in context_patterns.items():
            if any(keyword in ai_text for keyword in keywords):
                return situation
        
        # Default context based on location
        location = self._get_current_location_description(game_state)
        return f"general gameplay in {location}"
    
    def _get_current_location_description(self, game_state: Dict[str, Any]) -> str:
        """Get human-readable location description"""
        position = game_state.get("position", {})
        map_id = position.get("map_id", 0)
        x = position.get("x", 0)
        y = position.get("y", 0)
        
        # Use existing map name function if available
        map_name = getattr(self, '_get_map_name', lambda mid: f"Map {mid}")(map_id)
        return f"{map_name} ({x}, {y})"
    
    def _update_position_tracking(self, x: int, y: int, direction: str, map_id: int):
        """Update position tracking for movement pattern analysis"""
        current_position = {
            'x': x, 'y': y, 'direction': direction, 'map_id': map_id,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        }
        
        # Add to position history
        self.position_history.append(current_position)
        if len(self.position_history) > 10:
            self.position_history.pop(0)
            
        # Detect if position hasn't changed (stuck detection)
        if len(self.position_history) >= 3:
            recent_positions = [(p['x'], p['y'], p['map_id']) for p in self.position_history[-3:]]
            if len(set(recent_positions)) == 1:  # All recent positions are the same
                print(f"⚠️ Movement stuck detected at position ({x}, {y}) on map {map_id}")
    
    def _get_movement_analysis_text(self) -> str:
        """Generate movement analysis text for LLM context"""
        if len(self.position_history) < 2:
            return ""
            
        analysis = ["\n## MOVEMENT ANALYSIS:"]
        
        # Recent movement summary
        if len(self.position_history) >= 3:
            last_3 = self.position_history[-3:]
            positions = [(p['x'], p['y']) for p in last_3]
            
            if len(set(positions)) == 1:
                analysis.append("⚠️ WARNING: You haven't moved in the last 3 actions - you may be stuck!")
                analysis.append("- Try a different direction or approach")
                analysis.append("- Look for alternative paths or interactable objects")
            elif len(set(positions)) == 2:
                analysis.append("⚠️ You're moving back and forth between the same positions")
                analysis.append("- This suggests you're blocked or stuck in a pattern")
                analysis.append("- Try a completely different direction or strategy")
            else:
                analysis.append("✅ Good movement progress - you're exploring new positions")
        
        # Map transition detection
        if len(self.position_history) >= 2:
            current_map = self.position_history[-1]['map_id']
            prev_map = self.position_history[-2]['map_id']
            
            if current_map != prev_map:
                analysis.append(f"🚪 Map transition detected: from map {prev_map} to map {current_map}")
                analysis.append("- You successfully entered a new area!")
                analysis.append("- Update your notepad with this new location")
        
        # Position trend analysis
        if len(self.position_history) >= 5:
            recent_x = [p['x'] for p in self.position_history[-5:]]
            recent_y = [p['y'] for p in self.position_history[-5:]]
            
            x_trend = "stable"
            if max(recent_x) - min(recent_x) > 2:
                x_trend = "increasing" if recent_x[-1] > recent_x[0] else "decreasing"
                
            y_trend = "stable" 
            if max(recent_y) - min(recent_y) > 2:
                y_trend = "increasing" if recent_y[-1] > recent_y[0] else "decreasing"
                
            if x_trend != "stable" or y_trend != "stable":
                analysis.append(f"📈 Movement trend: X-axis {x_trend}, Y-axis {y_trend}")
        
        return "\n".join(analysis) if len(analysis) > 1 else ""
    
    
    
    
    def _encode_screenshot_for_chat(self, screenshot_path: str) -> str:
        """Encode screenshot as base64 for chat display"""
        try:
            if os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = f.read()
                    encoded = base64.b64encode(image_data).decode('utf-8')
                    return f"data:image/png;base64,{encoded}"
            else:
                print(f"⚠️ Screenshot file not found: {screenshot_path}")
                return ""
        except Exception as e:
            print(f"⚠️ Error encoding screenshot: {e}")
            return ""
    
    def _cleanup(self):
        """Clean up resources"""
        self.running = False
        self.mgba_connected = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


# Global service instance
_ai_service_instance = None


def get_ai_service() -> Optional[AIGameService]:
    """Get the current AI service instance"""
    global _ai_service_instance
    return _ai_service_instance


def start_ai_service() -> bool:
    """Start the AI service"""
    global _ai_service_instance
    
    try:
        if _ai_service_instance and _ai_service_instance.is_alive():
            print("⚠️ AI service is already running")
            return True
        
        _ai_service_instance = AIGameService()
        _ai_service_instance.start()
        
        # Give it a moment to start
        time.sleep(0.5)
        
        print("✅ AI service started successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to start AI service: {e}")
        return False


def stop_ai_service() -> bool:
    """Stop the AI service"""
    global _ai_service_instance
    
    try:
        if _ai_service_instance:
            _ai_service_instance.stop()
            _ai_service_instance = None
        
        print("✅ AI service stopped")
        return True
        
    except Exception as e:
        print(f"❌ Failed to stop AI service: {e}")
        return False


def is_ai_service_running() -> bool:
    """Check if AI service is running"""
    global _ai_service_instance
    return _ai_service_instance is not None and _ai_service_instance.is_alive()


def reload_ai_service_timing_config() -> bool:
    """Reload timing configuration in the running AI service"""
    global _ai_service_instance
    
    try:
        if _ai_service_instance and _ai_service_instance.is_alive():
            _ai_service_instance.reload_timing_config()
            print("✅ AI service timing configuration reloaded")
            return True
        else:
            print("⚠️ AI service is not running - cannot reload timing config")
            return False
    except Exception as e:
        print(f"❌ Failed to reload AI service timing config: {e}")
        return False