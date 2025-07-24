#!/usr/bin/env python3
"""
Knowledge system migration utility.
Migrates existing JSON-based knowledge to SQLite storage.
"""

import asyncio
import json
import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.storage_service import StorageService
from core.logging_config import get_logger


class KnowledgeMigrator:
    """Migrates knowledge from JSON files to SQLite database."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("knowledge_migrator")
        self.storage_service = None
        
    async def initialize(self):
        """Initialize the storage service for migration."""
        self.storage_service = StorageService(self.config)
        await self.storage_service.initialize()
        
    async def migrate_knowledge_from_json(self, json_file_path: str) -> Dict[str, Any]:
        """Migrate knowledge data from JSON file to SQLite."""
        
        if not os.path.exists(json_file_path):
            self.logger.warning(f"⚠️ JSON knowledge file not found: {json_file_path}")
            return {"migrated": 0, "skipped": 0, "errors": 0}
        
        self.logger.info(f"📚 Starting knowledge migration from {json_file_path}")
        
        try:
            # Load JSON knowledge data
            with open(json_file_path, 'r') as f:
                json_data = json.load(f)
            
            self.logger.info(f"📖 Loaded JSON knowledge: {len(json_data)} top-level entries")
            
            # Start a migration session
            session_id = await self.storage_service.start_session(
                game_name=self.config.get('game', 'pokemon_red'),
                player_name=f"MIGRATION_{int(time.time())}"
            )
            
            migration_stats = {
                "migrated": 0,
                "skipped": 0, 
                "errors": 0,
                "session_id": session_id
            }
            
            # Migrate different knowledge categories
            if 'conversation_state' in json_data:
                await self._migrate_conversation_state(json_data['conversation_state'], migration_stats)
                
            if 'character_state' in json_data:
                await self._migrate_character_state(json_data['character_state'], migration_stats)
                
            if 'dialogue_records' in json_data:
                await self._migrate_dialogue_records(json_data['dialogue_records'], migration_stats)
                
            if 'context_memory' in json_data:
                await self._migrate_context_memory(json_data['context_memory'], migration_stats)
                
            if 'goals' in json_data:
                await self._migrate_goals(json_data['goals'], migration_stats)
                
            if 'locations' in json_data:
                await self._migrate_locations(json_data['locations'], migration_stats)
                
            if 'tutorial_progress' in json_data:
                await self._migrate_tutorial_progress(json_data['tutorial_progress'], migration_stats)
            
            # Close migration session
            await self.storage_service.close_current_session("migration_completed")
            
            self.logger.info(f"✅ Migration completed: {migration_stats['migrated']} migrated, {migration_stats['errors']} errors")
            return migration_stats
            
        except Exception as e:
            self.logger.error(f"❌ Migration failed: {e}")
            return {"migrated": 0, "skipped": 0, "errors": 1, "error": str(e)}
    
    async def _migrate_conversation_state(self, conversation_data: Dict[str, Any], stats: Dict[str, Any]):
        """Migrate conversation state data."""
        try:
            knowledge_data = {
                'knowledge_type': 'conversation',
                'category': 'current_state',
                'data': conversation_data,
                'priority_score': 8,
                'related_npc': conversation_data.get('current_npc'),
                'related_map_name': None  # Could be extracted if available
            }
            
            await self.storage_service.update_knowledge_base([knowledge_data])
            stats['migrated'] += 1
            self.logger.debug("📞 Migrated conversation state")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to migrate conversation state: {e}")
            stats['errors'] += 1
    
    async def _migrate_character_state(self, character_data: Dict[str, Any], stats: Dict[str, Any]):
        """Migrate character state data."""
        try:
            knowledge_data = {
                'knowledge_type': 'character',
                'category': 'identity',
                'data': character_data,
                'priority_score': 9,  # High priority for character identity
            }
            
            await self.storage_service.update_knowledge_base([knowledge_data])
            stats['migrated'] += 1
            self.logger.debug("👤 Migrated character state")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to migrate character state: {e}")
            stats['errors'] += 1
    
    async def _migrate_dialogue_records(self, dialogue_data: List[Dict[str, Any]], stats: Dict[str, Any]):
        """Migrate dialogue records."""
        try:
            knowledge_updates = []
            
            for i, dialogue in enumerate(dialogue_data):
                knowledge_data = {
                    'knowledge_type': 'dialogue',
                    'category': 'npc_interaction',
                    'data': dialogue,
                    'priority_score': 7,
                    'related_npc': dialogue.get('npc_name'),
                    'related_map_name': None  # Could extract from location_id if mapping available
                }
                knowledge_updates.append(knowledge_data)
            
            if knowledge_updates:
                await self.storage_service.update_knowledge_base(knowledge_updates)
                stats['migrated'] += len(knowledge_updates)
                self.logger.debug(f"💬 Migrated {len(knowledge_updates)} dialogue records")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to migrate dialogue records: {e}")
            stats['errors'] += 1
    
    async def _migrate_context_memory(self, context_data: List[Dict[str, Any]], stats: Dict[str, Any]):
        """Migrate context memory entries."""
        try:
            knowledge_updates = []
            
            for entry in context_data:
                knowledge_data = {
                    'knowledge_type': 'context',
                    'category': entry.get('context_type', 'general'),
                    'data': entry,
                    'priority_score': entry.get('priority', 5),
                }
                knowledge_updates.append(knowledge_data)
            
            if knowledge_updates:
                await self.storage_service.update_knowledge_base(knowledge_updates)
                stats['migrated'] += len(knowledge_updates)
                self.logger.debug(f"🧠 Migrated {len(knowledge_updates)} context memory entries")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to migrate context memory: {e}")
            stats['errors'] += 1
    
    async def _migrate_goals(self, goals_data: List[Dict[str, Any]], stats: Dict[str, Any]):
        """Migrate game goals."""
        try:
            knowledge_updates = []
            
            for goal in goals_data:
                knowledge_data = {
                    'knowledge_type': 'goal',
                    'category': goal.get('type', 'main'),
                    'data': goal,
                    'priority_score': goal.get('priority', 5),
                }
                knowledge_updates.append(knowledge_data)
            
            if knowledge_updates:
                await self.storage_service.update_knowledge_base(knowledge_updates)
                stats['migrated'] += len(knowledge_updates)
                self.logger.debug(f"🎯 Migrated {len(knowledge_updates)} goals")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to migrate goals: {e}")
            stats['errors'] += 1
    
    async def _migrate_locations(self, locations_data: List[Dict[str, Any]], stats: Dict[str, Any]):
        """Migrate location information."""
        try:
            knowledge_updates = []
            
            for location in locations_data:
                knowledge_data = {
                    'knowledge_type': 'location',
                    'category': location.get('map_type', 'unknown'),
                    'data': location,
                    'priority_score': 6,
                    'related_map_name': location.get('name')
                }
                knowledge_updates.append(knowledge_data)
            
            if knowledge_updates:
                await self.storage_service.update_knowledge_base(knowledge_updates)
                stats['migrated'] += len(knowledge_updates)
                self.logger.debug(f"🗺️ Migrated {len(knowledge_updates)} locations")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to migrate locations: {e}")
            stats['errors'] += 1
    
    async def _migrate_tutorial_progress(self, tutorial_data: Any, stats: Dict[str, Any]):
        """Migrate tutorial progress data."""
        try:
            knowledge_data = {
                'knowledge_type': 'tutorial',
                'category': 'progress',
                'data': {
                    'tutorial_progress': tutorial_data,
                    'migrated_at': datetime.now().isoformat()
                },
                'priority_score': 8,  # High priority for tutorial state
            }
            
            await self.storage_service.update_knowledge_base([knowledge_data])
            stats['migrated'] += 1
            self.logger.debug("📚 Migrated tutorial progress")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to migrate tutorial progress: {e}")
            stats['errors'] += 1
    
    async def create_backup_of_json(self, json_file_path: str) -> str:
        """Create a backup of the JSON file before migration."""
        if not os.path.exists(json_file_path):
            return ""
        
        timestamp = int(time.time())
        backup_path = f"{json_file_path}.backup_{timestamp}"
        
        try:
            with open(json_file_path, 'r') as src:
                with open(backup_path, 'w') as dst:
                    dst.write(src.read())
            
            self.logger.info(f"📋 Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create backup: {e}")
            return ""
    
    async def verify_migration(self, original_json_path: str) -> Dict[str, Any]:
        """Verify that migration was successful by comparing data."""
        # This would implement verification logic
        # For now, return basic verification
        
        verification_results = {
            "json_exists": os.path.exists(original_json_path),
            "database_accessible": self.storage_service is not None,
            "verification_time": datetime.now().isoformat()
        }
        
        self.logger.info(f"✅ Migration verification: {verification_results}")
        return verification_results


async def migrate_knowledge_system(config: Dict[str, Any]) -> Dict[str, Any]:
    """Main migration function."""
    
    migrator = KnowledgeMigrator(config)
    await migrator.initialize()
    
    # Get knowledge file path from config
    json_file = config.get('knowledge_file', 'data/knowledge_graph.json')
    
    # Create backup
    backup_path = await migrator.create_backup_of_json(json_file)
    
    # Perform migration
    migration_stats = await migrator.migrate_knowledge_from_json(json_file)
    migration_stats['backup_path'] = backup_path
    
    # Verify migration
    verification = await migrator.verify_migration(json_file)
    migration_stats['verification'] = verification
    
    return migration_stats


if __name__ == "__main__":
    """Run migration as standalone script."""
    
    import sys
    import json as json_module
    
    # Load config
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config_emulator.json"
    
    try:
        with open(config_path, 'r') as f:
            config = json_module.load(f)
        
        # Enable storage for migration
        if 'storage' not in config:
            config['storage'] = {'enabled': True, 'database_path': 'data/pokemon_ai.db'}
        
        # Run migration
        result = asyncio.run(migrate_knowledge_system(config))
        
        print("🎉 Knowledge Migration Results:")
        print(json_module.dumps(result, indent=2))
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)