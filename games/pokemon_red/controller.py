#!/usr/bin/env python3
"""
Pokemon Red specific controller implementation.
"""

from typing import Dict, List, Any, Tuple, Optional
import socket
import time
import os
import sys
import threading

# Add parent directories to path to import core modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.base_game_controller import BaseGameController, ToolCall
from core.base_game_engine import BaseGameEngine
from core.base_knowledge_system import BaseKnowledgeSystem
from core.base_prompt_template import BasePromptTemplate

# Use absolute imports to avoid relative import issues when loaded dynamically
import importlib.util
import os

def _load_module_from_file(module_name, file_path):
    """Helper to load a module from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load game-specific modules
current_dir = os.path.dirname(__file__)
game_engine_module = _load_module_from_file("game_engine", os.path.join(current_dir, "game_engine.py"))
knowledge_system_module = _load_module_from_file("knowledge_system", os.path.join(current_dir, "knowledge_system.py"))
prompt_template_module = _load_module_from_file("prompt_template", os.path.join(current_dir, "prompt_template.py"))
llm_client_module = _load_module_from_file("llm_client", os.path.join(current_dir, "llm_client.py"))

PokemonRedGameEngine = game_engine_module.PokemonRedGameEngine
PokemonRedKnowledgeSystem = knowledge_system_module.PokemonRedKnowledgeSystem
PokemonRedPromptTemplate = prompt_template_module.PokemonRedPromptTemplate
GeminiClient = llm_client_module.GeminiClient


class PokemonRedController(BaseGameController):
    """Controller specifically for Pokemon Red."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # The logger is now properly initialized in the base class
        
        # Initialize notepad for Pokemon Red
        self._initialize_pokemon_notepad()
        
        # Continuous recording state (current_recording_id already initialized in base class)
        self.pending_video_id = None
    
    def _create_game_engine(self) -> BaseGameEngine:
        """Create Pokemon Red game engine."""
        return PokemonRedGameEngine(self.config)
    
    def _create_knowledge_system(self) -> BaseKnowledgeSystem:
        """Create Pokemon Red knowledge system."""
        knowledge_file = self.config.get('knowledge_file', 'data/knowledge_graph.json')
        return PokemonRedKnowledgeSystem(knowledge_file)
    
    def _create_prompt_template(self) -> BasePromptTemplate:
        """Create Pokemon Red prompt template."""
        template_path = self.config.get('prompt_template_path', 'data/prompt_template.txt')
        return PokemonRedPromptTemplate(template_path)
    
    def _create_llm_client(self):
        """Create LLM client for Pokemon Red."""
        provider_config = self.config["providers"]["google"]
        return GeminiClient(
            api_key=provider_config["api_key"],
            model_name=provider_config["model_name"],
            max_tokens=provider_config.get("max_tokens", 1024)
        )
    
    def _initialize_pokemon_notepad(self):
        """Initialize Pokemon Red specific notepad."""
        if not os.path.exists(self.notepad_path):
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            initial_content = f"""# Pokémon Red Game Progress

Game started: {timestamp}

## Current Objectives
- Enter my name 'GEMINI' and give my rival a name
- Exit my house and start the Pokemon journey
- Find Professor Oak to get first Pokémon
- Begin the quest to become Pokemon Champion

## Current Location
- Starting in player's house in Pallet Town

## Game Progress
- Just beginning the adventure

## Items
- None yet

## Pokémon Team
- None yet

## Gym Badges
- None yet
"""
            
            with open(self.notepad_path, 'w') as f:
                f.write(initial_content)
    
    def _handle_game_specific_tool_call(self, call: ToolCall):
        """Handle Pokemon Red specific tool calls."""
        if call.name == "record_success":
            situation = call.arguments.get("situation", "")
            successful_action = call.arguments.get("successful_action", "")
            if situation and successful_action:
                # This would integrate with the knowledge system's failure patterns
                self.logger.success(f"Recorded successful strategy: {successful_action[:50]}...")
        
        elif call.name == "detect_goal":
            goal_description = call.arguments.get("goal_description", "")
            priority = call.arguments.get("priority", 5)
            if goal_description:
                goal_id = f"detected_{int(time.time())}"
                from core.base_knowledge_system import Goal
                goal = Goal(
                    id=goal_id,
                    description=goal_description,
                    type="detected",
                    status="active",
                    priority=int(priority),
                    location_id=self.current_game_state.map_id
                )
                self.knowledge_system.add_goal(goal)
                self.logger.goal(f"New goal detected: {goal_description}")
        
        elif call.name == "record_pokemon_encounter":
            pokemon_name = call.arguments.get("pokemon_name", "")
            caught = call.arguments.get("caught", False)
            if pokemon_name:
                self.knowledge_system.record_pokemon_encounter(
                    pokemon_name, self.current_game_state.map_id, caught
                )
                self.logger.pokemon(f"Recorded Pokémon encounter: {pokemon_name}")
        
        elif call.name == "record_gym_victory":
            gym_leader = call.arguments.get("gym_leader", "")
            badge_name = call.arguments.get("badge_name", "")
            if gym_leader and badge_name:
                self.knowledge_system.record_gym_victory(gym_leader, badge_name)
                self.logger.achievement(f"Recorded gym victory: {gym_leader} - {badge_name} Badge")
    
    def handle_client(self, client_socket, client_address):
        """Handle communication with the mGBA emulator client."""
        self.logger.section(f"Connected to emulator at {client_address}")
        
        self.current_client = client_socket
        self.last_decision_time = 0
        self.last_action_time = 0
        self.pending_action_duration = 0
        
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
                    content = parts[1:]
                    
                    if message_type == "ready":
                        self._handle_ready_message(client_socket)
                    
                    elif message_type == "screenshot_with_state":
                        self._handle_screenshot_with_state(client_socket, content)
                    
                    elif message_type == "enhanced_screenshot_with_state":
                        self._handle_enhanced_screenshot_with_state(client_socket, content)
                    
                    elif message_type == "state":
                        self._handle_state_message(client_socket, content)
            
            except socket.error as e:
                if e.args[0] != socket.EWOULDBLOCK and str(e) != 'Resource temporarily unavailable':
                    self.logger.error(f"Socket error: {e}")
                    break
            except Exception as e:
                self.logger.error(f"Error handling client: {e}")
                if not self.running:
                    break
                continue
            
            time.sleep(0.01)
        
        self.logger.section(f"Disconnected from emulator at {client_address}")
        
        self.current_client = None
        try:
            client_socket.close()
        except:
            pass
    
    def _handle_ready_message(self, client_socket):
        """Handle ready message from emulator."""
        self.logger.game_state("Emulator is ready for next command")
        
        self.emulator_ready = True
        
        # Check cooldown
        current_time = time.time()
        time_since_last_decision = current_time - self.last_decision_time
        
        if time_since_last_decision < self.decision_cooldown:
            wait_time = self.decision_cooldown - time_since_last_decision
            self.logger.debug(f"Waiting {wait_time:.2f}s for cooldown")
            time.sleep(wait_time)
        
        # Process immediately with video capture or request screenshot based on capture system
        if not self.is_processing:
            capture_config = self.config.get('capture_system', {})
            if capture_config.get('type') == 'screen':
                # When using screen capture, get game state and immediately process with video
                self.logger.debug("Getting game state for immediate video capture processing")
                try:
                    # Request game state then immediately process with video (no waiting)
                    client_socket.send(b'request_state\n')
                except Exception as e:
                    self.logger.error(f"Failed to request game state: {e}")
            else:
                # Traditional emulator screenshot mode
                try:
                    self.logger.debug("Requesting screenshot from emulator")
                    client_socket.send(b'request_screenshot\n')
                except Exception as e:
                    self.logger.error(f"Failed to request screenshot: {e}")
    
    def _handle_state_message(self, client_socket, content):
        """Handle game state message for continuous recording mode."""
        self.logger.game_state("Received game state for continuous recording")
        
        if len(content) >= 4:
            # Parse game state using game engine
            state_data = content[0:4]  # direction, x, y, mapId
            self.current_game_state = self.game_engine.parse_game_state(state_data)
            
            self.logger.debug(f"Game State: {self.current_game_state}")
            
            if self.continuous_recording:
                # Use unified continuous recording workflow
                decision = self._handle_continuous_recording_workflow(client_socket)
                if decision:
                    self._send_button_decision(client_socket, decision)
            else:
                # Fallback to old video sequence method for non-screen capture
                decision = self.process_video_sequence(1.0)
                self._send_button_decision(client_socket, decision)
    
    def _handle_continuous_recording_workflow(self, client_socket):
        """Unified continuous recording workflow to avoid duplication."""
        # 1. Check if we have a completed action to process
        if hasattr(self, '_action_completed') and self._action_completed:
            # Stop the current recording that captured thinking + action
            if (hasattr(self.capture_system, 'is_recording') and self.capture_system.is_recording):
                self.logger.debug("🎬 Stopping complete recording (thinking + action)")
                video_segment = self.capture_system.stop_recording()
                
                if video_segment:
                    self.logger.debug(f"📊 Processing complete video: {len(video_segment.frames)} frames, {video_segment.duration:.2f}s")
                    
                    # Process and make decision immediately
                    gif_image = self._create_all_frames_gif(video_segment)
                    if gif_image:
                        processed_video = {
                            'video_segment': video_segment,
                            'gif_image': gif_image,
                            'frame_count': len(video_segment.frames),
                            'duration': video_segment.duration,
                            'processed_at': time.time()
                        }
                        
                        decision = self._make_decision_from_processed_video(processed_video)
                        
                        # Reset action completed flag
                        self._action_completed = False
                        
                        # Start new recording for next cycle
                        recording_id = self.start_continuous_recording()
                        if recording_id is not None:
                            self.logger.debug(f"🎬 Started new recording #{recording_id} for next cycle")
                        
                        return decision
                    else:
                        self.logger.warning("⚠️ Failed to create GIF from complete video")
                else:
                    self.logger.warning("⚠️ No video segment from complete recording")
            
            # Reset flag if processing failed
            self._action_completed = False
        
        # 2. Start initial recording if none exists
        if not hasattr(self.capture_system, 'is_recording') or not self.capture_system.is_recording:
            recording_id = self.start_continuous_recording()
            if recording_id is not None:
                self.logger.debug(f"🎬 Started continuous recording #{recording_id} (will capture thinking + action)")
            else:
                self.logger.warning("⚠️ Failed to start recording")
        
        # 3. Make decision for first cycle only (subsequent cycles use processed video)
        if not hasattr(self, '_first_decision_made'):
            # For the very first decision, use fallback since we have no previous video
            self.logger.debug("🧠 Making first decision with basic state analysis")
            decision = self.process_video_sequence(1.0)  # Basic fallback for first decision only
            self._first_decision_made = True
            return decision
        else:
            # Subsequent cycles should have processed video available
            # If we reach here, it means the action completion hasn't been detected yet
            self.logger.debug("🔄 Waiting for action to complete before processing video")
            # Don't make a new decision - wait for action completion
            return None
    
    def _make_decision_from_processed_video(self, processed_video):
        """Make AI decision from processed video with GIF."""
        gif_image = processed_video['gif_image']
        video_segment = processed_video['video_segment']
        frame_count = processed_video['frame_count']
        duration = processed_video['duration']
        
        if not gif_image:
            self.logger.warning("No GIF available from processed video")
            return None
        
        # Build context for AI decision
        current_map = self.game_engine.get_map_name(self.current_game_state.map_id)
        self.knowledge_system.update_location(self.current_game_state, current_map)
        context = self._build_prompt_context()
        
        # Add video analysis context
        context['video_analysis'] = f"Continuous recording: {frame_count} frames over {duration:.2f}s at {self.capture_fps} FPS"
        
        # Format prompt
        prompt = self.prompt_template.format_template(
            game_state=self.current_game_state,
            **context
        )
        
        # Create tool objects
        tool_objects = self.prompt_template.create_tool_objects()
        
        # Log content being sent
        frame_description = f"Animated GIF - Complete video (thinking + action): {frame_count} frames over {duration:.2f}s at {self.capture_fps} FPS"
        self.logger.debug(f"   Content 1: {frame_description}")
        
        # Save for inspection if debug mode
        save_ai_frames = self.config.get('capture_system', {}).get('auto_cleanup', {}).get('save_ai_frames', True)
        if self.debug_mode and save_ai_frames:
            self.logger.debug(f"💾 Saving AI frames for inspection: description='{frame_description}'")
            self._save_ai_frames_for_inspection([gif_image], [frame_description], duration)
            
            # Log where the GIF was saved
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            ai_frames_dir = os.path.join(os.path.dirname(self.video_path), 'ai_frames')
            ai_request_dir = os.path.join(ai_frames_dir, f"ai_request_{timestamp}")
            self.logger.debug(f"💾 GIF saved to: {ai_request_dir}/ai_content_01_*.gif")
        
        try:
            # 📸 Add prompt context logging before LLM call (missing from dual process mode)
            self.logger.info(f"📸 LLM PROMPT CONTEXT: Map={current_map}, Player=({self.current_game_state.player_x},{self.current_game_state.player_y})")
            self.logger.debug(f"📸 LLM PROMPT LENGTH: {len(prompt)} characters")
            if self.debug_mode:
                self.logger.debug(f"📸 LLM FULL PROMPT: {prompt[:500]}{'...' if len(prompt) > 500 else ''}")
            
            response, tool_calls, text = self.llm_client.call_with_tools(
                message=prompt,
                tools=tool_objects,
                images=[gif_image]
            )
            
            # 📸 Add enhanced response logging (missing from dual process mode)
            self.logger.ai_response(text)
            self.logger.info(f"📸 LLM RESPONSE PROCESSING: {len(tool_calls)} tool calls, {len(text)} chars response")
            
            # Log tool call details
            if tool_calls:
                for i, call in enumerate(tool_calls):
                    self.logger.debug(f"📸 LLM TOOL CALL {i+1}: {call.name} with {len(call.arguments)} arguments")
            else:
                self.logger.warning("📸 LLM TOOL CALLS: No tool calls found in response")
            
            # Track conversation state based on AI response
            self._update_conversation_state_from_response(text)
            
            # Track character state based on AI response
            self._update_character_state_from_response(text)
            
            # Add AI response to context memory
            self._add_response_to_context_memory(text)
            
            # Process tool calls to extract button decision
            button_codes = None
            button_durations = []
            
            # 📸 Add decision reasoning logging throughout AI decision pipeline
            self.logger.debug(f"📸 DECISION PIPELINE: Processing {len(tool_calls)} tool calls for button extraction")
            
            for call in tool_calls:
                if call.name == 'press_button':
                    buttons = call.arguments.get('buttons', [])
                    durations = call.arguments.get('durations', [])
                    
                    # 📸 Log button selection reasoning
                    self.logger.info(f"📸 BUTTON SELECTION: LLM chose {len(buttons)} buttons: {buttons}")
                    
                    # Convert button names to codes
                    button_codes = self.game_engine.convert_button_names_to_codes(buttons)
                    self.logger.debug(f"📸 BUTTON CONVERSION: {buttons} → codes {button_codes}")
                    
                    # Convert durations to integers if provided
                    if durations:
                        try:
                            button_durations = [int(d) for d in durations]
                            # Ensure durations list matches buttons list length
                            while len(button_durations) < len(button_codes):
                                button_durations.append(2)  # Default duration
                            self.logger.debug(f"📸 BUTTON DURATIONS: {durations} → {button_durations}")
                        except (ValueError, TypeError):
                            self.logger.warning(f"📸 INVALID DURATIONS: {durations}, using defaults")
                            button_durations = [2] * len(button_codes)  # Use defaults
                    else:
                        button_durations = [2] * len(button_codes)  # Default durations
                        self.logger.debug(f"📸 BUTTON DURATIONS: Using default durations {button_durations}")
                    
                    # 📸 Log final decision reasoning
                    total_duration = sum(button_durations)
                    self.logger.info(f"📸 FINAL DECISION: {len(button_codes)} buttons, {total_duration} frames total duration")
                    break
                else:
                    self._handle_game_specific_tool_call(call)
            
            # 📸 Log decision outcome
            if button_codes:
                self.logger.info(f"📸 DECISION OUTCOME: SUCCESS - Will execute {len(button_codes)} button commands")
            else:
                self.logger.warning(f"📸 DECISION OUTCOME: NO BUTTONS - No press_button tool call found")
            
            return {'text': text, 'buttons': button_codes, 'durations': button_durations, 'raw_response': str(response), 'reasoning': f"Selected {len(button_codes) if button_codes else 0} buttons based on game context and visual analysis"}
            
        except Exception as e:
            self.logger.error(f"Error making decision from processed video: {e}")
            return None
    
    def _schedule_action_completion_check(self, action_duration_seconds):
        """Schedule a check for when the action completes."""
        def mark_action_completed():
            self.logger.debug(f"⏰ Waiting {action_duration_seconds:.2f}s for action to complete")
            time.sleep(action_duration_seconds + 0.2)  # Add small buffer
            self._action_completed = True
            # Reset scheduling flags for next action
            if hasattr(self, '_action_completion_scheduled'):
                delattr(self, '_action_completion_scheduled')
            if hasattr(self, '_current_action_duration'):
                delattr(self, '_current_action_duration')
            self.logger.debug(f"⏰ Action completed after {action_duration_seconds:.2f}s")
        
        completion_thread = threading.Thread(target=mark_action_completed, daemon=True)
        completion_thread.start()
    
    def _handle_screenshot_with_state(self, client_socket, content):
        """Handle screenshot with game state message."""
        self.logger.game_state("Received screenshot with game state")
        
        if len(content) >= 5:
            screenshot_path = content[0]
            
            # Parse game state using game engine
            state_data = content[1:5]  # direction, x, y, mapId
            self.current_game_state = self.game_engine.parse_game_state(state_data)
            
            self.logger.debug(f"Game State: {self.current_game_state}")
            
            # Decide whether to use video capture or screenshot
            capture_config = self.config.get('capture_system', {})
            
            # Always use video capture when screen capture is enabled
            if capture_config.get('type') == 'screen':
                # Always use video sequences for screen capture mode
                current_time = time.time()
                video_duration = 1.0  # Default 1 second for state analysis
                
                # Check if we have a pending action that's completed
                if (hasattr(self, 'pending_action_duration') and 
                    self.pending_action_duration > 0 and
                    current_time - self.last_action_time >= self.pending_action_duration):
                    
                    # This is action result analysis
                    video_duration = self.pending_action_duration
                    self.logger.debug(f"Analyzing completed action results ({video_duration}s video)")
                    self.pending_action_duration = 0  # Reset
                else:
                    # Check if action is still in progress
                    if (hasattr(self, 'pending_action_duration') and 
                        self.pending_action_duration > 0 and
                        current_time - self.last_action_time < self.pending_action_duration):
                        
                        # Action still in progress, wait a bit more
                        remaining_time = self.pending_action_duration - (current_time - self.last_action_time)
                        self.logger.debug(f"Action still in progress, waiting {remaining_time:.1f}s more...")
                        time.sleep(remaining_time + 0.1)  # Add small buffer
                        self.pending_action_duration = 0  # Reset after waiting
                    
                    self.logger.debug(f"Analyzing current game state (1s video)")
                
                decision = self.process_video_sequence(video_duration)
            else:
                # Use traditional emulator screenshot file
                decision = self.process_screenshot(screenshot_path)  # Use file
            
            self._send_button_decision(client_socket, decision)
    
    def _handle_enhanced_screenshot_with_state(self, client_socket, content):
        """Handle enhanced screenshot with game state message."""
        self.logger.game_state("Received enhanced screenshot with game state")
        
        if len(content) >= 7:
            screenshot_path = content[0]
            previous_screenshot_path = content[1]
            
            # Parse game state
            state_data = content[2:6]  # direction, x, y, mapId
            self.current_game_state = self.game_engine.parse_game_state(state_data)
            button_count = int(content[6])
            
            self.logger.debug(f"Enhanced Game State: {self.current_game_state}, Button Count: {button_count}")
            
            # Process enhanced screenshot or use video capture based on capture system
            capture_config = self.config.get('capture_system', {})
            
            if capture_config.get('type') == 'screen':
                # Use unified continuous recording workflow for enhanced mode too
                decision = self._handle_continuous_recording_workflow(client_socket)
                if decision:
                    self._send_button_decision(client_socket, decision)
            else:
                # Traditional enhanced screenshot processing
                if os.path.exists(screenshot_path):
                    decision = self.process_screenshot(screenshot_path)
                    if decision:
                        self._send_button_decision(client_socket, decision)
                else:
                    self.logger.warning("⚠️ Enhanced screenshot file not found")
    
    def _send_button_decision(self, client_socket, decision):
        """Send button decision to emulator with continuous recording."""
        if decision and decision.get('buttons') is not None:
            try:
                button_codes = decision['buttons']
                button_durations = decision.get('durations', [])
                
                # Calculate expected action duration using the proper method (only once)
                if not hasattr(self, '_current_action_duration'):
                    action_duration_seconds = self._calculate_action_duration(button_codes, button_durations)
                    self._current_action_duration = action_duration_seconds
                else:
                    action_duration_seconds = self._current_action_duration
                
                if self.continuous_recording:
                    # NEW SINGLE RECORDING WORKFLOW - KEEP RECORDING DURING ACTION
                    # Don't stop recording here - let it continue through action execution
                    self.logger.debug("🎬 Continuing recording during action execution")
                    
                    # Schedule action completion detection (only if not already scheduled)
                    if not hasattr(self, '_action_completion_scheduled'):
                        self._schedule_action_completion_check(action_duration_seconds)
                        self._action_completion_scheduled = True
                
                # Format message for emulator
                button_codes_str = ','.join(str(code) for code in button_codes)
                if button_durations:
                    durations_str = ','.join(str(d) for d in button_durations)
                    message = f"{button_codes_str}|{durations_str}"
                else:
                    message = button_codes_str
                
                self.logger.debug(f"Sending button data: {message}")
                self.logger.ai_action(f"Button commands sent: {message}")
                
                # Send button commands
                client_socket.send(message.encode('utf-8') + b'\n')
                self.emulator_ready = False
                self.last_decision_time = time.time()
                
            except Exception as e:
                self.logger.error(f"Failed to send button commands: {e}")
        else:
            # No decision made, respect cooldown and request another screenshot
            self.last_decision_time = time.time()
            try:
                time.sleep(0.5)
                client_socket.send(b'request_screenshot\n')
            except Exception as e:
                self.logger.error(f"Failed to request another screenshot: {e}")
    
    def _update_conversation_state_from_response(self, ai_response: str):
        """Update conversation state based on AI response text."""
        response_lower = ai_response.lower()
        
        # Detect conversation mentions and update state
        conversation_keywords = {
            "mom": ["my mother", "mom", "my mom", "mother is", "she's telling"],
            "professor_oak": ["professor", "oak", "professor oak"],
            "rival": ["rival", "blue", "gary"],
            "nurse_joy": ["nurse", "joy", "nurse joy"],
        }
        
        # Look for dialogue-related phrases
        dialogue_indicators = [
            "talking to", "conversation", "dialogue", "she is speaking", 
            "asking", "telling me", "says", "dialogue box", "text box"
        ]
        
        # Check if we're in a conversation
        is_in_dialogue = any(indicator in response_lower for indicator in dialogue_indicators)
        
        if is_in_dialogue:
            # Detect which NPC we're talking to
            detected_npc = None
            detected_role = None
            
            for npc_role, keywords in conversation_keywords.items():
                if any(keyword in response_lower for keyword in keywords):
                    detected_npc = npc_role.replace("_", " ").title()
                    detected_role = npc_role
                    break
            
            # Extract conversation topic from response
            topic = self._extract_conversation_topic(ai_response)
            
            # Start or continue conversation
            if detected_npc and not self.knowledge_system.conversation_state.current_npc:
                self.knowledge_system.start_conversation(
                    npc_name=detected_npc,
                    npc_role=detected_role, 
                    topic=topic or "general conversation",
                    location_id=self.current_game_state.map_id
                )
            elif detected_npc and self.knowledge_system.conversation_state.current_npc:
                # Update existing conversation
                if topic:
                    self.knowledge_system.conversation_state.conversation_topic = topic
                
                # Add AI response as dialogue
                self.knowledge_system.add_dialogue_to_conversation("AI", ai_response[:100] + "...")
                
                # Analyze conversation flow for better dialogue management
                self.knowledge_system.analyze_conversation_flow(ai_response, self.current_game_state.map_id)
        
        # Detect expected actions from AI response
        expected_action = self._extract_expected_action(ai_response)
        if expected_action:
            self.knowledge_system.set_expected_action(expected_action)
    
    def _extract_conversation_topic(self, ai_response: str) -> str:
        """Extract the main topic of conversation from AI response."""
        response_lower = ai_response.lower()
        
        topic_patterns = {
            "setting clock": ["set the clock", "clock", "time"],
            "going upstairs": ["go to my room", "upstairs", "go upstairs"],
            "welcome home": ["welcome", "welcome home", "arrived"],
            "pokemon journey": ["pokemon journey", "adventure", "begin journey"],
            "starter pokemon": ["starter", "first pokemon", "choose pokemon"],
        }
        
        for topic, patterns in topic_patterns.items():
            if any(pattern in response_lower for pattern in patterns):
                return topic
        
        return "general conversation"
    
    def _extract_expected_action(self, ai_response: str) -> Optional[str]:
        """Extract what action the AI thinks it should do next."""
        response_lower = ai_response.lower()
        
        action_patterns = {
            "press A to advance dialogue": ["press 'a'", "press a", "advance the dialogue", "continue the conversation"],
            "go upstairs": ["go upstairs", "head upstairs", "go to my room"],
            "exit the house": ["exit the house", "leave the house", "step onto the mat"],
            "talk to mom": ["talk to", "interact with"],
        }
        
        for action, patterns in action_patterns.items():
            if any(pattern in response_lower for pattern in patterns):
                return action
        
        return None
    
    def _update_character_state_from_response(self, ai_response: str):
        """Update character state based on AI response text."""
        # Detect character name mentions
        detected_name = self.knowledge_system.detect_character_name_from_response(ai_response)
        if detected_name and detected_name != self.knowledge_system.character_state.name:
            self.knowledge_system.update_character_name(detected_name)
        
        # Detect tutorial progress
        tutorial_step = self.knowledge_system.detect_tutorial_completion(ai_response, "")
        if tutorial_step:
            self.knowledge_system.mark_tutorial_step_complete(tutorial_step)
        
        # Update current objective based on AI understanding
        objective = self._extract_current_objective(ai_response)
        if objective and objective != self.knowledge_system.character_state.current_objective:
            self.knowledge_system.set_current_objective(objective)
        
        # Update known NPCs when conversations are detected
        if self.knowledge_system.conversation_state.current_npc:
            npc_name = self.knowledge_system.conversation_state.current_npc
            npc_role = self.knowledge_system.conversation_state.npc_role
            if npc_name not in self.knowledge_system.character_state.known_npcs:
                self.knowledge_system.add_known_npc(npc_name, npc_role)
    
    def _extract_current_objective(self, ai_response: str) -> Optional[str]:
        """Extract current objective from AI response."""
        response_lower = ai_response.lower()
        
        objective_patterns = {
            "Follow mom's instructions to set the clock": ["set the clock", "go to my room", "upstairs"],
            "Exit the house to begin Pokemon journey": ["exit the house", "leave the house", "begin journey"],
            "Find Professor Oak to get starter Pokemon": ["professor oak", "starter pokemon", "choose pokemon"],
            "Explore Pallet Town": ["explore", "pallet town", "look around"],
        }
        
        for objective, patterns in objective_patterns.items():
            if any(pattern in response_lower for pattern in patterns):
                return objective
        
        return None
    
    def _add_response_to_context_memory(self, ai_response: str):
        """Add AI response to context memory for continuity."""
        # Extract key information from the response
        response_summary = self._summarize_ai_response(ai_response)
        
        # Determine priority based on content
        priority = self._calculate_response_priority(ai_response)
        
        # Add to context memory
        self.knowledge_system.add_context_memory(
            context_type="ai_decision",
            content=response_summary,
            priority=priority,
            location_id=self.current_game_state.map_id
        )
        
        # Record important moments
        if self._is_important_moment(ai_response):
            important_description = self._extract_important_moment(ai_response)
            self.knowledge_system.record_important_moment(important_description)
    
    def _summarize_ai_response(self, ai_response: str) -> str:
        """Create a concise summary of the AI response."""
        # Keep responses concise for memory efficiency
        if len(ai_response) <= 100:
            return ai_response
        
        # Extract the first sentence or main action
        sentences = ai_response.split('. ')
        if sentences:
            return sentences[0][:100] + "..."
        
        return ai_response[:100] + "..."
    
    def _calculate_response_priority(self, ai_response: str) -> int:
        """Calculate priority level for AI response (1-10 scale)."""
        response_lower = ai_response.lower()
        
        # High priority indicators
        high_priority_phrases = [
            "conversation", "talking to", "my mom", "mother",
            "objective", "goal", "quest", "important",
            "professor oak", "pokemon", "starter"
        ]
        
        # Medium priority indicators  
        medium_priority_phrases = [
            "press", "button", "move", "navigate",
            "dialogue", "text", "advance"
        ]
        
        # Count high priority matches
        high_matches = sum(1 for phrase in high_priority_phrases if phrase in response_lower)
        medium_matches = sum(1 for phrase in medium_priority_phrases if phrase in response_lower)
        
        if high_matches >= 2:
            return 8  # High priority
        elif high_matches >= 1:
            return 6  # Medium-high priority
        elif medium_matches >= 2:
            return 5  # Medium priority
        else:
            return 3  # Low priority
    
    def _is_important_moment(self, ai_response: str) -> bool:
        """Determine if this represents an important moment to remember."""
        response_lower = ai_response.lower()
        
        important_indicators = [
            "first time", "new area", "discovered", "found",
            "important", "quest", "mission", "objective",
            "pokemon center", "gym", "professor", "rival"
        ]
        
        return any(indicator in response_lower for indicator in important_indicators)
    
    def _extract_important_moment(self, ai_response: str) -> str:
        """Extract description of important moment."""
        response_lower = ai_response.lower()
        
        if "talking to" in response_lower and "mom" in response_lower:
            return "First conversation with Mom about setting clock"
        elif "pokemon" in response_lower and "journey" in response_lower:
            return "Beginning Pokemon journey"
        elif "professor" in response_lower:
            return "Encounter with Professor Oak"
        elif "gym" in response_lower:
            return "Gym-related event"
        else:
            # Generic important moment
            return f"Important event: {ai_response[:50]}..."
    
    def _record_location_change(self, old_location_id: int, new_location_id: int):
        """Record when the player changes locations."""
        old_name = self.game_engine.get_map_name(old_location_id)
        new_name = self.game_engine.get_map_name(new_location_id)
        
        self.knowledge_system.add_context_memory(
            context_type="location_change",
            content=f"Moved from {old_name} to {new_name}",
            priority=7,  # Location changes are important
            location_id=new_location_id
        )
        
        # Pin current location
        self.knowledge_system.pin_context("current_location", f"Currently in {new_name}")
    
    def _record_action_outcome(self, action_description: str, outcome: str):
        """Record the outcome of an action."""
        self.knowledge_system.add_context_memory(
            context_type="action_outcome",
            content=f"Action: {action_description} → Result: {outcome}",
            priority=6,
            location_id=self.current_game_state.map_id
        )