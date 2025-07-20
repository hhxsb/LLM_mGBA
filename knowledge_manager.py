#!/usr/bin/env python3
"""
Interactive Knowledge Manager - CRUD operations for AI's knowledge base
"""
import json
import sys
import time
from datetime import datetime
from knowledge_system import KnowledgeGraph, Goal, Location, FailurePattern, NPCInteraction
import argparse

class KnowledgeManager:
    def __init__(self, knowledge_file="data/knowledge_graph.json"):
        self.kg = KnowledgeGraph(knowledge_file)
        self.changes_made = False
    
    def save_if_changed(self):
        """Save knowledge if changes were made"""
        if self.changes_made:
            self.kg.save_knowledge()
            print("✅ Changes saved to knowledge base")
            self.changes_made = False
    
    # GOALS MANAGEMENT
    def list_goals(self, status_filter=None):
        """List goals, optionally filtered by status"""
        goals = list(self.kg.goals.values())
        
        if status_filter:
            goals = [g for g in goals if g.status == status_filter]
        
        if not goals:
            filter_text = f" with status '{status_filter}'" if status_filter else ""
            print(f"No goals found{filter_text}")
            return []
        
        # Sort by priority (high to low) then by creation time
        goals.sort(key=lambda x: (-x.priority, x.created_time))
        
        print(f"\n🎯 GOALS{f' ({status_filter})' if status_filter else ''}:")
        print("=" * 60)
        
        for i, goal in enumerate(goals, 1):
            created = datetime.fromtimestamp(goal.created_time).strftime("%m-%d %H:%M")
            location = ""
            if goal.location_id and goal.location_id in self.kg.locations:
                location = f" @ {self.kg.locations[goal.location_id].name}"
            
            status_emoji = {
                "active": "🔴",
                "completed": "✅", 
                "failed": "❌",
                "blocked": "🟡"
            }.get(goal.status, "⚪")
            
            print(f"{i:2d}. {status_emoji} [{goal.priority}] {goal.description}")
            print(f"     ID: {goal.id} | Type: {goal.type} | Created: {created}{location}")
            if goal.attempts:
                print(f"     Attempts: {len(goal.attempts)}")
            print()
        
        return goals
    
    def create_goal(self, description, priority=5, goal_type="manual", location_id=None):
        """Create a new goal"""
        goal_id = f"manual_{int(time.time())}"
        
        goal = Goal(
            id=goal_id,
            description=description,
            type=goal_type,
            status="active",
            priority=int(priority),
            location_id=location_id
        )
        
        self.kg.goals[goal_id] = goal
        self.changes_made = True
        
        print(f"✅ Created goal: {description}")
        print(f"   ID: {goal_id}")
        print(f"   Priority: {priority}")
        return goal_id
    
    def update_goal(self, goal_id, **kwargs):
        """Update an existing goal"""
        if goal_id not in self.kg.goals:
            print(f"❌ Goal not found: {goal_id}")
            return False
        
        goal = self.kg.goals[goal_id]
        updated_fields = []
        
        for field, value in kwargs.items():
            if hasattr(goal, field):
                old_value = getattr(goal, field)
                setattr(goal, field, value)
                updated_fields.append(f"{field}: {old_value} → {value}")
        
        if updated_fields:
            self.changes_made = True
            print(f"✅ Updated goal '{goal.description}':")
            for field in updated_fields:
                print(f"   {field}")
        else:
            print("⚠️ No valid fields to update")
        
        return True
    
    def delete_goal(self, goal_id):
        """Delete a goal"""
        if goal_id not in self.kg.goals:
            print(f"❌ Goal not found: {goal_id}")
            return False
        
        goal = self.kg.goals[goal_id]
        del self.kg.goals[goal_id]
        self.changes_made = True
        
        print(f"✅ Deleted goal: {goal.description}")
        return True
    
    def complete_goal(self, goal_id):
        """Mark a goal as completed"""
        return self.update_goal(goal_id, status="completed", completed_time=time.time())
    
    def activate_goal(self, goal_id):
        """Mark a goal as active"""
        return self.update_goal(goal_id, status="active")
    
    def block_goal(self, goal_id, reason=None):
        """Mark a goal as blocked"""
        updates = {"status": "blocked"}
        if reason:
            # Add reason to goal attempts
            if goal_id in self.kg.goals:
                goal = self.kg.goals[goal_id]
                goal.attempts.append({
                    "timestamp": time.time(),
                    "result": f"blocked: {reason}",
                    "success": False
                })
        return self.update_goal(goal_id, **updates)
    
    # LOCATIONS MANAGEMENT
    def list_locations(self):
        """List all discovered locations"""
        if not self.kg.locations:
            print("No locations discovered yet")
            return []
        
        locations = sorted(self.kg.locations.values(), 
                          key=lambda x: x.visited_count, reverse=True)
        
        print("\n📍 LOCATIONS:")
        print("=" * 50)
        
        for i, loc in enumerate(locations, 1):
            last_visit = datetime.fromtimestamp(loc.last_visited).strftime("%H:%M:%S") if loc.last_visited else "Never"
            print(f"{i:2d}. {loc.name} (Map ID: {loc.map_id})")
            print(f"     Position: ({loc.coordinates[0]}, {loc.coordinates[1]})")
            print(f"     Visited: {loc.visited_count} times (last: {last_visit})")
            if loc.npcs:
                print(f"     NPCs: {len(loc.npcs)}")
            if loc.items:
                print(f"     Items: {', '.join(loc.items)}")
            print()
        
        return locations
    
    def update_location(self, map_id, **kwargs):
        """Update location information"""
        if map_id not in self.kg.locations:
            print(f"❌ Location not found: Map ID {map_id}")
            return False
        
        location = self.kg.locations[map_id]
        updated_fields = []
        
        for field, value in kwargs.items():
            if hasattr(location, field):
                old_value = getattr(location, field)
                setattr(location, field, value)
                updated_fields.append(f"{field}: {old_value} → {value}")
        
        if updated_fields:
            self.changes_made = True
            print(f"✅ Updated location '{location.name}':")
            for field in updated_fields:
                print(f"   {field}")
        
        return True
    
    # FAILURE PATTERNS MANAGEMENT
    def list_failure_patterns(self):
        """List learned failure patterns"""
        if not self.kg.failure_patterns:
            print("No failure patterns learned yet")
            return []
        
        patterns = sorted(self.kg.failure_patterns.values(),
                         key=lambda x: x.occurrence_count, reverse=True)
        
        print("\n❌ FAILURE PATTERNS:")
        print("=" * 40)
        
        for i, pattern in enumerate(patterns, 1):
            last_seen = datetime.fromtimestamp(pattern.last_seen).strftime("%H:%M:%S")
            print(f"{i:2d}. Situation: {pattern.situation}")
            print(f"     Failed actions: {', '.join(pattern.failed_actions)}")
            print(f"     Occurrences: {pattern.occurrence_count} (last: {last_seen})")
            if pattern.successful_alternative:
                print(f"     ✅ Alternative: {pattern.successful_alternative}")
            print(f"     ID: {pattern.pattern_id}")
            print()
        
        return patterns
    
    def add_solution_to_pattern(self, pattern_id, solution):
        """Add a successful solution to a failure pattern"""
        if pattern_id not in self.kg.failure_patterns:
            print(f"❌ Pattern not found: {pattern_id}")
            return False
        
        pattern = self.kg.failure_patterns[pattern_id]
        pattern.successful_alternative = solution
        self.changes_made = True
        
        print(f"✅ Added solution to pattern '{pattern.situation}':")
        print(f"   Solution: {solution}")
        return True
    
    def delete_failure_pattern(self, pattern_id):
        """Delete a failure pattern"""
        if pattern_id not in self.kg.failure_patterns:
            print(f"❌ Pattern not found: {pattern_id}")
            return False
        
        pattern = self.kg.failure_patterns[pattern_id]
        del self.kg.failure_patterns[pattern_id]
        self.changes_made = True
        
        print(f"✅ Deleted failure pattern: {pattern.situation}")
        return True
    
    # INTERACTIVE MENU SYSTEM
    def interactive_mode(self):
        """Interactive management mode"""
        print("🛠️ INTERACTIVE KNOWLEDGE MANAGER")
        print("=" * 45)
        
        while True:
            print("\n📋 MAIN MENU:")
            print("1. Goals Management")
            print("2. Locations Management") 
            print("3. Failure Patterns Management")
            print("4. Export Knowledge")
            print("5. Import Knowledge")
            print("6. Save & Exit")
            print("0. Exit without saving")
            
            try:
                choice = input("\n🔍 Select option (0-6): ").strip()
                
                if choice == '0':
                    if self.changes_made:
                        save = input("💾 Save changes before exiting? (y/n): ").lower()
                        if save == 'y':
                            self.save_if_changed()
                    break
                elif choice == '1':
                    self.goals_menu()
                elif choice == '2':
                    self.locations_menu()
                elif choice == '3':
                    self.patterns_menu()
                elif choice == '4':
                    self.export_menu()
                elif choice == '5':
                    self.import_menu()
                elif choice == '6':
                    self.save_if_changed()
                    break
                else:
                    print("❓ Invalid option")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
    
    def goals_menu(self):
        """Goals management submenu"""
        while True:
            print("\n🎯 GOALS MANAGEMENT:")
            print("1. List all goals")
            print("2. List active goals")
            print("3. List completed goals")
            print("4. Create new goal")
            print("5. Update goal")
            print("6. Complete goal")
            print("7. Activate goal")
            print("8. Block goal")
            print("9. Delete goal")
            print("0. Back to main menu")
            
            choice = input("\n🔍 Select option (0-9): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.list_goals()
            elif choice == '2':
                self.list_goals("active")
            elif choice == '3':
                self.list_goals("completed")
            elif choice == '4':
                self.create_goal_interactive()
            elif choice == '5':
                self.update_goal_interactive()
            elif choice == '6':
                self.complete_goal_interactive()
            elif choice == '7':
                self.activate_goal_interactive()
            elif choice == '8':
                self.block_goal_interactive()
            elif choice == '9':
                self.delete_goal_interactive()
            else:
                print("❓ Invalid option")
    
    def create_goal_interactive(self):
        """Interactive goal creation"""
        print("\n📝 CREATE NEW GOAL:")
        description = input("Goal description: ").strip()
        if not description:
            print("❌ Description cannot be empty")
            return
        
        try:
            priority = int(input("Priority (1-10, default 5): ") or "5")
            priority = max(1, min(10, priority))
        except ValueError:
            priority = 5
        
        goal_type = input("Type (manual/main/sub/exploration, default manual): ").strip() or "manual"
        
        # Show available locations
        if self.kg.locations:
            print("\nAvailable locations:")
            for map_id, loc in list(self.kg.locations.items())[:5]:
                print(f"  {map_id}: {loc.name}")
        
        location_input = input("Location ID (optional): ").strip()
        location_id = None
        if location_input:
            try:
                location_id = int(location_input)
                if location_id not in self.kg.locations:
                    print("⚠️ Location ID not found, but will be stored anyway")
            except ValueError:
                print("⚠️ Invalid location ID")
        
        self.create_goal(description, priority, goal_type, location_id)
    
    def update_goal_interactive(self):
        """Interactive goal update"""
        goals = self.list_goals()
        if not goals:
            return
        
        try:
            idx = int(input("\nSelect goal number to update: ")) - 1
            if 0 <= idx < len(goals):
                goal = goals[idx]
                print(f"\nUpdating goal: {goal.description}")
                
                updates = {}
                
                new_desc = input(f"New description (current: {goal.description}): ").strip()
                if new_desc:
                    updates["description"] = new_desc
                
                new_priority = input(f"New priority (current: {goal.priority}): ").strip()
                if new_priority:
                    try:
                        updates["priority"] = int(new_priority)
                    except ValueError:
                        print("⚠️ Invalid priority, skipping")
                
                new_status = input(f"New status (current: {goal.status}): ").strip()
                if new_status:
                    updates["status"] = new_status
                
                if updates:
                    self.update_goal(goal.id, **updates)
                else:
                    print("No updates provided")
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def complete_goal_interactive(self):
        """Interactive goal completion"""
        goals = self.list_goals("active")
        if not goals:
            return
        
        try:
            idx = int(input("\nSelect goal number to complete: ")) - 1
            if 0 <= idx < len(goals):
                self.complete_goal(goals[idx].id)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def activate_goal_interactive(self):
        """Interactive goal activation"""
        goals = self.list_goals()
        if not goals:
            return
        
        try:
            idx = int(input("\nSelect goal number to activate: ")) - 1
            if 0 <= idx < len(goals):
                self.activate_goal(goals[idx].id)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def block_goal_interactive(self):
        """Interactive goal blocking"""
        goals = self.list_goals("active")
        if not goals:
            return
        
        try:
            idx = int(input("\nSelect goal number to block: ")) - 1
            if 0 <= idx < len(goals):
                reason = input("Block reason (optional): ").strip()
                self.block_goal(goals[idx].id, reason if reason else None)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def delete_goal_interactive(self):
        """Interactive goal deletion"""
        goals = self.list_goals()
        if not goals:
            return
        
        try:
            idx = int(input("\nSelect goal number to delete: ")) - 1
            if 0 <= idx < len(goals):
                goal = goals[idx]
                confirm = input(f"Delete '{goal.description}'? (y/n): ").lower()
                if confirm == 'y':
                    self.delete_goal(goal.id)
                else:
                    print("❌ Deletion cancelled")
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def locations_menu(self):
        """Locations management submenu"""
        while True:
            print("\n📍 LOCATIONS MANAGEMENT:")
            print("1. List all locations")
            print("2. Update location")
            print("0. Back to main menu")
            
            choice = input("\n🔍 Select option (0-2): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.list_locations()
            elif choice == '2':
                self.update_location_interactive()
            else:
                print("❓ Invalid option")
    
    def update_location_interactive(self):
        """Interactive location update"""
        locations = self.list_locations()
        if not locations:
            return
        
        try:
            idx = int(input("\nSelect location number to update: ")) - 1
            if 0 <= idx < len(locations):
                location = locations[idx]
                print(f"\nUpdating location: {location.name}")
                
                new_name = input(f"New name (current: {location.name}): ").strip()
                if new_name:
                    self.update_location(location.map_id, name=new_name)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def patterns_menu(self):
        """Failure patterns management submenu"""
        while True:
            print("\n❌ FAILURE PATTERNS MANAGEMENT:")
            print("1. List all patterns")
            print("2. Add solution to pattern")
            print("3. Delete pattern")
            print("0. Back to main menu")
            
            choice = input("\n🔍 Select option (0-3): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.list_failure_patterns()
            elif choice == '2':
                self.add_solution_interactive()
            elif choice == '3':
                self.delete_pattern_interactive()
            else:
                print("❓ Invalid option")
    
    def add_solution_interactive(self):
        """Interactive solution adding"""
        patterns = self.list_failure_patterns()
        if not patterns:
            return
        
        try:
            idx = int(input("\nSelect pattern number to add solution: ")) - 1
            if 0 <= idx < len(patterns):
                pattern = patterns[idx]
                solution = input("Enter successful solution: ").strip()
                if solution:
                    self.add_solution_to_pattern(pattern.pattern_id, solution)
                else:
                    print("❌ Solution cannot be empty")
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def delete_pattern_interactive(self):
        """Interactive pattern deletion"""
        patterns = self.list_failure_patterns()
        if not patterns:
            return
        
        try:
            idx = int(input("\nSelect pattern number to delete: ")) - 1
            if 0 <= idx < len(patterns):
                pattern = patterns[idx]
                confirm = input(f"Delete pattern '{pattern.situation}'? (y/n): ").lower()
                if confirm == 'y':
                    self.delete_failure_pattern(pattern.pattern_id)
                else:
                    print("❌ Deletion cancelled")
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def export_menu(self):
        """Export knowledge"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = input(f"Export filename (default: knowledge_export_{timestamp}.json): ").strip()
        if not filename:
            filename = f"knowledge_export_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                data = {
                    'locations': {k: v.__dict__ for k, v in self.kg.locations.items()},
                    'goals': {k: v.__dict__ for k, v in self.kg.goals.items()},
                    'failure_patterns': {k: v.__dict__ for k, v in self.kg.failure_patterns.items()},
                    'npc_interactions': {k: v.__dict__ for k, v in self.kg.npc_interactions.items()},
                    'action_history': list(self.kg.action_history)
                }
                json.dump(data, f, indent=2, default=str)
            
            print(f"✅ Knowledge exported to {filename}")
        except Exception as e:
            print(f"❌ Export failed: {e}")
    
    def import_menu(self):
        """Import knowledge"""
        filename = input("Import filename: ").strip()
        if not filename:
            print("❌ Filename required")
            return
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            confirm = input(f"This will overwrite current knowledge. Continue? (y/n): ").lower()
            if confirm != 'y':
                print("❌ Import cancelled")
                return
            
            # Reconstruct objects
            if 'locations' in data:
                self.kg.locations = {
                    int(k): Location(**v) for k, v in data['locations'].items()
                }
            if 'goals' in data:
                self.kg.goals = {
                    k: Goal(**v) for k, v in data['goals'].items()
                }
            # Add other imports as needed
            
            self.changes_made = True
            print(f"✅ Knowledge imported from {filename}")
            
        except Exception as e:
            print(f"❌ Import failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Manage AI's knowledge base")
    parser.add_argument("--file", "-f", default="data/knowledge_graph.json", 
                       help="Knowledge file to manage")
    
    # Quick commands
    parser.add_argument("--list-goals", action="store_true", help="List all goals")
    parser.add_argument("--list-active", action="store_true", help="List active goals")
    parser.add_argument("--create-goal", metavar="DESCRIPTION", help="Create a new goal")
    parser.add_argument("--priority", type=int, default=5, help="Priority for new goal (1-10)")
    parser.add_argument("--complete-goal", metavar="GOAL_ID", help="Complete a goal")
    parser.add_argument("--delete-goal", metavar="GOAL_ID", help="Delete a goal")
    
    args = parser.parse_args()
    
    try:
        manager = KnowledgeManager(args.file)
        
        # Handle quick commands
        if args.list_goals:
            manager.list_goals()
        elif args.list_active:
            manager.list_goals("active")
        elif args.create_goal:
            manager.create_goal(args.create_goal, args.priority)
            manager.save_if_changed()
        elif args.complete_goal:
            manager.complete_goal(args.complete_goal)
            manager.save_if_changed()
        elif args.delete_goal:
            manager.delete_goal(args.delete_goal)
            manager.save_if_changed()
        else:
            # Default to interactive mode
            manager.interactive_mode()
            
    except FileNotFoundError:
        print(f"❌ Knowledge file not found: {args.file}")
        print("The AI hasn't started yet, or the file path is incorrect.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()