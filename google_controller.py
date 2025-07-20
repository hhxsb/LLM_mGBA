#!/usr/bin/env python3
import os
import socket
import time
import threading
import PIL.Image
import signal
import sys
import atexit
import argparse
import json
from collections import deque
from typing import Dict, List, Any, Tuple

# Import from your existing modules
from pokemon_logger import PokemonLogger
from knowledge_system import KnowledgeGraph

class Tool:
    """Simple class to define a tool for the LLM"""
    def __init__(self, name: str, description: str, parameters: List[Dict[str, Any]]):
        self.name = name
        self.description = description
        self.parameters = parameters
    
    def to_gemini_format(self) -> Dict[str, Any]:
        """Convert to Gemini's expected format"""
        properties = {}
        for p in self.parameters:
            prop = {
                "type": p["type"],
                "description": p["description"]
            }
            # Handle array types with items
            if p["type"] == "array" and "items" in p:
                prop["items"] = p["items"]
            # Handle enum values
            if "enum" in p:
                prop["enum"] = p["enum"]
            properties[p["name"]] = prop
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": [p["name"] for p in self.parameters if p.get("required", False)]
            }
        }

class ToolCall:
    """Represents a tool call from the LLM"""
    def __init__(self, id: str, name: str, arguments: Dict[str, Any]):
        self.id = id
        self.name = name
        self.arguments = arguments

class GeminiClient:
    """Client specifically for communicating with Gemini"""
    def __init__(self, api_key: str, model_name: str, max_tokens: int = 1024):
        self.api_key = api_key
        self.model_name = model_name
        self.max_tokens = max_tokens
        self._setup_client()
    
    def _setup_client(self):
        """Set up the Gemini client"""
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        self.client = genai
    
    def call_with_tools(self, message: str, tools: List[Tool], images: List[PIL.Image.Image] = None) -> Tuple[Any, List[ToolCall], str]:
        """
        Call Gemini with the given message and tools, optionally including images
        """
        import google.generativeai as genai
        
        provider_tools = [tool.to_gemini_format() for tool in tools]
        
        model = self.client.GenerativeModel(model_name=self.model_name)
        
        system_message = """
        You are playing Pokémon. Your job is to press buttons to control the game.
        
        IMPORTANT: After analyzing the screenshot, you MUST use the press_button function.
        You are REQUIRED to use the press_button function with every response.
        
        NEVER just say what button to press - ALWAYS use the press_button function to actually press it.
        
        You can specify multiple buttons to press in sequence by providing a list of buttons.
        For example, you might press ["UP", "UP", "A"] to move up twice then interact.

        Your overall goals are: 1. Beat the Elite Four and become champion. 2. Collect all pokemons. 3. fight all gyms.
        """
        
        chat = model.start_chat(
            history=[
                {"role": "user", "parts": [system_message]},
                {"role": "model", "parts": ["I understand. For every screenshot, I will use the press_button function to specify which button to press (A, B, UP, DOWN, LEFT, RIGHT, START or SELECT)."]}
            ]
        )
        
        enhanced_message = f"{message}\n\nIMPORTANT: You MUST use the press_button function. Select which button(s) to press (A, B, UP, DOWN, LEFT, RIGHT, START or SELECT). You can specify multiple buttons in a list to press them in sequence."
        
        content_parts = [enhanced_message]
        
        if images:
            for image in images:
                content_parts.append(image)
        
        response = chat.send_message(
            content=content_parts,
            generation_config={
                "max_output_tokens": self.max_tokens,
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 0
            },
            tools={"function_declarations": provider_tools}
        )
        
        # Check for safety-filtered or blocked responses
        if hasattr(response, "candidates") and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, "finish_reason"):
                    if candidate.finish_reason == 2:  # SAFETY
                        print("⚠️ WARNING: Response blocked by safety filter. Retrying with fallback action...")
                        # Return a safe fallback response to keep the game going
                        fallback_response = self._create_fallback_response()
                        return fallback_response, self._parse_tool_calls(fallback_response), "Safety filter activated - using fallback action"
                    elif candidate.finish_reason == 3:  # RECITATION
                        print("⚠️ WARNING: Response blocked for recitation. Retrying with fallback action...")
                        fallback_response = self._create_fallback_response()
                        return fallback_response, self._parse_tool_calls(fallback_response), "Recitation filter activated - using fallback action"
        
        return response, self._parse_tool_calls(response), self._extract_text(response)
    
    def _create_fallback_response(self):
        """Create a fallback response when the main response is blocked"""
        # Create a mock response object that contains a safe button press
        class MockResponse:
            def __init__(self):
                self.candidates = [MockCandidate()]
        
        class MockCandidate:
            def __init__(self):
                self.content = MockContent()
        
        class MockContent:
            def __init__(self):
                self.parts = [MockPart()]
        
        class MockPart:
            def __init__(self):
                self.function_call = MockFunctionCall()
        
        class MockFunctionCall:
            def __init__(self):
                self.name = "press_button"
                self.args = MockArgs()
        
        class MockArgs:
            def __init__(self):
                pass
            
            def items(self):
                # Return a safe default action - just press B (cancel/back)
                return [("buttons", ["B"])]
        
        return MockResponse()
    
    def _parse_tool_calls(self, response: Any) -> List[ToolCall]:
        """Parse tool calls from Gemini's response"""
        tool_calls = []
        
        try:
            if hasattr(response, "candidates"):
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and candidate.content:
                        for part in candidate.content.parts:
                            if hasattr(part, "function_call") and part.function_call:
                                if hasattr(part.function_call, "name") and part.function_call.name:
                                    args = {}
                                    if hasattr(part.function_call, "args") and part.function_call.args is not None:
                                        try:
                                            if hasattr(part.function_call.args, "items"):
                                                for key, value in part.function_call.args.items():
                                                    # Handle protobuf list values
                                                    if hasattr(value, '__iter__') and not isinstance(value, str):
                                                        # It's a list-like object, convert to actual list
                                                        args[key] = [str(item) for item in value]
                                                    else:
                                                        args[key] = str(value)
                                            else:
                                                args = {"argument": str(part.function_call.args)}
                                        except Exception as e:
                                            print(f"Error parsing function call args: {e}")
                                            pass
                                    
                                    tool_calls.append(ToolCall(
                                        id=f"call_{len(tool_calls)}",
                                        name=part.function_call.name,
                                        arguments=args
                                    ))
        except Exception as e:
            print(f"Error parsing Gemini tool calls: {e}")
            import traceback
            print(traceback.format_exc())
        
        for call in tool_calls:
            print(f"Tool call: {call.name}, args: {call.arguments}")
        
        return tool_calls
    
    def _extract_text(self, response: Any) -> str:
        """Extract text from the Gemini response"""
        try:
            # Handle the structured response format first
            if hasattr(response, "candidates") and response.candidates:
                text_parts = []
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and candidate.content:
                        # Handle both direct parts and nested parts
                        if hasattr(candidate.content, "parts"):
                            for part in candidate.content.parts:
                                # Only get text parts, not function_call parts
                                if hasattr(part, "text") and part.text:
                                    text_parts.append(part.text)
                        elif hasattr(candidate.content, "text"):
                            text_parts.append(candidate.content.text)
                
                if text_parts:
                    return "\n".join(text_parts)
            
            # Handle result attribute if it exists
            if hasattr(response, "result") and response.result:
                return self._extract_text(response.result)
            
            # Try the direct text attribute last (this might cause the error)
            if hasattr(response, "text"):
                try:
                    return response.text
                except Exception:
                    # If response.text fails, we've already extracted from candidates above
                    pass
                
        except Exception as e:
            # Handle specific error cases
            error_msg = str(e)
            if "Could not convert" in error_msg and "function_call" in error_msg:
                # Expected error when trying to convert function calls to text
                pass
            elif "quick accessor requires the response to contain a valid" in error_msg:
                # Safety filter or blocked response - already handled in call_with_tools
                pass
            elif "finish_reason" in error_msg:
                # Response was blocked by safety systems
                pass
            else:
                print(f"Error extracting text: {e}")
        
        return ""

