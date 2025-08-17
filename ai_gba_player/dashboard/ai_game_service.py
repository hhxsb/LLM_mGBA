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
import sys
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
        
        # Game state tracking
        self.player_direction = "UNKNOWN"
        self.player_x = 0
        self.player_y = 0
        self.map_id = 0
        
        # Initialize notepad
        self._initialize_notepad()
        
        print(f"🎮 AIGameService initialized - will listen on {self.host}:{self.port}")
    
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
                    data = self.client_socket.recv(1024).decode('utf-8').strip()
                    if not data:
                        break
                    
                    # Split by newlines to handle multiple messages in one recv()
                    messages = [msg.strip() for msg in data.split('\n') if msg.strip()]
                    
                    for message in messages:
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
            else:
                print(f"🤔 Unknown message from mGBA: {message}")
        except Exception as e:
            print(f"❌ Error processing mGBA message: {e}")
            self._send_chat_message("system", f"❌ Error processing message: {str(e)}")
    
    def _handle_ready_message(self):
        """Handle 'ready' message from mGBA"""
        print("✅ mGBA is ready for gameplay")
        self._send_chat_message("system", "✅ mGBA ready - detecting game and sending config...")
        
        # Detect game and send configuration to Lua
        self._detect_and_configure_game()
        
        # Wait a moment for config to be processed before requesting screenshot
        time.sleep(0.5)
        
        # Then request first screenshot
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
            self.player_x = game_state.get('position', {}).get('x', 0)
            self.player_y = game_state.get('position', {}).get('y', 0) 
            self.player_direction = game_state.get('direction', 'UNKNOWN')
            self.map_id = game_state.get('map_id', 0)
            
            # Show screenshot in chat (sent message)
            self._send_screenshot_message(screenshot_path, game_state)
            
            # Load current configuration from database
            config = self._load_config()
            if not config:
                self._send_chat_message("system", "❌ No AI configuration found")
                return
            
            # Get recent actions text for enhanced context
            recent_actions_text = self._get_recent_actions_text()
            
            # Process through AI with enhanced context
            ai_response = self._call_ai_api(screenshot_path, game_state, config, recent_actions_text)
            
            # Show AI response in chat (received message)
            self._send_ai_response_message(ai_response)
            
            # Process tool calls (notepad updates and button actions)
            actions_to_send = []
            durations_to_send = []
            
            if ai_response.get("actions"):
                actions_to_send = ai_response["actions"]
                durations_to_send = ai_response.get("durations", [])
                
                # Validate actions
                valid_buttons = ["A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L"]
                invalid_actions = [action for action in actions_to_send if action not in valid_buttons]
                if invalid_actions:
                    # Filter out invalid actions and corresponding durations
                    valid_action_indices = [i for i, action in enumerate(actions_to_send) if action in valid_buttons]
                    actions_to_send = [actions_to_send[i] for i in valid_action_indices]
                    
                    # Filter durations to match valid actions
                    if durations_to_send:
                        durations_to_send = [durations_to_send[i] if i < len(durations_to_send) else 2 for i in valid_action_indices]
                    
                    if not actions_to_send:
                        actions_to_send = ["A"]
                        durations_to_send = []
                
                # Add to recent actions history
                if actions_to_send:
                    reasoning = ai_response.get("text", "No reasoning provided")
                    sequence_description = f"{len(actions_to_send)} actions: {', '.join(actions_to_send)}"
                    self._add_recent_action(sequence_description, reasoning, game_state)
                
                # Send button sequence to mGBA  
                self._send_button_sequence(actions_to_send, durations_to_send)
            
            self.decision_count += 1
            
            # Wait for cooldown, then request next screenshot
            cooldown = config.get("decision_cooldown", 3)
            print(f"⏳ Waiting {cooldown}s cooldown before next decision...")
            time.sleep(cooldown)
            
            # Only request next screenshot if still connected
            if self.mgba_connected:
                self._request_screenshot()
            else:
                print("⚠️ Skipping screenshot request - mGBA disconnected")
            
        except Exception as e:
            print(f"❌ AI decision error: {e}")
            traceback.print_exc()
            self._handle_ai_processing_error(e, screenshot_path, game_state)
    
    def _load_config(self) -> Optional[Dict[str, Any]]:
        """Load configuration from SQLite database"""
        try:
            config = Configuration.get_config()
            return config.to_dict()
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return None
    
    def _call_ai_api(self, screenshot_path: str, game_state: Dict[str, Any], config: Dict[str, Any], recent_actions_text: str = "") -> Dict[str, Any]:
        """Call AI API with screenshot and game state"""
        try:
            # Initialize LLM client if needed
            if not self.llm_client:
                self.llm_client = LLMClient(config)
            
            # Call LLM with error handling and timeout
            print(f"🤖 Calling {config.get('llm_provider', 'unknown')} API...")
            start_time = time.time()
            
            result = self.llm_client.analyze_game_state(screenshot_path, game_state, recent_actions_text)
            
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
            
            # Validate actions
            valid_actions = [action for action in actions if action in button_map]
            if not valid_actions:
                print(f"⚠️ No valid actions in: {actions}")
                valid_actions = ["A"]  # Fallback to safe action
                durations = []
            
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
        """Normalize direction string to handle UNKNOWN values"""
        if not direction_str:
            return "UNKNOWN"
        
        # Handle "UNKNOWN (XX)" format
        if direction_str.startswith("UNKNOWN"):
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