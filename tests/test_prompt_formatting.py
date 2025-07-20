#!/usr/bin/env python3
"""
Test script to verify enhanced prompt formatting functionality.
"""

import json
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from games.pokemon_red.controller import PokemonRedController

def test_prompt_formatting():
    """Test enhanced prompt formatting with realistic conversation scenario."""
    
    # Load config
    try:
        with open('config_emulator.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Create controller
    controller = PokemonRedController(config)
    
    print("🧪 Testing enhanced prompt formatting...")
    
    # Set up a realistic conversation scenario
    print("\n📝 Setting up conversation scenario...")
    
    # Simulate conversation setup
    controller.knowledge_system.start_conversation(
        npc_name="Mom",
        npc_role="mom", 
        topic="setting clock",
        location_id=24
    )
    
    controller.knowledge_system.set_current_objective("Follow mom's instructions to set the clock")
    controller.knowledge_system.add_dialogue_to_conversation("Mom", "Welcome home! Please go upstairs and set the clock.")
    controller.knowledge_system.set_expected_action("Go upstairs to your room")
    
    # Add some context memory
    controller.knowledge_system.add_context_memory(
        "ai_decision", 
        "I see my character, Gemini, standing in a room with my mom talking about setting the clock.",
        priority=8
    )
    
    controller.knowledge_system.record_important_moment("First conversation with Mom in tutorial")
    
    # Pin essential context
    controller.knowledge_system.pin_context("game", "This is Pokemon Red")
    controller.knowledge_system.pin_context("character_name", "Your name is GEMINI")
    
    print("✅ Conversation scenario set up complete")
    
    # Test prompt context building
    print("\n🔧 Building prompt context...")
    context = controller._build_prompt_context()
    
    print("📄 Generated context keys:")
    for key in sorted(context.keys()):
        print(f"   - {key}")
    
    # Test critical summary generation
    print(f"\n🚨 Critical Summary:")
    if 'critical_summary' in context:
        print(context['critical_summary'])
    else:
        print("   No critical summary generated")
    
    # Test enhanced character context
    print(f"\n🎭 Enhanced Character Context:")
    if 'character_context' in context:
        print(context['character_context'])
    
    # Test enhanced conversation context  
    print(f"\n🗣️ Enhanced Conversation Context:")
    if 'conversation_context' in context:
        print(context['conversation_context'])
    
    # Test enhanced memory context
    print(f"\n🧠 Enhanced Memory Context:")
    if 'memory_context' in context:
        print(context['memory_context'])
    
    # Test enhanced game phase guidance
    print(f"\n📚 Enhanced Game Phase Guidance:")
    if 'game_phase_guidance' in context:
        print(context['game_phase_guidance'])
    
    # Test complete formatted prompt
    print(f"\n📋 Testing prompt template formatting...")
    
    # Create a mock game state for prompt formatting
    from core.base_game_engine import GameState
    controller.current_game_state = GameState(
        player_x=24, player_y=28, player_direction="DOWN", map_id=24
    )
    
    try:
        formatted_prompt = controller.prompt_template.format_template(
            game_state=controller.current_game_state,
            **context
        )
        
        print("✅ Prompt template formatted successfully")
        print(f"📏 Prompt length: {len(formatted_prompt)} characters")
        
        # Show key sections of the formatted prompt
        lines = formatted_prompt.split('\n')
        important_sections = []
        current_section = None
        
        for line in lines:
            if line.startswith('## 🚨'):
                current_section = ['🚨 IMMEDIATE SITUATION & CONTEXT:', line]
            elif line.startswith('## 📋'):
                if current_section:
                    important_sections.append('\n'.join(current_section[:10]))  # First 10 lines
                current_section = ['📋 GAME GUIDANCE & ACTIONS:', line]
            elif current_section and len(current_section) < 10:
                current_section.append(line)
        
        if current_section:
            important_sections.append('\n'.join(current_section[:10]))
        
        print(f"\n📄 Key prompt sections:")
        for i, section in enumerate(important_sections, 1):
            print(f"\nSection {i}:")
            print(section)
            print("-" * 40)
        
    except Exception as e:
        print(f"❌ Error formatting prompt template: {e}")
        return False
    
    print("🎉 Enhanced prompt formatting test completed!")
    return True

if __name__ == '__main__':
    print("🧪 Starting enhanced prompt formatting tests...")
    
    success = test_prompt_formatting()
    
    if success:
        print("✅ Enhanced prompt formatting implementation is working!")
    else:
        print("❌ Enhanced prompt formatting test failed.")
        sys.exit(1)