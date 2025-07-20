#!/usr/bin/env python3
"""
Real-time knowledge base monitor for Pokemon Red AI.
Shows current conversation state, character state, and context memory.
"""

import json
import time
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

def monitor_knowledge_file():
    """Monitor the knowledge file for changes and display current state."""
    knowledge_file = "data/knowledge_graph.json"
    last_modified = 0
    
    print("🔍 Pokemon Red AI Knowledge Base Monitor")
    print("=" * 50)
    print(f"Monitoring: {knowledge_file}")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        while True:
            try:
                # Check if file was modified
                if os.path.exists(knowledge_file):
                    current_modified = os.path.getmtime(knowledge_file)
                    
                    if current_modified > last_modified:
                        last_modified = current_modified
                        display_knowledge_state(knowledge_file)
                
                time.sleep(2)  # Check every 2 seconds
                
            except KeyboardInterrupt:
                print("\n👋 Knowledge monitoring stopped")
                break
            except Exception as e:
                print(f"❌ Error monitoring knowledge: {e}")
                time.sleep(5)
    
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")

def display_knowledge_state(knowledge_file):
    """Display current knowledge base state."""
    try:
        with open(knowledge_file, 'r') as f:
            data = json.load(f)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n📊 Knowledge Update [{timestamp}]")
        print("-" * 40)
        
        # Show active goals
        goals = data.get('goals', [])
        active_goals = [g for g in goals if g.get('status') == 'active']
        if active_goals:
            print(f"🎯 Active Goals: {len(active_goals)}")
            for goal in active_goals[:3]:  # Show top 3
                print(f"   - {goal.get('description', 'Unknown goal')}")
        
        # Show locations
        locations = data.get('locations', [])
        if locations:
            print(f"🗺️ Known Locations: {len(locations)}")
            for loc in locations[-3:]:  # Show last 3
                print(f"   - {loc.get('name', 'Unknown location')}")
        
        # Show recent actions
        actions = data.get('action_history', [])
        if actions:
            print(f"📋 Recent Actions: {len(actions)}")
            for action in actions[-2:]:  # Show last 2
                result = action.get('result', 'No result')[:50]
                print(f"   - {action.get('action', 'Unknown')}: {result}...")
        
        # Show game-specific data
        game_data = data.get('game_specific_data', {})
        if game_data:
            print(f"🎮 Game Data Keys: {list(game_data.keys())}")
        
    except Exception as e:
        print(f"❌ Error reading knowledge file: {e}")

def show_current_knowledge_state():
    """Show a one-time snapshot of current knowledge state."""
    knowledge_file = "data/knowledge_graph.json"
    
    if not os.path.exists(knowledge_file):
        print(f"❌ Knowledge file not found: {knowledge_file}")
        print("💡 Start the AI system first with: python start_dual_process.py --show-output")
        return
    
    print("🔍 Current Knowledge Base State")
    print("=" * 50)
    
    display_knowledge_state(knowledge_file)
    
    # Additional detailed view
    try:
        with open(knowledge_file, 'r') as f:
            data = json.load(f)
        
        print(f"\n📈 Detailed Statistics:")
        print(f"   Total Goals: {len(data.get('goals', []))}")
        print(f"   Total Locations: {len(data.get('locations', []))}")
        print(f"   Total Actions: {len(data.get('action_history', []))}")
        print(f"   Game Data Size: {len(str(data.get('game_specific_data', {})))} chars")
        
        # Show file modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(knowledge_file))
        print(f"   Last Updated: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error showing detailed state: {e}")

def main():
    """Main function with command line options."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor Pokemon Red AI Knowledge Base')
    parser.add_argument('--monitor', action='store_true', 
                       help='Monitor knowledge base in real-time')
    parser.add_argument('--show', action='store_true',
                       help='Show current knowledge state once')
    
    args = parser.parse_args()
    
    if args.monitor:
        monitor_knowledge_file()
    elif args.show:
        show_current_knowledge_state()
    else:
        print("🔍 Pokemon Red AI Knowledge Base Inspector")
        print("\nUsage:")
        print("  python monitor_knowledge.py --monitor    # Real-time monitoring")
        print("  python monitor_knowledge.py --show       # Show current state")
        print("\nAlternatively:")
        print("  python knowledge_inspector.py           # Existing detailed inspector")
        print("  python knowledge_web_viewer.py          # Web-based viewer")

if __name__ == '__main__':
    main()