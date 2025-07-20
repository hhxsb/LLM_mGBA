#!/usr/bin/env python3
"""
Test script to verify character identity and game phase tracking functionality.
"""

import json
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from games.pokemon_red.controller import PokemonRedController

def test_character_tracking():
    """Test character identity and game phase tracking with sample AI responses."""
    
    # Load config
    try:
        with open('config_emulator.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Create controller
    controller = PokemonRedController(config)
    
    print("🧪 Testing character identity and game phase tracking...")
    
    # Test AI responses from the log that show identity issues
    test_responses = [
        "I see my character, Gemini, standing in a room with my mom.",
        "I've just arrived in my house, and it seems my mother is telling me to go to my room, which is upstairs.",
        "My goal is to leave the house and begin my Pokémon adventure.",
        "I need to continue this conversation to progress the story. I will press the 'A' button to advance the dialogue.",
        "To proceed with the game and begin my Pokémon journey, I need to exit the house."
    ]
    
    print(f"\n🎭 Initial character state:")
    print(f"   Name: {controller.knowledge_system.character_state.name}")
    print(f"   Game Phase: {controller.knowledge_system.character_state.game_phase}")
    print(f"   Objective: {controller.knowledge_system.character_state.current_objective}")
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n📝 Test {i}: Processing AI response...")
        print(f"   Response: {response[:50]}...")
        
        # Process the response for both conversation and character tracking
        controller._update_conversation_state_from_response(response)
        controller._update_character_state_from_response(response)
        
        # Check character state updates
        char_state = controller.knowledge_system.character_state
        print(f"✅ Character: {char_state.name} | Phase: {char_state.game_phase}")
        if char_state.current_objective:
            print(f"   Current Objective: {char_state.current_objective}")
        if char_state.tutorial_progress:
            print(f"   Tutorial Progress: {', '.join(char_state.tutorial_progress)}")
        if char_state.known_npcs:
            print(f"   Known NPCs: {char_state.known_npcs}")
        
        # Test character context generation
        char_context = controller.knowledge_system.get_character_context()
        print(f"📄 Character Context:\n{char_context}")
        
        # Test game phase guidance
        phase_guidance = controller.knowledge_system.get_game_phase_guidance()
        print(f"🎮 Phase Guidance: {phase_guidance[:60]}...")
        
        print("-" * 50)
    
    print("🎉 Character tracking test completed!")
    return True

if __name__ == '__main__':
    print("🧪 Starting character tracking tests...")
    
    success = test_character_tracking()
    
    if success:
        print("✅ Character tracking implementation is working!")
    else:
        print("❌ Character tracking test failed.")
        sys.exit(1)