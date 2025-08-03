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
    
    def __init__(self, api_key: str, model_name: str, max_tokens: int = 4096, timeout_seconds: int = 60):
        self.api_key = api_key
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
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
            # Add timeout protection for LLM API calls
            import concurrent.futures
            import time
            from core.logging_config import get_logger
            logger = get_logger("pokemon_red.llm_client")
            
            def make_llm_call():
                return chat.send_message(
                    content=content_parts,
                    generation_config={
                        "max_output_tokens": self.max_tokens,
                        "temperature": 0.2,
                        "top_p": 0.95,
                        "top_k": 0
                    },
                    tools={"function_declarations": provider_tools}
                )
            
            # Use ThreadPoolExecutor with timeout
            logger.debug(f"📸 LLM_TIMEOUT: Starting LLM call with {self.timeout_seconds}s timeout")
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(make_llm_call)
                try:
                    # Configurable timeout for LLM API calls
                    response = future.result(timeout=self.timeout_seconds)
                    elapsed = time.time() - start_time
                    logger.debug(f"📸 LLM_TIMEOUT: LLM call completed in {elapsed:.2f}s")
                except concurrent.futures.TimeoutError:
                    elapsed = time.time() - start_time
                    logger.error(f"📸 LLM_TIMEOUT: LLM API call timed out after {elapsed:.2f}s")
                    print(f"⚠️ WARNING: LLM API call timed out after {self.timeout_seconds} seconds. Using fallback action...")
                    # Create a fallback response
                    fallback_response = self._create_fallback_response()
                    return fallback_response, self._parse_tool_calls(fallback_response), "LLM API timeout - using fallback action"
            
            # 📸 Add comprehensive LLM API response logging (missing from dual process mode)
            # (logger already imported above)
            
            # Log basic response info
            logger.info(f"📸 LLM API CALL SUCCESSFUL: Model={self.model_name}")
            logger.debug(f"📸 LLM REQUEST: {len(enhanced_message)} chars, {len(images) if images else 0} images")
            
            # Log complete raw response payload at DEBUG level
            try:
                import json
                # Convert response to dict for serialization (handling Gemini response objects)
                response_dict = {}
                if hasattr(response, '__dict__'):
                    response_dict = response.__dict__
                elif hasattr(response, '_pb'):
                    # Handle protobuf objects
                    response_dict = {"_pb_data": str(response._pb) if hasattr(response, '_pb') else str(response)}
                else:
                    response_dict = {"response_type": str(type(response)), "response_str": str(response)}
                
                # Safely serialize the response
                try:
                    response_json = json.dumps(response_dict, default=str, indent=2)
                    logger.debug(f"📸 LLM RAW RESPONSE PAYLOAD (FULL): {response_json}")
                except (TypeError, ValueError) as e:
                    # Fallback to string representation if JSON serialization fails
                    logger.debug(f"📸 LLM RAW RESPONSE PAYLOAD (STRING): {str(response)}")
                    logger.debug(f"📸 LLM RESPONSE SERIALIZATION ERROR: {e}")
            except Exception as e:
                logger.debug(f"📸 LLM RAW RESPONSE LOGGING ERROR: {e}")
                logger.debug(f"📸 LLM RAW RESPONSE FALLBACK: {str(response)}")
            
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
                # Log truncated version at INFO level for general monitoring
                logger.info(f"📸 LLM RESPONSE TEXT: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
                # Log full raw response at DEBUG level for detailed analysis
                logger.debug(f"📸 LLM RAW RESPONSE (FULL): {response_text}")
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
                    elif candidate.finish_reason == 4:  # MAX_TOKENS
                        print("⚠️ WARNING: Response cut off due to max tokens limit. Using what we have or fallback action...")
                        logger = self._get_logger()
                        logger.warning(f"📸 LLM MAX_TOKENS reached. Response truncated. Consider reducing prompt length.")
                        # Try to extract any partial tool calls, otherwise use fallback
                        tool_calls = self._parse_tool_calls(response)
                        if tool_calls:
                            logger.info(f"📸 LLM partial response recovered {len(tool_calls)} tool calls despite MAX_TOKENS")
                            return response, tool_calls, "MAX_TOKENS reached - using partial response"
                        else:
                            logger.warning(f"📸 LLM MAX_TOKENS with no tool calls - using fallback")
                            fallback_response = self._create_fallback_response()
                            return fallback_response, self._parse_tool_calls(fallback_response), "MAX_TOKENS reached - using fallback action"
        
        logger.debug(f"📸 LLM_FLOW: Starting post-LLM processing...")
        
        # Parse tool calls with detailed logging
        logger.debug(f"📸 LLM_FLOW: Parsing tool calls...")
        tool_calls = self._parse_tool_calls(response)
        logger.debug(f"📸 LLM_FLOW: Tool calls parsed - {len(tool_calls)} calls found")
        
        # Extract text with detailed logging
        logger.debug(f"📸 LLM_FLOW: Extracting response text...")
        response_text = self._extract_text(response)
        logger.debug(f"📸 LLM_FLOW: Response text extracted - {len(response_text) if response_text else 0} chars")
        
        logger.debug(f"📸 LLM_FLOW: LLM client processing complete, returning to caller...")
        return response, tool_calls, response_text
    
    def _get_logger(self):
        """Get logger instance for this class."""
        from core.logging_config import get_logger
        return get_logger("pokemon_red.llm_client")
    
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
        logger = self._get_logger()
        tool_calls = []
        
        try:
            logger.debug("📸 TOOL_PARSE: Starting tool call parsing")
            if hasattr(response, "candidates"):
                logger.debug(f"📸 TOOL_PARSE: Found {len(response.candidates)} candidates")
                for i, candidate in enumerate(response.candidates):
                    logger.debug(f"📸 TOOL_PARSE: Processing candidate {i}")
                    if hasattr(candidate, "content") and candidate.content:
                        logger.debug(f"📸 TOOL_PARSE: Candidate {i} has content with {len(candidate.content.parts)} parts")
                        for j, part in enumerate(candidate.content.parts):
                            logger.debug(f"📸 TOOL_PARSE: Processing part {j}")
                            if hasattr(part, "function_call") and part.function_call:
                                logger.debug(f"📸 TOOL_PARSE: Part {j} has function_call")
                                if hasattr(part.function_call, "name") and part.function_call.name:
                                    func_name = part.function_call.name
                                    logger.debug(f"📸 TOOL_PARSE: Function name: {func_name}")
                                    args = {}
                                    if hasattr(part.function_call, "args") and part.function_call.args is not None:
                                        logger.debug(f"📸 TOOL_PARSE: Function has args, type: {type(part.function_call.args)}")
                                        try:
                                            # Use a more robust argument parsing approach with timeout protection
                                            args = self._parse_function_args_safe(part.function_call.args, logger)
                                            logger.debug(f"📸 TOOL_PARSE: Final args: {args}")
                                        except Exception as e:
                                            logger.error(f"📸 TOOL_PARSE: Error parsing function call args: {e}")
                                            # Fallback to empty args to prevent hanging
                                            args = {}
                                    
                                    logger.debug(f"📸 TOOL_PARSE: Creating ToolCall for {func_name}")
                                    tool_calls.append(ToolCall(
                                        id=f"call_{len(tool_calls)}",
                                        name=func_name,
                                        arguments=args
                                    ))
                                    logger.debug(f"📸 TOOL_PARSE: ToolCall created successfully")
                            else:
                                logger.debug(f"📸 TOOL_PARSE: Part {j} has no function_call")
                    else:
                        logger.debug(f"📸 TOOL_PARSE: Candidate {i} has no content")
            else:
                logger.debug("📸 TOOL_PARSE: Response has no candidates")
        except Exception as e:
            logger.error(f"📸 TOOL_PARSE: Error parsing Gemini tool calls: {e}")
            import traceback
            logger.error(f"📸 TOOL_PARSE: Traceback: {traceback.format_exc()}")
        
        logger.debug(f"📸 TOOL_PARSE: Completed, found {len(tool_calls)} tool calls")
        for call in tool_calls:
            logger.debug(f"📸 TOOL_PARSE: Tool call: {call.name}, args: {call.arguments}")
        
        return tool_calls
    
    def _parse_function_args_safe(self, args_obj, logger):
        """Safely parse function arguments with timeout protection."""
        import time
        
        args = {}
        start_time = time.time()
        
        try:
            logger.debug("📸 ARG_PARSE: Starting safe argument parsing")
            
            # Handle MapComposite (Google protobuf structure) specifically
            if str(type(args_obj)) == "<class 'proto.marshal.collections.maps.MapComposite'>":
                logger.debug("📸 ARG_PARSE: Processing MapComposite structure")
                try:
                    # Convert MapComposite to dict first
                    args_dict = dict(args_obj)
                    logger.debug(f"📸 ARG_PARSE: MapComposite converted to dict with keys: {list(args_dict.keys())}")
                    
                    for key, value in args_dict.items():
                        logger.debug(f"📸 ARG_PARSE: Processing key '{key}', value type: {type(value)}")
                        
                        # Handle protobuf Value objects
                        if hasattr(value, 'list_value') and value.list_value:
                            logger.debug("📸 ARG_PARSE: Found list_value in protobuf Value")
                            values_list = []
                            if hasattr(value.list_value, 'values'):
                                for val in value.list_value.values:
                                    if hasattr(val, 'string_value'):
                                        values_list.append(val.string_value)
                                    else:
                                        values_list.append(str(val))
                            args[key] = values_list
                            logger.debug(f"📸 ARG_PARSE: Extracted list: {args[key]}")
                        elif hasattr(value, 'string_value'):
                            logger.debug("📸 ARG_PARSE: Found string_value in protobuf Value")
                            args[key] = value.string_value
                            logger.debug(f"📸 ARG_PARSE: Extracted string: {args[key]}")
                        else:
                            logger.debug(f"📸 ARG_PARSE: Converting value to string: {value}")
                            args[key] = str(value)
                            
                except Exception as e:
                    logger.error(f"📸 ARG_PARSE: Error processing MapComposite: {e}")
                    # Fallback to simple conversion
                    args = {"fallback": str(args_obj)}
                    
            elif hasattr(args_obj, "items"):
                logger.debug("📸 ARG_PARSE: Args has items() method")
                # Limit iteration to prevent infinite loops
                count = 0
                for key, value in args_obj.items():
                    count += 1
                    if count > 100:  # Safety limit
                        logger.warning("📸 ARG_PARSE: Hit iteration limit, breaking")
                        break
                        
                    logger.debug(f"📸 ARG_PARSE: Processing arg {key}, value type: {type(value)}")
                    
                    # Handle different value types more carefully
                    if hasattr(value, 'list_value'):
                        # This is a protobuf list_value structure
                        logger.debug("📸 ARG_PARSE: Found list_value structure")
                        if hasattr(value.list_value, 'values'):
                            values_list = []
                            for val in value.list_value.values:
                                if hasattr(val, 'string_value'):
                                    values_list.append(val.string_value)
                                else:
                                    values_list.append(str(val))
                            args[key] = values_list
                        else:
                            args[key] = [str(value.list_value)]
                    elif hasattr(value, 'string_value'):
                        # This is a protobuf string_value structure
                        logger.debug("📸 ARG_PARSE: Found string_value structure")
                        args[key] = value.string_value
                    elif hasattr(value, '__iter__') and not isinstance(value, str):
                        # Generic iterable
                        logger.debug("📸 ARG_PARSE: Found generic iterable")
                        args[key] = [str(item) for item in value]
                    else:
                        # Simple value
                        logger.debug("📸 ARG_PARSE: Found simple value")
                        args[key] = str(value)
                    
                    # Check if we're taking too long
                    if time.time() - start_time > 3:
                        logger.warning("📸 ARG_PARSE: Taking too long, breaking")
                        break
            else:
                logger.debug("📸 ARG_PARSE: Args has no items() method, using string conversion")
                args = {"argument": str(args_obj)}
                
        except Exception as e:
            logger.error(f"📸 ARG_PARSE: Error in safe parsing: {e}")
            args = {"error": str(e)}
            
        logger.debug(f"📸 ARG_PARSE: Safe parsing completed in {time.time() - start_time:.2f}s")
        return args
    
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