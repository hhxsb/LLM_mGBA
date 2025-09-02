#!/usr/bin/env python3
"""
PlayerAgent - Handles game decision making and AI gameplay logic.
Extracted from AIGameService for better separation of concerns.
"""

import time
import os
import queue
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Callable
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
    """Autonomous AI agent responsible for making game decisions and controlling gameplay"""
    
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
        
        # Session-aware context memory (similar to NarrationAgent but focused on decisions)
        self.session_context = {
            "recent_decisions": [],  # Last 5 decisions with outcomes
            "current_objectives": [],  # Session-specific objectives
            "encountered_npcs": [],  # NPCs met this session
            "discovered_locations": [],  # New locations found
            "failed_attempts": {},  # Track what didn't work (location -> failed_actions)
            "successful_patterns": {},  # Track what worked (situation -> successful_actions)
            "token_usage": {  # Track token optimization
                "total_estimated_tokens": 0,
                "context_lengths": [],
                "optimization_savings": 0
            }
        }
        self.max_session_history = 5
        
        # Autonomous operation capabilities
        self.autonomous_mode = False
        self.autonomous_thread = None
        self.running = False
        
        # Screenshot tracking and management
        self.screenshot_map = {}  # {filename: creation_time}
        self.screenshot_counter = 0
        self.current_screenshot_path = None
        
        # Communication interfaces
        self.narration_queue = None  # Queue for sending responses to NarrationAgent
        self.chat_message_sender = None  # Callback for sending messages to frontend
        self.screenshot_requester = None  # Callback for requesting screenshots from mGBA
        self.button_sender = None  # Callback for sending button commands to mGBA
        
        # Game cycle management
        self.decision_count = 0
        self.cycle_times = []
        self.max_cycle_history = 10
        
        print("🎮 PlayerAgent initialized - ready for autonomous game decision making")
    
    def initialize_llm(self, config: Dict[str, Any]):
        """Initialize LLM client with configuration"""
        if not self.llm_client:
            self.llm_client = LLMClient(config)
            print("🤖 PlayerAgent LLM client initialized")
    
    def set_narration_queue(self, narration_queue: queue.Queue):
        """Set the queue for sending successful responses to NarrationAgent"""
        self.narration_queue = narration_queue
        print("🎯 PlayerAgent connected to narration queue")
    
    def set_chat_message_sender(self, message_sender: Callable[[str, str], None]):
        """Set callback for sending messages directly to frontend chat"""
        self.chat_message_sender = message_sender
        print("💬 PlayerAgent connected to chat messaging")
    
    def set_screenshot_requester(self, screenshot_requester: Callable[[], str]):
        """Set callback for requesting screenshots from mGBA"""
        self.screenshot_requester = screenshot_requester
        print("📸 PlayerAgent connected to screenshot requester")
    
    def set_button_sender(self, button_sender: Callable[[List[str], Optional[List[int]]], bool]):
        """Set callback for sending button commands to mGBA"""
        self.button_sender = button_sender
        print("🎮 PlayerAgent connected to button sender")
    
    def start_autonomous_play(self, initial_screenshot: str, initial_game_state: Dict[str, Any]):
        """Start autonomous gameplay in a separate thread"""
        if self.autonomous_mode:
            print("⚠️ PlayerAgent already running in autonomous mode")
            return
        
        if not all([self.chat_message_sender, self.screenshot_requester, self.button_sender]):
            print("❌ PlayerAgent: Missing required communication interfaces")
            return
        
        self.autonomous_mode = True
        self.running = True
        self.current_screenshot_path = initial_screenshot
        
        # Register initial screenshot
        self._register_screenshot(initial_screenshot)
        
        # Start autonomous thread
        self.autonomous_thread = threading.Thread(
            target=self._autonomous_game_loop, 
            args=(initial_screenshot, initial_game_state),
            daemon=True,
            name="PlayerAgent-Autonomous"
        )
        self.autonomous_thread.start()
        print("🚀 PlayerAgent started in autonomous mode")
    
    def stop_autonomous_play(self):
        """Stop autonomous gameplay"""
        if not self.autonomous_mode:
            return
        
        self.running = False
        self.autonomous_mode = False
        
        if self.autonomous_thread and self.autonomous_thread.is_alive():
            self.autonomous_thread.join(timeout=5.0)
        
        print("🛑 PlayerAgent autonomous mode stopped")
    
    def _autonomous_game_loop(self, initial_screenshot: str, initial_game_state: Dict[str, Any]):
        """Main autonomous game loop - runs in separate thread"""
        current_screenshot = initial_screenshot
        current_game_state = initial_game_state.copy()
        
        try:
            # Send initial screenshot message
            self._send_single_screenshot_message(current_screenshot, current_game_state)
            
            while self.running:
                cycle_start = time.time()
                
                try:
                    # Get previous screenshot for comparison
                    previous_screenshot = self._get_previous_screenshot_path(current_screenshot)
                    
                    # Send screenshot messages to frontend
                    if previous_screenshot and previous_screenshot != current_screenshot:
                        self._send_screenshot_comparison_message(previous_screenshot, current_screenshot, current_game_state)
                    else:
                        self._send_single_screenshot_message(current_screenshot, current_game_state)
                    
                    # Make AI decision
                    player_response = self._make_autonomous_decision(
                        current_screenshot, current_game_state, previous_screenshot
                    )
                    
                    # Update session context with decision outcome
                    self._update_session_context(player_response, current_game_state)
                    
                    # Send AI response to chat
                    self._send_ai_response_message(player_response.to_dict())
                    
                    # If successful, send to narration queue with enhanced context
                    if player_response.success and self.narration_queue:
                        try:
                            # Send enhanced data including session context
                            narration_data = {
                                "player_response": player_response.to_dict(),
                                "game_state": current_game_state.copy(),
                                "session_context": self.get_session_context_for_narration()
                            }
                            self.narration_queue.put_nowait(narration_data)
                            print("📤 PlayerAgent: Response sent to narration queue with session context")
                        except queue.Full:
                            print("⚠️ PlayerAgent: Narration queue full - dropping narration request")
                    
                    # Execute actions if any
                    if player_response.actions and player_response.success:
                        self._execute_actions(player_response.actions, player_response.durations)
                        
                        # Wait for game to process actions
                        action_delay = self._calculate_action_delay(player_response.actions, player_response.durations)
                        time.sleep(action_delay)
                    
                    # Request next screenshot for next cycle
                    if self.running:  # Check if we're still running
                        next_screenshot = self._request_next_screenshot()
                        if next_screenshot:
                            current_screenshot = next_screenshot
                            self._register_screenshot(current_screenshot)
                    
                    # Performance tracking
                    cycle_time = time.time() - cycle_start
                    self.cycle_times.append(cycle_time)
                    if len(self.cycle_times) > self.max_cycle_history:
                        self.cycle_times = self.cycle_times[-self.max_cycle_history:]
                    
                    self.decision_count += 1
                    print(f"🎯 PlayerAgent cycle #{self.decision_count} completed in {cycle_time:.2f}s")
                    
                    # Apply decision cooldown
                    config = self._load_config()
                    cooldown = config.get('decision_cooldown', 3) if config else 3
                    time.sleep(cooldown)
                    
                except Exception as cycle_error:
                    import traceback
                    error_details = traceback.format_exc()
                    print(f"❌ PlayerAgent cycle error: {cycle_error}")
                    print(f"📋 Full error traceback: {error_details}")
                    self._send_chat_message("system", f"⚠️ PlayerAgent cycle error: {str(cycle_error)}")
                    
                    # Wait before next attempt
                    time.sleep(2.0)
                    
        except Exception as e:
            print(f"❌ PlayerAgent autonomous loop error: {e}")
            self._send_chat_message("system", f"⚠️ PlayerAgent autonomous loop failed: {str(e)}")
        
        finally:
            print("🎮 PlayerAgent autonomous loop ended")
    
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
        
        # Process objective discovery if present
        if "objective_discovery" in ai_response and self.memory_system:
            self._process_objective_discovery(ai_response["objective_discovery"], game_state)
        
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
        
        # Reset session context
        self.session_context = {
            "recent_decisions": [],
            "current_objectives": [],
            "encountered_npcs": [],
            "discovered_locations": [],
            "failed_attempts": {},
            "successful_patterns": {}
        }
        
        # Reset autonomous state
        self.decision_count = 0
        self.cycle_times = []
        self.screenshot_map = {}
        self.screenshot_counter = 0
        
        print("🔄 PlayerAgent session reset with enhanced context")
    
    def set_memory_system(self, memory_system):
        """Set memory system for integration"""
        self.memory_system = memory_system
        print("🧠 PlayerAgent memory system connected")
    
    # === Autonomous Operation Helper Methods ===
    
    def _make_autonomous_decision(self, screenshot_path: str, game_state: Dict[str, Any], 
                                 previous_screenshot: Optional[str] = None) -> PlayerResponse:
        """Make AI decision for autonomous gameplay with token-optimized context"""
        # Get compact session context for immediate decision support
        enhanced_context = self._get_enhanced_context(game_state)
        
        # Add optimized memory context (token-efficient)
        optimized_memory = self._get_optimized_memory_context(game_state, max_tokens=100)
        if optimized_memory:
            enhanced_context += f"\n\n## 🧠 Memory:\n{optimized_memory}"
        
        # Add compact situational context for immediate needs
        situational_context = self._get_situational_memory_context(game_state)
        if situational_context:
            enhanced_context += f"\n\n## 🎯 Current:\n{situational_context}"
        
        # Track token usage for optimization insights
        self._track_token_usage(enhanced_context)
        
        # Use existing analyze_and_decide logic with optimized context
        return self.analyze_and_decide(
            screenshot_path=screenshot_path,
            game_state=game_state,
            previous_screenshot=previous_screenshot,
            enhanced_context=enhanced_context
        )
    
    def _get_situational_memory_context(self, game_state: Dict[str, Any]) -> str:
        """Get memory context filtered by current situation for more relevant decisions"""
        current_situation = self._classify_current_situation(game_state)
        current_location = self._get_current_location_key(game_state)
        
        context_lines = []
        
        # Critical failures first (most important)
        if current_location in self.session_context["failed_attempts"]:
            failed_actions = self.session_context["failed_attempts"][current_location]
            unique_failures = list(dict.fromkeys(failed_actions[-3:]))  # Reduced from 5 to 3
            if unique_failures:
                context_lines.append(f"❌ Avoid: {', '.join(unique_failures)}")
        
        # High-value successful patterns (reduced token usage)
        if current_situation in self.session_context["successful_patterns"]:
            successful_actions = self.session_context["successful_patterns"][current_situation]
            from collections import Counter
            action_counts = Counter(successful_actions)
            top_actions = [action for action, _ in action_counts.most_common(2)]  # Reduced from 3 to 2
            if top_actions:
                context_lines.append(f"✅ {', '.join(top_actions)}")
        
        # Recent dialogue opportunities (compact)
        current_map = game_state.get("map_id", 0)
        map_npcs = [npc for npc in self.session_context["encountered_npcs"] 
                   if f"map_{current_map}_" in npc.get("location", "")]
        if map_npcs:
            latest_dialogue = map_npcs[-1].get("dialogue", "")[:30]  # Truncate to 30 chars
            context_lines.append(f"💬 {latest_dialogue}...")
        
        # Critical performance warnings only
        if self.consecutive_errors >= 2:
            context_lines.append("⚠️ Try simpler actions")
        elif len(self.session_context["recent_decisions"]) >= 3:
            recent_actions = [d.get("actions", []) for d in self.session_context["recent_decisions"][-3:]]
            if len(set(str(actions) for actions in recent_actions)) == 1:
                context_lines.append("🔄 Vary actions")
        
        return "\n".join(context_lines)
    
    def _get_optimized_memory_context(self, game_state: Dict[str, Any], max_tokens: int = 150) -> str:
        """Get memory context optimized for token usage with intelligent prioritization"""
        if not self.memory_system:
            return ""
        
        try:
            # Get full memory context from Graphiti
            recent_events = self.session_context.get("recent_decisions", [])
            recent_events_safe = recent_events[-3:] if recent_events else []
            
            full_context = self.memory_system.get_context(
                current_situation=self._classify_current_situation(game_state),
                location=self._get_current_location_key(game_state),
                recent_events=recent_events_safe
            )
            
            # Priority-based context extraction
            priority_sections = []
            
            # P1: Current objectives (critical for decision making)
            if full_context and "objectives" in full_context.lower():
                obj_lines = [line for line in full_context.split('\n') if line and 'objective' in line.lower()]
                if obj_lines:
                    priority_sections.append(f"🎯 {obj_lines[0][:50]}...")
            
            # P2: Learned strategies for current situation (high value)
            if full_context and ("strategies" in full_context.lower() or "learned" in full_context.lower()):
                strategy_lines = [line for line in full_context.split('\n') if line and any(word in line.lower() for word in ['learned', 'strategy', 'works'])]
                if strategy_lines:
                    priority_sections.append(f"💡 {strategy_lines[0][:40]}...")
            
            # P3: Critical warnings (safety)
            if full_context and ("avoid" in full_context.lower() or "failed" in full_context.lower()):
                warning_lines = [line for line in full_context.split('\n') if line and any(word in line.lower() for word in ['avoid', 'failed', 'stuck'])]
                if warning_lines:
                    priority_sections.append(f"⚠️ {warning_lines[0][:40]}...")
            
            # Combine and trim to token limit
            optimized_context = "\n".join(priority_sections)
            
            # Rough token estimation (4 chars per token)
            if len(optimized_context) > max_tokens * 4:
                optimized_context = optimized_context[:max_tokens * 4] + "..."
            
            return optimized_context
            
        except Exception as e:
            print(f"⚠️ PlayerAgent: Memory context optimization failed: {e}")
            return ""
    
    def _get_enhanced_context(self, game_state: Dict[str, Any]) -> str:
        """Build enhanced context for AI decision making with intelligent prioritization"""
        context_parts = []
        
        # Critical information first (always include)
        if self.consecutive_errors > 0:
            context_parts.append(f"⚠️ Errors: {self.consecutive_errors}")
        
        # Location-specific failures (high priority when relevant)
        current_location = self._get_current_location_key(game_state)
        if current_location in self.session_context["failed_attempts"]:
            failed_actions = self.session_context["failed_attempts"][current_location]
            context_parts.append(f"❌ Avoid: {', '.join(failed_actions[-2:])}")
        
        # Successful patterns for current situation (high value)
        current_situation = self._classify_current_situation(game_state)
        if current_situation in self.session_context["successful_patterns"]:
            successful_actions = self.session_context["successful_patterns"][current_situation]
            context_parts.append(f"✅ Try: {', '.join(successful_actions[-2:])}")
        
        # Recent outcomes (compact format)
        if self.session_context["recent_decisions"]:
            recent = self.session_context["recent_decisions"][-2:]  # Only last 2
            outcomes = []
            for decision in recent:
                outcome = "✅" if decision.get("success", True) else "❌"
                actions = decision.get("actions", [])
                action = actions[0] if actions else ""  # Safe access to first action
                outcomes.append(f"{outcome}{action}")
            context_parts.append(f"Recent: {' '.join(outcomes)}")
        
        # Performance metrics (only if significant)
        if self.cycle_times and len(self.cycle_times) > 5:
            avg_time = sum(self.cycle_times[-5:]) / 5  # Last 5 cycles only
            if avg_time > 3.0:  # Only show if slow
                context_parts.append(f"⏱️ {avg_time:.1f}s")
        
        # Session progress (compact)
        context_parts.append(f"#{self.decision_count}")
        
        return " | ".join(context_parts)
    
    def _track_token_usage(self, context: str):
        """Track token usage for optimization insights"""
        # Estimate tokens (rough approximation: 4 chars per token)
        estimated_tokens = len(context) // 4
        
        # Update token usage tracking
        token_data = self.session_context["token_usage"]
        token_data["total_estimated_tokens"] += estimated_tokens
        token_data["context_lengths"].append(estimated_tokens)
        
        # Keep only last 10 context lengths for trend analysis
        if len(token_data["context_lengths"]) > 10:
            token_data["context_lengths"] = token_data["context_lengths"][-10:]
        
        # Calculate optimization savings compared to unoptimized context
        if len(token_data["context_lengths"]) > 1:
            avg_optimized = sum(token_data["context_lengths"]) / len(token_data["context_lengths"])
            baseline_estimate = 200  # Estimated tokens for unoptimized context
            if avg_optimized < baseline_estimate:
                token_data["optimization_savings"] = baseline_estimate - avg_optimized
        
        # Log token usage periodically
        if self.decision_count % 10 == 0 and token_data["context_lengths"]:
            avg_tokens = sum(token_data["context_lengths"]) / len(token_data["context_lengths"])
            savings = token_data["optimization_savings"]
            print(f"🧮 TokenOptimization: Avg {avg_tokens:.0f} tokens/decision, saving ~{savings:.0f} tokens vs baseline")
    
    def get_token_optimization_stats(self) -> Dict[str, Any]:
        """Get token usage optimization statistics"""
        token_data = self.session_context["token_usage"]
        if not token_data["context_lengths"]:
            return {"status": "No data available"}
        
        avg_tokens = sum(token_data["context_lengths"]) / len(token_data["context_lengths"])
        total_decisions = len(token_data["context_lengths"])
        
        return {
            "average_tokens_per_decision": round(avg_tokens, 1),
            "total_decisions": total_decisions,
            "total_estimated_tokens": token_data["total_estimated_tokens"],
            "optimization_savings_per_decision": round(token_data["optimization_savings"], 1),
            "total_savings": round(token_data["optimization_savings"] * total_decisions, 1),
            "efficiency_improvement": f"{(token_data['optimization_savings'] / 200) * 100:.1f}%" if token_data["optimization_savings"] > 0 else "0%"
        }
    
    def _execute_actions(self, actions: List[str], durations: Optional[List[int]] = None):
        """Execute button actions using the configured button sender"""
        if not self.button_sender:
            print("⚠️ PlayerAgent: No button sender configured")
            return
        
        try:
            success = self.button_sender(actions, durations)
            if success:
                print(f"🎮 PlayerAgent: Executed {len(actions)} actions: {', '.join(actions)}")
            else:
                print(f"⚠️ PlayerAgent: Failed to execute actions: {', '.join(actions)}")
        except Exception as e:
            print(f"❌ PlayerAgent: Error executing actions: {e}")
    
    def _calculate_action_delay(self, actions: List[str], durations: Optional[List[int]] = None) -> float:
        """Calculate how long to wait for actions to complete"""
        if not actions:
            return 0.0
        
        # Base delay for game state stabilization
        base_delay = 0.5
        
        # Additional delay based on action type and count
        action_delay = len(actions) * 0.3  # 0.3s per action
        
        # If custom durations provided, use those
        if durations and len(durations) == len(actions):
            total_duration = sum(durations) / 1000.0  # Convert ms to seconds
            return max(base_delay, total_duration)
        
        return base_delay + action_delay
    
    def _request_next_screenshot(self) -> Optional[str]:
        """Request next screenshot from mGBA"""
        if not self.screenshot_requester:
            print("⚠️ PlayerAgent: No screenshot requester configured")
            return None
        
        try:
            screenshot_path = self.screenshot_requester()
            print(f"📸 PlayerAgent: Requested new screenshot: {os.path.basename(screenshot_path) if screenshot_path else 'None'}")
            return screenshot_path
        except Exception as e:
            print(f"❌ PlayerAgent: Error requesting screenshot: {e}")
            return None
    
    def _register_screenshot(self, screenshot_path: str):
        """Register screenshot in tracking map"""
        if not screenshot_path or not os.path.exists(screenshot_path):
            return
        
        filename = os.path.basename(screenshot_path)
        self.screenshot_counter += 1
        self.screenshot_map[filename] = self.screenshot_counter
        
        # Keep only recent screenshots for comparison
        if len(self.screenshot_map) > 10 and self.screenshot_map:
            # Remove oldest screenshot
            oldest_file = min(self.screenshot_map.keys(), key=lambda k: self.screenshot_map[k])
            del self.screenshot_map[oldest_file]
        
        print(f"📸 PlayerAgent: Registered screenshot {filename} (#{self.screenshot_counter})")
    
    def _get_previous_screenshot_path(self, current_path: str) -> Optional[str]:
        """Get previous screenshot path for comparison"""
        if not current_path:
            return None
        
        current_filename = os.path.basename(current_path)
        current_counter = self.screenshot_map.get(current_filename, 0)
        
        # Find previous screenshot
        previous_counter = current_counter - 1
        for filename, counter in self.screenshot_map.items():
            if counter == previous_counter:
                previous_path = os.path.join(os.path.dirname(current_path), filename)
                if os.path.exists(previous_path):
                    return previous_path
        
        return None
    
    def _send_chat_message(self, message_type: str, content: str):
        """Send message to frontend chat"""
        if self.chat_message_sender:
            try:
                self.chat_message_sender(message_type, content)
            except Exception as e:
                print(f"❌ PlayerAgent: Error sending chat message: {e}")
        else:
            print(f"⚠️ PlayerAgent chat message (no sender): [{message_type}] {content}")
    
    def _send_single_screenshot_message(self, screenshot_path: str, game_state: Dict[str, Any]):
        """Send single screenshot message to frontend"""
        if not screenshot_path:
            return
        
        filename = os.path.basename(screenshot_path)
        position = game_state.get("position", {})
        
        message = f"📸 Screenshot: {filename} | Position: ({position.get('x', '?')}, {position.get('y', '?')}) | Direction: {game_state.get('direction', '?')}"
        self._send_chat_message("screenshot", message)
    
    def _send_screenshot_comparison_message(self, previous_path: str, current_path: str, game_state: Dict[str, Any]):
        """Send screenshot comparison message to frontend"""
        if not previous_path or not current_path:
            self._send_single_screenshot_message(current_path, game_state)
            return
        
        prev_filename = os.path.basename(previous_path)
        curr_filename = os.path.basename(current_path)
        position = game_state.get("position", {})
        
        message = f"📸 Screenshots: {prev_filename} → {curr_filename} | Position: ({position.get('x', '?')}, {position.get('y', '?')}) | Direction: {game_state.get('direction', '?')}"
        self._send_chat_message("screenshot", message)
    
    def _send_ai_response_message(self, response_dict: Dict[str, Any]):
        """Send AI response message to frontend"""
        actions_text = ", ".join(response_dict.get("actions", [])) if response_dict.get("actions") else "No actions"
        success_indicator = "✅" if response_dict.get("success", True) else "❌"
        
        message = f"{success_indicator} AI Decision: {actions_text} | {response_dict.get('text', 'No reasoning')}"
        self._send_chat_message("ai_response", message)
    
    # === Session Context Management ===
    
    def _update_session_context(self, player_response: PlayerResponse, game_state: Dict[str, Any]):
        """Update session context with decision outcomes for better learning"""
        # Record this decision
        decision_record = {
            "timestamp": time.time(),
            "actions": player_response.actions.copy(),
            "success": player_response.success,
            "situation": player_response.current_situation,
            "location": self._get_current_location_key(game_state),
            "dialogue": player_response.detected_dialogue,
            "reasoning": player_response.action_reasoning
        }
        
        self.session_context["recent_decisions"].append(decision_record)
        
        
        # Keep only recent decisions
        if len(self.session_context["recent_decisions"]) > self.max_session_history:
            self.session_context["recent_decisions"] = self.session_context["recent_decisions"][-self.max_session_history:]
        
        # Track failed attempts by location
        if not player_response.success:
            location_key = self._get_current_location_key(game_state)
            if location_key not in self.session_context["failed_attempts"]:
                self.session_context["failed_attempts"][location_key] = []
            self.session_context["failed_attempts"][location_key].extend(player_response.actions)
            
            # Keep only recent failures per location
            if len(self.session_context["failed_attempts"][location_key]) > 10:
                self.session_context["failed_attempts"][location_key] = self.session_context["failed_attempts"][location_key][-10:]
        
        # Track successful patterns by situation
        if player_response.success and player_response.actions:
            situation_key = self._classify_current_situation(game_state)
            if situation_key not in self.session_context["successful_patterns"]:
                self.session_context["successful_patterns"][situation_key] = []
            self.session_context["successful_patterns"][situation_key].extend(player_response.actions)
            
            # Keep only recent successes per situation
            if len(self.session_context["successful_patterns"][situation_key]) > 6:
                self.session_context["successful_patterns"][situation_key] = self.session_context["successful_patterns"][situation_key][-6:]
        
        # Track dialogue encounters
        if player_response.detected_dialogue:
            npc_record = {
                "timestamp": time.time(),
                "location": self._get_current_location_key(game_state),
                "dialogue": player_response.detected_dialogue
            }
            self.session_context["encountered_npcs"].append(npc_record)
            
            # Keep only recent NPCs
            if len(self.session_context["encountered_npcs"]) > 5:
                self.session_context["encountered_npcs"] = self.session_context["encountered_npcs"][-5:]
    
    def _get_current_location_key(self, game_state: Dict[str, Any]) -> str:
        """Generate location key for session tracking"""
        position = game_state.get("position", {})
        map_id = game_state.get("map_id", 0)
        return f"map_{map_id}_x{position.get('x', 0)}_y{position.get('y', 0)}"
    
    def _classify_current_situation(self, game_state: Dict[str, Any]) -> str:
        """Classify current game situation for pattern matching"""
        # Basic situation classification - can be enhanced with more game-specific logic
        map_id = game_state.get("map_id", 0)
        
        # Common situation patterns
        if map_id == 0:
            return "overworld_exploration"
        elif 1 <= map_id <= 50:  # Indoor locations
            return "indoor_navigation"  
        elif 51 <= map_id <= 100:  # Battle areas
            return "battle_situation"
        else:
            return "special_area"
    
    def get_session_context_for_narration(self) -> Dict[str, Any]:
        """Get session context data to share with NarrationAgent"""
        return {
            "recent_decisions": self.session_context["recent_decisions"][-3:],  # Last 3 decisions
            "encountered_npcs": self.session_context["encountered_npcs"][-3:],  # Last 3 NPCs
            "current_objectives": self.session_context["current_objectives"],
            "performance_stats": {
                "decision_count": self.decision_count,
                "consecutive_errors": self.consecutive_errors,
                "success_rate": self._calculate_session_success_rate()
            }
        }
    
    def _calculate_session_success_rate(self) -> float:
        """Calculate success rate for current session"""
        if not self.session_context["recent_decisions"]:
            return 1.0
        
        successful_decisions = sum(1 for d in self.session_context["recent_decisions"] if d.get("success", True))
        return successful_decisions / len(self.session_context["recent_decisions"])
    
    def _process_objective_discovery(self, objective_data: Dict[str, Any], game_state: Dict[str, Any]):
        """Process objective discovery from LLM function call"""
        if not self.memory_system or not objective_data:
            return
        
        try:
            description = objective_data.get("description", "").strip()
            priority = objective_data.get("priority", 5)
            category = objective_data.get("category", "general")
            
            if not description:
                print("⚠️ PlayerAgent: Empty objective description received")
                return
            
            current_location = self._get_current_location_key(game_state)
            
            objective_id = self.memory_system.discover_objective(
                description=description,
                location=current_location,
                category=category,
                priority=priority
            )
            
            if objective_id:
                print(f"🎯 PlayerAgent: Discovered objective via function call: '{description}' (Priority: {priority}, Category: {category})")
                # Also send to chat for user visibility
                self._send_chat_message("system", f"🎯 New objective discovered: {description}")
            else:
                print(f"⚠️ PlayerAgent: Failed to create objective: {description}")
        
        except Exception as e:
            print(f"⚠️ PlayerAgent: Error processing objective discovery: {e}")
    
