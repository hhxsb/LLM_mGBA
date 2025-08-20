#!/usr/bin/env python3
"""
Test memory system core functionality without Django dependencies.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(__file__))

def test_core_memory():
    """Test core memory functionality"""
    print("🧠 Testing Core Memory System...")
    
    try:
        # Test memory system creation
        from ai_gba_player.core.graphiti_memory import create_memory_system
        memory_system = create_memory_system()
        
        print(f"✅ Memory system type: {type(memory_system).__name__}")
        
        # Test objective discovery
        obj_id = memory_system.discover_objective(
            description="Test: Find Professor Oak's lab",
            location="Pallet Town (12, 8)",
            category="main",
            priority=8
        )
        print(f"✅ Objective discovered: {obj_id}")
        
        # Test strategy learning
        strat_id = memory_system.learn_strategy(
            situation="talking to professor",
            button_sequence=["A", "A", "A"],
            success=True
        )
        print(f"✅ Strategy learned: {strat_id}")
        
        # Test memory context
        context = memory_system.get_memory_context("test situation")
        print(f"✅ Context generated with {len(context.get('current_objectives', []))} objectives")
        
        # Test completion
        if obj_id:
            memory_system.complete_objective(obj_id, "Pallet Town (12, 8)")
            print("✅ Objective completed")
        
        # Test stats
        stats = memory_system.get_stats()
        print(f"✅ Final stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🧪 Core Memory System Test")
    
    success = test_core_memory()
    
    if success:
        print("\n✅ Core memory system is working!")
        print("🎮 Ready for AI GBA Player integration")
    else:
        print("\n❌ Core memory test failed")
        sys.exit(1)