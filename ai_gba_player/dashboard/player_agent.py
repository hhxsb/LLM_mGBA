#!/usr/bin/env python3
"""
PlayerAgent - Handles game decision making and AI gameplay logic.
Extracted from AIGameService for better separation of concerns.
"""

import time
import os
from typing import Dict, Any, Optional, List, Tuple
from .llm_client import LLMClient
from .models import Configuration


class PlayerResponse:
    """Structured response from PlayerAgent game analysis"""
    
    def __init__(self, success: bool = True, actions: List[str] = None, text: str = "", 
                 error: str = "", durations: List[int] = None, game_analysis: str = "", 
                 detected_dialogue: str = "", action_reasoning: str = "", 
                 current_situation: str = "", emotional_context: str = ""):
        self.success = success
        self.actions = actions or []
        self.text = text
        self.error = error
        self.durations = durations or []
        
        # New structured fields for narration
        self.game_analysis = game_analysis
        self.detected_dialogue = detected_dialogue
        self.action_reasoning = action_reasoning
        self.current_situation = current_situation
        self.emotional_context = emotional_context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return {
            "success": self.success,
            "actions": self.actions,
            "text": self.text,
            "error": self.error,
            "durations": self.durations,
            "game_analysis": self.game_analysis,
            "detected_dialogue": self.detected_dialogue,
            "action_reasoning": self.action_reasoning,
            "current_situation": self.current_situation,
            "emotional_context": self.emotional_context
        }