class PokemonController:
    def __init__(self, config_path='config.json'):
        self._cleanup_done = False
        self._cleanup_lock = threading.Lock()
        
        # Load config directly from JSON file
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Failed to load config from {config_path}: {e}")
            sys.exit(1)
        
        # Ensure paths are absolute
        if 'notepad_path' in self.config and not os.path.isabs(self.config['notepad_path']):
            self.config['notepad_path'] = os.path.abspath(self.config['notepad_path'])
            
        if 'screenshot_path' in self.config and not os.path.isabs(self.config['screenshot_path']):
            self.config['screenshot_path'] = os.path.abspath(self.config['screenshot_path'])
            
        if 'video_path' in self.config and not os.path.isabs(self.config['video_path']):
            self.config['video_path'] = os.path.abspath(self.config['video_path'])
        
        provider_config = self.config["providers"]["google"]
        
        self.llm_client = GeminiClient(
            api_key=provider_config["api_key"],
            model_name=provider_config["model_name"],
            max_tokens=provider_config.get("max_tokens", 1024)
        )
        
        self.server_socket = None
        self.tools = self._define_tools()
        
        self.notepad_path = self.config['notepad_path']
        self.screenshot_path = self.config['screenshot_path']
        self.video_path = self.config['video_path']
        self.current_client = None
        self.running = True
        self.decision_cooldown = self.config['decision_cooldown']
        self.client_threads = []
        self.debug_mode = self.config.get('debug_mode', False)
        
        # Prompt management
        self.prompt_template_path = self.config.get('prompt_template_path', 'data/prompt_template.txt')
        if not os.path.isabs(self.prompt_template_path):
            self.prompt_template_path = os.path.abspath(self.prompt_template_path)
        self.prompt_template = ""
        self.prompt_last_modified = 0
        
        # Game state tracking
        self.player_direction = "UNKNOWN"
        self.player_x = 0
        self.player_y = 0
        self.map_id = 0
        
        # Processing state flags
        self.is_processing = False
        self.emulator_ready = False
        
        # Modified: Store timestamp, button, full reasoning text, and position/direction
        self.recent_actions = deque(maxlen=10)
        
        os.makedirs(os.path.dirname(self.notepad_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.screenshot_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.video_path), exist_ok=True)
        
        self.logger = PokemonLogger(debug_mode=self.debug_mode)
        self.initialize_notepad()
        self.load_prompt_template()
        
        # Initialize knowledge system
        self.knowledge = KnowledgeGraph(
            knowledge_file=self.config.get('knowledge_file', 'data/knowledge_graph.json')
        )
        
        self.logger.info("Controller initialized")
        self.logger.debug(f"Notepad path: {self.notepad_path}")
        self.logger.debug(f"Screenshot path: {self.screenshot_path}")
        self.logger.debug(f"Prompt template path: {self.prompt_template_path}")
        
        self.setup_socket()
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        atexit.register(self.cleanup)

    def _define_tools(self) -> List[Tool]:
        """Define the tools needed for the Pokémon game controller"""
        press_button = Tool(
            name="press_button",
            description="Press one or more buttons on the Game Boy emulator to control the game. You can specify multiple buttons to press in sequence, and optionally specify how long to hold each button.",
            parameters=[{
                "name": "buttons",
                "type": "array",
                "description": "List of buttons to press in sequence (A, B, START, SELECT, UP, DOWN, LEFT, RIGHT, R, L)",
                "required": True,
                "items": {
                    "type": "string",
                    "enum": ["A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L"]
                }
            }, {
                "name": "durations",
                "type": "array",
                "description": "Optional list of durations in frames (60fps) to hold each button. If not specified, uses default duration of 2 frames. Must have same length as buttons array if provided. Valid range: 1-180 frames.",
                "required": False,
                "items": {
                    "type": "integer"
                }
            }]
        )
        
        update_notepad = Tool(
            name="update_notepad",
            description="Update the AI's long-term memory with new information about the game state",
            parameters=[{
                "name": "content",
                "type": "string",
                "description": "Content to add to the notepad. Only include important information about game progress, objectives, or status.",
                "required": True
            }]
        )
        
        record_success = Tool(
            name="record_success",
            description="Record a successful action or strategy for future reference",
            parameters=[{
                "name": "situation",
                "type": "string",
                "description": "Description of the situation where this action worked",
                "required": True
            }, {
                "name": "successful_action",
                "type": "string", 
                "description": "The action or sequence that was successful",
                "required": True
            }]
        )
        
        detect_goal = Tool(
            name="detect_goal",
            description="Identify and record a new goal based on game dialogue or situation",
            parameters=[{
                "name": "goal_description",
                "type": "string",
                "description": "Clear description of the goal or objective",
                "required": True
            }, {
                "name": "priority",
                "type": "integer",
                "description": "Priority level 1-10 (10 being highest priority)",
                "required": True
            }]
        )
        
        return [press_button, update_notepad, record_success, detect_goal]

    def load_prompt_template(self):
        """Load the prompt template from file"""
        try:
            if os.path.exists(self.prompt_template_path):
                with open(self.prompt_template_path, 'r') as f:
                    self.prompt_template = f.read()
                self.prompt_last_modified = os.path.getmtime(self.prompt_template_path)
                self.logger.success(f"Loaded prompt template from {self.prompt_template_path}")
            else:
                self.logger.warning(f"Prompt template file not found: {self.prompt_template_path}")
                self.logger.info("Using default embedded prompt")
                self.prompt_template = self._get_default_prompt()
        except Exception as e:
            self.logger.error(f"Failed to load prompt template: {e}")
            self.prompt_template = self._get_default_prompt()

    def check_prompt_updates(self):
        """Check if the prompt template file has been updated"""
        try:
            if os.path.exists(self.prompt_template_path):
                current_modified = os.path.getmtime(self.prompt_template_path)
                if current_modified > self.prompt_last_modified:
                    old_length = len(self.prompt_template)
                    self.load_prompt_template()
                    new_length = len(self.prompt_template)
                    self.logger.success(f"🔄 Prompt template reloaded! ({old_length} → {new_length} chars)")
                    return True
        except Exception as e:
            self.logger.error(f"Error checking prompt updates: {e}")
        return False

    def _get_default_prompt(self):
        """Get the default embedded prompt as fallback"""
        return """You are an AI playing Pokémon, you are the character with the white hair. The name is GEMINI. Look at this screenshot and choose button(s) to press.

## Current Location
You are in {current_map}
Position: X={player_x}, Y={player_y}

## Current Direction
You are facing: {player_direction}

## Controls:
- A: To talk to people or interact with objects or advance text (NOT for entering/exiting buildings)
- B: To cancel or go back
- UP, DOWN, LEFT, RIGHT: To move your character (use these to enter/exit buildings)
- START: To open the main menu
- SELECT: Rarely used special function

## Multi-Button Actions:
You can now press multiple buttons in sequence by providing a list like ["UP", "UP", "A"] to move up twice then interact.
This is useful for:
- Moving multiple steps: ["UP", "UP", "UP"]
- Moving then interacting: ["RIGHT", "A"]

{recent_actions}

{direction_guidance}

## Long-term Memory (Game State):
{notepad_content}

## IMPORTANT INSTRUCTIONS:
1. FIRST, provide a SHORT paragraph (2-3 sentences) describing what you see in the screenshot.
2. THEN, provide a BRIEF explanation of what you plan to do and why.
3. FINALLY, use the press_button function to execute your decision."""

    def setup_socket(self):
        """Set up the socket server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            try:
                self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
            except (AttributeError, OSError):
                self.logger.debug("TCP keepalive options not fully supported")
            
            try:
                self.server_socket.bind((self.config['host'], self.config['port']))
            except socket.error:
                self.logger.warning(f"Port {self.config['port']} in use. Attempting to free it...")
                os.system(f"lsof -ti:{self.config['port']} | xargs kill -9")
                time.sleep(1)
                self.server_socket.bind((self.config['host'], self.config['port']))
            
            self.server_socket.listen(1)
            self.server_socket.settimeout(1)
            self.logger.success(f"Socket server set up on {self.config['host']}:{self.config['port']}")
        except socket.error as e:
            self.logger.error(f"Socket setup error: {e}")
            sys.exit(1)

    def signal_handler(self, sig, _frame):
        """Handle termination signals"""
        print(f"\nReceived signal {sig}. Shutting down server...")
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

    def initialize_notepad(self):
        """Initialize the notepad file with clear game objectives"""
        if not os.path.exists(self.notepad_path):
            os.makedirs(os.path.dirname(self.notepad_path), exist_ok=True)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(self.notepad_path, 'w') as f:
                f.write("# Pokémon Red Game Progress\n\n")
                f.write(f"Game started: {timestamp}\n\n")
                f.write("## Current Objectives\n- Enter my name 'Gemini' and give my rival a name.\n\n")
                f.write("## Exit my house\n\n")
                f.write("## Current Objectives\n- Find Professor Oak to get first Pokémon\n- Start Pokémon journey\n\n")
                f.write("## Current Location\n- Starting in player's house in Pallet Town\n\n")
                f.write("## Game Progress\n- Just beginning the adventure\n\n")
                f.write("## Items\n- None yet\n\n")
                f.write("## Pokémon Team\n- None yet\n\n")

    def read_notepad(self):
        """Read the current notepad content"""
        try:
            with open(self.notepad_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading notepad: {e}")
            return "Error reading notepad"

    def update_notepad(self, new_content):
        """Update the notepad"""
        try:
            current_content = self.read_notepad()
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            updated_content = current_content + f"\n## Update {timestamp}\n{new_content}\n"
            with open(self.notepad_path, 'w') as f:
                f.write(updated_content)
            self.logger.debug("Notepad updated")
            if len(updated_content) > 10000:
                self.summarize_notepad()
        except Exception as e:
            self.logger.error(f"Error updating notepad: {e}")

    def summarize_notepad(self):
        """Summarize the notepad when it gets too long"""
        try:
            self.logger.info("Notepad is getting large, summarizing...")
            notepad_content = self.read_notepad()
            summarize_prompt = """
            Please summarize the following game notes into a more concise format.
            Maintain these key sections:
            - Current Status
            - Game Progress
            - Important Items
            - Pokemon Team
            Remove redundant information while preserving all important game state details.
            Format the response as a well-structured markdown document.
            Here are the notes to summarize:
            """
            _, _, text = self.llm_client.call_with_tools(
                message=summarize_prompt + notepad_content,
                tools=[]
            )
            if text:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                summary = f"# Pokémon Game AI Notepad (Summarized)\n\n"
                summary += f"Last summarized: {timestamp}\n\n"
                summary += text
                with open(self.notepad_path, 'w') as f:
                    f.write(summary)
                self.logger.success("Notepad summarized successfully")
        except Exception as e:
            self.logger.error(f"Error summarizing notepad: {e}")

    def get_recent_actions_text(self):
        """Get formatted text of recent actions with reasoning and position/direction"""
        if not self.recent_actions:
            return "No recent actions."
        
        recent_actions_text = "## Short-term Memory (Recent Actions and Reasoning):\n"
        for i, (timestamp, button, reasoning, direction, x, y, map_id) in enumerate(self.recent_actions, 1):
            recent_actions_text += f"{i}. [{timestamp}] Pressed {button} while facing {direction} at position ({x}, {y}) on map {map_id}\n"
            recent_actions_text += f"   Reasoning: {reasoning.strip()}\n\n"
        return recent_actions_text

    def get_direction_guidance_text(self):
        """Generate guidance text about player orientation and interactions"""
        directions = {
            "UP": "north",
            "DOWN": "south", 
            "LEFT": "west",
            "RIGHT": "east"
        }
        
        facing_direction = directions.get(self.player_direction, self.player_direction)
        
        guidance = f"""
        ## Navigation Tips:
        - To INTERACT with objects or NPCs, you MUST be FACING them and then press A
        - Your current direction is {self.player_direction} (facing {facing_direction})
        - Your current position is (X={self.player_x}, Y={self.player_y}) on map {self.map_id}
        - If you need to face a different direction, press the appropriate directional button first
        - In buildings, look for exits via stairs, doors, or red mats and walk directly over them
        """
        
        return guidance

    def get_map_name(self, map_id):
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
            # Add more map IDs as you explore the game
        }
        
        return map_names.get(map_id, f"Unknown Area (Map ID: {map_id})")

    def process_screenshot(self, screenshot_path=None):
        """Process a screenshot with enhanced game state information"""
        if self.is_processing:
            self.logger.debug("Already processing a decision, skipping")
            return None
            
        self.is_processing = True
        try:
            # Check for prompt updates
            self.check_prompt_updates()
            
            # Update knowledge system with current location
            current_map = self.get_map_name(self.map_id)
            self.knowledge.update_location(self.map_id, current_map, self.player_x, self.player_y, self.player_direction)
            
            # Get enhanced context from knowledge system
            notepad_content = self.read_notepad()
            recent_actions = self.get_recent_actions_text()
            direction_guidance = self.get_direction_guidance_text()
            knowledge_context = self.knowledge.generate_context_summary()
            navigation_advice = self.knowledge.get_navigation_advice(self.map_id)
            location_context = self.knowledge.get_location_context(self.map_id)
            
            path_to_use = screenshot_path if screenshot_path else self.screenshot_path
            
            if not os.path.exists(path_to_use):
                self.logger.error(f"Screenshot not found at {path_to_use}")
                self.is_processing = False
                return None
            
            # Load and enhance the image
            original_image = PIL.Image.open(path_to_use)
            
            # Scale the image to 3x its original size for better detail recognition
            scale_factor = 3
            scaled_width = original_image.width * scale_factor
            scaled_height = original_image.height * scale_factor
            scaled_image = original_image.resize((scaled_width, scaled_height), PIL.Image.LANCZOS)
            
            # Enhance contrast for better visibility
            from PIL import ImageEnhance
            contrast_enhancer = ImageEnhance.Contrast(scaled_image)
            contrast_image = contrast_enhancer.enhance(1.5)  # Increase contrast by 50%
            
            # Enhance color saturation for better color visibility
            saturation_enhancer = ImageEnhance.Color(contrast_image)
            enhanced_image = saturation_enhancer.enhance(1.8)  # Increase saturation by 80%
            
            # Optionally enhance brightness slightly
            brightness_enhancer = ImageEnhance.Brightness(enhanced_image)
            final_image = brightness_enhancer.enhance(1.1)  # Increase brightness by 10%
            
            # Use the template and format it with current game state and knowledge
            prompt = self.prompt_template.format(
                current_map=current_map,
                player_x=self.player_x,
                player_y=self.player_y,
                player_direction=self.player_direction,
                recent_actions=recent_actions,
                direction_guidance=direction_guidance,
                notepad_content=notepad_content
            )
            
            # Add knowledge system context
            prompt += f"\n\n{knowledge_context}"
            if navigation_advice:
                prompt += f"\n## Navigation Advice:\n{navigation_advice}\n"
            if location_context:
                prompt += f"\n## Location Context:\n{location_context}\n"
            
            images = [final_image]
            self.logger.section(f"Requesting decision from LLM")
            
            _, tool_calls, text = self.llm_client.call_with_tools(
                message=prompt,
                tools=self.tools,
                images=images
            )
            
            print(f"LLM Text Response: {text}")
            
            for call in tool_calls:
                if call.name == "update_notepad":
                    content = call.arguments.get("content", "")
                    if content:
                        self.update_notepad(content)
                        print(f"Updated notepad with: {content[:50]}...")
                
                elif call.name == "record_success":
                    situation = call.arguments.get("situation", "")
                    successful_action = call.arguments.get("successful_action", "")
                    if situation and successful_action:
                        # Find and update the corresponding failure pattern
                        for pattern in self.knowledge.failure_patterns.values():
                            if situation.lower() in pattern.situation.lower():
                                pattern.successful_alternative = successful_action
                                self.knowledge.save_knowledge()
                                break
                        print(f"🧠 Recorded successful strategy: {successful_action[:50]}...")
                
                elif call.name == "detect_goal":
                    goal_description = call.arguments.get("goal_description", "")
                    priority = call.arguments.get("priority", 5)
                    if goal_description:
                        goal_id = f"detected_{int(time.time())}"
                        from knowledge_system import Goal
                        goal = Goal(
                            id=goal_id,
                            description=goal_description,
                            type="detected",
                            status="active",
                            priority=int(priority),
                            location_id=self.map_id
                        )
                        self.knowledge.goals[goal_id] = goal
                        self.knowledge.save_knowledge()
                        print(f"🎯 New goal detected: {goal_description}")
                
                elif call.name == "press_button":
                    buttons = call.arguments.get("buttons", [])
                    durations = call.arguments.get("durations", [])
                    
                    button_map = {
                        "A": 0, "B": 1, "SELECT": 2, "START": 3,
                        "RIGHT": 4, "LEFT": 5, "UP": 6, "DOWN": 7,
                        "R": 8, "L": 9
                    }
                    
                    if buttons:
                        button_codes = []
                        button_durations = []
                        valid_buttons = []
                        
                        for i, button in enumerate(buttons):
                            button = str(button).upper()
                            if button in button_map:
                                button_codes.append(button_map[button])
                                valid_buttons.append(button)
                                
                                # Use provided duration or default (2 frames)
                                if durations and i < len(durations):
                                    try:
                                        duration = max(1, min(180, int(float(durations[i]))))  # Convert float to int, clamp between 1-180
                                        button_durations.append(duration)
                                    except (ValueError, TypeError):
                                        button_durations.append(2)  # Default on error
                                else:
                                    button_durations.append(2)  # Default 2 frames
                        
                        if button_codes:
                            buttons_str = ", ".join(valid_buttons)
                            if durations:
                                durations_str = ", ".join(str(d) for d in button_durations)
                                self.logger.success(f"Tool used buttons: {buttons_str} (durations: {durations_str} frames)")
                            else:
                                self.logger.success(f"Tool used buttons: {buttons_str}")
                            
                            # Store timestamp, buttons, reasoning, and position/direction
                            timestamp = time.strftime("%H:%M:%S")
                            self.recent_actions.append(
                                (timestamp, buttons_str, text, self.player_direction, 
                                self.player_x, self.player_y, self.map_id)
                            )
                            
                            # Record action in knowledge system for learning
                            self.knowledge.record_action(
                                action=buttons_str,
                                result=text[:200],  # First 200 chars of reasoning
                                location=self.map_id,
                                success=True  # Assume success for now, can be updated later
                            )
                            
                            self.logger.ai_action(buttons_str, button_codes)
                            return {'buttons': button_codes, 'durations': button_durations}
            
            if not any(call.name == "press_button" for call in tool_calls):
                self.logger.warning("No press_button tool call found!")
                return None
            
        except Exception as e:
            self.logger.error(f"Error processing screenshot: {e}")
            if self.debug_mode:
                import traceback
                self.logger.debug(traceback.format_exc())
        finally:
            self.is_processing = False
        return None

    def process_video(self, video_path, button_count):
        """Process a video sequence with enhanced game state information"""
        if self.is_processing:
            self.logger.debug("Already processing a decision, skipping")
            return None
            
        self.is_processing = True
        try:
            # Check for prompt updates
            self.check_prompt_updates()
            
            # Update knowledge system with current location
            current_map = self.get_map_name(self.map_id)
            self.knowledge.update_location(self.map_id, current_map, self.player_x, self.player_y, self.player_direction)
            
            # Get enhanced context from knowledge system
            notepad_content = self.read_notepad()
            recent_actions = self.get_recent_actions_text()
            direction_guidance = self.get_direction_guidance_text()
            knowledge_context = self.knowledge.generate_context_summary()
            navigation_advice = self.knowledge.get_navigation_advice(self.map_id)
            location_context = self.knowledge.get_location_context(self.map_id)
            
            if not os.path.exists(video_path):
                self.logger.error(f"Video not found at {video_path}")
                self.is_processing = False
                return None
            
            # Create video-specific prompt
            video_prompt = self.prompt_template.format(
                current_map=current_map,
                player_x=self.player_x,
                player_y=self.player_y,
                player_direction=self.player_direction,
                recent_actions=recent_actions,
                direction_guidance=direction_guidance,
                notepad_content=notepad_content,
                knowledge_context=knowledge_context,
                navigation_advice=navigation_advice,
                location_context=location_context
            )
            
            # Add video-specific context
            video_context = f"\n\n## Video Analysis Context\n"
            video_context += f"This video shows the results of your previous {button_count} button press(es).\n"
            video_context += f"Watch the sequence to understand:\n"
            video_context += f"- How the game responded to your actions\n"
            video_context += f"- What changes occurred in the game state\n"
            video_context += f"- Whether your actions achieved the intended result\n"
            video_context += f"- What the current situation is after the sequence\n\n"
            video_context += f"Based on this video sequence, decide your next action."
            
            enhanced_prompt = video_prompt + video_context
            
            # Read the video file and send to LLM
            with open(video_path, 'rb') as f:
                video_data = f.read()
            
            # Create video part for Gemini
            video_part = {
                "mime_type": "video/mp4",
                "data": video_data
            }
            
            self.logger.debug(f"Sending video to LLM: {video_path} ({len(video_data)} bytes)")
            
            # Send to LLM with video
            response, tool_calls, response_text = self.llm_client.call_with_tools(
                enhanced_prompt,
                images=[video_part],  # Gemini handles both images and videos in the same parameter
                tools=self.tools
            )
            
            print(f"LLM Text Response: {response_text}")
            
            # Process tool calls directly (same as process_screenshot)
            for call in tool_calls:
                if call.name == "update_notepad":
                    content = call.arguments.get("content", "")
                    if content:
                        self.update_notepad(content)
                        print(f"Updated notepad with: {content[:50]}...")
                
                elif call.name == "record_success":
                    situation = call.arguments.get("situation", "")
                    successful_action = call.arguments.get("successful_action", "")
                    if situation and successful_action:
                        # Find and update the corresponding failure pattern
                        for pattern in self.knowledge.failure_patterns.values():
                            if situation.lower() in pattern.situation.lower():
                                pattern.successful_alternative = successful_action
                                self.knowledge.save_knowledge()
                                break
                        print(f"🧠 Recorded successful strategy: {successful_action[:50]}...")
                
                elif call.name == "detect_goal":
                    goal_description = call.arguments.get("goal_description", "")
                    priority = call.arguments.get("priority", 5)
                    if goal_description:
                        goal_id = f"detected_{int(time.time())}"
                        from knowledge_system import Goal
                        goal = Goal(
                            id=goal_id,
                            description=goal_description,
                            type="detected",
                            status="active",
                            priority=int(priority),
                            location_id=self.map_id
                        )
                        self.knowledge.goals[goal_id] = goal
                        self.knowledge.save_knowledge()
                        print(f"🎯 New goal detected: {goal_description}")
                
                elif call.name == "press_button":
                    buttons = call.arguments.get("buttons", [])
                    durations = call.arguments.get("durations", [])
                    
                    button_map = {
                        "A": 0, "B": 1, "SELECT": 2, "START": 3,
                        "RIGHT": 4, "LEFT": 5, "UP": 6, "DOWN": 7,
                        "R": 8, "L": 9
                    }
                    
                    if buttons:
                        button_codes = []
                        button_durations = []
                        valid_buttons = []
                        
                        for i, button in enumerate(buttons):
                            button = str(button).upper()
                            if button in button_map:
                                button_codes.append(button_map[button])
                                valid_buttons.append(button)
                                
                                # Use provided duration or default (2 frames)
                                if durations and i < len(durations):
                                    try:
                                        duration = max(1, min(180, int(float(durations[i]))))  # Convert float to int, clamp between 1-180
                                        button_durations.append(duration)
                                    except (ValueError, TypeError):
                                        button_durations.append(2)  # Default on error
                                else:
                                    button_durations.append(2)  # Default 2 frames
                        
                        if button_codes:
                            buttons_str = ", ".join(valid_buttons)
                            if durations:
                                durations_str = ", ".join(str(d) for d in button_durations)
                                self.logger.success(f"Tool used buttons: {buttons_str} (durations: {durations_str} frames)")
                            else:
                                self.logger.success(f"Tool used buttons: {buttons_str}")
                            
                            # Store timestamp, buttons, reasoning, and position/direction
                            timestamp = time.strftime("%H:%M:%S")
                            self.recent_actions.append(
                                (timestamp, buttons_str, response_text, self.player_direction, 
                                self.player_x, self.player_y, self.map_id)
                            )
                            
                            # Record action in knowledge system for learning
                            self.knowledge.record_action(
                                action=buttons_str,
                                result=response_text[:200],  # First 200 chars of reasoning
                                location=self.map_id,
                                success=True  # Assume success for now, can be updated later
                            )
                            
                            self.logger.ai_action(buttons_str, button_codes)
                            return {'buttons': button_codes, 'durations': button_durations}
            
            if not any(call.name == "press_button" for call in tool_calls):
                self.logger.warning("No press_button tool call found!")
                return None
                
        except Exception as e:
            self.logger.error(f"Error processing video: {e}")
            if self.debug_mode:
                import traceback
                self.logger.debug(traceback.format_exc())
        finally:
            self.is_processing = False
        return None

    def process_enhanced_screenshot(self, screenshot_path, previous_screenshot_path, button_count):
        """Process an enhanced screenshot with before/after comparison"""
        if self.is_processing:
            self.logger.debug("Already processing a decision, skipping")
            return None
            
        self.is_processing = True
        try:
            # Check for prompt updates
            self.check_prompt_updates()
            
            # Update knowledge system with current location
            current_map = self.get_map_name(self.map_id)
            self.knowledge.update_location(self.map_id, current_map, self.player_x, self.player_y, self.player_direction)
            
            # Get enhanced context from knowledge system
            notepad_content = self.read_notepad()
            recent_actions = self.get_recent_actions_text()
            direction_guidance = self.get_direction_guidance_text()
            knowledge_context = self.knowledge.generate_context_summary()
            navigation_advice = self.knowledge.get_navigation_advice(self.map_id)
            location_context = self.knowledge.get_location_context(self.map_id)
            
            if not os.path.exists(screenshot_path):
                self.logger.error(f"Enhanced screenshot not found at {screenshot_path}")
                self.is_processing = False
                return None
            
            # Load both screenshots
            current_image = PIL.Image.open(screenshot_path)
            previous_image = None
            if os.path.exists(previous_screenshot_path):
                previous_image = PIL.Image.open(previous_screenshot_path)
            
            # Create enhanced screenshot prompt with before/after comparison
            screenshot_prompt = self.prompt_template.format(
                current_map=current_map,
                player_x=self.player_x,
                player_y=self.player_y,
                player_direction=self.player_direction,
                recent_actions=recent_actions,
                direction_guidance=direction_guidance,
                notepad_content=notepad_content,
                knowledge_context=knowledge_context,
                navigation_advice=navigation_advice,
                location_context=location_context
            )
            
            # Add before/after comparison context
            if previous_image:
                comparison_context = f"\n\n## Before/After Screenshot Comparison\n"
                comparison_context += f"You are seeing TWO screenshots:\n"
                comparison_context += f"1. BEFORE: The state before you pressed {button_count} button(s)\n"
                comparison_context += f"2. AFTER: The current state after your button sequence completed\n"
                comparison_context += f"\nCompare the two images to understand:\n"
                comparison_context += f"- What changed between the before and after screenshots?\n"
                comparison_context += f"- Did your button sequence achieve the intended result?\n"
                comparison_context += f"- What progress did you make in the game?\n"
                comparison_context += f"- Are there any new elements, dialogue, or changes in position?\n"
                comparison_context += f"\nUse this comparison to make better decisions about your next action.\n"
            else:
                comparison_context = f"\n\n## Single Screenshot Analysis\n"
                comparison_context += f"This screenshot shows the result after you pressed {button_count} button(s) in sequence.\n"
                comparison_context += f"The image shows the current state AFTER your button sequence completed.\n"
                comparison_context += f"Analyze the result to understand:\n"
                comparison_context += f"- Did your button sequence achieve the intended result?\n"
                comparison_context += f"- What is the current situation after the sequence?\n"
                comparison_context += f"- What should be your next action based on this outcome?\n\n"
                comparison_context += f"Based on this post-sequence screenshot, decide your next action."
            
            enhanced_prompt = screenshot_prompt + comparison_context
            
            # Prepare images for LLM
            images = []
            
            # If we have a previous image, include it first
            if previous_image:
                # Enhance previous image
                scale_factor = 3
                prev_scaled_width = previous_image.width * scale_factor
                prev_scaled_height = previous_image.height * scale_factor
                prev_scaled_image = previous_image.resize((prev_scaled_width, prev_scaled_height), PIL.Image.LANCZOS)
                
                from PIL import ImageEnhance
                prev_contrast_enhancer = ImageEnhance.Contrast(prev_scaled_image)
                prev_contrast_image = prev_contrast_enhancer.enhance(1.5)
                
                prev_saturation_enhancer = ImageEnhance.Color(prev_contrast_image)
                prev_enhanced_image = prev_saturation_enhancer.enhance(1.8)
                
                prev_brightness_enhancer = ImageEnhance.Brightness(prev_enhanced_image)
                prev_final_image = prev_brightness_enhancer.enhance(1.1)
                
                images.append(prev_final_image)
            
            # Load and enhance the current image
            original_image = PIL.Image.open(screenshot_path)
            
            # Scale the image to 3x its original size for better detail recognition
            scale_factor = 3
            scaled_width = original_image.width * scale_factor
            scaled_height = original_image.height * scale_factor
            scaled_image = original_image.resize((scaled_width, scaled_height), PIL.Image.LANCZOS)
            
            # Enhance contrast for better visibility
            from PIL import ImageEnhance
            contrast_enhancer = ImageEnhance.Contrast(scaled_image)
            contrast_image = contrast_enhancer.enhance(1.5)
            
            # Enhance color saturation for better color visibility
            saturation_enhancer = ImageEnhance.Color(contrast_image)
            enhanced_image = saturation_enhancer.enhance(1.8)
            
            # Enhance brightness slightly
            brightness_enhancer = ImageEnhance.Brightness(enhanced_image)
            final_image = brightness_enhancer.enhance(1.1)
            
            images.append(final_image)
            
            self.logger.debug(f"Sending enhanced screenshot to LLM: {screenshot_path} (after {button_count} buttons)")
            
            # Send to LLM with enhanced image(s)
            _, tool_calls, response_text = self.llm_client.call_with_tools(
                enhanced_prompt,
                images=images,
                tools=self.tools
            )
            
            print(f"LLM Text Response: {response_text}")
            
            # Process tool calls directly (same as process_screenshot)
            for call in tool_calls:
                if call.name == "update_notepad":
                    content = call.arguments.get("content", "")
                    if content:
                        self.update_notepad(content)
                        print(f"Updated notepad with: {content[:50]}...")
                
                elif call.name == "record_success":
                    situation = call.arguments.get("situation", "")
                    successful_action = call.arguments.get("successful_action", "")
                    if situation and successful_action:
                        # Find and update the corresponding failure pattern
                        for pattern in self.knowledge.failure_patterns.values():
                            if situation.lower() in pattern.situation.lower():
                                pattern.successful_alternative = successful_action
                                self.knowledge.save_knowledge()
                                break
                        print(f"🧠 Recorded successful strategy: {successful_action[:50]}...")
                
                elif call.name == "detect_goal":
                    goal_description = call.arguments.get("goal_description", "")
                    priority = call.arguments.get("priority", 5)
                    if goal_description:
                        goal_id = f"detected_{int(time.time())}"
                        from knowledge_system import Goal
                        goal = Goal(
                            id=goal_id,
                            description=goal_description,
                            type="detected",
                            status="active",
                            priority=int(priority),
                            location_id=self.map_id
                        )
                        self.knowledge.goals[goal_id] = goal
                        self.knowledge.save_knowledge()
                        print(f"🎯 New goal detected: {goal_description}")
                
                elif call.name == "press_button":
                    buttons = call.arguments.get("buttons", [])
                    durations = call.arguments.get("durations", [])
                    
                    button_map = {
                        "A": 0, "B": 1, "SELECT": 2, "START": 3,
                        "RIGHT": 4, "LEFT": 5, "UP": 6, "DOWN": 7,
                        "R": 8, "L": 9
                    }
                    
                    if buttons:
                        button_codes = []
                        button_durations = []
                        valid_buttons = []
                        
                        for i, button in enumerate(buttons):
                            button = str(button).upper()
                            if button in button_map:
                                button_codes.append(button_map[button])
                                valid_buttons.append(button)
                                
                                # Use provided duration or default (2 frames)
                                if durations and i < len(durations):
                                    try:
                                        duration = max(1, min(180, int(float(durations[i]))))  # Convert float to int, clamp between 1-180
                                        button_durations.append(duration)
                                    except (ValueError, TypeError):
                                        button_durations.append(2)  # Default on error
                                else:
                                    button_durations.append(2)  # Default 2 frames
                        
                        if button_codes:
                            buttons_str = ", ".join(valid_buttons)
                            if durations:
                                durations_str = ", ".join(str(d) for d in button_durations)
                                self.logger.success(f"Tool used buttons: {buttons_str} (durations: {durations_str} frames)")
                            else:
                                self.logger.success(f"Tool used buttons: {buttons_str}")
                            
                            # Store timestamp, buttons, reasoning, and position/direction
                            timestamp = time.strftime("%H:%M:%S")
                            self.recent_actions.append(
                                (timestamp, buttons_str, response_text, self.player_direction, 
                                self.player_x, self.player_y, self.map_id)
                            )
                            
                            # Record action in knowledge system for learning
                            self.knowledge.record_action(
                                action=buttons_str,
                                result=response_text[:200],  # First 200 chars of reasoning
                                location=self.map_id,
                                success=True  # Assume success for now, can be updated later
                            )
                            
                            self.logger.ai_action(buttons_str, button_codes)
                            return {'buttons': button_codes, 'durations': button_durations}
            
            if not any(call.name == "press_button" for call in tool_calls):
                self.logger.warning("No press_button tool call found!")
                return None
                
        except Exception as e:
            self.logger.error(f"Error processing enhanced screenshot: {e}")
            if self.debug_mode:
                import traceback
                self.logger.debug(traceback.format_exc())
        finally:
            self.is_processing = False
        return None

    def handle_client(self, client_socket, client_address):
        """Handle communication with the emulator client"""
        self.logger.section(f"Connected to emulator at {client_address}")
        self.current_client = client_socket
        self.last_decision_time = 0  # Track the time of last decision
        
        self.logger.game_state("Waiting for game data...")
        
        while self.running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                message = data.decode('utf-8').strip()
                parts = message.split("||")
                
                if len(parts) >= 2:
                    message_type = parts[0]
                    content = parts[1:]  # Get all remaining parts
                    
                    # Handle the "ready" message from the emulator
                    if message_type == "ready":
                        self.logger.game_state("Emulator is ready for next command")
                        self.emulator_ready = True
                        
                        # Check if cooldown period has passed
                        current_time = time.time()
                        time_since_last_decision = current_time - self.last_decision_time
                        
                        if time_since_last_decision < self.decision_cooldown:
                            wait_time = self.decision_cooldown - time_since_last_decision
                            self.logger.debug(f"Waiting {wait_time:.2f}s for cooldown before next request")
                            time.sleep(wait_time)
                        
                        # Request a screenshot if we're not currently processing one
                        if not self.is_processing:
                            try:
                                self.logger.debug("Requesting screenshot from emulator")
                                client_socket.send(b'request_screenshot\n')
                            except Exception as e:
                                self.logger.error(f"Failed to request screenshot: {e}")
                    
                    # Handle the screenshot_with_state message type
                    elif message_type == "screenshot_with_state":
                        self.logger.game_state("Received new screenshot with game state from emulator")
                        
                        # Parse the content which now includes game state
                        if len(content) >= 5:  # Path, direction, x, y, mapId
                            screenshot_path = content[0]
                            self.player_direction = content[1]
                            self.player_x = int(content[2])
                            self.player_y = int(content[3])
                            self.map_id = int(content[4])
                            
                            self.logger.debug(f"Game State: Direction={self.player_direction}, " +
                                             f"Position=({self.player_x}, {self.player_y}), " +
                                             f"Map ID={self.map_id}")
                        
                            # Verify the file exists
                            if os.path.exists(screenshot_path):
                                # Process the screenshot with game state info
                                decision = self.process_screenshot(screenshot_path)
                                
                                if decision and decision.get('buttons') is not None:
                                    try:
                                        button_codes = decision['buttons']
                                        button_durations = decision.get('durations', [])
                                        
                                        # Send button codes and durations separated by commas
                                        button_codes_str = ','.join(str(code) for code in button_codes)
                                        if button_durations:
                                            durations_str = ','.join(str(d) for d in button_durations)
                                            message = f"{button_codes_str}|{durations_str}"
                                        else:
                                            message = button_codes_str
                                            
                                        self.logger.debug(f"Sending button data to emulator: {message}")
                                        client_socket.send(message.encode('utf-8') + b'\n')
                                        self.logger.success("Button commands sent to emulator")
                                        self.emulator_ready = False
                                        
                                        # Update the last decision time
                                        self.last_decision_time = time.time()
                                    except Exception as e:
                                        self.logger.error(f"Failed to send button commands: {e}")
                                        break
                    
                    # Handle the enhanced_screenshot_with_state message type
                    elif message_type == "enhanced_screenshot_with_state":
                        self.logger.game_state("Received enhanced screenshot with game state from emulator")
                        
                        # Parse the content which now includes game state and button count
                        if len(content) >= 7:  # Path, previousPath, direction, x, y, mapId, buttonCount
                            screenshot_path = content[0]
                            previous_screenshot_path = content[1]
                            self.player_direction = content[2]
                            self.player_x = int(content[3])
                            self.player_y = int(content[4])
                            self.map_id = int(content[5])
                            button_count = int(content[6])
                            
                            self.logger.debug(f"Game State: Direction={self.player_direction}, " +
                                             f"Position=({self.player_x}, {self.player_y}), " +
                                             f"Map ID={self.map_id}, Button Count={button_count}")
                        
                            # Verify the file exists
                            if os.path.exists(screenshot_path):
                                # Process the enhanced screenshot with before/after comparison
                                decision = self.process_enhanced_screenshot(screenshot_path, previous_screenshot_path, button_count)
                                
                                if decision and decision.get('buttons') is not None:
                                    try:
                                        button_codes = decision['buttons']
                                        button_durations = decision.get('durations', [])
                                        
                                        # Send button codes and durations separated by commas
                                        button_codes_str = ','.join(str(code) for code in button_codes)
                                        if button_durations:
                                            durations_str = ','.join(str(d) for d in button_durations)
                                            message = f"{button_codes_str}|{durations_str}"
                                        else:
                                            message = button_codes_str
                                            
                                        self.logger.debug(f"Sending button data to emulator: {message}")
                                        client_socket.send(message.encode('utf-8') + b'\n')
                                        self.logger.success("Button commands sent to emulator")
                                        self.emulator_ready = False
                                        
                                        # Update the last decision time
                                        self.last_decision_time = time.time()
                                    except Exception as e:
                                        self.logger.error(f"Failed to send button commands: {e}")
                                        break
                                else:
                                    # If no decision was made, we still need to respect the cooldown
                                    self.last_decision_time = time.time()
                                    
                                    # Request another screenshot after a small delay
                                    try:
                                        time.sleep(0.5)  # Small delay to avoid flooding
                                        client_socket.send(b'request_screenshot\n')
                                    except Exception as e:
                                        self.logger.error(f"Failed to request another screenshot: {e}")
                            else:
                                self.logger.error(f"Screenshot file not found at {screenshot_path}")
                
            except socket.error as e:
                if e.args[0] != socket.EWOULDBLOCK and str(e) != 'Resource temporarily unavailable':
                    self.logger.error(f"Socket error: {e}")
                    break
            except Exception as e:
                self.logger.error(f"Error handling client: {e}")
                if self.debug_mode:
                    import traceback
                    self.logger.debug(traceback.format_exc())
                if not self.running:
                    break
                continue
            
            # Add a small delay to avoid CPU spinning
            time.sleep(0.01)
        
        self.logger.section(f"Disconnected from emulator at {client_address}")
        self.current_client = None
        try:
            client_socket.close()
        except:
            pass

    def handle_client_connection(self, client_socket, client_address):
        """Wrapper around handle_client"""
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

    def start(self):
        """Start the controller server"""
        self.logger.header(f"Starting Pokémon Game Controller")
        
        try:
            while self.running:
                try:
                    self.logger.section("Waiting for emulator connection...")
                    client_socket, client_address = self.server_socket.accept()
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    try:
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
                    except (AttributeError, OSError):
                        pass
                    
                    client_socket.setblocking(0)
                    client_thread = threading.Thread(
                        target=self.handle_client_connection,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    self.client_threads.append(client_thread)
                except socket.timeout:
                    continue
                except KeyboardInterrupt:
                    self.logger.section("Keyboard interrupt detected. Shutting down...")
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pokémon Game AI Controller")
    parser.add_argument("--config", "-c", default="config.json", help="Path to the configuration file")
    args = parser.parse_args()
    
    controller = PokemonController(args.config)
    try:
        controller.start()
    except KeyboardInterrupt:
        pass
    finally:
        controller.cleanup()