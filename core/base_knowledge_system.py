#!/usr/bin/env python3
"""
Abstract base class for game-specific knowledge systems.
Each game implementation should inherit from BaseKnowledgeSystem.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import deque
import json
import os
import time
from .base_game_engine import GameState

@dataclass
class ConversationState:
    """Tracks current conversation state for memory continuity."""
    current_npc: Optional[str] = None
    npc_role: Optional[str] = None  # "mom", "professor", "rival", etc.
    conversation_topic: Optional[str] = None
    conversation_history: List[str] = field(default_factory=list)
    expected_next_action: Optional[str] = None
    conversation_phase: str = "none"  # "greeting", "main_topic", "instruction", "conclusion"
    started_at: Optional[float] = None
    location_id: Optional[int] = None

@dataclass
class CharacterState:
    """Tracks persistent character identity and game phase."""
    name: str = "GEMINI"
    current_objective: Optional[str] = None
    game_phase: str = "tutorial"  # "tutorial", "early_game", "mid_game", "late_game"
    known_npcs: Dict[str, str] = field(default_factory=dict)  # name -> role mapping
    tutorial_progress: List[str] = field(default_factory=list)  # completed tutorial steps
    character_backstory: str = "You are playing as a young Pokemon trainer starting their journey"

@dataclass
class DialogueRecord:
    """Records detailed NPC dialogue interactions for learning and memory."""
    npc_name: str
    npc_role: str  # "mom", "professor", "rival", "gym_leader", etc.
    dialogue_text: str
    player_response: str
    outcome: str  # What happened as a result
    timestamp: float
    location_id: int
    important_info: List[str] = field(default_factory=list)  # extracted key facts
    conversation_id: Optional[str] = None  # Links related dialogues

@dataclass
class ContextMemoryEntry:
    """Single entry in the context memory buffer."""
    timestamp: float
    context_type: str  # "conversation", "action", "location_change", "important"
    content: str
    priority: int = 5  # 1-10 scale, 10 = highest priority (always included)
    location_id: Optional[int] = None

@dataclass
class Goal:
    """Represents a game goal or objective."""
    id: str
    description: str
    type: str  # "main", "side", "detected", etc.
    status: str  # "active", "completed", "failed"
    priority: int = 5  # 1-10 scale
    location_id: Optional[int] = None
    prerequisites: List[str] = None
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []

@dataclass
class ActionRecord:
    """Record of an action taken and its result."""
    action: str
    result: str
    location: int
    timestamp: float
    success: bool = True

@dataclass
class LocationInfo:
    """Information about a specific game location."""
    id: int
    name: str
    map_type: str = "unknown"
    connections: List[int] = None
    npcs: List[str] = None
    items: List[str] = None
    notes: str = ""
    
    def __post_init__(self):
        if self.connections is None:
            self.connections = []
        if self.npcs is None:
            self.npcs = []
        if self.items is None:
            self.items = []

class BaseKnowledgeSystem(ABC):
    """Abstract base class for game-specific knowledge systems."""
    
    def __init__(self, knowledge_file: str, game_name: str):
        self.knowledge_file = knowledge_file
        self.game_name = game_name
        self.goals: Dict[str, Goal] = {}
        self.locations: Dict[int, LocationInfo] = {}
        self.action_history: List[ActionRecord] = []
        self.game_specific_data: Dict[str, Any] = {}
        
        # Add conversation state tracking
        self.conversation_state = ConversationState()
        
        # Add character identity and game phase tracking
        self.character_state = CharacterState()
        
        # Add dialogue recording system
        self.dialogue_history: List[DialogueRecord] = []
        self.npc_interactions: Dict[str, List[DialogueRecord]] = {}  # npc_name -> dialogue list
        
        # Add context memory buffer
        self.context_memory = deque(maxlen=20)  # Keep last 20 context entries
        self.pinned_context = {}  # Always-included context by key
        
        self.load_knowledge()
    
    def load_knowledge(self):
        """Load knowledge from file if it exists."""
        if os.path.exists(self.knowledge_file):
            try:
                with open(self.knowledge_file, 'r') as f:
                    data = json.load(f)
                
                # Load goals
                for goal_data in data.get('goals', []):
                    goal = Goal(**goal_data)
                    self.goals[goal.id] = goal
                
                # Load locations
                for loc_data in data.get('locations', []):
                    location = LocationInfo(**loc_data)
                    self.locations[location.id] = location
                
                # Load action history (keep recent only)
                history_data = data.get('action_history', [])
                for action_data in history_data[-50:]:  # Keep last 50 actions
                    self.action_history.append(ActionRecord(**action_data))
                
                # Load game-specific data
                self.game_specific_data = data.get('game_specific_data', {})
                
            except Exception as e:
                print(f"Error loading knowledge: {e}")
    
    def save_knowledge(self):
        """Save knowledge to file."""
        try:
            os.makedirs(os.path.dirname(self.knowledge_file), exist_ok=True)
            
            data = {
                'game_name': self.game_name,
                'goals': [goal.__dict__ for goal in self.goals.values()],
                'locations': [loc.__dict__ for loc in self.locations.values()],
                'action_history': [action.__dict__ for action in self.action_history[-50:]],
                'dialogue_history': [dialogue.__dict__ for dialogue in self.dialogue_history[-20:]],  # Save recent dialogues
                'conversation_state': self.conversation_state.__dict__,
                'character_state': self.character_state.__dict__,
                'game_specific_data': self.game_specific_data
            }
            
            with open(self.knowledge_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving knowledge: {e}")
    
    def update_location(self, game_state: GameState, map_name: str):
        """Update location information."""
        loc_id = game_state.map_id
        if loc_id not in self.locations:
            self.locations[loc_id] = LocationInfo(id=loc_id, name=map_name)
        else:
            self.locations[loc_id].name = map_name
    
    def record_action(self, action: str, result: str, location: int, success: bool = True):
        """Record an action taken by the AI."""
        import time
        record = ActionRecord(
            action=action,
            result=result,
            location=location,
            timestamp=time.time(),
            success=success
        )
        self.action_history.append(record)
        
        # Keep only recent actions
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-50:]
    
    def add_goal(self, goal: Goal):
        """Add a new goal."""
        self.goals[goal.id] = goal
        self.save_knowledge()
    
    def complete_goal(self, goal_id: str):
        """Mark a goal as completed."""
        if goal_id in self.goals:
            self.goals[goal_id].status = "completed"
            self.save_knowledge()
    
    def get_active_goals(self) -> List[Goal]:
        """Get all active goals."""
        return [goal for goal in self.goals.values() if goal.status == "active"]
    
    def get_location_context(self, location_id: int) -> str:
        """Get context information about a location."""
        if location_id in self.locations:
            loc = self.locations[location_id]
            context = f"Location: {loc.name}"
            if loc.notes:
                context += f"\nNotes: {loc.notes}"
            if loc.npcs:
                context += f"\nNPCs: {', '.join(loc.npcs)}"
            if loc.items:
                context += f"\nItems: {', '.join(loc.items)}"
            return context
        return ""
    
    @abstractmethod
    def generate_context_summary(self) -> str:
        """Generate a context summary for the current game state."""
        pass
    
    @abstractmethod
    def get_navigation_advice(self, current_location: int) -> str:
        """Get navigation advice for the current location."""
        pass
    
    @abstractmethod
    def analyze_game_progress(self) -> Dict[str, Any]:
        """Analyze current game progress and return insights."""
        pass
    
    @abstractmethod
    def suggest_next_actions(self, game_state: GameState) -> List[str]:
        """Suggest next actions based on current game state."""
        pass
    
    # Conversation State Management Methods
    def start_conversation(self, npc_name: str, npc_role: str, topic: str, location_id: int):
        """Start a new conversation with an NPC."""
        self.conversation_state = ConversationState(
            current_npc=npc_name,
            npc_role=npc_role,
            conversation_topic=topic,
            conversation_history=[],
            conversation_phase="greeting",
            started_at=time.time(),
            location_id=location_id
        )
        print(f"🗣️ Started conversation with {npc_name} ({npc_role}) about {topic}")
    
    def add_dialogue_to_conversation(self, speaker: str, dialogue: str):
        """Add dialogue to current conversation history."""
        if self.conversation_state.current_npc:
            dialogue_entry = f"{speaker}: {dialogue}"
            self.conversation_state.conversation_history.append(dialogue_entry)
            
            # Keep only last 5 exchanges to prevent overwhelming context
            if len(self.conversation_state.conversation_history) > 5:
                self.conversation_state.conversation_history = self.conversation_state.conversation_history[-5:]
    
    def set_expected_action(self, action: str):
        """Set what action the NPC expects the player to do next."""
        if self.conversation_state.current_npc:
            self.conversation_state.expected_next_action = action
            print(f"💭 {self.conversation_state.current_npc} expects: {action}")
    
    def update_conversation_phase(self, phase: str):
        """Update the current conversation phase."""
        if self.conversation_state.current_npc:
            self.conversation_state.conversation_phase = phase
    
    def end_conversation(self):
        """End the current conversation."""
        if self.conversation_state.current_npc:
            print(f"👋 Ended conversation with {self.conversation_state.current_npc}")
            self.conversation_state = ConversationState()
    
    def get_conversation_context(self) -> str:
        """Get formatted conversation context for prompts."""
        if not self.conversation_state.current_npc:
            return ""
        
        context_parts = []
        context_parts.append(f"🗣️ **Currently talking to:** {self.conversation_state.current_npc}")
        
        if self.conversation_state.npc_role:
            context_parts.append(f"👤 **Role:** {self.conversation_state.npc_role}")
        
        if self.conversation_state.conversation_topic:
            context_parts.append(f"📝 **Topic:** {self.conversation_state.conversation_topic}")
        
        if self.conversation_state.conversation_phase != "none":
            context_parts.append(f"📊 **Phase:** {self.conversation_state.conversation_phase}")
        
        if self.conversation_state.expected_next_action:
            context_parts.append(f"⏭️ **Expected action:** {self.conversation_state.expected_next_action}")
        
        if self.conversation_state.conversation_history:
            context_parts.append("💭 **Recent dialogue:**")
            for dialogue in self.conversation_state.conversation_history[-3:]:  # Last 3 exchanges
                context_parts.append(f"   {dialogue}")
        
        return "\n".join(context_parts)
    
    def detect_conversation_from_dialogue(self, dialogue_text: str, location_id: int) -> Optional[str]:
        """Attempt to detect conversation details from dialogue text."""
        dialogue_lower = dialogue_text.lower()
        
        # Simple NPC detection patterns
        npc_patterns = {
            "mom": ["mom", "mother", "welcome home", "set the clock"],
            "professor_oak": ["professor", "oak", "pokemon", "starter"],
            "rival": ["rival", "smell ya later", "battle"],
            "nurse_joy": ["nurse", "joy", "heal", "pokemon center"],
        }
        
        for npc_role, patterns in npc_patterns.items():
            if any(pattern in dialogue_lower for pattern in patterns):
                return npc_role
        
        return None
    
    # Character State Management Methods
    def update_character_name(self, name: str):
        """Update the character's name."""
        self.character_state.name = name.upper()  # Pokemon names are typically uppercase
        print(f"🎭 Character name set to: {self.character_state.name}")
    
    def set_current_objective(self, objective: str):
        """Set the character's current objective."""
        self.character_state.current_objective = objective
        print(f"🎯 Current objective: {objective}")
    
    def update_game_phase(self, phase: str):
        """Update the current game phase."""
        valid_phases = ["tutorial", "early_game", "mid_game", "late_game"]
        if phase in valid_phases:
            self.character_state.game_phase = phase
            print(f"🎮 Game phase: {phase}")
    
    def add_known_npc(self, npc_name: str, npc_role: str):
        """Add an NPC to the known characters list."""
        self.character_state.known_npcs[npc_name] = npc_role
        print(f"👤 Learned about NPC: {npc_name} ({npc_role})")
    
    def mark_tutorial_step_complete(self, step: str):
        """Mark a tutorial step as completed."""
        if step not in self.character_state.tutorial_progress:
            self.character_state.tutorial_progress.append(step)
            print(f"✅ Tutorial step completed: {step}")
    
    def get_character_context(self) -> str:
        """Get formatted character identity context for prompts."""
        context_parts = []
        
        # Character identity
        context_parts.append(f"🎭 **Your Character:** {self.character_state.name}")
        context_parts.append(f"📖 **Background:** {self.character_state.character_backstory}")
        
        # Current game state
        context_parts.append(f"🎮 **Game Phase:** {self.character_state.game_phase}")
        
        if self.character_state.current_objective:
            context_parts.append(f"🎯 **Current Objective:** {self.character_state.current_objective}")
        
        # Tutorial progress (if in tutorial)
        if self.character_state.game_phase == "tutorial" and self.character_state.tutorial_progress:
            context_parts.append(f"📚 **Tutorial Progress:** {', '.join(self.character_state.tutorial_progress)}")
        
        # Known NPCs
        if self.character_state.known_npcs:
            npc_list = [f"{name} ({role})" for name, role in self.character_state.known_npcs.items()]
            context_parts.append(f"👥 **Known Characters:** {', '.join(npc_list)}")
        
        return "\n".join(context_parts)
    
    def get_game_phase_guidance(self) -> str:
        """Get guidance specific to current game phase."""
        phase_guidance = {
            "tutorial": "🎓 **Tutorial Mode**: Focus on learning basic controls, following NPC instructions, and understanding game mechanics. Take time to read dialogue carefully and follow directions step by step.",
            "early_game": "🌱 **Early Game**: Build your Pokemon team, explore the world, and work toward your first gym battles. Focus on catching Pokemon and learning type matchups.",
            "mid_game": "⚔️ **Mid Game**: Challenge gyms strategically, evolve your Pokemon, and explore more complex areas. Balance training with story progression.",
            "late_game": "🏆 **Late Game**: Prepare for the Elite Four, complete your Pokedex, and tackle the most challenging content in the game."
        }
        
        return phase_guidance.get(self.character_state.game_phase, "🎮 Continue your Pokemon journey!")
    
    def detect_character_name_from_response(self, ai_response: str) -> Optional[str]:
        """Detect character name mentions in AI responses."""
        response_upper = ai_response.upper()
        
        # Look for common character name patterns
        name_patterns = ["GEMINI", "RED", "ASH", "PLAYER"]
        
        for pattern in name_patterns:
            if pattern in response_upper:
                return pattern
        
        return None
    
    def detect_tutorial_completion(self, ai_response: str, action_taken: str) -> Optional[str]:
        """Detect tutorial step completion from AI response and actions."""
        response_lower = ai_response.lower()
        
        tutorial_steps = {
            "entered_name": ["name", "gemini", "character"],
            "talked_to_mom": ["mom", "mother", "talking to"],
            "learned_controls": ["press", "button", "advance dialogue"],
            "received_instructions": ["clock", "upstairs", "room"],
            "attempted_movement": ["down", "exit", "leave house"],
        }
        
        for step, keywords in tutorial_steps.items():
            if step not in self.character_state.tutorial_progress:
                if any(keyword in response_lower for keyword in keywords):
                    return step
        
        return None
    
    # Context Memory Buffer Methods
    def add_context_memory(self, context_type: str, content: str, priority: int = 5, location_id: Optional[int] = None):
        """Add a new context entry to the memory buffer."""
        entry = ContextMemoryEntry(
            timestamp=time.time(),
            context_type=context_type,
            content=content,
            priority=priority,
            location_id=location_id
        )
        self.context_memory.append(entry)
        
        # Log high priority entries
        if priority >= 8:
            print(f"📝 High priority context: {content[:50]}...")
    
    def pin_context(self, key: str, content: str):
        """Pin important context that should always be included."""
        self.pinned_context[key] = content
        print(f"📌 Pinned context: {key}")
    
    def unpin_context(self, key: str):
        """Remove pinned context."""
        if key in self.pinned_context:
            del self.pinned_context[key]
            print(f"📌 Unpinned context: {key}")
    
    # Enhanced Dialogue Recording & Memory Methods
    def record_dialogue(self, npc_name: str, npc_role: str, dialogue_text: str, 
                       player_response: str, outcome: str, location_id: int,
                       important_info: List[str] = None) -> str:
        """Record a complete dialogue interaction for learning and memory."""
        if important_info is None:
            important_info = []
        
        # Generate conversation ID for linking related dialogues
        conversation_id = f"{npc_name}_{int(time.time())}"
        
        dialogue_record = DialogueRecord(
            npc_name=npc_name,
            npc_role=npc_role,
            dialogue_text=dialogue_text,
            player_response=player_response,
            outcome=outcome,
            timestamp=time.time(),
            location_id=location_id,
            important_info=important_info,
            conversation_id=conversation_id
        )
        
        # Add to main dialogue history
        self.dialogue_history.append(dialogue_record)
        
        # Add to NPC-specific interactions
        if npc_name not in self.npc_interactions:
            self.npc_interactions[npc_name] = []
        self.npc_interactions[npc_name].append(dialogue_record)
        
        # Extract important information automatically
        extracted_info = self._extract_important_info(dialogue_text, npc_role)
        dialogue_record.important_info.extend(extracted_info)
        
        # Add to context memory for immediate use
        self.add_context_memory(
            "dialogue_record",
            f"Conversation with {npc_name}: {dialogue_text[:100]}...",
            priority=7,
            location_id=location_id
        )
        
        # Keep dialogue history manageable
        if len(self.dialogue_history) > 50:
            self.dialogue_history = self.dialogue_history[-30:]
        
        print(f"📝 Recorded dialogue with {npc_name} ({npc_role})")
        return conversation_id
    
    def get_npc_interaction_history(self, npc_name: str) -> List[DialogueRecord]:
        """Get all previous interactions with a specific NPC."""
        return self.npc_interactions.get(npc_name, [])
    
    def get_recent_dialogues(self, limit: int = 5) -> List[DialogueRecord]:
        """Get the most recent dialogue interactions."""
        return self.dialogue_history[-limit:] if self.dialogue_history else []
    
    def find_relevant_past_conversations(self, current_npc: str, current_topic: str) -> List[DialogueRecord]:
        """Find past conversations relevant to current situation."""
        relevant = []
        
        # Get past interactions with same NPC
        npc_history = self.get_npc_interaction_history(current_npc)
        relevant.extend(npc_history[-3:])  # Last 3 interactions with this NPC
        
        # Search for topic-related conversations
        topic_lower = current_topic.lower() if current_topic else ""
        if topic_lower:
            for dialogue in self.dialogue_history[-10:]:  # Search recent dialogues
                if (topic_lower in dialogue.dialogue_text.lower() or 
                    topic_lower in dialogue.player_response.lower() or
                    any(topic_lower in info.lower() for info in dialogue.important_info)):
                    if dialogue not in relevant:
                        relevant.append(dialogue)
        
        return relevant
    
    def _extract_important_info(self, dialogue_text: str, npc_role: str) -> List[str]:
        """Extract important information from dialogue based on content and NPC role."""
        important_info = []
        dialogue_lower = dialogue_text.lower()
        
        # Role-specific information extraction
        extraction_patterns = {
            "mom": [
                ("clock", "Instructions about setting the clock"),
                ("upstairs", "Directions to go upstairs"),
                ("room", "Information about player's room"),
                ("welcome", "Welcome home message")
            ],
            "professor": [
                ("pokemon", "Pokemon-related information"),
                ("research", "Research or study information"),
                ("starter", "Information about starter Pokemon"),
                ("pokedex", "Pokedex-related instructions")
            ],
            "rival": [
                ("battle", "Battle challenge or taunt"),
                ("weak", "Rivalry or competitive dialogue"),
                ("champion", "Goal or ambition statements")
            ],
            "gym_leader": [
                ("badge", "Information about gym badges"),
                ("challenge", "Gym challenge information"),
                ("strong", "Strength or training advice")
            ]
        }
        
        patterns = extraction_patterns.get(npc_role, [])
        for keyword, info_type in patterns:
            if keyword in dialogue_lower:
                important_info.append(f"{info_type}: {dialogue_text[:80]}...")
        
        # General important keywords
        general_patterns = [
            ("must", "Important instruction"),
            ("need to", "Required action"),
            ("don't forget", "Important reminder"),
            ("remember", "Important information to remember")
        ]
        
        for keyword, info_type in general_patterns:
            if keyword in dialogue_lower:
                important_info.append(f"{info_type}: {dialogue_text[:80]}...")
        
        return important_info
    
    def get_dialogue_memory_context(self) -> str:
        """Generate dialogue memory context for prompts."""
        if not self.dialogue_history:
            return ""
        
        context_parts = []
        context_parts.append("📚 **Previous Conversations:**")
        
        # Show recent important dialogues
        recent_dialogues = self.get_recent_dialogues(3)
        for dialogue in recent_dialogues:
            time_str = time.strftime("%H:%M", time.localtime(dialogue.timestamp))
            context_parts.append(f"   [{time_str}] {dialogue.npc_name} ({dialogue.npc_role}): {dialogue.dialogue_text[:60]}...")
            if dialogue.important_info:
                for info in dialogue.important_info[:2]:  # Show top 2 important items
                    context_parts.append(f"      💡 {info}")
        
        # Show current NPC history if relevant
        if self.conversation_state.current_npc:
            npc_history = self.get_npc_interaction_history(self.conversation_state.current_npc)
            if len(npc_history) > 1:  # More than just current conversation
                context_parts.append(f"   📖 **Previous talks with {self.conversation_state.current_npc}:** {len(npc_history)} conversations")
        
        return "\n".join(context_parts)
    
    # Conversation Flow Management Methods
    def detect_conversation_start(self, dialogue_text: str) -> bool:
        """Detect when a new conversation begins."""
        dialogue_lower = dialogue_text.lower()
        
        conversation_start_patterns = [
            "welcome", "hello", "hi there", "good morning", "good afternoon",
            "oh!", "hey", "excuse me", "wait", "stop right there",
            "who are you", "what are you doing", "can i help you"
        ]
        
        return any(pattern in dialogue_lower for pattern in conversation_start_patterns)
    
    def detect_conversation_end(self, dialogue_text: str) -> bool:
        """Detect when a conversation concludes."""
        dialogue_lower = dialogue_text.lower()
        
        conversation_end_patterns = [
            "goodbye", "see you later", "talk to you later", "take care",
            "good luck", "bye", "see ya", "until next time",
            "that's all", "nothing else", "i'm done", "go ahead"
        ]
        
        return any(pattern in dialogue_lower for pattern in conversation_end_patterns)
    
    def extract_expected_action(self, dialogue_text: str) -> Optional[str]:
        """Extract what the NPC expects the player to do."""
        dialogue_lower = dialogue_text.lower()
        
        # Pattern matching for common expected actions
        action_patterns = {
            "go upstairs": ["go upstairs", "head upstairs", "upstairs"],
            "go to room": ["go to your room", "to your room", "in your room"],
            "set clock": ["set the clock", "setting the clock", "adjust the clock"],
            "talk to professor": ["see professor", "talk to professor", "visit professor"],
            "go outside": ["go outside", "head outside", "leave the house"],
            "choose pokemon": ["choose a pokemon", "pick a pokemon", "select your pokemon"],
            "battle": ["battle", "fight", "let's battle"],
            "heal pokemon": ["heal your pokemon", "to the pokemon center", "get healed"],
            "save game": ["save your game", "don't forget to save", "remember to save"]
        }
        
        for action, patterns in action_patterns.items():
            if any(pattern in dialogue_lower for pattern in patterns):
                return action
        
        # Look for general instruction patterns
        instruction_keywords = ["you should", "you need to", "you must", "go", "come", "find", "get", "take"]
        for keyword in instruction_keywords:
            if keyword in dialogue_lower:
                # Extract the sentence containing the instruction
                sentences = dialogue_text.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower():
                        return f"Follow instruction: {sentence.strip()}"
        
        return None
    
    def update_conversation_phase(self, dialogue_text: str, current_phase: str) -> str:
        """Determine current conversation phase based on dialogue content."""
        dialogue_lower = dialogue_text.lower()
        
        # Phase detection logic
        if current_phase == "none" and self.detect_conversation_start(dialogue_text):
            return "greeting"
        
        if current_phase == "greeting":
            # Look for transition to main topic
            topic_indicators = ["now", "so", "listen", "i need", "you should", "let me tell you"]
            if any(indicator in dialogue_lower for indicator in topic_indicators):
                return "main_topic"
        
        if current_phase in ["greeting", "main_topic"]:
            # Look for instruction phase
            instruction_indicators = ["go", "do", "you need to", "you must", "make sure", "don't forget"]
            if any(indicator in dialogue_lower for indicator in instruction_indicators):
                return "instruction"
        
        if self.detect_conversation_end(dialogue_text):
            return "conclusion"
        
        # Default: stay in current phase
        return current_phase
    
    def analyze_conversation_flow(self, dialogue_text: str, location_id: int):
        """Analyze and update conversation flow based on new dialogue."""
        # Update conversation phase
        new_phase = self.update_conversation_phase(dialogue_text, self.conversation_state.conversation_phase)
        
        if new_phase != self.conversation_state.conversation_phase:
            print(f"🔄 Conversation phase changed: {self.conversation_state.conversation_phase} → {new_phase}")
            self.conversation_state.conversation_phase = new_phase
        
        # Extract expected action if in instruction phase
        if new_phase == "instruction":
            expected_action = self.extract_expected_action(dialogue_text)
            if expected_action:
                self.conversation_state.expected_next_action = expected_action
                print(f"⏭️ Expected action identified: {expected_action}")
        
        # Handle conversation conclusion
        if new_phase == "conclusion":
            self.end_conversation_with_summary()
    
    def determine_response_type(self, dialogue_text: str, conversation_phase: str) -> str:
        """Determine what type of response is appropriate."""
        dialogue_lower = dialogue_text.lower()
        
        # Response type based on dialogue content and phase
        if conversation_phase == "greeting":
            if "?" in dialogue_text:
                return "answer_question"
            else:
                return "acknowledge_greeting"
        
        elif conversation_phase == "main_topic":
            if "?" in dialogue_text:
                return "answer_question"
            elif any(word in dialogue_lower for word in ["tell me", "explain", "what", "how"]):
                return "provide_information"
            else:
                return "acknowledge_information"
        
        elif conversation_phase == "instruction":
            return "acknowledge_instruction"
        
        elif conversation_phase == "conclusion":
            return "say_goodbye"
        
        # Default response types
        if "?" in dialogue_text:
            return "answer_question"
        elif any(word in dialogue_lower for word in ["go", "do", "you should", "you need"]):
            return "acknowledge_instruction"
        else:
            return "continue_conversation"
    
    def manage_multi_turn_conversation(self, dialogue_text: str, turn_number: int):
        """Handle conversations that span multiple exchanges."""
        # Add dialogue to conversation history
        self.conversation_state.conversation_history.append(f"Turn {turn_number}: {dialogue_text}")
        
        # Keep conversation history manageable
        if len(self.conversation_state.conversation_history) > 8:
            self.conversation_state.conversation_history = self.conversation_state.conversation_history[-5:]
        
        # Detect conversation patterns
        if turn_number > 1:
            # Look for conversation continuation cues
            continuation_patterns = ["also", "and", "furthermore", "by the way", "oh", "wait"]
            dialogue_lower = dialogue_text.lower()
            
            if any(pattern in dialogue_lower for pattern in continuation_patterns):
                print(f"🔗 Multi-turn conversation detected (Turn {turn_number})")
                
                # Extend conversation if it was about to end
                if self.conversation_state.conversation_phase == "conclusion":
                    self.conversation_state.conversation_phase = "main_topic"
                    print("🔄 Conversation extended due to additional content")
    
    def get_conversation_flow_context(self) -> str:
        """Generate conversation flow context for prompts."""
        if not self.conversation_state.current_npc:
            return ""
        
        context_parts = []
        context_parts.append("🎭 **Conversation Flow Analysis:**")
        
        # Current phase guidance
        phase_guidance = {
            "greeting": "Initial greeting phase - be polite and acknowledge the NPC",
            "main_topic": "Main conversation - engage with the topic being discussed", 
            "instruction": "Instruction phase - carefully follow the directions given",
            "conclusion": "Conversation ending - acknowledge and prepare to leave"
        }
        
        current_phase = self.conversation_state.conversation_phase
        if current_phase in phase_guidance:
            context_parts.append(f"   📊 **Phase:** {current_phase} - {phase_guidance[current_phase]}")
        
        # Response type guidance
        if self.conversation_state.current_npc and current_phase != "none":
            response_type = self.determine_response_type("", current_phase)
            context_parts.append(f"   💬 **Suggested response type:** {response_type.replace('_', ' ').title()}")
        
        # Expected action reminder
        if self.conversation_state.expected_next_action:
            context_parts.append(f"   ⏭️ **Next action:** {self.conversation_state.expected_next_action}")
        
        # Conversation turn tracking
        if self.conversation_state.conversation_history:
            turn_count = len(self.conversation_state.conversation_history)
            context_parts.append(f"   🔢 **Conversation turns:** {turn_count}")
            
            if turn_count > 3:
                context_parts.append("   ⚠️ **Long conversation** - consider wrapping up if appropriate")
        
        return "\n".join(context_parts)
    
    def end_conversation_with_summary(self):
        """End the current conversation and create a summary."""
        if not self.conversation_state.current_npc:
            return
        
        # Create conversation summary
        summary_parts = []
        summary_parts.append(f"Completed conversation with {self.conversation_state.current_npc}")
        
        if self.conversation_state.conversation_topic:
            summary_parts.append(f"Topic: {self.conversation_state.conversation_topic}")
        
        if self.conversation_state.expected_next_action:
            summary_parts.append(f"Next action: {self.conversation_state.expected_next_action}")
        
        summary = " | ".join(summary_parts)
        
        # Record as important context
        self.add_context_memory(
            "conversation_summary",
            summary,
            priority=8,
            location_id=self.conversation_state.location_id
        )
        
        print(f"📋 Conversation summary: {summary}")
        
        # Reset conversation state but preserve expected action for prompt context
        last_action = self.conversation_state.expected_next_action
        self.conversation_state = ConversationState()
        
        # Keep the expected action available for immediate context
        if last_action:
            self.add_context_memory(
                "pending_action",
                f"Pending action from last conversation: {last_action}",
                priority=9
            )
    
    # Smart Context Prioritization Methods
    def calculate_context_relevance_score(self, context_entry: ContextMemoryEntry, current_situation: Dict[str, Any]) -> float:
        """Calculate relevance score for a context entry based on current situation."""
        score = float(context_entry.priority)  # Base score from priority (1-10)
        
        # Time decay factor - more recent contexts are more relevant
        current_time = time.time()
        age_hours = (current_time - context_entry.timestamp) / 3600
        
        if age_hours < 0.1:  # Less than 6 minutes
            score += 3.0
        elif age_hours < 0.5:  # Less than 30 minutes
            score += 2.0
        elif age_hours < 2.0:  # Less than 2 hours
            score += 1.0
        elif age_hours > 24:  # Older than 24 hours
            score -= 2.0
        
        # Context type relevance
        if context_entry.context_type == "conversation" and current_situation.get("in_conversation", False):
            score += 4.0
        elif context_entry.context_type == "important":
            score += 3.0
        elif context_entry.context_type == "ai_decision":
            score += 2.0
        elif context_entry.context_type == "location_change":
            score += 1.0
        
        # Location relevance
        current_location = current_situation.get("location_id")
        if current_location and context_entry.location_id == current_location:
            score += 2.0
        
        # Content keyword matching
        current_npc = current_situation.get("current_npc", "").lower()
        current_topic = current_situation.get("current_topic", "").lower()
        content_lower = context_entry.content.lower()
        
        if current_npc and current_npc in content_lower:
            score += 3.0
        if current_topic and current_topic in content_lower:
            score += 2.0
        
        # Conversation-specific scoring
        conversation_keywords = ["dialogue", "conversation", "talking", "speaking", "says", "told", "asked"]
        if any(keyword in content_lower for keyword in conversation_keywords):
            if current_situation.get("in_conversation", False):
                score += 2.0
        
        # Action-related scoring  
        action_keywords = ["go", "move", "press", "button", "action", "do", "need to", "should"]
        if any(keyword in content_lower for keyword in action_keywords):
            score += 1.5
        
        return max(0.0, score)  # Ensure non-negative score
    
    def prioritize_context_entries(self, current_situation: Dict[str, Any], max_entries: int = 10) -> List[ContextMemoryEntry]:
        """Select and prioritize most relevant context entries for current situation."""
        if not self.context_memory:
            return []
        
        # Calculate relevance scores for all entries
        scored_entries = []
        for entry in self.context_memory:
            score = self.calculate_context_relevance_score(entry, current_situation)
            scored_entries.append((entry, score))
        
        # Sort by score (highest first)
        scored_entries.sort(key=lambda x: x[1], reverse=True)
        
        # Return top entries
        return [entry for entry, score in scored_entries[:max_entries]]
    
    def get_current_situation_context(self) -> Dict[str, Any]:
        """Build current situation context for prioritization."""
        situation = {
            "location_id": getattr(self, 'current_location_id', None),
            "in_conversation": bool(self.conversation_state.current_npc),
            "current_npc": self.conversation_state.current_npc or "",
            "current_topic": self.conversation_state.conversation_topic or "",
            "conversation_phase": self.conversation_state.conversation_phase,
            "game_phase": self.character_state.game_phase,
            "current_objective": self.character_state.current_objective or ""
        }
        return situation
    
    def select_context_by_type_priority(self, context_types: List[str], max_per_type: int = 3) -> List[ContextMemoryEntry]:
        """Select context entries by type with priority ordering."""
        selected = []
        current_situation = self.get_current_situation_context()
        
        for context_type in context_types:
            # Get entries of this type
            type_entries = [entry for entry in self.context_memory if entry.context_type == context_type]
            
            if type_entries:
                # Score and sort entries of this type
                scored = [(entry, self.calculate_context_relevance_score(entry, current_situation)) 
                         for entry in type_entries]
                scored.sort(key=lambda x: x[1], reverse=True)
                
                # Take top entries for this type
                selected.extend([entry for entry, score in scored[:max_per_type]])
        
        return selected
    
    def apply_context_length_management(self, context_parts: List[str], max_total_chars: int = 2000) -> List[str]:
        """Manage context length by prioritizing most important information."""
        if not context_parts:
            return []
        
        # Calculate current total length
        total_length = sum(len(part) for part in context_parts)
        
        if total_length <= max_total_chars:
            return context_parts
        
        # Prioritize context parts
        priority_order = [
            "🚨", "🔥", "⚠️",  # Critical/urgent markers
            "🗣️", "💬",        # Conversation markers  
            "🎯", "⏭️",        # Objective/action markers
            "🧠", "📚",        # Memory/knowledge markers
            "📍", "🗺️"         # Location markers
        ]
        
        prioritized_parts = []
        remaining_parts = context_parts.copy()
        
        # First pass: add high-priority context
        for priority_marker in priority_order:
            matching_parts = [part for part in remaining_parts if priority_marker in part]
            for part in matching_parts:
                if sum(len(p) for p in prioritized_parts) + len(part) <= max_total_chars:
                    prioritized_parts.append(part)
                    remaining_parts.remove(part)
        
        # Second pass: add remaining context if space allows
        for part in remaining_parts:
            if sum(len(p) for p in prioritized_parts) + len(part) <= max_total_chars:
                prioritized_parts.append(part)
        
        return prioritized_parts
    
    def get_context_relevance_summary(self) -> str:
        """Generate a summary of context relevance for debugging."""
        current_situation = self.get_current_situation_context()
        
        summary_parts = []
        summary_parts.append("🎯 **Context Relevance Analysis:**")
        summary_parts.append(f"   📍 Current location: {current_situation['location_id']}")
        summary_parts.append(f"   💬 In conversation: {current_situation['in_conversation']}")
        
        if current_situation['current_npc']:
            summary_parts.append(f"   🗣️ Talking to: {current_situation['current_npc']}")
            summary_parts.append(f"   📝 Topic: {current_situation['current_topic']}")
        
        summary_parts.append(f"   🎮 Game phase: {current_situation['game_phase']}")
        
        if current_situation['current_objective']:
            summary_parts.append(f"   🎯 Objective: {current_situation['current_objective']}")
        
        # Show context entry counts by type
        if self.context_memory:
            type_counts = {}
            for entry in self.context_memory:
                type_counts[entry.context_type] = type_counts.get(entry.context_type, 0) + 1
            
            summary_parts.append("   📊 Context by type:")
            for context_type, count in type_counts.items():
                summary_parts.append(f"      {context_type}: {count}")
        
        return "\n".join(summary_parts)
    
    def get_relevant_context_memory(self, max_entries: int = 10, use_smart_prioritization: bool = True) -> str:
        """Get most relevant context from memory buffer with smart prioritization."""
        if not self.context_memory and not self.pinned_context:
            return ""
        
        context_parts = []
        
        # Always include pinned context first
        if self.pinned_context:
            context_parts.append("🔒 **Essential Context:**")
            for key, content in self.pinned_context.items():
                context_parts.append(f"   {key}: {content}")
        
        if not self.context_memory:
            return "\n".join(context_parts)
        
        if use_smart_prioritization:
            # Use smart context prioritization
            current_situation = self.get_current_situation_context()
            selected_entries = self.prioritize_context_entries(current_situation, max_entries)
            
            if selected_entries:
                context_parts.append("🧠 **Smart-Prioritized Context:**")
                for entry in selected_entries:
                    # Calculate and show relevance score for debugging
                    score = self.calculate_context_relevance_score(entry, current_situation)
                    
                    # Format timestamp
                    import datetime
                    time_str = datetime.datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S")
                    
                    # Show score for high-priority entries
                    if score >= 8.0:
                        context_parts.append(f"   🔥 [{time_str}] {entry.context_type}: {entry.content}")
                    elif score >= 6.0:
                        context_parts.append(f"   ⚡ [{time_str}] {entry.context_type}: {entry.content}")
                    else:
                        context_parts.append(f"   📝 [{time_str}] {entry.context_type}: {entry.content}")
        else:
            # Legacy prioritization (for comparison)
            recent_entries = list(self.context_memory)
            recent_entries.sort(key=lambda x: (x.priority, x.timestamp), reverse=True)
            selected_entries = recent_entries[:max_entries]
            
            if selected_entries:
                context_parts.append("📋 **Recent Context:**")
                for entry in selected_entries:
                    import datetime
                    time_str = datetime.datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S")
                    context_parts.append(f"   [{time_str}] {entry.context_type}: {entry.content}")
        
        # Apply context length management if needed
        if len("\n".join(context_parts)) > 2500:  # If context is too long
            context_parts = self.apply_context_length_management(context_parts, max_total_chars=2000)
        
        return "\n".join(context_parts)
    
    # Tutorial Progress Tracking Methods
    def initialize_tutorial_system(self):
        """Initialize the tutorial tracking system with Pokemon Red specific steps."""
        self.tutorial_steps = {
            "game_start": {
                "id": "game_start",
                "description": "Game introduction and Oak's speech",
                "required_actions": ["listen to introduction", "enter name"],
                "completion_indicators": ["character name entered", "game world entered"],
                "next_step": "enter_house",
                "guidance": "Listen carefully to Professor Oak's introduction and enter your character name when prompted."
            },
            "enter_house": {
                "id": "enter_house", 
                "description": "Enter your house and meet your mom",
                "required_actions": ["move down into house", "approach mom"],
                "completion_indicators": ["inside house", "near mom npc"],
                "next_step": "talk_to_mom",
                "guidance": "Use the DOWN arrow key to move into your house. Look for your mom NPC."
            },
            "talk_to_mom": {
                "id": "talk_to_mom",
                "description": "Have first conversation with mom about the clock",
                "required_actions": ["press A to talk", "read dialogue"],
                "completion_indicators": ["dialogue started", "clock mentioned"],
                "next_step": "go_upstairs",
                "guidance": "Press A when near your mom to start the conversation. She will tell you about setting the clock."
            },
            "go_upstairs": {
                "id": "go_upstairs",
                "description": "Navigate upstairs to your room",
                "required_actions": ["move to stairs", "go up"],
                "completion_indicators": ["upstairs reached", "in bedroom area"],
                "next_step": "set_clock",
                "guidance": "Find the stairs and use the UP arrow key to go to the second floor where your room is located."
            },
            "set_clock": {
                "id": "set_clock",
                "description": "Interact with the clock to set the time",
                "required_actions": ["find clock", "press A to interact", "set time"],
                "completion_indicators": ["clock interaction", "time set"],
                "next_step": "go_downstairs", 
                "guidance": "Look for the clock in your room and press A to interact with it. Set the time as instructed."
            },
            "go_downstairs": {
                "id": "go_downstairs",
                "description": "Return downstairs after setting clock",
                "required_actions": ["go down stairs", "return to mom"],
                "completion_indicators": ["back downstairs", "near mom"],
                "next_step": "exit_house",
                "guidance": "Go back downstairs to the main floor where your mom is located."
            },
            "exit_house": {
                "id": "exit_house",
                "description": "Leave your house to begin the adventure",
                "required_actions": ["move to door", "exit house"],
                "completion_indicators": ["outside house", "in pallet town"],
                "next_step": "explore_town",
                "guidance": "Move to the house entrance and exit to Pallet Town. Your Pokemon journey begins!"
            },
            "explore_town": {
                "id": "explore_town",
                "description": "Explore Pallet Town and find Professor Oak",
                "required_actions": ["move around town", "find oak"],
                "completion_indicators": ["pallet town explored", "oak encountered"],
                "next_step": "meet_oak",
                "guidance": "Explore Pallet Town and look for Professor Oak. He may be in tall grass or his lab."
            },
            "meet_oak": {
                "id": "meet_oak",
                "description": "Meet Professor Oak and learn about Pokemon",
                "required_actions": ["talk to oak", "listen to explanation"],
                "completion_indicators": ["oak dialogue", "pokemon explained"],
                "next_step": "choose_starter",
                "guidance": "Talk to Professor Oak and listen to his explanation about Pokemon and your journey."
            },
            "choose_starter": {
                "id": "choose_starter",
                "description": "Choose your first Pokemon from the three options",
                "required_actions": ["examine pokeballs", "choose pokemon", "confirm choice"],
                "completion_indicators": ["starter chosen", "pokemon obtained"],
                "next_step": "first_battle",
                "guidance": "Choose between Bulbasaur, Charmander, or Squirtle. Each has different strengths!"
            },
            "first_battle": {
                "id": "first_battle",
                "description": "Battle your rival with your new Pokemon",
                "required_actions": ["battle rival", "use moves", "win or lose"],
                "completion_indicators": ["battle completed", "tutorial finished"],
                "next_step": "tutorial_complete",
                "guidance": "Use your Pokemon's moves to battle your rival. This teaches you battle mechanics."
            },
            "tutorial_complete": {
                "id": "tutorial_complete",
                "description": "Tutorial phase completed, ready for main adventure",
                "required_actions": [],
                "completion_indicators": ["tutorial finished"],
                "next_step": None,
                "guidance": "Congratulations! You've completed the tutorial and can now begin your Pokemon adventure."
            }
        }
        
        # Initialize tutorial progress tracking
        if not hasattr(self.character_state, 'current_tutorial_step'):
            self.character_state.current_tutorial_step = "game_start"
            self.character_state.completed_tutorial_steps = []
            self.character_state.tutorial_completion_percentage = 0.0
    
    def detect_tutorial_step_completion(self, ai_response: str, action_taken: str, game_state) -> Optional[str]:
        """Detect if a tutorial step was just completed based on AI response and game state."""
        current_step_id = getattr(self.character_state, 'current_tutorial_step', 'game_start')
        
        if current_step_id not in self.tutorial_steps:
            return None
        
        current_step = self.tutorial_steps[current_step_id]
        response_lower = ai_response.lower()
        action_lower = action_taken.lower() if action_taken else ""
        
        # Check completion indicators for current step
        completion_indicators = current_step["completion_indicators"]
        
        step_completions = {
            "game_start": self._check_game_start_completion(response_lower, action_lower, game_state),
            "enter_house": self._check_enter_house_completion(response_lower, action_lower, game_state),
            "talk_to_mom": self._check_talk_to_mom_completion(response_lower, action_lower, game_state),
            "go_upstairs": self._check_go_upstairs_completion(response_lower, action_lower, game_state),
            "set_clock": self._check_set_clock_completion(response_lower, action_lower, game_state),
            "go_downstairs": self._check_go_downstairs_completion(response_lower, action_lower, game_state),
            "exit_house": self._check_exit_house_completion(response_lower, action_lower, game_state),
            "explore_town": self._check_explore_town_completion(response_lower, action_lower, game_state),
            "meet_oak": self._check_meet_oak_completion(response_lower, action_lower, game_state),
            "choose_starter": self._check_choose_starter_completion(response_lower, action_lower, game_state),
            "first_battle": self._check_first_battle_completion(response_lower, action_lower, game_state)
        }
        
        completion_check = step_completions.get(current_step_id)
        if completion_check and completion_check():
            return current_step_id
        
        return None
    
    def _check_game_start_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("gemini" in response_lower or "character" in response_lower or 
                       "name" in response_lower) and game_state and hasattr(game_state, 'map_id')
    
    def _check_enter_house_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("inside" in response_lower or "house" in response_lower or "mom" in response_lower) and \
                      game_state and getattr(game_state, 'map_id', 0) == 24  # Assuming house map ID is 24
    
    def _check_talk_to_mom_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("talking" in response_lower and "mom" in response_lower) or \
                      ("clock" in response_lower) or ("dialogue" in response_lower and "mom" in response_lower)
    
    def _check_go_upstairs_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("upstairs" in response_lower or "second floor" in response_lower or "bedroom" in response_lower)
    
    def _check_set_clock_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("set the clock" in response_lower or "clock set" in response_lower or 
                       "time set" in response_lower or "interacted with clock" in response_lower)
    
    def _check_go_downstairs_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("downstairs" in response_lower or "back to mom" in response_lower or "first floor" in response_lower)
    
    def _check_exit_house_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("outside" in response_lower or "pallet town" in response_lower or "left the house" in response_lower)
    
    def _check_explore_town_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("professor oak" in response_lower or "oak" in response_lower or "tall grass" in response_lower)
    
    def _check_meet_oak_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("talking to oak" in response_lower or "professor oak" in response_lower and "dialogue" in response_lower)
    
    def _check_choose_starter_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("bulbasaur" in response_lower or "charmander" in response_lower or "squirtle" in response_lower or 
                       "chose" in response_lower and "pokemon" in response_lower)
    
    def _check_first_battle_completion(self, response_lower: str, action_lower: str, game_state) -> callable:
        return lambda: ("battle" in response_lower and ("won" in response_lower or "lost" in response_lower or "ended" in response_lower))
    
    def complete_tutorial_step(self, step_id: str):
        """Mark a tutorial step as completed and advance to next step."""
        if step_id not in self.tutorial_steps:
            return
        
        # Add to completed steps if not already there
        if not hasattr(self.character_state, 'completed_tutorial_steps'):
            self.character_state.completed_tutorial_steps = []
        
        if step_id not in self.character_state.completed_tutorial_steps:
            self.character_state.completed_tutorial_steps.append(step_id)
            
            # Update completion percentage
            total_steps = len(self.tutorial_steps)
            completed_steps = len(self.character_state.completed_tutorial_steps)
            self.character_state.tutorial_completion_percentage = (completed_steps / total_steps) * 100
            
            print(f"✅ Tutorial step completed: {step_id} ({self.character_state.tutorial_completion_percentage:.1f}% done)")
        
        # Advance to next step
        current_step = self.tutorial_steps[step_id]
        next_step = current_step.get("next_step")
        
        if next_step:
            self.character_state.current_tutorial_step = next_step
            print(f"➡️ Advanced to tutorial step: {next_step}")
            
            # Add context memory about the progression
            self.add_context_memory(
                "tutorial_progress",
                f"Completed {step_id}, now on {next_step}",
                priority=8
            )
        else:
            # Tutorial completed
            self.character_state.current_tutorial_step = "tutorial_complete"
            self.character_state.game_phase = "early_game"
            print("🎉 Tutorial phase completed! Moving to early game phase.")
            
            self.record_important_moment("Tutorial phase completed successfully")
    
    def get_current_tutorial_guidance(self) -> str:
        """Get guidance for the current tutorial step."""
        if not hasattr(self.character_state, 'current_tutorial_step'):
            self.initialize_tutorial_system()
        
        current_step_id = self.character_state.current_tutorial_step
        
        if current_step_id not in self.tutorial_steps:
            return ""
        
        current_step = self.tutorial_steps[current_step_id]
        
        guidance_parts = []
        guidance_parts.append("📚 **Current Tutorial Step:**")
        guidance_parts.append(f"   🎯 **Step:** {current_step['description']}")
        guidance_parts.append(f"   💡 **Guidance:** {current_step['guidance']}")
        
        # Show required actions
        if current_step["required_actions"]:
            guidance_parts.append("   📋 **Required actions:**")
            for action in current_step["required_actions"]:
                guidance_parts.append(f"      • {action}")
        
        # Show completion indicators
        if current_step["completion_indicators"]:
            guidance_parts.append("   ✅ **Look for these indicators:**")
            for indicator in current_step["completion_indicators"]:
                guidance_parts.append(f"      • {indicator}")
        
        # Show progress
        if hasattr(self.character_state, 'tutorial_completion_percentage'):
            guidance_parts.append(f"   📊 **Tutorial progress:** {self.character_state.tutorial_completion_percentage:.1f}%")
        
        return "\n".join(guidance_parts)
    
    def get_tutorial_progress_summary(self) -> str:
        """Get a summary of tutorial progress."""
        if not hasattr(self.character_state, 'completed_tutorial_steps'):
            self.initialize_tutorial_system()
        
        summary_parts = []
        summary_parts.append("📈 **Tutorial Progress Summary:**")
        
        completed = getattr(self.character_state, 'completed_tutorial_steps', [])
        current = getattr(self.character_state, 'current_tutorial_step', 'game_start')
        completion_pct = getattr(self.character_state, 'tutorial_completion_percentage', 0.0)
        
        summary_parts.append(f"   📊 **Overall progress:** {completion_pct:.1f}% complete")
        summary_parts.append(f"   🎯 **Current step:** {current}")
        summary_parts.append(f"   ✅ **Completed steps:** {len(completed)}/{len(self.tutorial_steps)}")
        
        if completed:
            summary_parts.append("   📝 **Recently completed:**")
            for step_id in completed[-3:]:  # Show last 3 completed steps
                step_desc = self.tutorial_steps.get(step_id, {}).get('description', step_id)
                summary_parts.append(f"      • {step_desc}")
        
        return "\n".join(summary_parts)
    
    def process_tutorial_step_detection(self, ai_response: str, action_taken: str, game_state):
        """Process potential tutorial step completion and update progress."""
        if self.character_state.game_phase != "tutorial":
            return
        
        if not hasattr(self.character_state, 'current_tutorial_step'):
            self.initialize_tutorial_system()
        
        # Detect step completion
        completed_step = self.detect_tutorial_step_completion(ai_response, action_taken, game_state)
        
        if completed_step:
            self.complete_tutorial_step(completed_step)
    
    def get_next_tutorial_steps_preview(self, num_steps: int = 3) -> str:
        """Get a preview of upcoming tutorial steps."""
        if not hasattr(self.character_state, 'current_tutorial_step'):
            self.initialize_tutorial_system()
        
        current_step_id = self.character_state.current_tutorial_step
        
        if current_step_id not in self.tutorial_steps:
            return ""
        
        preview_parts = []
        preview_parts.append("🔮 **Upcoming Tutorial Steps:**")
        
        # Trace through next steps
        next_step_id = self.tutorial_steps[current_step_id].get("next_step")
        step_count = 0
        
        while next_step_id and step_count < num_steps:
            if next_step_id in self.tutorial_steps:
                step = self.tutorial_steps[next_step_id]
                preview_parts.append(f"   {step_count + 1}. {step['description']}")
                next_step_id = step.get("next_step")
                step_count += 1
            else:
                break
        
        return "\n".join(preview_parts)
    
    def get_context_summary_by_type(self, context_type: str, max_entries: int = 5) -> str:
        """Get context entries of a specific type."""
        entries = [entry for entry in self.context_memory if entry.context_type == context_type]
        entries.sort(key=lambda x: x.timestamp, reverse=True)  # Most recent first
        
        if not entries:
            return ""
        
        summary_parts = [f"📋 **Recent {context_type.title()} Context:**"]
        for entry in entries[:max_entries]:
            summary_parts.append(f"   {entry.content}")
        
        return "\n".join(summary_parts)
    
    def compress_old_context(self):
        """Compress older context entries to save space."""
        # This could be enhanced to summarize old context instead of just removing it
        current_time = time.time()
        
        # Mark entries older than 10 minutes for potential compression
        old_threshold = current_time - (10 * 60)  # 10 minutes
        
        old_entries = [entry for entry in self.context_memory if entry.timestamp < old_threshold]
        
        if len(old_entries) > 5:
            # Could implement summarization here
            print(f"📦 {len(old_entries)} old context entries available for compression")
    
    def record_important_moment(self, description: str, priority: int = 9):
        """Record an important moment that should be remembered."""
        self.add_context_memory(
            context_type="important",
            content=f"Important: {description}",
            priority=priority,
            location_id=getattr(self, 'current_location_id', None)
        )
        print(f"⭐ Recorded important moment: {description}")
    
    def get_context_stats(self) -> Dict[str, Any]:
        """Get statistics about the context memory buffer."""
        if not self.context_memory:
            return {"total_entries": 0, "types": {}}
        
        type_counts = {}
        priority_counts = {}
        
        for entry in self.context_memory:
            type_counts[entry.context_type] = type_counts.get(entry.context_type, 0) + 1
            priority_counts[entry.priority] = priority_counts.get(entry.priority, 0) + 1
        
        return {
            "total_entries": len(self.context_memory),
            "pinned_entries": len(self.pinned_context),
            "types": type_counts,
            "priorities": priority_counts,
            "oldest_entry": min(entry.timestamp for entry in self.context_memory),
            "newest_entry": max(entry.timestamp for entry in self.context_memory),
        }