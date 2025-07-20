#!/usr/bin/env python3
"""
Knowledge Inspector - Tool to examine the AI's learned knowledge
"""
import json
import sys
from datetime import datetime
from knowledge_system import KnowledgeGraph
import argparse

class KnowledgeInspector:
    def __init__(self, knowledge_file="data/knowledge_graph.json"):
        self.kg = KnowledgeGraph(knowledge_file)
    
    def show_summary(self):
        """Show high-level summary of knowledge"""
        print("🧠 AI KNOWLEDGE SUMMARY")
        print("=" * 50)
        print(f"📍 Locations discovered: {len(self.kg.locations)}")
        print(f"🎯 Goals tracked: {len(self.kg.goals)}")
        print(f"❌ Failure patterns learned: {len(self.kg.failure_patterns)}")
        print(f"👥 NPC interactions: {len(self.kg.npc_interactions)}")
        print(f"📝 Recent actions: {len(self.kg.action_history)}")
        print()
    
    def show_locations(self, detailed=False):
        """Show discovered locations"""
        print("📍 DISCOVERED LOCATIONS")
        print("=" * 30)
        
        if not self.kg.locations:
            print("No locations discovered yet.")
            return
        
        # Sort by visit count
        sorted_locations = sorted(self.kg.locations.values(), 
                                key=lambda x: x.visited_count, reverse=True)
        
        for loc in sorted_locations:
            last_visit = datetime.fromtimestamp(loc.last_visited).strftime("%H:%M:%S") if loc.last_visited else "Never"
            print(f"🗺️  {loc.name} (Map ID: {loc.map_id})")
            print(f"   📍 Position: ({loc.coordinates[0]}, {loc.coordinates[1]})")
            print(f"   🔄 Visited: {loc.visited_count} times (last: {last_visit})")
            
            if detailed:
                if loc.npcs:
                    print(f"   👥 NPCs: {len(loc.npcs)}")
                if loc.items:
                    print(f"   💎 Items: {', '.join(loc.items)}")
                if loc.connections:
                    print(f"   🔗 Connections: {loc.connections}")
            print()
    
    def show_goals(self):
        """Show current goals"""
        print("🎯 CURRENT GOALS")
        print("=" * 20)
        
        if not self.kg.goals:
            print("No goals set yet.")
            return
        
        # Group by status
        by_status = {}
        for goal in self.kg.goals.values():
            if goal.status not in by_status:
                by_status[goal.status] = []
            by_status[goal.status].append(goal)
        
        # Show active goals first
        for status in ["active", "blocked", "completed", "failed"]:
            if status in by_status:
                print(f"\n📋 {status.upper()} GOALS:")
                goals = sorted(by_status[status], key=lambda x: x.priority, reverse=True)
                for goal in goals:
                    created = datetime.fromtimestamp(goal.created_time).strftime("%m-%d %H:%M")
                    print(f"   🎯 [{goal.priority}] {goal.description}")
                    print(f"      📅 Created: {created} | Type: {goal.type}")
                    if goal.location_id:
                        loc_name = self.kg.locations.get(goal.location_id, {}).name if goal.location_id in self.kg.locations else f"Map {goal.location_id}"
                        print(f"      📍 Location: {loc_name}")
                    if goal.attempts:
                        print(f"      🔄 Attempts: {len(goal.attempts)}")
                    print()
    
    def show_failures(self):
        """Show learned failure patterns"""
        print("❌ LEARNED FAILURE PATTERNS")
        print("=" * 35)
        
        if not self.kg.failure_patterns:
            print("No failure patterns learned yet.")
            return
        
        # Sort by occurrence count
        patterns = sorted(self.kg.failure_patterns.values(), 
                         key=lambda x: x.occurrence_count, reverse=True)
        
        for pattern in patterns:
            last_seen = datetime.fromtimestamp(pattern.last_seen).strftime("%H:%M:%S")
            print(f"🚫 Situation: {pattern.situation}")
            print(f"   ❌ Failed actions: {', '.join(pattern.failed_actions)}")
            print(f"   🔄 Occurred: {pattern.occurrence_count} times (last: {last_seen})")
            if pattern.successful_alternative:
                print(f"   ✅ Alternative found: {pattern.successful_alternative}")
            print()
    
    def show_recent_actions(self, limit=20):
        """Show recent action history"""
        print(f"📝 RECENT ACTIONS (last {limit})")
        print("=" * 30)
        
        if not self.kg.action_history:
            print("No actions recorded yet.")
            return
        
        recent = list(self.kg.action_history)[-limit:]
        
        for i, action in enumerate(reversed(recent), 1):
            timestamp = datetime.fromtimestamp(action["timestamp"]).strftime("%H:%M:%S")
            status = "✅" if action["success"] else "❌"
            location = self.kg.locations.get(action["location"], {}).name if action["location"] in self.kg.locations else f"Map {action['location']}"
            
            print(f"{i:2d}. [{timestamp}] {status} {action['action']} at {location}")
            if action["result"]:
                print(f"     💭 {action['result'][:80]}...")
            print()
    
    def show_npcs(self):
        """Show NPC interaction history"""
        print("👥 NPC INTERACTIONS")
        print("=" * 25)
        
        if not self.kg.npc_interactions:
            print("No NPC interactions recorded yet.")
            return
        
        for npc in self.kg.npc_interactions.values():
            location = self.kg.locations.get(npc.location_id, {}).name if npc.location_id in self.kg.locations else f"Map {npc.location_id}"
            last_interaction = datetime.fromtimestamp(npc.last_interaction).strftime("%H:%M:%S") if npc.last_interaction else "Never"
            
            print(f"👤 {npc.name or npc.npc_id}")
            print(f"   📍 Location: {location} at ({npc.position[0]}, {npc.position[1]})")
            print(f"   💬 Interactions: {npc.interaction_count} (last: {last_interaction})")
            if npc.items_given:
                print(f"   🎁 Items given: {', '.join(npc.items_given)}")
            if npc.quests_received:
                print(f"   📜 Quests: {', '.join(npc.quests_received)}")
            print()
    
    def export_json(self, filename=None):
        """Export knowledge to a readable JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"knowledge_export_{timestamp}.json"
        
        export_data = {
            "export_time": datetime.now().isoformat(),
            "summary": {
                "locations_count": len(self.kg.locations),
                "goals_count": len(self.kg.goals),
                "failure_patterns_count": len(self.kg.failure_patterns),
                "npc_interactions_count": len(self.kg.npc_interactions),
                "actions_count": len(self.kg.action_history)
            },
            "locations": {k: {
                "name": v.name,
                "coordinates": v.coordinates,
                "visited_count": v.visited_count,
                "npcs_count": len(v.npcs),
                "items": v.items
            } for k, v in self.kg.locations.items()},
            "goals": {k: {
                "description": v.description,
                "type": v.type,
                "status": v.status,
                "priority": v.priority,
                "attempts_count": len(v.attempts)
            } for k, v in self.kg.goals.items()},
            "failure_patterns": {k: {
                "situation": v.situation,
                "failed_actions": v.failed_actions,
                "occurrence_count": v.occurrence_count,
                "has_alternative": bool(v.successful_alternative)
            } for k, v in self.kg.failure_patterns.items()}
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✅ Knowledge exported to {filename}")
    
    def interactive_mode(self):
        """Interactive inspection mode"""
        print("🔍 INTERACTIVE KNOWLEDGE INSPECTOR")
        print("=" * 40)
        print("Commands:")
        print("  s  - Summary")
        print("  l  - Locations")
        print("  ld - Locations (detailed)")
        print("  g  - Goals")
        print("  f  - Failure patterns")
        print("  a  - Recent actions")
        print("  n  - NPC interactions")
        print("  e  - Export to JSON")
        print("  q  - Quit")
        print()
        
        while True:
            try:
                cmd = input("🔍 Enter command: ").strip().lower()
                print()
                
                if cmd == 'q':
                    break
                elif cmd == 's':
                    self.show_summary()
                elif cmd == 'l':
                    self.show_locations()
                elif cmd == 'ld':
                    self.show_locations(detailed=True)
                elif cmd == 'g':
                    self.show_goals()
                elif cmd == 'f':
                    self.show_failures()
                elif cmd == 'a':
                    self.show_recent_actions()
                elif cmd == 'n':
                    self.show_npcs()
                elif cmd == 'e':
                    self.export_json()
                else:
                    print("❓ Unknown command. Try 's', 'l', 'g', 'f', 'a', 'n', 'e', or 'q'")
                
                print()
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break

def main():
    parser = argparse.ArgumentParser(description="Inspect AI's learned knowledge")
    parser.add_argument("--file", "-f", default="data/knowledge_graph.json", 
                       help="Knowledge file to inspect")
    parser.add_argument("--summary", "-s", action="store_true", 
                       help="Show summary and exit")
    parser.add_argument("--locations", "-l", action="store_true", 
                       help="Show locations and exit")
    parser.add_argument("--goals", "-g", action="store_true", 
                       help="Show goals and exit")
    parser.add_argument("--failures", "-F", action="store_true", 
                       help="Show failure patterns and exit")
    parser.add_argument("--actions", "-a", action="store_true", 
                       help="Show recent actions and exit")
    parser.add_argument("--export", "-e", metavar="FILE", 
                       help="Export knowledge to JSON file")
    
    args = parser.parse_args()
    
    try:
        inspector = KnowledgeInspector(args.file)
        
        # Check if knowledge file exists and has data
        if not inspector.kg.locations and not inspector.kg.goals:
            print("⚠️ No knowledge data found. The AI hasn't started learning yet.")
            return
        
        # Handle specific commands
        if args.summary:
            inspector.show_summary()
        elif args.locations:
            inspector.show_locations(detailed=True)
        elif args.goals:
            inspector.show_goals()
        elif args.failures:
            inspector.show_failures()
        elif args.actions:
            inspector.show_recent_actions()
        elif args.export:
            inspector.export_json(args.export)
        else:
            # Default to interactive mode
            inspector.interactive_mode()
            
    except FileNotFoundError:
        print(f"❌ Knowledge file not found: {args.file}")
        print("The AI hasn't started learning yet, or the file path is incorrect.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()