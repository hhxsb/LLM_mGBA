#!/usr/bin/env python3
"""
Test the global memory service within Django context.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent
AI_GBA_DIR = BASE_DIR / 'ai_gba_player'
sys.path.append(str(BASE_DIR))
sys.path.append(str(AI_GBA_DIR))

# Change to Django project directory
os.chdir(AI_GBA_DIR)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gba_player.settings')

# Setup Django
django.setup()

def test_global_memory_service():
    """Test the global memory service"""
    print("🧪 Testing Global Memory Service...")
    
    try:
        # Test import
        from core.memory_service import (
            get_global_memory_system,
            discover_objective,
            complete_objective,
            learn_strategy,
            get_memory_context,
            get_memory_stats,
            is_memory_system_available
        )
        print("✅ Global memory service imports successfully")
        
        # Test memory system availability
        is_available = is_memory_system_available()
        print(f"✅ Memory system available: {is_available}")
        
        # Test objective discovery
        obj_id = discover_objective(
            description="Test: Find the first gym",
            location="Pallet Town (10, 10)",
            category="main",
            priority=8
        )
        print(f"✅ Objective discovered: {obj_id}")
        
        # Test strategy learning
        strat_id = learn_strategy(
            situation="talking to gym leader",
            button_sequence=["A", "A", "UP", "A"],
            success=True
        )
        print(f"✅ Strategy learned: {strat_id}")
        
        # Test memory context
        context = get_memory_context("test situation")
        print(f"✅ Memory context retrieved with {len(context.get('current_objectives', []))} objectives")
        
        # Test stats
        stats = get_memory_stats()
        print(f"✅ Memory stats: {stats}")
        
        # Test objective completion
        if obj_id:
            success = complete_objective(obj_id, "Viridian City Gym")
            print(f"✅ Objective completed: {success}")
        
        print("\n🎉 Global memory service test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🧪 Testing Global Memory Service with Django...")
    
    success = test_global_memory_service()
    
    if success:
        print("\n✅ Global memory service is working!")
        print("🎮 Ready for AI GBA Player startup")
    else:
        print("\n❌ Global memory service test failed")
        sys.exit(1)