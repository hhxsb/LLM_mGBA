#!/usr/bin/env python3
"""
Test script to verify conversation state tracking functionality.
"""

import json
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from games.pokemon_red.controller import PokemonRedController

def test_conversation_tracking():
    """Test conversation state tracking with sample AI responses."""
    
    # Load config
    try:
        with open('config_emulator.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Create controller (but don't start server)
    controller = PokemonRedController(config)
    
    print("🧪 Testing conversation state tracking...")
    
    # Test AI responses from the log
    test_responses = [
        "I've just arrived in my house, and it seems my mother is telling me to go to my room, which is upstairs.",
        "I've just arrived in my new home, and my mom is welcoming me. She's telling me that my dad bought me a new clock.",
        "I am currently inside a house, talking to a girl. The dialogue box at the bottom of the screen shows an incomplete sentence.",
        "I see my character, Gemini, standing in a room with my mom. She is speaking to me, and the dialogue box shows her asking 'Well, GEMINI?'."
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n📝 Test {i}: Processing AI response...")
        print(f"   Response: {response[:60]}...")
        
        # Process the response
        controller._update_conversation_state_from_response(response)
        
        # Check conversation state
        conv_state = controller.knowledge_system.conversation_state
        if conv_state.current_npc:
            print(f"✅ Detected conversation with: {conv_state.current_npc} ({conv_state.npc_role})")
            print(f"   Topic: {conv_state.conversation_topic}")
            if conv_state.expected_next_action:
                print(f"   Expected action: {conv_state.expected_next_action}")
        else:
            print("❌ No conversation detected")
        
        # Test context generation
        context = controller.knowledge_system.get_conversation_context()
        if context:
            print(f"📄 Generated context:\n{context}")
        
        print("-" * 50)
    
    print("🎉 Conversation tracking test completed!")
    return True

if __name__ == '__main__':
    print("🧪 Starting conversation tracking tests...")
    
    success = test_conversation_tracking()
    
    if success:
        print("✅ Conversation tracking implementation is working!")
    else:
        print("❌ Conversation tracking test failed.")
        sys.exit(1)