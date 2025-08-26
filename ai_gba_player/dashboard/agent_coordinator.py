#!/usr/bin/env python3
"""
AgentCoordinator - Manages threaded PlayerAgent and NarrationAgent for optimal performance.
Coordinates async communication between agents to minimize game cycle times.
"""

import threading
import queue
import time
import traceback
from typing import Dict, Any, Optional, Tuple
from .player_agent import PlayerAgent, PlayerResponse
from .narration_agent import NarrationAgent, NarrationResponse


class ThreadedPlayerAgent(threading.Thread):
    """PlayerAgent running in dedicated thread for game decisions"""
    
    def __init__(self):
        super().__init__(daemon=True, name="ThreadedPlayerAgent")
        
        # Communication queues
        self.input_queue = queue.Queue(maxsize=10)
        self.output_queue = queue.Queue(maxsize=10)
        
        # Agent instance with separate LLM client
        self.player_agent = PlayerAgent()
        
        # Control flags
        self.running = True
        self.processing = False
        
        print("🎮 ThreadedPlayerAgent initialized")
    
    def run(self):
        """Main thread loop processing player decisions"""
        print("🎮 ThreadedPlayerAgent started")
        
        while self.running:
            try:
                # Wait for work with timeout
                task = self.input_queue.get(timeout=1.0)
                if task is None:  # Shutdown signal
                    break
                
                self.processing = True
                screenshot_path, game_state, previous_screenshot, enhanced_context = task
                
                print(f"🎮 PlayerAgent processing: {screenshot_path}")
                
                # Call player agent
                response = self.player_agent.analyze_and_decide(
                    screenshot_path=screenshot_path,
                    game_state=game_state,
                    previous_screenshot=previous_screenshot,
                    enhanced_context=enhanced_context
                )
                
                # Send result back
                self.output_queue.put(response)
                self.processing = False
                
                print(f"🎮 PlayerAgent completed: {len(response.actions)} actions")
                
            except queue.Empty:
                continue  # Timeout, check running flag
            except Exception as e:
                print(f"❌ ThreadedPlayerAgent error: {e}")
                traceback.print_exc()
                
                # Send error response
                error_response = PlayerResponse(
                    success=False,
                    error=str(e),
                    text=f"Player agent error: {e}",
                    actions=[]
                )
                self.output_queue.put(error_response)
                self.processing = False
        
        print("🎮 ThreadedPlayerAgent stopped")
    
    def process_request(self, screenshot_path: str, game_state: Dict[str, Any], 
                       previous_screenshot: Optional[str] = None, 
                       enhanced_context: str = "") -> None:
        """Queue a processing request (non-blocking)"""
        try:
            task = (screenshot_path, game_state, previous_screenshot, enhanced_context)
            self.input_queue.put(task, timeout=1.0)
        except queue.Full:
            print("⚠️ PlayerAgent input queue full - dropping request")
    
    def get_response(self, timeout: float = 10.0) -> Optional[PlayerResponse]:
        """Get response from player agent (blocking with timeout)"""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            print("⏰ PlayerAgent timeout - no response received")
            return None
    
    def initialize_llm(self, config: Dict[str, Any]):
        """Initialize LLM client"""
        self.player_agent.initialize_llm(config)
    
    def set_memory_system(self, memory_system):
        """Set memory system"""
        self.player_agent.set_memory_system(memory_system)
    
    def reset_session(self):
        """Reset agent session"""
        self.player_agent.reset_session()
    
    def is_processing(self) -> bool:
        """Check if agent is currently processing"""
        return self.processing
    
    def shutdown(self):
        """Graceful shutdown"""
        print("🎮 Shutting down ThreadedPlayerAgent...")
        self.running = False
        self.input_queue.put(None)  # Shutdown signal


