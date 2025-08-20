#!/usr/bin/env python3
"""
Simple test to verify Django startup and memory system initialization
"""

import os
import sys
import django
from django.conf import settings

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gba_player.settings')

def test_django_startup():
    """Test Django startup and memory system"""
    print("🧪 Testing Django startup with memory system...")
    
    try:
        # Initialize Django
        django.setup()
        print("✅ Django setup successful")
        
        # Test memory system import
        from core.memory_service import get_global_memory_system, is_memory_system_available
        print("✅ Memory service imports successful")
        
        # Test memory system availability
        available = is_memory_system_available()
        print(f"✅ Memory system available: {available}")
        
        # Get memory system
        memory_system = get_global_memory_system()
        if memory_system:
            print(f"✅ Memory system type: {type(memory_system).__name__}")
            
            # Test basic functionality
            stats = memory_system.get_stats()
            print(f"✅ Memory stats: {stats}")
        else:
            print("❌ Memory system is None")
        
        print("\n🎉 Django startup test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Django startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_django_startup()
    sys.exit(0 if success else 1)