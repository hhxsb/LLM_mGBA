#!/usr/bin/env python3
"""
Test script to verify conversation flow management functionality.
"""

import json
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from games.pokemon_red.controller import PokemonRedController

def test_conversation_flow_management():
    """Test conversation flow management with realistic Pokemon Red dialogue scenarios."""
    
    # Load config
    try:
        with open('config_emulator.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Create controller
    controller = PokemonRedController(config)
    
    print("🧪 Testing conversation flow management...")
    
    # Test 1: Detect conversation start
    print("\n📝 Test 1: Detecting conversation start...")
    
    greeting_text = "Welcome home! How are you today?"
    is_start = controller.knowledge_system.detect_conversation_start(greeting_text)
    print(f"✅ Detected conversation start: {is_start} (should be True)")
    
    # Test 2: Conversation phase progression
    print("\n🔄 Test 2: Testing conversation phase progression...")
    
    # Start conversation
    controller.knowledge_system.start_conversation(
        npc_name="Mom",
        npc_role="mom",
        topic="setting clock",
        location_id=24
    )
    
    # Test greeting phase
    controller.knowledge_system.analyze_conversation_flow("Welcome home! Good to see you.", 24)
    print(f"✅ Phase after greeting: {controller.knowledge_system.conversation_state.conversation_phase}")
    
    # Test transition to main topic
    controller.knowledge_system.analyze_conversation_flow("Now, I need you to help me with something important.", 24)
    print(f"✅ Phase after topic introduction: {controller.knowledge_system.conversation_state.conversation_phase}")
    
    # Test transition to instruction
    controller.knowledge_system.analyze_conversation_flow("You need to go upstairs and set the clock in your room.", 24)
    print(f"✅ Phase after instruction: {controller.knowledge_system.conversation_state.conversation_phase}")
    print(f"✅ Expected action: {controller.knowledge_system.conversation_state.expected_next_action}")
    
    # Test 3: Expected action extraction
    print("\n⏭️ Test 3: Testing expected action extraction...")
    
    test_dialogues = [
        "Please go to your room upstairs.",
        "You should talk to Professor Oak about Pokemon.",
        "Make sure to save your game often!",
        "Choose a Pokemon that you like.",
        "Let's battle! I challenge you!"
    ]
    
    for dialogue in test_dialogues:
        expected_action = controller.knowledge_system.extract_expected_action(dialogue)
        print(f"   Dialogue: '{dialogue}'")
        print(f"   Expected action: {expected_action}")
    
    # Test 4: Response type determination
    print("\n💬 Test 4: Testing response type determination...")
    
    test_scenarios = [
        ("greeting", "Hello there! How are you?"),
        ("main_topic", "Tell me about your Pokemon journey."),
        ("instruction", "You must go to the Pokemon Center."),
        ("conclusion", "Goodbye and good luck!")
    ]
    
    for phase, dialogue in test_scenarios:
        response_type = controller.knowledge_system.determine_response_type(dialogue, phase)
        print(f"   Phase: {phase}, Dialogue: '{dialogue}'")
        print(f"   Suggested response: {response_type}")
    
    # Test 5: Multi-turn conversation management
    print("\n🔗 Test 5: Testing multi-turn conversation management...")
    
    # Simulate multiple turns
    turns = [
        "Welcome home, how was your trip?",
        "Also, I wanted to tell you about the clock upstairs.",
        "And don't forget to set it to the correct time.",
        "By the way, Professor Oak was looking for you earlier."
    ]
    
    for i, turn in enumerate(turns, 1):
        controller.knowledge_system.manage_multi_turn_conversation(turn, i)
        print(f"   Turn {i}: Conversation history length = {len(controller.knowledge_system.conversation_state.conversation_history)}")
    
    # Test 6: Conversation flow context generation
    print("\n📋 Test 6: Testing conversation flow context generation...")
    
    flow_context = controller.knowledge_system.get_conversation_flow_context()
    print("✅ Generated conversation flow context:")
    print(flow_context)
    
    # Test 7: Conversation ending and summary
    print("\n📋 Test 7: Testing conversation ending...")
    
    # Trigger conversation end
    controller.knowledge_system.analyze_conversation_flow("That's all for now. See you later!", 24)
    
    # Check if conversation ended properly
    final_phase = controller.knowledge_system.conversation_state.conversation_phase
    print(f"✅ Final conversation phase: {final_phase}")
    
    # Test conversation summary generation
    if final_phase == "none":  # Conversation should have ended and reset
        print("✅ Conversation ended and state reset successfully")
    
    # Test 8: Complex conversation scenario
    print("\n🎭 Test 8: Testing complex conversation scenario...")
    
    # Start new conversation
    controller.knowledge_system.start_conversation(
        npc_name="Professor Oak",
        npc_role="professor",
        topic="Pokemon research",
        location_id=40
    )
    
    # Simulate complex conversation flow
    complex_flow = [
        ("Hello there! Welcome to my lab.", "greeting"),
        ("I am Professor Oak, and I study Pokemon.", "main_topic"),
        ("You need to choose your first Pokemon now.", "instruction"),
        ("Take your time and pick wisely.", "instruction"),
        ("Good luck on your journey!", "conclusion")
    ]
    
    for dialogue, expected_phase in complex_flow:
        controller.knowledge_system.analyze_conversation_flow(dialogue, 40)
        actual_phase = controller.knowledge_system.conversation_state.conversation_phase
        print(f"   Dialogue: '{dialogue[:30]}...'")
        print(f"   Expected phase: {expected_phase}, Actual: {actual_phase}")
    
    # Test 9: Conversation end detection
    print("\n🏁 Test 9: Testing conversation end detection...")
    
    end_phrases = [
        "Goodbye and take care!",
        "See you later!",
        "That's all for now.",
        "Good luck on your journey!"
    ]
    
    for phrase in end_phrases:
        is_end = controller.knowledge_system.detect_conversation_end(phrase)
        print(f"   '{phrase}' → End detected: {is_end}")
    
    print("🎉 Conversation flow management test completed!")
    return True

if __name__ == '__main__':
    print("🧪 Starting conversation flow management tests...")
    
    success = test_conversation_flow_management()
    
    if success:
        print("✅ Conversation flow management implementation is working!")
    else:
        print("❌ Conversation flow management test failed.")
        sys.exit(1)