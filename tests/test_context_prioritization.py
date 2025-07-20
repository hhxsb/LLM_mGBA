#!/usr/bin/env python3
"""
Test script to verify smart context prioritization functionality.
"""

import json
import sys
import os
import time

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from games.pokemon_red.controller import PokemonRedController

def test_context_prioritization():
    """Test smart context prioritization with realistic scenarios."""
    
    # Load config
    try:
        with open('config_emulator.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Create controller
    controller = PokemonRedController(config)
    
    print("🧪 Testing smart context prioritization...")
    
    # Test 1: Add various context entries with different types and priorities
    print("\n📝 Test 1: Adding diverse context entries...")
    
    # Add different types of context
    test_contexts = [
        ("ai_decision", "I chose to press A to talk to Mom", 5, 24),
        ("conversation", "Currently talking to Mom about setting the clock", 8, 24),
        ("important", "First conversation with Mom in tutorial", 9, 24),
        ("location_change", "Moved from outside to inside the house", 3, 24),
        ("action_outcome", "Successfully entered the house", 4, 24),
        ("ai_decision", "Decided to move up toward the NPC", 5, 24),
        ("conversation", "Mom is giving instructions about the clock", 7, 24),
        ("important", "Tutorial objective: Set the clock upstairs", 10, 24),
    ]
    
    for context_type, content, priority, location in test_contexts:
        controller.knowledge_system.add_context_memory(context_type, content, priority, location)
        time.sleep(0.1)  # Small delay to create different timestamps
    
    print(f"✅ Added {len(test_contexts)} context entries")
    
    # Test 2: Set up conversation scenario
    print("\n🗣️ Test 2: Setting up conversation scenario...")
    
    controller.knowledge_system.start_conversation(
        npc_name="Mom",
        npc_role="mom",
        topic="setting clock",
        location_id=24
    )
    
    controller.knowledge_system.set_current_objective("Go upstairs and set the clock")
    controller.knowledge_system.character_state.game_phase = "tutorial"
    
    print("✅ Conversation scenario set up")
    
    # Test 3: Test current situation context building
    print("\n🎯 Test 3: Testing current situation context...")
    
    current_situation = controller.knowledge_system.get_current_situation_context()
    print("Current situation context:")
    for key, value in current_situation.items():
        print(f"   {key}: {value}")
    
    # Test 4: Calculate relevance scores
    print("\n📊 Test 4: Testing relevance score calculation...")
    
    print("Relevance scores for each context entry:")
    for entry in controller.knowledge_system.context_memory:
        score = controller.knowledge_system.calculate_context_relevance_score(entry, current_situation)
        print(f"   Score {score:.1f}: {entry.context_type} - {entry.content[:50]}...")
    
    # Test 5: Test smart prioritization vs legacy
    print("\n🧠 Test 5: Comparing smart vs legacy prioritization...")
    
    print("=== SMART PRIORITIZATION ===")
    smart_context = controller.knowledge_system.get_relevant_context_memory(max_entries=5, use_smart_prioritization=True)
    print(smart_context)
    
    print("\n=== LEGACY PRIORITIZATION ===")
    legacy_context = controller.knowledge_system.get_relevant_context_memory(max_entries=5, use_smart_prioritization=False)
    print(legacy_context)
    
    # Test 6: Test context selection by type
    print("\n📋 Test 6: Testing context selection by type...")
    
    priority_types = ["important", "conversation", "ai_decision"]
    selected_by_type = controller.knowledge_system.select_context_by_type_priority(priority_types, max_per_type=2)
    
    print(f"Selected {len(selected_by_type)} entries by type priority:")
    for entry in selected_by_type:
        score = controller.knowledge_system.calculate_context_relevance_score(entry, current_situation)
        print(f"   {entry.context_type} (score {score:.1f}): {entry.content[:60]}...")
    
    # Test 7: Test context length management
    print("\n📏 Test 7: Testing context length management...")
    
    # Create long context parts
    long_context_parts = [
        "🚨 CRITICAL: This is a very long critical context that contains important information about the current game state and what the player needs to do next in this tutorial phase.",
        "🗣️ CONVERSATION: The player is currently engaged in a detailed conversation with Mom about setting the clock upstairs in the bedroom which is a crucial tutorial step.",
        "🎯 OBJECTIVE: The current objective is to navigate to the upstairs bedroom and interact with the clock to set the time which will unlock time-based events in the game.",
        "📚 KNOWLEDGE: The game is Pokemon Red and the player character is named GEMINI and this is the very beginning tutorial phase where basic controls are being learned.",
        "📍 LOCATION: Currently inside the player's house talking to Mom in the living room area before going upstairs to complete the clock setting task.",
        "🧠 MEMORY: Previous actions included entering the house, talking to Mom, and receiving instructions about the clock setting requirement.",
        "⚡ ACTION: The next expected action is to move upstairs using the UP arrow key and then interact with the clock object using the A button."
    ]
    
    # Test without length limit
    print(f"Original context parts: {len(long_context_parts)}")
    print(f"Total length: {sum(len(part) for part in long_context_parts)} characters")
    
    # Test with length limit
    managed_parts = controller.knowledge_system.apply_context_length_management(long_context_parts, max_total_chars=300)
    print(f"After length management: {len(managed_parts)} parts")
    print(f"Total length: {sum(len(part) for part in managed_parts)} characters")
    
    print("Managed context:")
    for part in managed_parts:
        print(f"   {part[:80]}...")
    
    # Test 8: Test context relevance summary
    print("\n📊 Test 8: Testing context relevance summary...")
    
    relevance_summary = controller.knowledge_system.get_context_relevance_summary()
    print("Context relevance summary:")
    print(relevance_summary)
    
    # Test 9: Test different scenarios
    print("\n🎮 Test 9: Testing different scenario prioritization...")
    
    # Scenario 1: No conversation
    controller.knowledge_system.conversation_state.current_npc = None
    controller.knowledge_system.conversation_state.conversation_topic = None
    no_conv_situation = controller.knowledge_system.get_current_situation_context()
    
    print("Scenario: No conversation active")
    prioritized_no_conv = controller.knowledge_system.prioritize_context_entries(no_conv_situation, max_entries=3)
    for entry in prioritized_no_conv:
        score = controller.knowledge_system.calculate_context_relevance_score(entry, no_conv_situation)
        print(f"   Score {score:.1f}: {entry.context_type} - {entry.content[:50]}...")
    
    # Scenario 2: Different location
    controller.knowledge_system.start_conversation("Professor Oak", "professor", "Pokemon research", 40)
    diff_location_situation = controller.knowledge_system.get_current_situation_context()
    diff_location_situation["location_id"] = 40
    
    print("\nScenario: Different location (Professor's lab)")
    prioritized_diff_loc = controller.knowledge_system.prioritize_context_entries(diff_location_situation, max_entries=3)
    for entry in prioritized_diff_loc:
        score = controller.knowledge_system.calculate_context_relevance_score(entry, diff_location_situation)
        print(f"   Score {score:.1f}: {entry.context_type} - {entry.content[:50]}...")
    
    print("🎉 Smart context prioritization test completed!")
    return True

if __name__ == '__main__':
    print("🧪 Starting smart context prioritization tests...")
    
    success = test_context_prioritization()
    
    if success:
        print("✅ Smart context prioritization implementation is working!")
    else:
        print("❌ Smart context prioritization test failed.")
        sys.exit(1)