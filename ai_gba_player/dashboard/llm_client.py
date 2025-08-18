"""
LLM Client for AI Game Service
Handles API calls to different LLM providers with error handling and timeouts.
"""

import os
import time
import base64
from typing import Dict, List, Any, Optional, Tuple
import json
import traceback
from datetime import datetime
from pathlib import Path
import PIL.Image
from PIL import ImageEnhance


class LLMClient:
    """Client for making LLM API calls with robust error handling"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get('llm_provider', 'google')
        self.providers_config = config.get('providers', {})
        self.timeout = config.get('llm_timeout_seconds', 30)
        
        # Notepad and memory paths
        self.notepad_path = Path("/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/notepad.txt")
        
        # Prompt template system
        self.prompt_template_path = Path("/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/prompt_template.txt")
        self.prompt_template = ""
        self.template_last_modified = 0
        self._load_prompt_template()
        
        # Initialize provider-specific clients
        self._init_clients()
    
    def _init_clients(self):
        """Initialize LLM provider clients"""
        try:
            if self.provider == 'google':
                import google.generativeai as genai
                api_key = self.providers_config.get('google', {}).get('api_key', '')
                if api_key:
                    genai.configure(api_key=api_key)
                    self.google_client = genai
                else:
                    self.google_client = None
                    print("⚠️ Google API key not configured")
            
            if self.provider == 'openai':
                from openai import OpenAI
                api_key = self.providers_config.get('openai', {}).get('api_key', '')
                if api_key:
                    self.openai_client = OpenAI(api_key=api_key)
                else:
                    self.openai_client = None
                    print("⚠️ OpenAI API key not configured")
                    
        except ImportError as e:
            print(f"⚠️ LLM provider import error: {e}")
    
    def _load_prompt_template(self):
        """Load prompt template from file with hot-reload capability"""
        try:
            if self.prompt_template_path.exists():
                current_modified = self.prompt_template_path.stat().st_mtime
                if current_modified > self.template_last_modified:
                    with open(self.prompt_template_path, 'r') as f:
                        self.prompt_template = f.read()
                    self.template_last_modified = current_modified
                    print(f"📝 Loaded prompt template from {self.prompt_template_path}")
            else:
                # Fallback to a minimal template if file doesn't exist
                self.prompt_template = "You are an AI playing Pokémon. Look at the screenshot and choose a button to press.\n\n{spatial_context}\n\n{recent_actions}\n\n{notepad_content}"
                print(f"⚠️ Prompt template file not found at {self.prompt_template_path}, using fallback")
        except Exception as e:
            print(f"❌ Error loading prompt template: {e}")
            self.prompt_template = "You are an AI playing Pokémon. Look at the screenshot and choose a button to press.\n\n{spatial_context}\n\n{recent_actions}\n\n{notepad_content}"
    
    def analyze_game_state(self, screenshot_path: str, game_state: Dict[str, Any], recent_actions_text: str = "") -> Dict[str, Any]:
        """
        Analyze game state and return AI decision with enhanced processing
        
        Returns:
            {
                "text": "AI reasoning text",
                "actions": ["UP"],
                "success": True/False,
                "error": "error message if failed"
            }
        """
        try:
            # Load and enhance screenshot
            if not os.path.exists(screenshot_path):
                return {
                    "text": "Screenshot not found",
                    "actions": ["A"],  # Default action
                    "success": False,
                    "error": f"Screenshot file not found: {screenshot_path}"
                }
            
            # Create enhanced game context with recent actions
            context = self._create_game_context(game_state, recent_actions_text)
            
            # Call appropriate LLM provider
            if self.provider == 'google':
                return self._call_google_api(screenshot_path, context)
            elif self.provider == 'openai':
                return self._call_openai_api(screenshot_path, context)
            else:
                return self._fallback_response(context)
                
        except Exception as e:
            print(f"❌ LLM analysis error: {e}")
            traceback.print_exc()
            return {
                "text": f"AI analysis failed: {str(e)}",
                "actions": ["A"],  # Safe default
                "success": False,
                "error": str(e)
            }
    
    def _create_game_context(self, game_state: Dict[str, Any], recent_actions_text: str = "") -> str:
        """Create enhanced context string for LLM using optimized template"""
        # Check for template updates (hot-reload)
        self._load_prompt_template()
        
        position = game_state.get('position', {})
        x, y = position.get('x', 0), position.get('y', 0)
        direction = game_state.get('direction', 'UNKNOWN')
        map_id = game_state.get('map_id', 0)
        
        # Get current map name
        current_map = self._get_map_name(map_id)
        
        # Read notepad content
        notepad_content = self._read_notepad()
        
        # Generate spatial context
        spatial_context = self._create_spatial_context(current_map, x, y, direction, map_id)
        
        # Format recent actions
        if not recent_actions_text:
            recent_actions_text = "No recent actions."
        
        # Format direction guidance
        direction_guidance = self._get_direction_guidance_text(direction, x, y, map_id)
        
        # Substitute variables in the optimized template
        try:
            context = self.prompt_template.format(
                spatial_context=spatial_context,
                recent_actions=recent_actions_text,
                direction_guidance=direction_guidance,
                notepad_content=notepad_content
            )
        except KeyError as e:
            print(f"⚠️ Missing template variable {e}, using fallback context")
            # Fallback context if template substitution fails
            context = f"""You are an AI playing Pokémon, you are the character with the white hair. The name is GEMINI. Look at the screenshot(s) provided and choose button(s) to press.

