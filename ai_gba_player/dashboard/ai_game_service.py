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
        self.max_messages = 100  # Keep last 100 messages
        
        # LLM client
        self.llm_client = None
        
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
                    
                    print(f"📨 Received from mGBA: {data}")
                    self._process_mgba_message(data)
                    
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
            if message == "ready":
                self._handle_ready_message()
            elif message.startswith("screenshot_data"):
                self._handle_screenshot_data(message)
            else:
                print(f"🤔 Unknown message from mGBA: {message}")
        except Exception as e:
            print(f"❌ Error processing mGBA message: {e}")
            self._send_chat_message("system", f"❌ Error processing message: {str(e)}")
    
    def _handle_ready_message(self):
        """Handle 'ready' message from mGBA"""
        print("✅ mGBA is ready for gameplay")
        self._send_chat_message("system", "✅ mGBA ready - requesting first screenshot...")
        self._request_screenshot()
    
    def _handle_screenshot_data(self, message: str):
        """Handle screenshot data from mGBA and process through AI"""
        try:
            # Parse: "screenshot_data|path|x|y|direction|mapId"
            parts = message.split("|")
            if len(parts) >= 6:
                screenshot_path = parts[1]
                x, y = int(parts[2]), int(parts[3])
                direction = parts[4]
                map_id = int(parts[5])
                
                game_state = {
                    "position": {"x": x, "y": y},
                    "direction": direction,
                    "map_id": map_id
                }
                
                print(f"📷 Processing screenshot: {screenshot_path}")
                self._process_ai_decision(screenshot_path, game_state)
            else:
                print(f"⚠️ Invalid screenshot data format: {message}")
        except Exception as e:
            print(f"❌ Error handling screenshot data: {e}")
            self._send_chat_message("system", f"❌ Screenshot processing error: {str(e)}")
    
    def _process_ai_decision(self, screenshot_path: str, game_state: Dict[str, Any]):
        """Process screenshot through AI and send commands back to mGBA"""
        try:
            # Show screenshot in chat (sent message)
            self._send_screenshot_message(screenshot_path, game_state)
            
            # Load current configuration from database
            config = self._load_config()
            if not config:
                self._send_chat_message("system", "❌ No AI configuration found")
                return
            
            # TODO: Process through AI (placeholder for now)
            ai_response = self._call_ai_api(screenshot_path, game_state, config)
            
            # Show AI response in chat (received message)
            self._send_ai_response_message(ai_response)
            
            # Send button commands to mGBA
            if ai_response.get("actions"):
                self._send_button_commands(ai_response["actions"])
            
            self.decision_count += 1
            
            # Wait for cooldown, then request next screenshot
            cooldown = config.get("decision_cooldown", 3)
            time.sleep(cooldown)
            self._request_screenshot()
            
        except Exception as e:
            print(f"❌ AI decision error: {e}")
            traceback.print_exc()
            self._send_chat_message("system", f"❌ AI decision error: {str(e)}")
    
    def _load_config(self) -> Optional[Dict[str, Any]]:
        """Load configuration from SQLite database"""
        try:
            config = Configuration.get_config()
            return config.to_dict()
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return None
    
    def _call_ai_api(self, screenshot_path: str, game_state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Call AI API with screenshot and game state"""
        try:
            # Initialize LLM client if needed
            if not self.llm_client:
                self.llm_client = LLMClient(config)
            
            # Call LLM with error handling and timeout
            print(f"🤖 Calling {config.get('llm_provider', 'unknown')} API...")
            start_time = time.time()
            
            result = self.llm_client.analyze_game_state(screenshot_path, game_state)
            
            elapsed = time.time() - start_time
            print(f"⏱️ AI response received in {elapsed:.1f}s")
            
            return result
            
        except Exception as e:
            print(f"❌ AI API call failed: {e}")
            traceback.print_exc()
            return {
                "text": f"AI API failed: {str(e)}. Using fallback actions.",
                "actions": ["A"],  # Safe fallback
                "success": False,
                "error": str(e)
            }
    
    def _request_screenshot(self):
        """Request a screenshot from mGBA"""
        if self.mgba_connected and self.client_socket:
            try:
                self.client_socket.send("request_screenshot\n".encode('utf-8'))
                print("📸 Requested screenshot from mGBA")
            except Exception as e:
                print(f"❌ Error requesting screenshot: {e}")
    
    def _send_button_commands(self, actions: list):
        """Send button commands to mGBA"""
        if not self.mgba_connected or not self.client_socket:
            return
        
        try:
            # Convert action names to button codes (placeholder mapping)
            button_map = {
                "A": "0", "B": "1", "SELECT": "2", "START": "3",
                "RIGHT": "4", "LEFT": "5", "UP": "6", "DOWN": "7", "R": "8", "L": "9"
            }
            
            button_codes = [button_map.get(action, "0") for action in actions]
            command = ",".join(button_codes)
            
            self.client_socket.send(f"{command}\n".encode('utf-8'))
            print(f"🎮 Sent button commands: {actions} -> {command}")
            
            self._send_chat_message("system", f"✅ Commands sent: {', '.join(actions)}")
            
        except Exception as e:
            print(f"❌ Error sending button commands: {e}")
    
    def _send_chat_message(self, message_type: str, content: str):
        """Send a message to the frontend chat interface"""
        try:
            message = {
                "type": "system",
                "content": content,
                "timestamp": datetime.now().isoformat()
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
                
                message = {
                    "type": "screenshot",
                    "image_data": f"data:image/png;base64,{image_data}",
                    "game_state": position_text,
                    "timestamp": datetime.now().isoformat()
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
            message = {
                "type": "ai_response",
                "text": ai_response.get("text", ""),
                "actions": ai_response.get("actions", []),
                "success": ai_response.get("success", True),
                "timestamp": datetime.now().isoformat()
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