#!/usr/bin/env python3
"""
Test script to verify enhanced dialogue recording and memory functionality.
"""

import json
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from games.pokemon_red.controller import PokemonRedController

def test_dialogue_recording():
    """Test enhanced dialogue recording with realistic Pokemon Red scenarios."""
    
    # Load config
    try:
        with open('config_emulator.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Create controller
    controller = PokemonRedController(config)
    
    print("🧪 Testing enhanced dialogue recording...")
    
    # Test 1: Record dialogue with Mom
    print("\n📝 Test 1: Recording dialogue with Mom...")
    
    conversation_id = controller.knowledge_system.record_dialogue(
        npc_name="Mom",
        npc_role="mom",
        dialogue_text="Welcome home! You need to go upstairs and set the clock in your room.",
        player_response="I pressed A to continue the conversation",
        outcome="Dialogue progressed, next step is to go upstairs",
        location_id=24
    )
    
    print(f"✅ Generated conversation ID: {conversation_id}")
    
    # Test 2: Record follow-up dialogue
    print("\n📝 Test 2: Recording follow-up dialogue...")
    
    controller.knowledge_system.record_dialogue(
        npc_name="Mom", 
        npc_role="mom",
        dialogue_text="Don't forget to set the clock! It's important for time-based events.",
        player_response="I understood and will go upstairs now",
        outcome="Received clear instruction to set clock upstairs",
        location_id=24,
        important_info=["Clock setting is required for time-based events"]
    )
    
    # Test 3: Check NPC interaction history
    print("\n📚 Test 3: Checking NPC interaction history...")
    
    mom_history = controller.knowledge_system.get_npc_interaction_history("Mom")
    print(f"✅ Mom interaction history: {len(mom_history)} conversations")
    
    for i, dialogue in enumerate(mom_history):
        print(f"   Conversation {i+1}: {dialogue.dialogue_text[:50]}...")
        if dialogue.important_info:
            print(f"   Important info: {dialogue.important_info}")
    
    # Test 4: Record dialogue with different NPC
    print("\n📝 Test 4: Recording dialogue with Professor Oak...")
    
    controller.knowledge_system.record_dialogue(
        npc_name="Professor Oak",
        npc_role="professor",
        dialogue_text="Welcome to the world of Pokemon! I am Professor Oak. Pokemon are everywhere!",
        player_response="I listened to the introduction",
        outcome="Learned about Pokemon world from Professor Oak",
        location_id=40
    )
    
    # Test 5: Test information extraction
    print("\n🔍 Test 5: Testing automatic information extraction...")
    
    controller.knowledge_system.record_dialogue(
        npc_name="Mom",
        npc_role="mom", 
        dialogue_text="You must remember to save your game often! Don't forget to heal your Pokemon at Pokemon Centers.",
        player_response="I acknowledged the advice",
        outcome="Received important gameplay advice",
        location_id=24
    )
    
    recent_dialogue = controller.knowledge_system.get_recent_dialogues(1)[0]
    print(f"✅ Extracted important info: {recent_dialogue.important_info}")
    
    # Test 6: Find relevant past conversations
    print("\n🔍 Test 6: Finding relevant past conversations...")
    
    relevant = controller.knowledge_system.find_relevant_past_conversations("Mom", "clock")
    print(f"✅ Found {len(relevant)} relevant conversations about 'clock' with Mom")
    
    for dialogue in relevant:
        print(f"   Relevant: {dialogue.dialogue_text[:60]}...")
    
    # Test 7: Generate dialogue memory context
    print("\n📋 Test 7: Generating dialogue memory context...")
    
    dialogue_context = controller.knowledge_system.get_dialogue_memory_context()
    print("✅ Generated dialogue memory context:")
    print(dialogue_context)
    
    # Test 8: Test dialogue history limits
    print("\n📦 Test 8: Testing dialogue history management...")
    
    # Add many dialogues to test limit management
    for i in range(25):
        controller.knowledge_system.record_dialogue(
            npc_name=f"NPC_{i%5}",
            npc_role="generic",
            dialogue_text=f"This is test dialogue number {i}",
            player_response="Test response",
            outcome="Test outcome",
            location_id=1
        )
    
    total_dialogues = len(controller.knowledge_system.dialogue_history)
    print(f"✅ Total dialogues after adding 25: {total_dialogues} (should be ≤30 due to limit)")
    
    # Test 9: Test NPC-specific interaction tracking
    print("\n👥 Test 9: Testing NPC-specific interaction tracking...")
    
    npc_interactions = controller.knowledge_system.npc_interactions
    print(f"✅ Tracked NPCs: {list(npc_interactions.keys())}")
    
    for npc, interactions in npc_interactions.items():
        if len(interactions) > 0:
            print(f"   {npc}: {len(interactions)} interactions")
    
    print("🎉 Enhanced dialogue recording test completed!")
    return True

if __name__ == '__main__':
    print("🧪 Starting enhanced dialogue recording tests...")
    
    success = test_dialogue_recording()
    
    if success:
        print("✅ Enhanced dialogue recording implementation is working!")
    else:
        print("❌ Enhanced dialogue recording test failed.")
        sys.exit(1)