{spatial_context}

{recent_actions_text}

{direction_guidance}

## Long-term Memory (Game State):
{notepad_content}

IMPORTANT: After each significant change (entering new area, talking to someone, finding items), use the update_notepad function to record what you learned or where you are."""
        
        return context
    
    def _create_spatial_context(self, current_map: str, x: int, y: int, direction: str, map_id: int) -> str:
        """Generate spatial context for the optimized prompt template"""
        spatial_context = f"""## Current Location & Spatial Awareness
You are in {current_map}
Position: X={x}, Y={y}
Direction: {direction}
Map ID: {map_id}

**IMPORTANT: Use these coordinates for intelligent navigation!**
- Lower X values = LEFT, Higher X values = RIGHT
- Lower Y values = UP, Higher Y values = DOWN
- **CRITICAL MOVEMENT MECHANICS**: 
  * **Turning**: 2 frames changes facing direction (no coordinate movement)
  * **Moving**: 30 frames moves 1 coordinate unit (only if already facing that direction)
  * **Total movement**: Turn (2 frames) + Move (30×units frames) if changing direction
  * **Same direction**: Just 30×units frames if already facing the right way"""
        
        return spatial_context
    
    def _call_google_api(self, screenshot_path: str, context: str) -> Dict[str, Any]:
        """Call Google Gemini API"""
        try:
            if not self.google_client:
                return self._fallback_response(context, "Google client not initialized")
            
            # Load and enhance image
            enhanced_image = self._enhance_image(screenshot_path)
            
            # Convert enhanced PIL image to bytes
            import io
            img_bytes = io.BytesIO()
            enhanced_image.save(img_bytes, format='PNG')
            image_data = img_bytes.getvalue()
            
            # Create model
            model_name = self.providers_config.get('google', {}).get('model_name', 'gemini-2.0-flash-exp')
            model = self.google_client.GenerativeModel(model_name)
            
            # Create image part
            image_part = {
                'mime_type': 'image/png',
                'data': image_data
            }
            
            # Enhanced prompt with tool definition
            prompt = context + """

Use the press_button_sequence tool to indicate your chosen actions. You can press multiple buttons in sequence with custom durations.

Examples:
- Single button: press_button_sequence(actions=["UP"])
- Multiple buttons: press_button_sequence(actions=["UP", "UP", "A"])
- With durations: press_button_sequence(actions=["UP", "A"], durations=[10, 5])

