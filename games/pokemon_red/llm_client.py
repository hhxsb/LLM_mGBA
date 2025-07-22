#!/usr/bin/env python3
"""
LLM client for Pokemon Red (extracted from original google_controller.py).
"""

from typing import Dict, List, Any, Tuple
import PIL.Image
import sys
import os

# Add parent directories to path to import core modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.base_prompt_template import Tool
from core.base_game_controller import ToolCall


class GeminiClient:
    """Client specifically for communicating with Gemini for Pokemon Red."""
    
    def __init__(self, api_key: str, model_name: str, max_tokens: int = 1024):
        self.api_key = api_key
        self.model_name = model_name
        self.max_tokens = max_tokens
        self._setup_client()
    
    def _setup_client(self):
        """Set up the Gemini client."""
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        self.client = genai
    
    def call_with_tools(self, message: str, tools: List[Tool], images: List[PIL.Image.Image] = None) -> Tuple[Any, List[ToolCall], str]:
        """Call Gemini with the given message and tools, optionally including images."""
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
        
        try:
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
            
            # 📸 Add comprehensive LLM API response logging (missing from dual process mode)
            from core.logging_config import get_logger
            logger = get_logger("pokemon_red.llm_client")
            
            # Log basic response info
            logger.info(f"📸 LLM API CALL SUCCESSFUL: Model={self.model_name}")
            logger.debug(f"📸 LLM REQUEST: {len(enhanced_message)} chars, {len(images) if images else 0} images")
            
            # Log response structure details
            if hasattr(response, 'candidates') and response.candidates:
                logger.info(f"📸 LLM RESPONSE: {len(response.candidates)} candidates received")
                for i, candidate in enumerate(response.candidates):
                    if hasattr(candidate, 'finish_reason'):
                        logger.debug(f"📸 LLM CANDIDATE {i}: finish_reason={candidate.finish_reason}")
                    if hasattr(candidate, 'content') and candidate.content:
                        parts_count = len(candidate.content.parts) if hasattr(candidate.content, 'parts') else 0
                        logger.debug(f"📸 LLM CANDIDATE {i}: {parts_count} content parts")
            
            # Log any safety/content filtering
            response_text = self._extract_text(response)
            if response_text:
                logger.info(f"📸 LLM RESPONSE TEXT: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
            else:
                logger.warning("📸 LLM RESPONSE: No text content extracted")
                
            # Log tool calls found
            tool_calls = self._parse_tool_calls(response)
            if tool_calls:
                logger.info(f"📸 LLM TOOL CALLS: {len(tool_calls)} function calls detected")
                for call in tool_calls:
                    logger.debug(f"📸 LLM TOOL CALL: {call.name} with args: {call.arguments}")
            else:
                logger.warning("📸 LLM TOOL CALLS: No function calls detected")
        except Exception as e:
            error_str = str(e)
            if "MALFORMED_FUNCTION_CALL" in error_str:
                print(f"⚠️ WARNING: Malformed function call detected. Using fallback action...")
                print(f"⚠️ Error details: {error_str}")
                fallback_response = self._create_fallback_response()
                return fallback_response, self._parse_tool_calls(fallback_response), "Malformed function call - using fallback action"
            else:
                # Re-raise other exceptions
                raise
        
        # Check for safety-filtered or blocked responses
        if hasattr(response, "candidates") and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, "finish_reason"):
                    if candidate.finish_reason == 2:  # SAFETY
                        print("⚠️ WARNING: Response blocked by safety filter. Retrying with fallback action...")
                        fallback_response = self._create_fallback_response()
                        return fallback_response, self._parse_tool_calls(fallback_response), "Safety filter activated - using fallback action"
                    elif candidate.finish_reason == 3:  # RECITATION
                        print("⚠️ WARNING: Response blocked for recitation. Retrying with fallback action...")
                        fallback_response = self._create_fallback_response()
                        return fallback_response, self._parse_tool_calls(fallback_response), "Recitation filter activated - using fallback action"
        
        return response, self._parse_tool_calls(response), self._extract_text(response)
    
    def _create_fallback_response(self):
        """Create a fallback response when the main response is blocked."""
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
        """Parse tool calls from Gemini's response."""
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
        """Extract text from the Gemini response."""
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