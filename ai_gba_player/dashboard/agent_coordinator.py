#!/usr/bin/env python3
"""
AgentCoordinator - Simplified coordinator for autonomous agent lifecycle management.
Manages PlayerAgent and NarrationAgent with direct inter-agent communication.
"""

from typing import Dict, Any, Optional, Callable
from .player_agent import PlayerAgent
from .narration_agent import NarrationAgent


class AgentCoordinator:
    """Simplified coordinator for autonomous agent lifecycle management and inter-agent communication"""
    
    def __init__(self):
        # Create autonomous agents
        self.player_agent = PlayerAgent()
        self.narration_agent = NarrationAgent()
        
        # Agent status
        self.agents_initialized = False
        self.agents_connected = False
        
        # Store configurations for restarts
        self._last_config = None
        self._memory_system = None
        
        print("🎯 AgentCoordinator initialized - autonomous agent management")
    
    def initialize_agents(self, config: Dict[str, Any]):
        """Initialize LLM clients for all agents"""
        self._last_config = config  # Store for restarts
        
        # Initialize both agents
        self.player_agent.initialize_llm(config)
        self.narration_agent.initialize_llm(config)
        
        self.agents_initialized = True
        print("🤖 All agents initialized with LLM clients")
    
    def start_agents(self):
        """Start autonomous agent processing"""
        if not self.agents_initialized:
            print("❌ AgentCoordinator: Cannot start agents - not initialized")
            return
        
        # Start narration agent background processing
        self.narration_agent.start_background_processing()
        
        print("🚀 All autonomous agents started")
    
    def connect_agent_communication(self):
        """Connect PlayerAgent output to NarrationAgent input queue"""
        if not self.agents_initialized:
            print("❌ AgentCoordinator: Cannot connect agents - not initialized")
            return
        
        # Connect PlayerAgent's narration queue to NarrationAgent's response queue
        narration_queue = self.narration_agent.get_response_queue()
        self.player_agent.set_narration_queue(narration_queue)
        
        self.agents_connected = True
        print("🔗 Agent communication connected: PlayerAgent → NarrationAgent")
    
    def set_communication_interfaces(self, chat_message_sender: Callable[[str, str], None], 
                                   screenshot_requester: Callable[[], str], 
                                   button_sender: Callable[[list, Optional[list]], bool]):
        """Set communication interfaces for agents to interact with external systems"""
        if not self.agents_initialized:
            print("❌ AgentCoordinator: Cannot set interfaces - not initialized")
            return
        
        # Connect PlayerAgent to external systems
        self.player_agent.set_chat_message_sender(chat_message_sender)
        self.player_agent.set_screenshot_requester(screenshot_requester)
        self.player_agent.set_button_sender(button_sender)
        
        # Connect NarrationAgent to chat
        self.narration_agent.set_chat_message_sender(chat_message_sender)
        
        print("🔌 All agent communication interfaces connected")
    
    def set_memory_system(self, memory_system):
        """Set memory system for player agent"""
        self._memory_system = memory_system  # Store for restarts
        self.player_agent.set_memory_system(memory_system)
        print("🧠 Memory system connected to PlayerAgent")
    
    def start_autonomous_gameplay(self, initial_screenshot: str, initial_game_state: Dict[str, Any]) -> bool:
        """Start autonomous gameplay with PlayerAgent driving the game cycle"""
        if not all([self.agents_initialized, self.agents_connected]):
            print("❌ AgentCoordinator: Cannot start gameplay - agents not ready")
            return False
        
        # Start autonomous PlayerAgent
        self.player_agent.start_autonomous_play(initial_screenshot, initial_game_state)
        print("🎮 Autonomous gameplay started - PlayerAgent in control")
        return True
    
    def stop_autonomous_gameplay(self):
        """Stop autonomous gameplay"""
        self.player_agent.stop_autonomous_play()
        self.narration_agent.stop_background_processing()
        print("🛑 Autonomous gameplay stopped")
    
    def reset_sessions(self):
        """Reset all agent sessions"""
        self.player_agent.reset_session()
        self.narration_agent.reset_session()
        print("🔄 All agent sessions reset")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            "agents_initialized": self.agents_initialized,
            "agents_connected": self.agents_connected,
            "player_agent": {
                "autonomous_mode": getattr(self.player_agent, 'autonomous_mode', False),
                "decision_count": getattr(self.player_agent, 'decision_count', 0),
                "consecutive_errors": getattr(self.player_agent, 'consecutive_errors', 0)
            },
            "narration_agent": {
                "processing": getattr(self.narration_agent, 'running', False),
                "narrations_generated": getattr(self.narration_agent, 'narrations_generated', 0),
                "processing_errors": getattr(self.narration_agent, 'processing_errors', 0)
            }
        }
    
    def shutdown(self):
        """Graceful shutdown of all agents"""
        print("🎯 Shutting down AgentCoordinator...")
        
        # Stop autonomous gameplay
        self.stop_autonomous_gameplay()
        
        # Reset state
        self.agents_initialized = False
        self.agents_connected = False
        
        print("✅ AgentCoordinator shutdown complete")