Duration is in frames (60 frames = 1 second). Default duration is 2 frames if not specified.
"""

            # Log prompt statistics for token optimization tracking
            prompt_words = len(prompt.split())
            prompt_chars = len(prompt)
            estimated_tokens = prompt_words * 1.3  # Rough estimation: 1 token ≈ 0.75 words
            print(f"📊 Prompt Stats: {prompt_chars} chars, {prompt_words} words, ~{estimated_tokens:.0f} tokens (estimated)")

            # Define tools (including both press_button and update_notepad)
            tools = [
                self.google_client.protos.Tool(
                    function_declarations=[
                        self.google_client.protos.FunctionDeclaration(
                            name="press_button_sequence",
                            description="Press a sequence of buttons on the Game Boy emulator with optional custom durations",
                            parameters=self.google_client.protos.Schema(
                                type=self.google_client.protos.Type.OBJECT,
                                properties={
                                    "actions": self.google_client.protos.Schema(
                                        type=self.google_client.protos.Type.ARRAY,
                                        items=self.google_client.protos.Schema(
                                            type=self.google_client.protos.Type.STRING,
                                            enum=["A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L"]
                                        ),
                                        description="Array of buttons to press in sequence"
                                    ),
                                    "durations": self.google_client.protos.Schema(
                                        type=self.google_client.protos.Type.ARRAY,
                                        items=self.google_client.protos.Schema(
                                            type=self.google_client.protos.Type.INTEGER
                                        ),
                                        description="Optional array of durations (in frames, 60fps) for each button. Default is 2 frames if not specified."
                                    )
                                },
                                required=["actions"]
                            )
                        ),
                        self.google_client.protos.FunctionDeclaration(
                            name="update_notepad",
                            description="Update the AI's long-term memory with new information about the game state",
                            parameters=self.google_client.protos.Schema(
                                type=self.google_client.protos.Type.OBJECT,
                                properties={
                                    "content": self.google_client.protos.Schema(
                                        type=self.google_client.protos.Type.STRING,
                                        description="Content to add to the notepad. Only include important information about game progress, objectives, or status."
                                    )
                                },
                                required=["content"]
                            )
                        )
                    ]
                )
            ]
            
            # Generate response
            response = model.generate_content(
                [prompt, image_part],
                tools=tools,
                generation_config={'temperature': 0.7}
            )
            
            # Parse response
            response_text = ""
            actions = ["A"]  # Default action
            durations = []  # Default durations
            notepad_update = None
            tool_call_found = False
            
            if response.candidates:
                candidate = response.candidates[0]
                
                # Get text content and tool calls
                if hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
                        if hasattr(part, 'function_call') and part.function_call:
                            tool_call_found = True
                            # Extract function calls
                            if part.function_call.name == "press_button_sequence":
                                # Extract actions from Google's nested structure
                                args_to_check = part.function_call.args
                                
                                # Handle both 'fields' and direct access patterns
                                if hasattr(args_to_check, 'fields') and 'actions' in args_to_check.fields:
                                    actions_field = args_to_check.fields['actions']
                                elif 'actions' in args_to_check:
                                    actions_field = args_to_check['actions']
                                else:
                                    actions_field = None
                                
                                if actions_field:
                                    # Handle Google's list_value structure
                                    if hasattr(actions_field, 'list_value') and hasattr(actions_field.list_value, 'values'):
                                        actions = [val.string_value for val in actions_field.list_value.values if hasattr(val, 'string_value')]
                                    # Handle direct value access
                                    elif hasattr(actions_field, 'value') and hasattr(actions_field.value, 'list_value'):
                                        actions = [val.string_value for val in actions_field.value.list_value.values if hasattr(val, 'string_value')]
                                    else:
                                        # Fallback: try direct conversion
                                        try:
                                            actions = list(actions_field)
                                        except:
                                            actions = ["A"]  # Fallback
                                    
                                    # Extract durations if provided
                                    durations_field = None
                                    if hasattr(args_to_check, 'fields') and 'durations' in args_to_check.fields:
                                        durations_field = args_to_check.fields['durations']
                                    elif 'durations' in args_to_check:
                                        durations_field = args_to_check['durations']
                                    
                                    if durations_field:
                                        if hasattr(durations_field, 'list_value') and hasattr(durations_field.list_value, 'values'):
                                            durations = []
                                            for val in durations_field.list_value.values:
                                                if hasattr(val, 'number_value'):
                                                    durations.append(int(val.number_value))
                                                elif hasattr(val, 'string_value'):
                                                    try:
                                                        durations.append(int(val.string_value))
                                                    except ValueError:
                                                        durations.append(2)  # Default
                                        elif hasattr(durations_field, 'value') and hasattr(durations_field.value, 'list_value'):
                                            durations = []
                                            for val in durations_field.value.list_value.values:
                                                if hasattr(val, 'number_value'):
                                                    durations.append(int(val.number_value))
                                                elif hasattr(val, 'string_value'):
                                                    try:
                                                        durations.append(int(val.string_value))
                                                    except ValueError:
                                                        durations.append(2)  # Default
                                        else:
                                            try:
                                                durations = [int(d) for d in durations_field]
                                            except:
                                                durations = []
                                    else:
                                        durations = []  # Will use defaults
                                else:
                                    actions = ["A"]  # Fallback
                            # Legacy support for old press_button calls
                            elif part.function_call.name == "press_button":
                                legacy_args = part.function_call.args
                                
                                # Check for 'button' parameter
                                button_field = None
                                if hasattr(legacy_args, 'fields') and 'button' in legacy_args.fields:
                                    button_field = legacy_args.fields['button']
                                elif 'button' in legacy_args:
                                    button_field = legacy_args['button']
                                
                                if button_field:
                                    if hasattr(button_field, 'string_value'):
                                        button = button_field.string_value
                                    elif hasattr(button_field, 'value') and hasattr(button_field.value, 'string_value'):
                                        button = button_field.value.string_value
                                    else:
                                        button = str(button_field)
                                    actions = [button]
                                    durations = []
                                else:
                                    # Check for 'actions' parameter
                                    actions_field = None
                                    if hasattr(legacy_args, 'fields') and 'actions' in legacy_args.fields:
                                        actions_field = legacy_args.fields['actions']
                                    elif 'actions' in legacy_args:
                                        actions_field = legacy_args['actions']
                                    
                                    if actions_field:
                                        if hasattr(actions_field, 'list_value') and hasattr(actions_field.list_value, 'values'):
                                            actions = [val.string_value for val in actions_field.list_value.values if hasattr(val, 'string_value')]
                                        elif hasattr(actions_field, 'value') and hasattr(actions_field.value, 'list_value'):
                                            actions = [val.string_value for val in actions_field.value.list_value.values if hasattr(val, 'string_value')]
                                        else:
                                            actions = list(actions_field)
                                        durations = []
                                    else:
                                        actions = ["A"]  # Fallback
                                        durations = []
                            elif part.function_call.name == "update_notepad":
                                notepad_args = part.function_call.args
                                
                                content_field = None
                                if hasattr(notepad_args, 'fields') and 'content' in notepad_args.fields:
                                    content_field = notepad_args.fields['content']
                                elif 'content' in notepad_args:
                                    content_field = notepad_args['content']
                                
                                if content_field:
                                    if hasattr(content_field, 'string_value'):
                                        notepad_update = content_field.string_value
                                    elif hasattr(content_field, 'value') and hasattr(content_field.value, 'string_value'):
                                        notepad_update = content_field.value.string_value
                                    else:
                                        notepad_update = str(content_field)
            
            # Handle notepad update
            if notepad_update:
                self._update_notepad(notepad_update)
            
            if not response_text:
                response_text = "AI analyzed the game state and chose action."
            
            return {
                "text": response_text,
                "actions": actions,
                "durations": durations,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            print(f"❌ Google API error: {e}")
            return self._fallback_response(context, str(e))
    
    def _call_openai_api(self, screenshot_path: str, context: str) -> Dict[str, Any]:
        """Call OpenAI API"""
        try:
            if not self.openai_client:
                return self._fallback_response(context, "OpenAI client not initialized")
            
            # Encode image
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Create messages
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": context},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_data}"}
                        }
                    ]
                }
            ]
            
            # Define tools
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "press_button_sequence",
                        "description": "Press a sequence of buttons on the Game Boy emulator with optional custom durations",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "actions": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": ["A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L"]
                                    },
                                    "description": "Array of buttons to press in sequence"
                                },
                                "durations": {
                                    "type": "array",
                                    "items": {
                                        "type": "integer"
                                    },
                                    "description": "Optional array of durations (in frames, 60fps) for each button. Default is 2 frames if not specified."
                                }
                            },
                            "required": ["actions"]
                        }
                    }
                }
            ]
            
            # Get model name
            model_name = self.providers_config.get('openai', {}).get('model_name', 'gpt-4o')
            
            # Make API call
            response = self.openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools,
                timeout=self.timeout
            )
            
            # Parse response
            message = response.choices[0].message
            response_text = message.content or "AI analyzed the game state."
            actions = ["A"]  # Default
            durations = []  # Default durations
            
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "press_button_sequence":
                        print(f"🔧 OpenAI tool call: press_button_sequence")
                        args = json.loads(tool_call.function.arguments)
                        print(f"🔧 Args: {args}")
                        if 'actions' in args:
                            actions = args['actions']
                            print(f"✅ Extracted actions: {actions}")
                            
                            # Extract durations if provided
                            if 'durations' in args:
                                durations = args['durations']
                                print(f"✅ Extracted durations: {durations}")
                            else:
                                durations = []
                        else:
                            print(f"⚠️ No 'actions' parameter found: {args}")
                    # Legacy support
                    elif tool_call.function.name == "press_button":
                        print(f"🔧 OpenAI legacy tool call: press_button")
                        args = json.loads(tool_call.function.arguments)
                        print(f"🔧 Args: {args}")
                        if 'button' in args:
                            button = str(args['button'])
                            actions = [button]
                            durations = []
                            print(f"✅ Extracted legacy button: {button}")
                        elif 'actions' in args:
                            actions = args['actions']
                            durations = []
                            print(f"✅ Extracted legacy actions: {actions}")
                        else:
                            print(f"⚠️ No 'button' or 'actions' parameter found: {args}")
            else:
                print(f"⚠️ No tool calls found, using default: {actions}")
            
            return {
                "text": response_text,
                "actions": actions,
                "durations": durations,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            return self._fallback_response(context, str(e))
    
    def _enhance_image(self, image_path: str) -> PIL.Image.Image:
        """Enhance image for better AI vision based on example.py"""
        try:
            # Load the original image
            original_image = PIL.Image.open(image_path)
            
            # Scale the image to 3x its original size for better detail recognition
            scale_factor = 3
            scaled_width = original_image.width * scale_factor
            scaled_height = original_image.height * scale_factor
            scaled_image = original_image.resize((scaled_width, scaled_height), PIL.Image.LANCZOS)
            
            # Enhance contrast for better visibility
            contrast_enhancer = ImageEnhance.Contrast(scaled_image)
            contrast_image = contrast_enhancer.enhance(1.5)  # Increase contrast by 50%
            
            # Enhance color saturation for better color visibility
            saturation_enhancer = ImageEnhance.Color(contrast_image)
            enhanced_image = saturation_enhancer.enhance(1.8)  # Increase saturation by 80%
            
            # Optionally enhance brightness slightly
            brightness_enhancer = ImageEnhance.Brightness(enhanced_image)
            final_image = brightness_enhancer.enhance(1.1)  # Increase brightness by 10%
            
            return final_image
            
        except Exception as e:
            print(f"⚠️ Image enhancement failed: {e}")
            # Return original image if enhancement fails
            return PIL.Image.open(image_path)
    
    def _get_map_name(self, map_id: int) -> str:
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
    
    def _get_direction_guidance_text(self, direction: str, x: int, y: int, map_id: int) -> str:
        """Generate enhanced guidance text with spatial context and movement optimization"""
        directions = {
            "UP": "north",
            "DOWN": "south", 
            "LEFT": "west",
            "RIGHT": "east"
        }
        
        facing_direction = directions.get(direction, direction)
        
        # Generate spatial context based on position
        spatial_context = self._generate_spatial_context(x, y, map_id)
        
        # Generate movement suggestions based on position and direction
        movement_suggestions = self._generate_movement_suggestions(direction, x, y, map_id)
        
        guidance = f"""
