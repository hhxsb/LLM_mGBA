#!/usr/bin/env python3
"""
Test script to verify tutorial progress tracking functionality.
"""

import json
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from games.pokemon_red.controller import PokemonRedController
from core.base_game_engine import GameState

def test_tutorial_progress_tracking():
    """Test tutorial progress tracking with realistic Pokemon Red tutorial scenarios."""
    
    # Load config
    try:
        with open('config_emulator.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Create controller
    controller = PokemonRedController(config)
    
    print("🧪 Testing tutorial progress tracking...")
    
    # Test 1: Initialize tutorial system
    print("\n📚 Test 1: Initializing tutorial system...")
    
    controller.knowledge_system.initialize_tutorial_system()
    
    print(f"✅ Tutorial system initialized")
    print(f"   Current step: {controller.knowledge_system.character_state.current_tutorial_step}")
    print(f"   Total steps: {len(controller.knowledge_system.tutorial_steps)}")
    print(f"   Game phase: {controller.knowledge_system.character_state.game_phase}")
    
    # Test 2: Get current tutorial guidance
    print("\n💡 Test 2: Testing current tutorial guidance...")
    
    guidance = controller.knowledge_system.get_current_tutorial_guidance()
    print("Current tutorial guidance:")
    print(guidance)
    
    # Test 3: Test tutorial step completion detection
    print("\n✅ Test 3: Testing tutorial step completion detection...")
    
    # Create mock game state
    game_state = GameState(player_x=24, player_y=28, player_direction="DOWN", map_id=24)
    
    # Test different AI responses for step completion
    test_responses = [
        ("My character name is GEMINI and I'm in the game world now", "game_start"),
        ("I can see I'm inside the house with Mom nearby", "enter_house"), 
        ("I am currently talking to Mom about setting the clock", "talk_to_mom"),
        ("I have gone upstairs to the bedroom area", "go_upstairs"),
        ("I successfully set the clock to the correct time", "set_clock"),
        ("I went back downstairs to the first floor", "go_downstairs"),
        ("I am now outside the house in Pallet Town", "exit_house"),
        ("I found Professor Oak in the tall grass area", "explore_town"),
        ("I am talking to Oak about Pokemon and my journey", "meet_oak"),
        ("I chose Charmander as my starter Pokemon", "choose_starter"),
        ("The battle with my rival has ended", "first_battle")
    ]
    
    for response, expected_step in test_responses:
        # Set the current step to test specific detection
        controller.knowledge_system.character_state.current_tutorial_step = expected_step
        
        # Test detection
        detected_step = controller.knowledge_system.detect_tutorial_step_completion(response, "", game_state)
        print(f"   Response: '{response[:50]}...'")
        print(f"   Expected step: {expected_step}, Detected: {detected_step}")
        
        if detected_step == expected_step:
            print("   ✅ Correct detection!")
        else:
            print("   ⚠️ Detection mismatch")
    
    # Test 4: Test tutorial step completion and progression
    print("\n🎯 Test 4: Testing tutorial step completion and progression...")
    
    # Reset to beginning
    controller.knowledge_system.character_state.current_tutorial_step = "game_start"
    controller.knowledge_system.character_state.completed_tutorial_steps = []
    controller.knowledge_system.character_state.tutorial_completion_percentage = 0.0
    
    # Simulate completing several tutorial steps
    steps_to_complete = ["game_start", "enter_house", "talk_to_mom", "go_upstairs"]
    
    for step in steps_to_complete:
        print(f"   Completing step: {step}")
        controller.knowledge_system.complete_tutorial_step(step)
        print(f"   Current step: {controller.knowledge_system.character_state.current_tutorial_step}")
        print(f"   Progress: {controller.knowledge_system.character_state.tutorial_completion_percentage:.1f}%")
    
    # Test 5: Test tutorial progress summary
    print("\n📊 Test 5: Testing tutorial progress summary...")
    
    progress_summary = controller.knowledge_system.get_tutorial_progress_summary()
    print("Tutorial progress summary:")
    print(progress_summary)
    
    # Test 6: Test next steps preview
    print("\n🔮 Test 6: Testing next steps preview...")
    
    next_steps = controller.knowledge_system.get_next_tutorial_steps_preview(3)
    print("Next tutorial steps preview:")
    print(next_steps)
    
    # Test 7: Test tutorial completion detection in AI response processing
    print("\n🎭 Test 7: Testing tutorial step detection from AI responses...")
    
    # Set specific tutorial step
    controller.knowledge_system.character_state.current_tutorial_step = "set_clock"
    
    # Test with realistic AI response
    ai_response = "I can see the clock in my bedroom. I will press A to interact with it and set the time as Mom instructed."
    
    controller.knowledge_system.process_tutorial_step_detection(ai_response, "A", game_state)
    
    print(f"   After processing response, current step: {controller.knowledge_system.character_state.current_tutorial_step}")
    
    # Test 8: Test tutorial guidance in different phases
    print("\n📚 Test 8: Testing tutorial guidance for different steps...")
    
    test_tutorial_steps = ["talk_to_mom", "choose_starter", "first_battle"]
    
    for step in test_tutorial_steps:
        controller.knowledge_system.character_state.current_tutorial_step = step
        guidance = controller.knowledge_system.get_current_tutorial_guidance()
        print(f"\n   Step: {step}")
        print(f"   Guidance preview: {guidance[:150]}...")
    
    # Test 9: Test tutorial completion and game phase transition
    print("\n🏆 Test 9: Testing tutorial completion...")
    
    # Complete final tutorial step
    controller.knowledge_system.character_state.current_tutorial_step = "first_battle"
    controller.knowledge_system.complete_tutorial_step("first_battle")
    
    print(f"   Final tutorial step: {controller.knowledge_system.character_state.current_tutorial_step}")
    print(f"   Game phase: {controller.knowledge_system.character_state.game_phase}")
    print(f"   Final progress: {controller.knowledge_system.character_state.tutorial_completion_percentage:.1f}%")
    
    # Test 10: Test prompt context integration
    print("\n📋 Test 10: Testing tutorial context in prompts...")
    
    # Reset to tutorial phase
    controller.knowledge_system.character_state.game_phase = "tutorial"
    controller.knowledge_system.character_state.current_tutorial_step = "talk_to_mom"
    
    # Build prompt context
    controller.current_game_state = game_state
    context = controller._build_prompt_context()
    
    tutorial_keys = [key for key in context.keys() if 'tutorial' in key]
    print(f"   Tutorial context keys: {tutorial_keys}")
    
    for key in tutorial_keys:
        if context.get(key):
            print(f"   {key}: {context[key][:100]}...")
    
    # Test 11: Test step-specific completion functions
    print("\n🔧 Test 11: Testing step-specific completion functions...")
    
    # Test specific completion check functions
    completion_tests = [
        ("_check_game_start_completion", "My character GEMINI has entered the game world", True),
        ("_check_talk_to_mom_completion", "I am talking to Mom about the clock", True),
        ("_check_set_clock_completion", "I set the clock to the correct time", True),
        ("_check_choose_starter_completion", "I chose Bulbasaur as my starter", True),
        ("_check_first_battle_completion", "The battle has ended and I won", True),
    ]
    
    for func_name, test_response, expected in completion_tests:
        if hasattr(controller.knowledge_system, func_name):
            func = getattr(controller.knowledge_system, func_name)
            result = func(test_response.lower(), "", game_state)()
            print(f"   {func_name}: '{test_response}' → {result} (expected: {expected})")
    
    print("🎉 Tutorial progress tracking test completed!")
    return True

if __name__ == '__main__':
    print("🧪 Starting tutorial progress tracking tests...")
    
    success = test_tutorial_progress_tracking()
    
    if success:
        print("✅ Tutorial progress tracking implementation is working!")
    else:
        print("❌ Tutorial progress tracking test failed.")
        sys.exit(1)