class ThreadedNarrationAgent(threading.Thread):
    """NarrationAgent running in background thread for entertainment"""
    
    def __init__(self):
        super().__init__(daemon=True, name="ThreadedNarrationAgent")
        
        # Communication queues
        self.input_queue = queue.Queue(maxsize=10)
        self.output_queue = queue.Queue(maxsize=10)
        
        # Agent instance with separate LLM client
        self.narration_agent = NarrationAgent()
        
        # Control flags
        self.running = True
        self.processing = False
        
        print("🎤 ThreadedNarrationAgent initialized")
    
    def run(self):
        """Main thread loop processing narration requests"""
        print("🎤 ThreadedNarrationAgent started")
        
        while self.running:
            try:
                # Wait for work with timeout
                task = self.input_queue.get(timeout=1.0)
                if task is None:  # Shutdown signal
                    break
                
                self.processing = True
                player_response_dict, game_context = task
                
                print(f"🎤 NarrationAgent processing narration")
                
                # Call narration agent
                response = self.narration_agent.generate_narration(
                    player_response_dict, game_context
                )
                
                # Send result back
                self.output_queue.put(response)
                self.processing = False
                
                print(f"🎤 NarrationAgent completed: {response.success}")
                
            except queue.Empty:
                continue  # Timeout, check running flag
            except Exception as e:
                print(f"❌ ThreadedNarrationAgent error: {e}")
                traceback.print_exc()
                
                # Send error response
                error_response = NarrationResponse(
                    success=False,
                    error=str(e),
                    narration=f"Narration error: {e}"
                )
                self.output_queue.put(error_response)
                self.processing = False
        
        print("🎤 ThreadedNarrationAgent stopped")
    
    def process_request(self, player_response_dict: Dict[str, Any], 
                       game_context: Dict[str, Any]) -> None:
        """Queue a narration request (non-blocking)"""
        try:
            task = (player_response_dict, game_context)
            self.input_queue.put(task, timeout=1.0)
        except queue.Full:
            print("⚠️ NarrationAgent input queue full - dropping request")
    
    def get_response(self, timeout: float = 5.0) -> Optional[NarrationResponse]:
        """Get response from narration agent (blocking with timeout)"""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            print("⏰ NarrationAgent timeout - using fallback")
            return NarrationResponse(
                success=False,
                error="Timeout",
                narration="The adventure continues..."
            )
    
    def initialize_llm(self, config: Dict[str, Any]):
        """Initialize LLM client"""
        self.narration_agent.initialize_llm(config)
    
    def reset_session(self):
        """Reset agent session"""
        self.narration_agent.reset_session()
    
    def is_processing(self) -> bool:
        """Check if agent is currently processing"""
        return self.processing
    
    def shutdown(self):
        """Graceful shutdown"""
        print("🎤 Shutting down ThreadedNarrationAgent...")
        self.running = False
        self.input_queue.put(None)  # Shutdown signal