## CURRENT SPATIAL CONTEXT:
- Location: {self._get_map_name(map_id)} at coordinates (X={x}, Y={y})
- Facing: {direction} ({facing_direction})
{spatial_context}

## MOVEMENT & INTERACTION STRATEGY:
{movement_suggestions}

## Navigation Rules:
- To INTERACT with objects or NPCs, FIRST face them using directional buttons, THEN press A
- Your current direction is {direction} - you can only interact with things in front of you
- To enter/exit buildings, walk directly over doors, stairs, or red mats (use movement buttons)
- If you've been pressing the same direction 3+ times with no progress, try a different approach
- When stuck, analyze the environment and find clear paths or interactable objects
        """
        
        return guidance
    
    def _generate_spatial_context(self, x: int, y: int, map_id: int) -> str:
        """Generate context about current spatial position and surroundings"""
        
        # Known locations with specific context
        location_contexts = {
            0: {  # Pallet Town
                "general": "- Small town with houses and Oak's lab to the north",
                "positions": {
                    (10, 12): "- Near the center of town - good position to explore",
                    (10, 6): "- Close to Oak's lab entrance",
                    (8, 14): "- Near Red's house", 
                    (12, 14): "- Near Blue's house"
                }
            },
            1: {  # Viridian City
                "general": "- Larger city with gym, Pokemon Center, and shop",
                "positions": {}
            },
            37: {  # Red's House 1F
                "general": "- Inside Red's house, ground floor",
                "positions": {
                    (3, 4): "- Near the stairs to go upstairs",
                    (7, 7): "- Near the door to exit outside"
                }
            },
            40: {  # Oak's Lab
                "general": "- Professor Oak's laboratory with Pokemon and research",
                "positions": {
                    (5, 7): "- Near the entrance/exit",
                    (5, 4): "- Close to Oak's desk area"
                }
            }
        }
        
        context = ""
        if map_id in location_contexts:
            loc_data = location_contexts[map_id]
            context += loc_data["general"] + "\n"
            
            # Check for specific position context
            if (x, y) in loc_data["positions"]:
                context += loc_data["positions"][(x, y)] + "\n"
            else:
                # General position analysis
                context += f"- At position ({x}, {y}) - analyze your surroundings for exits and interactables\n"
        else:
            context += f"- Unknown area (Map {map_id}) - explore carefully and observe landmarks\n"
            context += f"- Position ({x}, {y}) - look for exits, NPCs, or items to interact with\n"
        
        return context
    
    def _generate_movement_suggestions(self, direction: str, x: int, y: int, map_id: int) -> str:
        """Generate smart movement suggestions based on current position and facing direction"""
        
        suggestions = []
        
        # Direction-specific interaction tips
        if direction == "UP":
            suggestions.append("- You can interact with anything directly above you by pressing A")
            suggestions.append("- To interact with objects to your sides, turn LEFT or RIGHT first")
        elif direction == "DOWN":
            suggestions.append("- You can interact with anything directly below you by pressing A") 
            suggestions.append("- To interact with objects to your sides, turn LEFT or RIGHT first")
        elif direction == "LEFT":
            suggestions.append("- You can interact with anything directly to your left by pressing A")
            suggestions.append("- To interact with objects above/below, turn UP or DOWN first")
        elif direction == "RIGHT":
            suggestions.append("- You can interact with anything directly to your right by pressing A")
            suggestions.append("- To interact with objects above/below, turn UP or DOWN first")
        else:
            suggestions.append("- Direction unknown - try pressing a directional button to orient yourself")
        
        # Position-specific suggestions
        if map_id == 0:  # Pallet Town
            if y < 8:  # Northern part
                suggestions.append("- You're in the northern area - Oak's lab should be nearby")
            elif y > 12:  # Southern part  
                suggestions.append("- You're in the southern area - near the houses")
            
            if x < 8:  # Western part
                suggestions.append("- Western side of town - Red's house area")
            elif x > 12:  # Eastern part
                suggestions.append("- Eastern side of town - Blue's house area")
                
        elif map_id == 37:  # Red's House 1F
            suggestions.append("- Look for stairs (usually dark colored) to go upstairs")
            suggestions.append("- Look for the door (usually at bottom) to exit outside")
            
        elif map_id == 40:  # Oak's Lab
            suggestions.append("- Look for Professor Oak to talk to him")
            suggestions.append("- Examine the Pokeball on the table if you haven't chosen a starter")
            
        # General movement optimization
        suggestions.append("- If you see a clear path, move towards your objective")
        suggestions.append("- If blocked, try moving around obstacles or look for alternative routes")
        
        return "\n".join(suggestions)
    
    def _read_notepad(self) -> str:
        """Read the current notepad content"""
        try:
            if self.notepad_path.exists():
                with open(self.notepad_path, 'r') as f:
                    return f.read()
            else:
                return "# Pokémon Red Game Progress\n\nGame just started. No progress recorded yet."
        except Exception as e:
            print(f"Error reading notepad: {e}")
            return "Error reading notepad"
    
    def _update_notepad(self, new_content: str) -> None:
        """Update the notepad with new content"""
        try:
            current_content = self._read_notepad()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated_content = current_content + f"\n## Update {timestamp}\n{new_content}\n"
            
            # Ensure directory exists
            self.notepad_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.notepad_path, 'w') as f:
                f.write(updated_content)
            print("📝 Notepad updated")
        except Exception as e:
            print(f"❌ Error updating notepad: {e}")
    
    def _fallback_response(self, context: str, error: str = None) -> Dict[str, Any]:
        """Generate fallback response when AI fails"""
        fallback_actions = ["A"]  # Simple safe action
        
        fallback_text = "AI service is in fallback mode. Using safe default action."
        if error:
            fallback_text += f" (Error: {error})"
        
        return {
            "text": fallback_text,
            "actions": fallback_actions,
            "success": False,
            "error": error
        }