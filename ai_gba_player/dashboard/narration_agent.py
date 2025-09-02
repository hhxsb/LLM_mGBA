#!/usr/bin/env python3
"""
NarrationAgent - Handles narrative generation for AI gameplay entertainment.
Uses configured LLM provider for dynamic, entertaining commentary and narration.
"""

import time
import os
import queue
import threading
from typing import Dict, Any, Optional, List, Callable
from .models import Configuration
from .llm_client import LLMClient


class NarrationResponse:
    """Structured response from NarrationAgent narration generation"""
    
    def __init__(self, success: bool = True, narration: str = "", 
                 dialogue_reading: str = "", scene_description: str = "",
                 excitement_level: str = "neutral", error: str = ""):
        self.success = success
        self.narration = narration
        self.dialogue_reading = dialogue_reading  # TTS-friendly dialogue reading
        self.scene_description = scene_description
        self.excitement_level = excitement_level  # low, neutral, high, epic
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "success": self.success,
            "narration": self.narration,
            "dialogue_reading": self.dialogue_reading,
            "scene_description": self.scene_description,
            "excitement_level": self.excitement_level,
            "error": self.error
        }


class NarrationAgent:
    """Autonomous AI agent responsible for generating entertaining narration for streaming audiences"""
    
    def __init__(self):
        # LLM client for narration generation (supports multiple providers)
        self.llm_client = None
        
        # Session-based context memory
        self.session_context = {
            "recent_events": [],  # Last 5-10 significant events
            "character_state": {},  # Player status, location context
            "ongoing_narrative": "",  # Current story thread
            "dialogue_history": []  # Recent NPC interactions
        }
        
        # Narration configuration
        self.max_context_events = 10
        self.narration_styles = {
            "exploration": "curious and observant",
            "battle": "intense and exciting", 
            "dialogue": "character-focused and engaging",
            "discovery": "wonder and excitement",
            "stuck": "encouraging and strategic"
        }
        
        # Autonomous operation capabilities
        self.response_queue = queue.Queue(maxsize=20)  # Queue for receiving player responses
        self.processing_thread = None
        self.running = False
        
        # Communication interface
        self.chat_message_sender = None  # Callback for sending messages to frontend
        
        # Performance tracking
        self.narrations_generated = 0
        self.processing_errors = 0
        
        print("🎤 NarrationAgent initialized - ready for autonomous entertaining commentary")
    
    def initialize_llm(self, config: Dict[str, Any]):
        """Initialize LLM client with same config as PlayerAgent"""
        try:
            if not self.llm_client:
                self.llm_client = LLMClient(config)
                print(f"🤖 NarrationAgent: LLM client initialized with {config.get('llm_provider', 'google')} provider")
            return True
            
        except Exception as e:
            print(f"❌ NarrationAgent: Failed to initialize LLM client: {e}")
            return False
    
    def get_response_queue(self) -> queue.Queue:
        """Get the queue for receiving player responses"""
        return self.response_queue
    
    def set_chat_message_sender(self, message_sender: Callable[[str, str], None]):
        """Set callback for sending messages directly to frontend chat"""
        self.chat_message_sender = message_sender
        print("💬 NarrationAgent connected to chat messaging")
    
    def start_background_processing(self):
        """Start autonomous background narration processing"""
        if self.running:
            print("⚠️ NarrationAgent already running in background mode")
            return
        
        self.running = True
        self.processing_thread = threading.Thread(
            target=self._background_processing_loop,
            daemon=True,
            name="NarrationAgent-Background"
        )
        self.processing_thread.start()
        print("🚀 NarrationAgent started in background processing mode")
    
    def stop_background_processing(self):
        """Stop autonomous background processing"""
        if not self.running:
            return
        
        self.running = False
        
        # Add poison pill to wake up processing thread
        try:
            self.response_queue.put_nowait(None)
        except queue.Full:
            pass
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        print("🛑 NarrationAgent background processing stopped")
    
    def _background_processing_loop(self):
        """Main background processing loop - runs in separate thread"""
        print("🎤 NarrationAgent background processing started")
        
        try:
            while self.running:
                try:
                    # Wait for player response with timeout
                    queue_item = self.response_queue.get(timeout=1.0)
                    
                    # Check for poison pill (shutdown signal)
                    if queue_item is None:
                        break
                    
                    # Handle both old format (tuple) and new format (dict) for backward compatibility
                    if isinstance(queue_item, dict) and "player_response" in queue_item:
                        # New enhanced format with session context
                        player_response_dict = queue_item["player_response"]
                        game_context = queue_item["game_state"]
                        session_context = queue_item.get("session_context", {})
                        
                        # Integrate session context into narration context
                        self._integrate_player_session_context(session_context)
                    else:
                        # Old format for backward compatibility
                        player_response_dict, game_context = queue_item
                        session_context = {}
                    
                    print(f"🎤 NarrationAgent: Processing narration request #{self.narrations_generated + 1}")
                    
                    # Generate narration with enhanced context
                    narration_response = self.generate_narration(player_response_dict, game_context)
                    
                    # Send narration to frontend
                    if narration_response.success:
                        self._send_narration_message(narration_response)
                        self.narrations_generated += 1
                        print(f"✅ NarrationAgent: Sent narration #{self.narrations_generated}")
                    else:
                        self.processing_errors += 1
                        error_msg = f"⚠️ NarrationAgent: Failed to generate narration - {narration_response.error}"
                        print(error_msg)
                        self._send_chat_message("system", error_msg)
                    
                    # Mark task as done
                    self.response_queue.task_done()
                    
                except queue.Empty:
                    continue  # Timeout, check if still running
                
                except Exception as e:
                    self.processing_errors += 1
                    error_msg = f"❌ NarrationAgent processing error: {str(e)}"
                    print(error_msg)
                    self._send_chat_message("system", error_msg)
                    
                    # Mark task as done even if it failed
                    try:
                        self.response_queue.task_done()
                    except ValueError:
                        pass  # No task to mark as done
        
        except Exception as e:
            print(f"❌ NarrationAgent background loop error: {e}")
        
        finally:
            print("🎤 NarrationAgent background processing ended")
    
    def _send_chat_message(self, message_type: str, content: str):
        """Send message to frontend chat"""
        if self.chat_message_sender:
            try:
                self.chat_message_sender(message_type, content)
            except Exception as e:
                print(f"❌ NarrationAgent: Error sending chat message: {e}")
        else:
            print(f"⚠️ NarrationAgent chat message (no sender): [{message_type}] {content}")
    
    def _send_narration_message(self, narration_response: NarrationResponse):
        """Send narration message to frontend"""
        if not narration_response.narration:
            return
        
        # Create formatted narration message
        excitement_emoji = {
            "low": "😴",
            "neutral": "🎮",
            "high": "⚡",
            "epic": "🔥"
        }.get(narration_response.excitement_level, "🎮")
        
        message = f"{excitement_emoji} Narration: {narration_response.narration}"
        
        if narration_response.dialogue_reading:
            message += f" | 🗣️ Dialogue: {narration_response.dialogue_reading}"
        
        self._send_chat_message("narration", message)
    
    def _integrate_player_session_context(self, player_session_context: Dict[str, Any]):
        """Integrate PlayerAgent's session context into narration context for richer storytelling"""
        if not player_session_context:
            return
        
        # Add recent NPC encounters from PlayerAgent to our dialogue history
        player_npcs = player_session_context.get("encountered_npcs", [])
        for npc_record in player_npcs:
            # Avoid duplicates by checking if we already have this dialogue
            if not any(existing.get("dialogue") == npc_record.get("dialogue") 
                      for existing in self.session_context["dialogue_history"]):
                self.session_context["dialogue_history"].append({
                    "timestamp": npc_record.get("timestamp", time.time()),
                    "dialogue": npc_record.get("dialogue", "")
                })
        
        # Keep only recent dialogues
        if len(self.session_context["dialogue_history"]) > 5:
            self.session_context["dialogue_history"] = self.session_context["dialogue_history"][-5:]
        
        # Enhance ongoing narrative with performance context
        performance_stats = player_session_context.get("performance_stats", {})
        decision_count = performance_stats.get("decision_count", 0)
        consecutive_errors = performance_stats.get("consecutive_errors", 0)
        success_rate = performance_stats.get("success_rate", 1.0)
        
        # Update narrative tone based on performance
        if consecutive_errors > 2:
            self.session_context["ongoing_narrative"] = "struggle and determination"
        elif success_rate > 0.8:
            self.session_context["ongoing_narrative"] = "confident exploration"
        else:
            self.session_context["ongoing_narrative"] = "careful navigation"
        
        # Add decision pattern context for more dynamic narration
        recent_decisions = player_session_context.get("recent_decisions", [])
        if recent_decisions:
            last_decision = recent_decisions[-1]
            if last_decision.get("dialogue"):
                self.session_context["character_state"]["last_interaction"] = "conversation"
            elif any(action in last_decision.get("actions", []) for action in ["UP", "DOWN", "LEFT", "RIGHT"]):
                self.session_context["character_state"]["last_interaction"] = "movement"
            else:
                self.session_context["character_state"]["last_interaction"] = "action"
    
    def generate_narration(self, player_response: Dict[str, Any], 
                          game_context: Dict[str, Any]) -> NarrationResponse:
        """Generate entertaining narration based on player actions and game state"""
        
        if not self.llm_client:
            config = self._load_config()
            if not config or not self.initialize_llm(config):
                return NarrationResponse(
                    success=False,
                    error="LLM client not initialized",
                    narration="Unable to generate narration - AI not available"
                )
        
        try:
            # Update session context with new information
            self._update_session_context(player_response, game_context)
            
            # Determine narration style based on game context
            style = self._determine_narration_style(game_context, player_response)
            
            # Build narration prompt
            prompt = self._build_narration_prompt(player_response, game_context, style)
            
            # Call LLM for narration
            print(f"🎤 Generating narration with {self.llm_client.provider} provider...")
            
            response = self._call_llm_for_narration(prompt)
            
            if not response or not response.get('success'):
                return NarrationResponse(
                    success=False,
                    error=response.get('error', 'Unknown error') if response else 'No response',
                    narration="The adventure continues in silence..."
                )
            
            # Parse the structured narration response
            return self._parse_narration_response(response.get('text', ''), style)
            
        except Exception as e:
            print(f"❌ NarrationAgent error: {e}")
            return NarrationResponse(
                success=False,
                error=str(e),
                narration=f"An unexpected turn in the adventure... {self._get_fallback_narration(game_context)}"
            )
    
    def _update_session_context(self, player_response: Dict[str, Any], game_context: Dict[str, Any]):
        """Update session-based context memory with new information"""
        
        # Extract key information
        current_situation = player_response.get("current_situation", "")
        detected_dialogue = player_response.get("detected_dialogue", "")
        actions_taken = player_response.get("actions", [])
        game_analysis = player_response.get("game_analysis", "")
        
        # Update character state
        position = game_context.get("position", {})
        self.session_context["character_state"] = {
            "location": f"({position.get('x', 0)}, {position.get('y', 0)})",
            "direction": game_context.get("direction", "UNKNOWN"),
            "map_id": game_context.get("map_id", 0),
            "situation": current_situation
        }
        
        # Add significant events
        if actions_taken or detected_dialogue or "stuck" in current_situation.lower():
            event = {
                "timestamp": time.time(),
                "actions": actions_taken,
                "dialogue": detected_dialogue,
                "situation": current_situation,
                "analysis": game_analysis[:100] + "..." if len(game_analysis) > 100 else game_analysis
            }
            
            self.session_context["recent_events"].append(event)
            
            # Keep only recent events
            if len(self.session_context["recent_events"]) > self.max_context_events:
                self.session_context["recent_events"] = self.session_context["recent_events"][-self.max_context_events:]
        
        # Track dialogue history
        if detected_dialogue:
            self.session_context["dialogue_history"].append({
                "timestamp": time.time(),
                "dialogue": detected_dialogue
            })
            
            # Keep only recent dialogues
            if len(self.session_context["dialogue_history"]) > 5:
                self.session_context["dialogue_history"] = self.session_context["dialogue_history"][-5:]
    
    def _determine_narration_style(self, game_context: Dict[str, Any], 
                                  player_response: Dict[str, Any]) -> str:
        """Determine the appropriate narration style based on context"""
        
        current_situation = player_response.get("current_situation", "").lower()
        detected_dialogue = player_response.get("detected_dialogue", "")
        actions = player_response.get("actions", [])
        
        # Priority-based style determination
        if detected_dialogue:
            return "dialogue"
        elif "battle" in current_situation or "fight" in current_situation:
            return "battle"
        elif "stuck" in current_situation or len(set(actions)) == 1 and len(actions) > 3:
            return "stuck"
        elif "found" in current_situation or "discovered" in current_situation:
            return "discovery"
        else:
            return "exploration"
    
    def _call_llm_for_narration(self, prompt: str) -> Dict[str, Any]:
        """Call the LLM with narration-specific prompt"""
        try:
            # Use LLMClient's text-only generation method
            response = self._call_text_llm(prompt)
            return {
                'success': True,
                'text': response,
                'error': None
            }
        except Exception as e:
            print(f"❌ NarrationAgent LLM call failed: {e}")
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }
    
    def _call_text_llm(self, prompt: str) -> str:
        """Call LLM provider with text-only prompt"""
        if self.llm_client.provider == 'google':
            import google.generativeai as genai
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,  # Creative but not too random
                    max_output_tokens=300,  # Keep narration concise
                    top_p=0.9
                )
            )
            return response.text if response and response.text else ""
        
        elif self.llm_client.provider == 'openai':
            response = self.llm_client.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use mini for cost-effective narration
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=300
            )
            return response.choices[0].message.content if response.choices else ""
        
        else:
            # Fallback for unsupported providers
            raise Exception(f"Narration not supported for provider: {self.llm_client.provider}")
    
    def _build_narration_prompt(self, player_response: Dict[str, Any], 
                               game_context: Dict[str, Any], style: str) -> str:
        """Build the narration generation prompt for LLM"""
        
        # Get recent context
        recent_events = self.session_context["recent_events"][-3:]  # Last 3 events
        character_state = self.session_context["character_state"]
        
        # Build context summary
        context_summary = f"Player at {character_state.get('location', 'unknown location')}, facing {character_state.get('direction', 'unknown direction')}."
        
        if recent_events:
            context_summary += " Recent events: " + "; ".join([
                f"took {len(event.get('actions', []))} actions ({', '.join(event.get('actions', [])[:2])}{'...' if len(event.get('actions', [])) > 2 else ''})"
                for event in recent_events[-2:]
            ])
        
        style_description = self.narration_styles.get(style, "engaging and entertaining")
        
        prompt = f"""You are a Pokemon adventure narrator creating entertaining commentary for streaming audiences.

CONTEXT:
{context_summary}

CURRENT ACTION:
- Player took actions: {player_response.get('actions', [])}
- Current situation: {player_response.get('current_situation', 'exploring')}
- AI reasoning: {player_response.get('action_reasoning', 'continuing adventure')}

DETECTED DIALOGUE (if any):
{player_response.get('detected_dialogue', 'None')}

NARRATION STYLE: {style_description}

Generate a brief, entertaining narration (2-3 sentences max) that:
1. Describes what's happening in an engaging way
2. If there's dialogue, read it in a character voice  
3. Maintains excitement and entertainment value
4. Uses Pokemon terminology when appropriate

RESPONSE FORMAT:
Narration: [Your entertaining commentary here]
Dialogue: [Character voice reading of any dialogue, or "None"]
Scene: [Brief scene description for context]
Energy: [low/neutral/high/epic based on action intensity]

Keep it fun, engaging, and suitable for streaming audiences!"""
        
        return prompt
    
    def _parse_narration_response(self, response_text: str, style: str) -> NarrationResponse:
        """Parse Gemini's response into structured narration data"""
        
        try:
            lines = response_text.strip().split('\n')
            
            narration = ""
            dialogue = ""
            scene = ""
            energy = "neutral"
            
            # Parse structured response
            for line in lines:
                line = line.strip()
                if line.startswith("Narration:"):
                    narration = line[10:].strip()
                elif line.startswith("Dialogue:"):
                    dialogue = line[9:].strip()
                    if dialogue.lower() in ["none", "n/a", ""]:
                        dialogue = ""
                elif line.startswith("Scene:"):
                    scene = line[6:].strip()
                elif line.startswith("Energy:"):
                    energy = line[7:].strip().lower()
                elif not any(line.startswith(prefix) for prefix in ["Narration:", "Dialogue:", "Scene:", "Energy:"]):
                    # Unstructured response - use as narration
                    if not narration and line:
                        narration = line
            
            # Fallback if parsing failed
            if not narration:
                narration = response_text.strip()
            
            # Validate energy level
            if energy not in ["low", "neutral", "high", "epic"]:
                energy = "neutral"
            
            return NarrationResponse(
                success=True,
                narration=narration,
                dialogue_reading=dialogue,
                scene_description=scene,
                excitement_level=energy
            )
            
        except Exception as e:
            print(f"⚠️ NarrationAgent: Failed to parse response, using raw text: {e}")
            return NarrationResponse(
                success=True,
                narration=response_text.strip() if response_text else "The adventure continues...",
                excitement_level="neutral"
            )
    
    def _get_fallback_narration(self, game_context: Dict[str, Any]) -> str:
        """Generate fallback narration when AI fails"""
        
        fallback_lines = [
            "Our hero presses onward through the Pokemon world...",
            "The adventure takes an unexpected turn...",
            "What will happen next in this Pokemon journey?",
            "The trainer continues their quest with determination...",
            "Another step forward in this grand adventure..."
        ]
        
        import random
        return random.choice(fallback_lines)
    
    def reset_session(self):
        """Reset session-based context when game session ends"""
        self.session_context = {
            "recent_events": [],
            "character_state": {},
            "ongoing_narrative": "",
            "dialogue_history": []
        }
        print("🔄 NarrationAgent session reset")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from database"""
        try:
            from .models import Configuration
            config_obj = Configuration.get_config()
            return config_obj.to_dict() if config_obj else None
        except Exception as e:
            print(f"⚠️ NarrationAgent: Error loading configuration: {e}")
            return None