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


class LLMClient:
    """Client for making LLM API calls with robust error handling"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get('llm_provider', 'google')
        self.providers_config = config.get('providers', {})
        self.timeout = config.get('llm_timeout_seconds', 30)
        
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
    
    def analyze_game_state(self, screenshot_path: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze game state and return AI decision
        
        Returns:
            {
                "text": "AI reasoning text",
                "actions": ["UP", "A"],
                "success": True/False,
                "error": "error message if failed"
            }
        """
        try:
            # Load and encode screenshot
            if not os.path.exists(screenshot_path):
                return {
                    "text": "Screenshot not found",
                    "actions": ["A"],  # Default action
                    "success": False,
                    "error": f"Screenshot file not found: {screenshot_path}"
                }
            
            # Create game context
            context = self._create_game_context(game_state)
            
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
    
    def _create_game_context(self, game_state: Dict[str, Any]) -> str:
        """Create context string for LLM"""
        position = game_state.get('position', {})
        x, y = position.get('x', 0), position.get('y', 0)
        direction = game_state.get('direction', 'UNKNOWN')
        map_id = game_state.get('map_id', 0)
        
        context = f"""You are an AI playing Pokémon Red on Game Boy Advance.

Current Game State:
- Position: ({x}, {y})
- Facing: {direction}
- Map ID: {map_id}

Analyze the screenshot and decide what action to take. Your response should include:
1. What you see in the game
2. Your strategic reasoning
3. The action you want to take

Available actions: A, B, SELECT, START, RIGHT, LEFT, UP, DOWN, R, L

Respond with your reasoning and then call the press_button tool with your chosen actions."""
        
        return context
    
    def _call_google_api(self, screenshot_path: str, context: str) -> Dict[str, Any]:
        """Call Google Gemini API"""
        try:
            if not self.google_client:
                return self._fallback_response(context, "Google client not initialized")
            
            # Load image
            with open(screenshot_path, 'rb') as f:
                image_data = f.read()
            
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

Use the press_button tool to indicate your chosen actions. You can press multiple buttons in sequence.
For example, to move up and then press A: press_button(["UP", "A"])
"""

            # Define tools
            tools = [
                self.google_client.protos.Tool(
                    function_declarations=[
                        self.google_client.protos.FunctionDeclaration(
                            name="press_button",
                            description="Press game controller buttons",
                            parameters=self.google_client.protos.Schema(
                                type=self.google_client.protos.Type.OBJECT,
                                properties={
                                    "actions": self.google_client.protos.Schema(
                                        type=self.google_client.protos.Type.ARRAY,
                                        items=self.google_client.protos.Schema(
                                            type=self.google_client.protos.Type.STRING,
                                            enum=["A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L"]
                                        ),
                                        description="List of button actions to press in sequence"
                                    )
                                },
                                required=["actions"]
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
            
            if response.candidates:
                candidate = response.candidates[0]
                
                # Get text content
                if hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text'):
                            response_text += part.text
                        elif hasattr(part, 'function_call'):
                            # Extract function call
                            if part.function_call.name == "press_button":
                                if 'actions' in part.function_call.args:
                                    actions = list(part.function_call.args['actions'])
            
            if not response_text:
                response_text = "AI analyzed the game state and chose actions."
            
            return {
                "text": response_text,
                "actions": actions,
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
                        "name": "press_button",
                        "description": "Press game controller buttons",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "actions": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": ["A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L"]
                                    },
                                    "description": "List of button actions to press in sequence"
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
            
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "press_button":
                        args = json.loads(tool_call.function.arguments)
                        if 'actions' in args:
                            actions = args['actions']
            
            return {
                "text": response_text,
                "actions": actions,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            return self._fallback_response(context, str(e))
    
    def _fallback_response(self, context: str, error: str = None) -> Dict[str, Any]:
        """Generate fallback response when AI fails"""
        fallback_actions = ["UP", "A"]  # Simple exploration pattern
        
        fallback_text = "AI service is in fallback mode. Using basic exploration pattern."
        if error:
            fallback_text += f" (Error: {error})"
        
        return {
            "text": fallback_text,
            "actions": fallback_actions,
            "success": False,
            "error": error
        }