#!/usr/bin/env python3
"""
Fix Knowledge Data - Repair any issues with the knowledge base
"""
import json
import os
import time
from knowledge_system import KnowledgeGraph, Goal

def fix_knowledge_data(knowledge_file="data/knowledge_graph.json"):
    """Fix any issues with the knowledge data"""
    print("🔧 Checking and fixing knowledge data...")
    
    try:
        kg = KnowledgeGraph(knowledge_file)
        
        # Check if we have any goals
        print(f"📊 Current status:")
        print(f"   Goals: {len(kg.goals)}")
        print(f"   Locations: {len(kg.locations)}")
        print(f"   Patterns: {len(kg.failure_patterns)}")
        
        # Fix goals without proper IDs
        fixed_count = 0
        for goal_id, goal in kg.goals.items():
            if not hasattr(goal, 'id') or not goal.id:
                goal.id = goal_id
                fixed_count += 1
                print(f"✅ Fixed goal ID: {goal_id}")
        
        # Add some default goals if none exist
        if len(kg.goals) == 0:
            print("📝 No goals found, creating default goals...")
            
            default_goals = [
                ("Enter player name as GEMINI", 10, "setup"),
                ("Exit starting house", 9, "main"),
                ("Get first Pokemon", 8, "main"),
                ("Reach first gym", 7, "main"),
                ("Explore the world", 5, "exploration")
            ]
            
            for desc, priority, goal_type in default_goals:
                goal_id = f"default_{int(time.time())}_{len(kg.goals)}"
                goal = Goal(
                    id=goal_id,
                    description=desc,
                    type=goal_type,
                    status="active",
                    priority=priority
                )
                kg.goals[goal_id] = goal
                print(f"➕ Created default goal: {desc}")
        
        # Save the fixes
        kg.save_knowledge()
        
        if fixed_count > 0:
            print(f"✅ Fixed {fixed_count} goals")
        
        print(f"💾 Knowledge data saved to {knowledge_file}")
        
        # Verify the data
        print("\n🔍 Verification:")
        for goal_id, goal in list(kg.goals.items())[:5]:  # Show first 5 goals
            print(f"   Goal ID: '{goal_id}' → Description: '{goal.description}'")
        
        print(f"\n✅ Knowledge data is ready!")
        
    except FileNotFoundError:
        print(f"⚠️ Knowledge file not found: {knowledge_file}")
        print("Creating new knowledge base with default goals...")
        
        # Create new knowledge base
        os.makedirs(os.path.dirname(knowledge_file), exist_ok=True)
        kg = KnowledgeGraph(knowledge_file)
        
        # The knowledge system will automatically create default goals
        print(f"✅ New knowledge base created at {knowledge_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    fix_knowledge_data()