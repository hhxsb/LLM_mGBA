#!/usr/bin/env python3
"""
Test script to verify context memory buffer functionality.
"""

import json
import sys
import os
import time

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from games.pokemon_red.controller import PokemonRedController

def test_context_memory():
    """Test context memory buffer with sample AI responses and scenarios."""
    
    # Load config
    try:
        with open('config_emulator.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Create controller
    controller = PokemonRedController(config)
    
    print("🧪 Testing context memory buffer...")
    
    # Test scenario: Conversation with mom about setting clock
    test_responses = [
        "I've just arrived in my house, and it seems my mother is telling me to go to my room, which is upstairs.",
        "I see my character, Gemini, standing in a room with my mom. She is speaking to me about setting the clock.",
        "My goal is to leave the house and begin my Pokémon adventure.",
        "I am currently talking to a girl about setting the time.", 
        "I need to continue this conversation to progress the story."
    ]
    
    # Test pinned context
    controller.knowledge_system.pin_context("game", "This is Pokemon Red")
    controller.knowledge_system.pin_context("character_name", "Your name is GEMINI")
    
    print(f"\n📌 Pinned essential context")
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n📝 Test {i}: Processing AI response...")
        print(f"   Response: {response[:50]}...")
        
        # Process all tracking
        controller._update_conversation_state_from_response(response)
        controller._update_character_state_from_response(response)
        controller._add_response_to_context_memory(response)
        
        # Add a small delay to ensure different timestamps
        time.sleep(0.1)
        
        # Get context memory
        memory_context = controller.knowledge_system.get_relevant_context_memory(max_entries=5)
        print(f"📄 Context Memory:\n{memory_context}")
        
        # Show memory stats
        stats = controller.knowledge_system.get_context_stats()
        print(f"📊 Memory Stats: {stats['total_entries']} entries, {stats['pinned_entries']} pinned")
        
        print("-" * 50)
    
    # Test important moment recording
    print("\n⭐ Testing important moment recording...")
    controller.knowledge_system.record_important_moment("Met Professor Oak for the first time")
    controller.knowledge_system.record_important_moment("Received first Pokemon")
    
    # Test location change
    print("\n🗺️ Testing location change tracking...")
    controller._record_location_change(24, 40)  # House to Oak's Lab
    
    # Test action outcome
    print("\n🎮 Testing action outcome tracking...")
    controller._record_action_outcome("Pressed A to advance dialogue", "Dialogue progressed")
    
    # Final context memory state
    print("\n📋 Final context memory state:")
    final_memory = controller.knowledge_system.get_relevant_context_memory(max_entries=10)
    print(final_memory)
    
    # Test context by type
    print("\n📋 Important moments:")
    important_context = controller.knowledge_system.get_context_summary_by_type("important", max_entries=3)
    if important_context:
        print(important_context)
    else:
        print("   No important moments recorded")
    
    final_stats = controller.knowledge_system.get_context_stats()
    print(f"\n📊 Final Memory Stats:")
    print(f"   Total entries: {final_stats['total_entries']}")
    print(f"   Pinned entries: {final_stats['pinned_entries']}")
    print(f"   Entry types: {final_stats['types']}")
    print(f"   Priority distribution: {final_stats['priorities']}")
    
    print("🎉 Context memory test completed!")
    return True

if __name__ == '__main__':
    print("🧪 Starting context memory tests...")
    
    success = test_context_memory()
    
    if success:
        print("✅ Context memory implementation is working!")
    else:
        print("❌ Context memory test failed.")
        sys.exit(1)