class AgentCoordinator:
    """Coordinates threaded agents for optimal performance"""
    
    def __init__(self):
        # Threaded agents
        self.player_agent = ThreadedPlayerAgent()
        self.narration_agent = ThreadedNarrationAgent()
        
        # Agent status
        self.agents_started = False
        
        # Performance tracking
        self.cycle_times = []
        self.max_cycle_history = 10
        
        print("🎯 AgentCoordinator initialized")
    
    def start_agents(self):
        """Start all agent threads"""
        if not self.agents_started:
            self.player_agent.start()
            self.narration_agent.start()
            self.agents_started = True
            print("🚀 All agent threads started")
    
    def initialize_agents(self, config: Dict[str, Any]):
        """Initialize LLM clients for all agents"""
        self._last_config = config  # Store for restarts
        self.player_agent.initialize_llm(config)
        self.narration_agent.initialize_llm(config)
        print("🤖 All agents initialized with LLM clients")
    
    def set_memory_system(self, memory_system):
        """Set memory system for player agent"""
        self._memory_system = memory_system  # Store for restarts
        self.player_agent.set_memory_system(memory_system)
    
    def reset_sessions(self):
        """Reset all agent sessions"""
        self.player_agent.reset_session()
        self.narration_agent.reset_session()
        print("🔄 All agent sessions reset")
    
    def process_game_cycle(self, screenshot_path: str, game_state: Dict[str, Any], 
                          previous_screenshot: Optional[str] = None,
                          enhanced_context: str = "") -> Tuple[PlayerResponse, Optional[NarrationResponse]]:
        """
        Process a complete game cycle with parallel agent execution
        Returns: (player_response, narration_response)
        """
        cycle_start = time.time()
        
        # Ensure agents are started and healthy
        if not self.agents_started or not self._agents_healthy():
            self._restart_unhealthy_agents()
        
        print("🎯 Starting parallel game cycle processing...")
        
        # Start PlayerAgent processing (critical path)
        self.player_agent.process_request(
            screenshot_path, game_state, previous_screenshot, enhanced_context
        )
        
        # Wait for PlayerAgent response (blocking, critical path)
        player_response = self.player_agent.get_response(timeout=15.0)
        
        if not player_response:
            print("❌ PlayerAgent timeout - creating fallback response")
            # Create fallback response
            player_response = PlayerResponse(
                success=False,
                error="Player agent timeout",
                text="Player agent failed to respond in time",
                actions=["A"]  # Fallback action
            )
        
        # Start NarrationAgent processing (non-blocking, background)
        try:
            if player_response.success and self.narration_agent.is_alive():
                self.narration_agent.process_request(
                    player_response.to_dict(), game_state
                )
            else:
                print("⚠️ Skipping narration - player failed or narration agent unavailable")
        except Exception as e:
            print(f"⚠️ Failed to start narration processing: {e}")
        
        # Don't wait for narration - return immediately with player response
        # Narration will be collected later in a non-blocking manner
        
        cycle_time = time.time() - cycle_start
        self.cycle_times.append(cycle_time)
        if len(self.cycle_times) > self.max_cycle_history:
            self.cycle_times = self.cycle_times[-self.max_cycle_history:]
        
        print(f"🎯 Game cycle completed in {cycle_time:.2f}s (player response ready)")
        
        return player_response, None  # Narration will be retrieved separately
    
    def get_pending_narration(self) -> Optional[NarrationResponse]:
        """Get narration response if available (non-blocking)"""
        try:
            if self.narration_agent.is_alive():
                return self.narration_agent.get_response(timeout=0.1)
            else:
                print("⚠️ NarrationAgent thread is not alive")
                return None
        except Exception as e:
            print(f"⚠️ Error getting narration: {e}")
            return None
    
    def _agents_healthy(self) -> bool:
        """Check if all agents are healthy and responsive"""
        try:
            player_alive = self.player_agent.is_alive()
            narration_alive = self.narration_agent.is_alive()
            
            if not player_alive:
                print("❌ PlayerAgent thread is not alive")
            if not narration_alive:
                print("⚠️ NarrationAgent thread is not alive")
            
            return player_alive and narration_alive
        except Exception as e:
            print(f"❌ Error checking agent health: {e}")
            return False
    
    def _restart_unhealthy_agents(self):
        """Restart any unhealthy agents"""
        print("🏥 Checking and restarting unhealthy agents...")
        
        try:
            # Check PlayerAgent
            if not self.player_agent.is_alive():
                print("🔄 Restarting PlayerAgent...")
                self.player_agent = ThreadedPlayerAgent()
                if hasattr(self, '_last_config'):
                    self.player_agent.initialize_llm(self._last_config)
                if hasattr(self, '_memory_system') and self._memory_system:
                    self.player_agent.set_memory_system(self._memory_system)
                self.player_agent.start()
                print("✅ PlayerAgent restarted")
            
            # Check NarrationAgent
            if not self.narration_agent.is_alive():
                print("🔄 Restarting NarrationAgent...")
                self.narration_agent = ThreadedNarrationAgent()
                if hasattr(self, '_last_config'):
                    self.narration_agent.initialize_llm(self._last_config)
                self.narration_agent.start()
                print("✅ NarrationAgent restarted")
            
            self.agents_started = True
            
        except Exception as e:
            print(f"❌ Error restarting agents: {e}")
            # In case of restart failure, try to continue with what we have
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            "agents_started": self.agents_started,
            "player_agent": {
                "alive": self.player_agent.is_alive() if self.agents_started else False,
                "processing": self.player_agent.is_processing()
            },
            "narration_agent": {
                "alive": self.narration_agent.is_alive() if self.agents_started else False,
                "processing": self.narration_agent.is_processing()
            },
            "average_cycle_time": sum(self.cycle_times) / len(self.cycle_times) if self.cycle_times else 0
        }
    
    def shutdown(self):
        """Graceful shutdown of all agents"""
        print("🎯 Shutting down AgentCoordinator...")
        
        if self.agents_started:
            self.player_agent.shutdown()
            self.narration_agent.shutdown()
            
            # Wait for threads to finish
            if self.player_agent.is_alive():
                self.player_agent.join(timeout=5.0)
            if self.narration_agent.is_alive():
                self.narration_agent.join(timeout=5.0)
            
            self.agents_started = False
        
        print("✅ AgentCoordinator shutdown complete")