class PlayerAgent:
    """AI agent responsible for making game decisions and controlling gameplay"""
    
    def __init__(self):
        # LLM client for game analysis
        self.llm_client = None
        
        # Error state tracking and retry logic
        self.last_successful_screenshots = None  # Store (previous_path, current_path) for retry
        self.last_successful_game_state = None
        self.current_retry_count = 0
        self.max_retry_attempts = 3
        self.retry_backoff_delay = 2.0  # seconds between retries
        self.consecutive_errors = 0
        self.success_rate_tracking = {'successes': 0, 'failures': 0}
        
        # Memory system integration
        self.memory_system = None
        
        print("🎮 PlayerAgent initialized - ready for game decision making")
    
    def initialize_llm(self, config: Dict[str, Any]):
        """Initialize LLM client with configuration"""
        if not self.llm_client:
            self.llm_client = LLMClient(config)
            print("🤖 PlayerAgent LLM client initialized")
    
    def analyze_and_decide(self, screenshot_path: str, game_state: Dict[str, Any], 
                          previous_screenshot: Optional[str] = None,
                          enhanced_context: str = "") -> PlayerResponse:
        """Main method to analyze game state and make decisions with retry logic"""
        
        # Ensure LLM client is available
        if not self.llm_client:
            config = self._load_config()
            if not config:
                return PlayerResponse(
                    success=False,
                    text="No AI configuration found",
                    error="Missing LLM configuration"
                )
            self.initialize_llm(config)
        
        # Call AI with retry logic for better error handling
        return self._call_ai_with_retry(
            current_screenshot=screenshot_path,
            previous_screenshot=previous_screenshot,
            game_state=game_state,
            enhanced_context=enhanced_context
        )
    
    def _call_ai_with_retry(self, current_screenshot: str, previous_screenshot: Optional[str], 
                           game_state: Dict[str, Any], enhanced_context: str) -> PlayerResponse:
        """Call AI API with intelligent retry logic for error handling"""
        
        # Store screenshots for potential retry
        screenshot_pair = (previous_screenshot, current_screenshot)
        config = self._load_config()
        
        for attempt in range(self.max_retry_attempts + 1):  # +1 for initial attempt
            try:
                print(f"🤖 PlayerAgent API Call (attempt {attempt + 1}/{self.max_retry_attempts + 1})")
                
                # Make the actual AI API call
                ai_response = self._call_ai_api_with_comparison(
                    current_screenshot=current_screenshot,
                    previous_screenshot=previous_screenshot,
                    game_state=game_state,
                    config=config,
                    enhanced_context=enhanced_context
                )
                
                # Check if response is successful
                if ai_response and ai_response.get("success", True):
                    # Success! Record it and return structured response
                    if attempt == 0:
                        # This was the first attempt - record as normal success
                        self._record_ai_success(screenshot_pair, game_state)
                    else:
                        # This was a retry that succeeded
                        print(f"✅ PlayerAgent retry succeeded on attempt {attempt + 1}")
                        self._record_ai_success(screenshot_pair, game_state)
                    
                    return self._convert_to_structured_response(ai_response, game_state)
                
                # Response indicates failure - check if retryable
                error_text = ai_response.get("text", "") if ai_response else ""
                error_info = ai_response.get("error", "") if ai_response else ""
                
                # Create exception from error response for retry logic
                if "LLM provided no reasoning text" in error_text or "LLM provided empty response" in error_text:
                    error = Exception(f"Empty LLM response: {error_text}")
                elif "Google API" in error_info and "500" in error_info:
                    error = Exception(f"Google API error: {error_info}")
                elif "timeout" in error_info.lower() or "rate limit" in error_info.lower():
                    error = Exception(f"API issue: {error_info}")
                else:
                    error = Exception(f"LLM error response: {error_text}")
                
                # Check if we should retry this error
                if attempt < self.max_retry_attempts and self._should_retry_error(error):
                    self._record_ai_failure(error, current_screenshot, game_state)
                    retry_delay = self._calculate_retry_delay()
                    print(f"🔄 PlayerAgent error on attempt {attempt + 1} - retrying with same screenshots after {retry_delay:.1f}s")
                    print(f"📸 Reusing: {os.path.basename(previous_screenshot or 'None')} vs {os.path.basename(current_screenshot)}")
                    
                    time.sleep(retry_delay)
                    continue  # Retry with same screenshots
                else:
                    # Max retries reached or non-retryable error
                    print(f"🚫 PlayerAgent failed after {attempt + 1} attempts - returning error response")
                    self._record_ai_failure(error, current_screenshot, game_state)
                    return PlayerResponse(
                        success=False,
                        text=error_text or "Max retries exceeded",
                        error=str(error),
                        actions=[]
                    )
            
            except Exception as e:
                # Actual exception during API call
                if attempt < self.max_retry_attempts and self._should_retry_error(e):
                    self._record_ai_failure(e, current_screenshot, game_state)
                    retry_delay = self._calculate_retry_delay()
                    print(f"🔄 PlayerAgent exception on attempt {attempt + 1} - retrying after {retry_delay:.1f}s: {e}")
                    
                    time.sleep(retry_delay)
                    continue  # Retry with same screenshots
                else:
                    # Max retries reached or non-retryable error
                    print(f"❌ PlayerAgent exception after {attempt + 1} attempts: {e}")
                    self._record_ai_failure(e, current_screenshot, game_state)
                    return PlayerResponse(
                        success=False,
                        text=f"API error: {str(e)}",
                        error=str(e),
                        actions=[]
                    )
        
        # This should never be reached, but just in case
        return PlayerResponse(
            success=False,
            text="Unexpected error in retry logic",
            actions=[]
        )
    
    def _call_ai_api_with_comparison(self, current_screenshot: str, previous_screenshot: Optional[str], 
                                    game_state: Dict[str, Any], config: Dict[str, Any], 
                                    enhanced_context: str) -> Dict[str, Any]:
        """Make API call with comparison logic"""
        if previous_screenshot and os.path.exists(previous_screenshot) and os.path.exists(current_screenshot):
            # Use comparison analysis
            print(f"📤 PlayerAgent: Sending screenshot comparison: {os.path.basename(previous_screenshot)} vs {os.path.basename(current_screenshot)}")
            return self.llm_client.analyze_game_state_with_comparison(
                current_screenshot, previous_screenshot, game_state, enhanced_context
            )
        else:
            # Use single screenshot analysis  
            print(f"📤 PlayerAgent: Sending single screenshot: {os.path.basename(current_screenshot)}")
            return self.llm_client.analyze_game_state(current_screenshot, game_state, enhanced_context)
    
    def _convert_to_structured_response(self, ai_response: Dict[str, Any], game_state: Dict[str, Any]) -> PlayerResponse:
        """Convert LLM response to structured PlayerResponse"""
        # Extract basic response data
        actions = ai_response.get("actions", [])
        durations = ai_response.get("durations", [])
        text = ai_response.get("text", "")
        
        # Extract structured fields from LLM response (if available) or infer from text
        game_analysis = ai_response.get("game_analysis", text)
        detected_dialogue = ai_response.get("detected_dialogue", self._extract_dialogue_from_text(text))
        action_reasoning = ai_response.get("action_reasoning", self._extract_reasoning_from_text(text))
        current_situation = ai_response.get("current_situation", self._infer_situation_from_state(game_state))
        emotional_context = ai_response.get("emotional_context", self._infer_emotional_context(text))
        
        return PlayerResponse(
            success=ai_response.get("success", True),
            actions=actions,
            text=text,
            error=ai_response.get("error", ""),
            durations=durations,
            game_analysis=game_analysis,
            detected_dialogue=detected_dialogue,
            action_reasoning=action_reasoning,
            current_situation=current_situation,
            emotional_context=emotional_context
        )
    
    def _extract_dialogue_from_text(self, text: str) -> str:
        """Extract potential dialogue from AI response text"""
        # Look for quoted text or common dialogue patterns
        import re
        dialogue_patterns = [
            r'"([^"]*)"',  # Text in quotes
            r"'([^']*)'",  # Text in single quotes
            r'says:?\s*"([^"]*)"',  # "Character says: 'text'"
            r'Wild \w+ appeared!',  # Pokemon battle text
            r'\w+: (.+)',  # Character: dialogue format
        ]
        
        for pattern in dialogue_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0] if isinstance(matches[0], str) else matches[0]
        
        return ""
    
    def _extract_reasoning_from_text(self, text: str) -> str:
        """Extract action reasoning from AI response text"""
        # Look for reasoning indicators
        reasoning_keywords = ["should", "need to", "will", "going to", "plan to"]
        sentences = text.split('.')
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in reasoning_keywords):
                return sentence.strip()
        
        # Default to first sentence if no specific reasoning found
        return sentences[0].strip() if sentences else text
    
    def _infer_situation_from_state(self, game_state: Dict[str, Any]) -> str:
        """Infer current game situation from state"""
        # Basic situation inference - can be enhanced with game-specific logic
        map_id = game_state.get('map_id', 0)
        
        if map_id == 0:
            return "exploration"
        elif map_id in [1, 2, 3]:  # Example battle map IDs
            return "battle"
        else:
            return "general_gameplay"
    
    def _infer_emotional_context(self, text: str) -> str:
        """Infer emotional context from AI response"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["excited", "great", "awesome", "win"]):
            return "excited"
        elif any(word in text_lower for word in ["careful", "danger", "low health", "worried"]):
            return "tense"
        elif any(word in text_lower for word in ["explore", "curious", "interesting"]):
            return "curious"
        else:
            return "neutral"
    
    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error should be retried"""
        if self.current_retry_count >= self.max_retry_attempts:
            return False
        
        error_type = self._classify_error_type(error)
        return error_type != "non_retryable"
    
    def _classify_error_type(self, error: Exception) -> str:
        """Classify errors as retryable, non-retryable, or connection-related"""
        error_msg = str(error).lower()
        
        # Connection-related errors (usually retryable with connection reset)
        if any(keyword in error_msg for keyword in ['connection', 'socket', 'timeout', 'mgba']):
            return "connection"
        
        # API-related retryable errors
        if any(keyword in error_msg for keyword in ['timeout', 'rate limit', 'server error', '5', 'temporary']):
            return "retryable_api"
        
        # Parsing or response format errors (retryable)
        if any(keyword in error_msg for keyword in ['parse', 'json', 'format', 'invalid response']):
            return "retryable_parse"
        
        # Non-retryable errors (authentication, permissions, etc.)
        if any(keyword in error_msg for keyword in ['auth', 'permission', 'forbidden', 'unauthorized', 'api key']):
            return "non_retryable"
        
        # Default to retryable for unknown errors
        return "retryable_unknown"
    
    def _calculate_retry_delay(self) -> float:
        """Calculate backoff delay for retries"""
        # Exponential backoff with jitter
        base_delay = self.retry_backoff_delay
        backoff_multiplier = 1.5 ** self.current_retry_count
        return min(base_delay * backoff_multiplier, 10.0)  # Cap at 10 seconds
    
    def _record_ai_success(self, screenshot_paths: tuple, game_state: Dict[str, Any]):
        """Record successful AI request/response cycle"""
        self.current_retry_count = 0
        self.last_successful_screenshots = screenshot_paths
        self.last_successful_game_state = game_state.copy()
        self.consecutive_errors = 0
        self.success_rate_tracking['successes'] += 1
        
        if self.success_rate_tracking['successes'] % 10 == 0:
            total = self.success_rate_tracking['successes'] + self.success_rate_tracking['failures']
            success_rate = (self.success_rate_tracking['successes'] / total) * 100
            print(f"📊 PlayerAgent Success Rate: {success_rate:.1f}% ({total} total requests)")
    
    def _record_ai_failure(self, error: Exception, screenshot_path: str, game_state: Dict[str, Any]):
        """Record failed AI request/response cycle"""
        self.current_retry_count += 1
        self.consecutive_errors += 1
        self.success_rate_tracking['failures'] += 1
        
        print(f"📉 PlayerAgent Failure #{self.consecutive_errors} (Retry {self.current_retry_count}/{self.max_retry_attempts})")
        print(f"🔍 Error Type: {self._classify_error_type(error)}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from database"""
        try:
            config_obj = Configuration.get_config()
            return config_obj.to_dict() if config_obj else None
        except Exception as e:
            print(f"⚠️ PlayerAgent: Error loading configuration: {e}")
            return None
    
    def reset_session(self):
        """Reset agent state when mGBA session ends"""
        self.last_successful_screenshots = None
        self.last_successful_game_state = None
        self.current_retry_count = 0
        self.consecutive_errors = 0
        print("🔄 PlayerAgent session reset")
    
    def set_memory_system(self, memory_system):
        """Set memory system for integration"""
        self.memory_system = memory_system
        print("🧠 PlayerAgent memory system connected")