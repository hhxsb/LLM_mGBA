from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os
import json
from dashboard.models import (
    Configuration, Process, ProcessStatus, ChatMessage, MessageType,
    SystemLog, SystemStats, ManagedFile, ROMConfiguration
)


class ConfigurationModelTest(TestCase):
    """Test Configuration model with proper encapsulation testing"""
    
    def test_singleton_behavior(self):
        """Test that Configuration enforces singleton pattern"""
        config1 = Configuration.get_config()
        config2 = Configuration.get_config()
        self.assertEqual(config1.id, config2.id)
    
    def test_default_configuration(self):
        """Test default configuration values are properly set"""
        config = Configuration.get_config()
        self.assertEqual(config.llm_provider, 'google')
        self.assertEqual(config.decision_cooldown, 5)
        self.assertEqual(config.port, 8888)
        self.assertEqual(config.host, '127.0.0.1')
        self.assertIsInstance(config.providers, dict)
        self.assertIn('google', config.providers)
        self.assertIn('openai', config.providers)
        self.assertIn('anthropic', config.providers)
    
    def test_to_dict_method(self):
        """Test configuration serialization"""
        config = Configuration.get_config()
        config_dict = config.to_dict()
        
        # Test required fields are present
        required_fields = [
            'game', 'llm_provider', 'providers', 'host', 'port',
            'decision_cooldown', 'debug_mode', 'capture_system'
        ]
        for field in required_fields:
            self.assertIn(field, config_dict)
            
        # Test complex fields are serialized correctly
        self.assertIsInstance(config_dict['providers'], dict)
        self.assertIsInstance(config_dict['capture_system'], dict)
        self.assertIsInstance(config_dict['dashboard'], dict)
    
    def test_providers_structure(self):
        """Test providers configuration structure"""
        config = Configuration.get_config()
        providers = config.providers
        
        # Test Google provider defaults
        self.assertIn('google', providers)
        google_config = providers['google']
        self.assertIn('api_key', google_config)
        self.assertIn('model_name', google_config)
        self.assertEqual(google_config['model_name'], 'gemini-2.5-pro')
        self.assertEqual(google_config['max_tokens'], 65536)
        
        # Test OpenAI provider defaults
        self.assertIn('openai', providers)
        openai_config = providers['openai']
        self.assertEqual(openai_config['model_name'], 'gpt-4')
        self.assertEqual(openai_config['max_tokens'], 1024)
    
    def test_singleton_enforcement(self):
        """Test that only one Configuration can exist"""
        # Get the first config
        config1 = Configuration.get_config()
        
        # Try to create another one manually
        with self.assertRaises(ValueError):
            Configuration.objects.create(name="Another Config")
    
    def test_game_detection_fields(self):
        """Test game detection and override fields"""
        config = Configuration.get_config()
        config.game_override = 'pokemon_sapphire'
        config.detected_game = 'pokemon_red'
        config.detection_source = 'manual'
        config.save()
        
        # Reload from database
        config.refresh_from_db()
        self.assertEqual(config.game_override, 'pokemon_sapphire')
        self.assertEqual(config.detected_game, 'pokemon_red')
        self.assertEqual(config.detection_source, 'manual')
        
    def test_complex_json_fields(self):
        """Test complex JSON field handling"""
        config = Configuration.get_config()
        
        # Test capture_system JSON field
        self.assertIsInstance(config.capture_system, dict)
        self.assertIn('type', config.capture_system)
        self.assertIn('frame_enhancement', config.capture_system)
        
        # Test dashboard JSON field
        self.assertIsInstance(config.dashboard, dict)
        self.assertIn('enabled', config.dashboard)
        self.assertIn('theme', config.dashboard)
        self.assertEqual(config.dashboard['theme'], 'pokemon')
    
    def test_file_path_defaults(self):
        """Test default file paths are set correctly"""
        config = Configuration.get_config()
        self.assertEqual(config.notepad_path, 'notepad.txt')
        self.assertEqual(config.screenshot_path, 'data/screenshots/screenshot.png')
        self.assertEqual(config.prompt_template_path, 'data/prompt_template.txt')
    
    @classmethod
    def get_default_config_completeness(cls):
        """Test that get_default_config returns all expected fields"""
        defaults = Configuration.get_default_config()
        
        expected_top_level_keys = [
            'game', 'llm_provider', 'providers', 'host', 'port',
            'decision_cooldown', 'debug_mode', 'capture_system',
            'dashboard', 'storage', 'dual_process_mode', 'unified_service'
        ]
        
        for key in expected_top_level_keys:
            cls.assertIn(key, defaults)


class ProcessModelTest(TestCase):
    """Test Process model functionality"""
    
    def setUp(self):
        self.process_data = {
            'name': 'test_ai_service',
            'status': ProcessStatus.RUNNING,
            'pid': 12345,
            'port': 8888,
            'last_error': 'Test error message'
        }
    
    def test_process_creation(self):
        """Test process model creation"""
        process = Process.objects.create(**self.process_data)
        self.assertEqual(process.name, 'test_ai_service')
        self.assertEqual(process.status, ProcessStatus.RUNNING)
        self.assertEqual(process.pid, 12345)
        self.assertEqual(process.port, 8888)
        self.assertEqual(process.last_error, 'Test error message')
        self.assertIsNotNone(process.created_at)
        self.assertIsNotNone(process.updated_at)
    
    def test_process_status_choices(self):
        """Test process status enum values"""
        valid_statuses = [
            ProcessStatus.STOPPED,
            ProcessStatus.STARTING, 
            ProcessStatus.RUNNING,
            ProcessStatus.ERROR
        ]
        
        for status in valid_statuses:
            process = Process.objects.create(
                name=f'test_service_{status}',
                status=status
            )
            self.assertEqual(process.status, status)
    
    def test_process_string_representation(self):
        """Test process __str__ method"""
        process = Process.objects.create(**self.process_data)
        expected = f"{self.process_data['name']} ({self.process_data['status']})"
        self.assertEqual(str(process), expected)
    
    def test_process_unique_name_constraint(self):
        """Test that process names must be unique"""
        Process.objects.create(name='unique_service', status=ProcessStatus.RUNNING)
        
        # Should raise IntegrityError for duplicate name
        with self.assertRaises(Exception):  # Django will raise IntegrityError
            Process.objects.create(name='unique_service', status=ProcessStatus.STOPPED)
    
    def test_process_optional_fields(self):
        """Test process with optional fields as None"""
        process = Process.objects.create(
            name='minimal_service',
            status=ProcessStatus.STOPPED
            # pid and port are None
        )
        self.assertEqual(process.name, 'minimal_service')
        self.assertEqual(process.status, ProcessStatus.STOPPED)
        self.assertIsNone(process.pid)
        self.assertIsNone(process.port)
        self.assertEqual(process.last_error, '')  # Default empty string


class ChatMessageModelTest(TestCase):
    """Test ChatMessage model functionality"""
    
    def setUp(self):
        self.message_data = {
            'message_id': 'test_msg_001',
            'message_type': MessageType.RESPONSE,
            'source': 'ai_service',
            'content': {'text': 'Test message'},
            'timestamp': 1640995200.0,  # 2022-01-01 00:00:00 UTC
            'sequence': 1
        }
    
    def test_message_creation(self):
        """Test chat message creation"""
        message = ChatMessage.objects.create(**self.message_data)
        self.assertEqual(message.message_id, 'test_msg_001')
        self.assertEqual(message.message_type, MessageType.RESPONSE)
        self.assertEqual(message.source, 'ai_service')
        self.assertIsInstance(message.content, dict)
    
    def test_message_ordering(self):
        """Test messages are ordered by timestamp descending"""
        # Create messages with different timestamps
        msg1 = ChatMessage.objects.create(
            message_id='msg1',
            message_type=MessageType.SYSTEM,
            source='test',
            content={},
            timestamp=1000.0
        )
        msg2 = ChatMessage.objects.create(
            message_id='msg2', 
            message_type=MessageType.SYSTEM,
            source='test',
            content={},
            timestamp=2000.0
        )
        
        # Should be ordered by newest first
        messages = list(ChatMessage.objects.all())
        self.assertEqual(messages[0].message_id, 'msg2')
        self.assertEqual(messages[1].message_id, 'msg1')
    
    def test_message_type_choices(self):
        """Test message type enum values"""
        valid_types = [
            MessageType.GIF,
            MessageType.SCREENSHOTS,
            MessageType.RESPONSE,
            MessageType.ACTION,
            MessageType.SYSTEM
        ]
        
        for msg_type in valid_types:
            message = ChatMessage.objects.create(
                message_id=f'test_{msg_type}',
                message_type=msg_type,
                source='test',
                content={},
                timestamp=1640995200.0
            )
            self.assertEqual(message.message_type, msg_type)


class SystemLogModelTest(TestCase):
    """Test SystemLog model functionality"""
    
    def setUp(self):
        self.log_data = {
            'process_name': 'ai_game_service',
            'level': 'INFO',
            'message': 'Test log message',
            'timestamp': 1640995200.0
        }
    
    def test_system_log_creation(self):
        """Test system log creation"""
        log = SystemLog.objects.create(**self.log_data)
        self.assertEqual(log.process_name, 'ai_game_service')
        self.assertEqual(log.level, 'INFO')
        self.assertEqual(log.message, 'Test log message')
        self.assertEqual(log.timestamp, 1640995200.0)
        self.assertIsNotNone(log.created_at)
    
    def test_system_log_ordering(self):
        """Test logs are ordered by timestamp descending"""
        log1 = SystemLog.objects.create(
            process_name='service1',
            level='INFO',
            message='First message',
            timestamp=1000.0
        )
        log2 = SystemLog.objects.create(
            process_name='service2',
            level='ERROR',
            message='Second message',
            timestamp=2000.0
        )
        
        logs = list(SystemLog.objects.all())
        self.assertEqual(logs[0].message, 'Second message')  # Newer first
        self.assertEqual(logs[1].message, 'First message')   # Older second
    
    def test_system_log_string_representation(self):
        """Test SystemLog __str__ method"""
        log = SystemLog.objects.create(**self.log_data)
        str_repr = str(log)
        self.assertIn('INFO', str_repr)
        self.assertIn('ai_game_service', str_repr)
        self.assertIn('Test log message', str_repr)


class SystemStatsModelTest(TestCase):
    """Test SystemStats model functionality"""
    
    def setUp(self):
        self.stats_data = {
            'uptime': 3600.5,  # 1 hour uptime
            'memory_usage': {
                'total': 8192,
                'used': 4096,
                'available': 4096,
                'percent': 50.0
            },
            'active_connections': 5,
            'message_count': 150,
            'timestamp': 1640995200.0
        }
    
    def test_system_stats_creation(self):
        """Test system stats creation"""
        stats = SystemStats.objects.create(**self.stats_data)
        self.assertEqual(stats.uptime, 3600.5)
        self.assertEqual(stats.active_connections, 5)
        self.assertEqual(stats.message_count, 150)
        self.assertEqual(stats.timestamp, 1640995200.0)
        
        # Test JSON field
        self.assertIsInstance(stats.memory_usage, dict)
        self.assertEqual(stats.memory_usage['total'], 8192)
        self.assertEqual(stats.memory_usage['percent'], 50.0)
    
    def test_system_stats_ordering(self):
        """Test stats are ordered by timestamp descending"""
        stats1 = SystemStats.objects.create(
            uptime=100.0,
            memory_usage={'used': 1000},
            timestamp=1000.0
        )
        stats2 = SystemStats.objects.create(
            uptime=200.0,
            memory_usage={'used': 2000},
            timestamp=2000.0
        )
        
        stats_list = list(SystemStats.objects.all())
        self.assertEqual(stats_list[0].uptime, 200.0)  # Newer first
        self.assertEqual(stats_list[1].uptime, 100.0)  # Older second


class ManagedFileModelTest(TestCase):
    """Test ManagedFile model functionality"""
    
    def setUp(self):
        self.file_data = {
            'file_hash': 'a' * 64,  # 64-character SHA-256 hash
            'original_name': 'pokemon_sapphire.gba',
            'file_type': 'rom',
            'file_size': 16777216,  # 16MB
            'stored_path': '/media/roms/a' + 'a' * 63 + '.gba',
            'reference_count': 0
        }
    
    def test_managed_file_creation(self):
        """Test managed file creation"""
        file = ManagedFile.objects.create(**self.file_data)
        self.assertEqual(file.file_hash, 'a' * 64)
        self.assertEqual(file.original_name, 'pokemon_sapphire.gba')
        self.assertEqual(file.file_type, 'rom')
        self.assertEqual(file.file_size, 16777216)
        self.assertEqual(file.reference_count, 0)
        self.assertIsNotNone(file.uploaded_at)
        self.assertIsNotNone(file.last_accessed)
    
    def test_file_hash_unique_constraint(self):
        """Test file hash uniqueness"""
        ManagedFile.objects.create(**self.file_data)
        
        # Should raise IntegrityError for duplicate hash
        duplicate_data = self.file_data.copy()
        duplicate_data['original_name'] = 'different_name.gba'
        
        with self.assertRaises(Exception):  # Django IntegrityError
            ManagedFile.objects.create(**duplicate_data)
    
    def test_increment_reference(self):
        """Test reference count increment"""
        file = ManagedFile.objects.create(**self.file_data)
        self.assertEqual(file.reference_count, 0)
        
        file.increment_reference()
        file.refresh_from_db()
        self.assertEqual(file.reference_count, 1)
        
        file.increment_reference()
        file.refresh_from_db()
        self.assertEqual(file.reference_count, 2)
    
    def test_decrement_reference(self):
        """Test reference count decrement"""
        file_data = self.file_data.copy()
        file_data['reference_count'] = 3
        file = ManagedFile.objects.create(**file_data)
        
        file.decrement_reference()
        file.refresh_from_db()
        self.assertEqual(file.reference_count, 2)
        
        file.decrement_reference()
        file.refresh_from_db()
        self.assertEqual(file.reference_count, 1)
    
    def test_decrement_reference_at_zero(self):
        """Test decrement doesn't go below zero"""
        file = ManagedFile.objects.create(**self.file_data)  # reference_count = 0
        
        file.decrement_reference()
        file.refresh_from_db()
        self.assertEqual(file.reference_count, 0)  # Should stay at 0
    
    def test_is_orphaned(self):
        """Test orphaned file detection"""
        file = ManagedFile.objects.create(**self.file_data)  # reference_count = 0
        self.assertTrue(file.is_orphaned())
        
        file.increment_reference()
        file.refresh_from_db()
        self.assertFalse(file.is_orphaned())
    
    @patch('os.path.exists', return_value=True)
    @patch('os.remove')
    def test_cleanup_orphaned_files(self, mock_remove, mock_exists):
        """Test cleanup of orphaned files"""
        # Create some files with different reference counts
        orphan1 = ManagedFile.objects.create(
            file_hash='b' * 64,
            original_name='orphan1.gba',
            file_type='rom',
            file_size=1000,
            stored_path='/tmp/orphan1.gba',
            reference_count=0
        )
        orphan2 = ManagedFile.objects.create(
            file_hash='c' * 64,
            original_name='orphan2.gba', 
            file_type='rom',
            file_size=2000,
            stored_path='/tmp/orphan2.gba',
            reference_count=0
        )
        used_file = ManagedFile.objects.create(
            file_hash='d' * 64,
            original_name='used.gba',
            file_type='rom',
            file_size=3000,
            stored_path='/tmp/used.gba',
            reference_count=1
        )
        
        # Clean up orphaned files
        deleted_count = ManagedFile.cleanup_orphaned_files()
        
        # Should delete 2 orphaned files
        self.assertEqual(deleted_count, 2)
        
        # Verify file system calls
        self.assertEqual(mock_remove.call_count, 2)
        mock_remove.assert_any_call('/tmp/orphan1.gba')
        mock_remove.assert_any_call('/tmp/orphan2.gba')
        
        # Used file should still exist in database
        self.assertTrue(ManagedFile.objects.filter(file_hash='d' * 64).exists())
        
        # Orphaned files should be removed from database
        self.assertFalse(ManagedFile.objects.filter(file_hash='b' * 64).exists())
        self.assertFalse(ManagedFile.objects.filter(file_hash='c' * 64).exists())
    
    def test_managed_file_string_representation(self):
        """Test ManagedFile __str__ method"""
        file = ManagedFile.objects.create(**self.file_data)
        str_repr = str(file)
        self.assertIn('pokemon_sapphire.gba', str_repr)
        self.assertIn('rom', str_repr)


class ROMConfigurationModelTest(TestCase):
    """Test ROMConfiguration model functionality"""
    
    def setUp(self):
        self.rom_file = ManagedFile.objects.create(
            file_hash='rom' + 'a' * 61,
            original_name='Pokemon_Sapphire_USA.gba',
            file_type='rom',
            file_size=16777216,
            stored_path='/roms/Pokemon_Sapphire_USA.gba'
        )
        
        self.mgba_file = ManagedFile.objects.create(
            file_hash='mgba' + 'b' * 60,
            original_name='mgba',
            file_type='executable',
            file_size=5242880,
            stored_path='/usr/bin/mgba'
        )
    
    def test_rom_configuration_creation(self):
        """Test ROM configuration creation"""
        config = ROMConfiguration.objects.create(
            rom_file=self.rom_file,
            mgba_file=self.mgba_file
        )
        
        # Test auto-generated fields
        self.assertEqual(config.display_name, 'Pokemon Sapphire Usa')  # Auto-cleaned
        self.assertEqual(config.game_type, 'pokemon_sapphire')  # Auto-detected
        self.assertIsNotNone(config.created_at)
        self.assertIsNotNone(config.updated_at)
    
    def test_clean_filename(self):
        """Test filename cleaning functionality"""
        config = ROMConfiguration()
        
        test_cases = [
            ('Pokemon_Red_USA.gba', 'Pokemon Red Usa'),
            ('pokemon-sapphire-v1.0.gba', 'Pokemon Sapphire V1.0'),
            ('MARIO_KART__SUPER_CIRCUIT.gba', 'Mario Kart Super Circuit'),
            ('file___with____spaces.rom', 'File With Spaces')
        ]
        
        for input_name, expected_output in test_cases:
            with self.subTest(input_name=input_name):
                result = config.clean_filename(input_name)
                self.assertEqual(result, expected_output)
    
    def test_detect_game_type(self):
        """Test game type detection"""
        config = ROMConfiguration()
        
        pokemon_test_cases = [
            ('Pokemon Sapphire Version USA.gba', 'pokemon_sapphire'),
            ('POKEMON_RUBY_V1.0.gba', 'pokemon_ruby'),
            ('Pokemon-Emerald.gba', 'pokemon_emerald'),
            ('Pokemon FireRed (U).gba', 'pokemon_firered'),
            ('Pokemon LeafGreen.gba', 'pokemon_leafgreen'),
            ('Pokemon Red.gb', 'pokemon_red'),
            ('Pokemon Blue (USA).gb', 'pokemon_blue')
        ]
        
        for filename, expected_type in pokemon_test_cases:
            with self.subTest(filename=filename):
                result = config.detect_game_type(filename)
                self.assertEqual(result, expected_type)
        
        # Test non-Pokemon games
        other_test_cases = [
            ('Golden Sun.gba', 'golden_sun'),
            ('Fire Emblem Sacred Stones.gba', 'fire_emblem'),
            ('Super Mario Advance.gba', 'super_mario'),
            ('Unknown Game.gba', 'unknown_gba')
        ]
        
        for filename, expected_type in other_test_cases:
            with self.subTest(filename=filename):
                result = config.detect_game_type(filename)
                self.assertEqual(result, expected_type)
    
    def test_file_reference_management(self):
        """Test file reference counting on save/delete"""
        # Initial reference counts should be 0
        self.assertEqual(self.rom_file.reference_count, 0)
        self.assertEqual(self.mgba_file.reference_count, 0)
        
        # Create ROM config - should increment references
        config = ROMConfiguration.objects.create(
            rom_file=self.rom_file,
            mgba_file=self.mgba_file
        )
        
        self.rom_file.refresh_from_db()
        self.mgba_file.refresh_from_db()
        self.assertEqual(self.rom_file.reference_count, 1)
        self.assertEqual(self.mgba_file.reference_count, 1)
        
        # Delete config - should decrement references
        config.delete()
        
        self.rom_file.refresh_from_db()
        self.mgba_file.refresh_from_db()
        self.assertEqual(self.rom_file.reference_count, 0)
        self.assertEqual(self.mgba_file.reference_count, 0)
    
    def test_property_paths(self):
        """Test backwards compatibility path properties"""
        config = ROMConfiguration.objects.create(
            rom_file=self.rom_file,
            mgba_file=self.mgba_file
        )
        
        self.assertEqual(config.rom_path, '/roms/Pokemon_Sapphire_USA.gba')
        self.assertEqual(config.mgba_path, '/usr/bin/mgba')
        
        # Test with None files
        config_no_files = ROMConfiguration.objects.create()
        self.assertIsNone(config_no_files.rom_path)
        self.assertIsNone(config_no_files.mgba_path)
        self.assertIsNone(config_no_files.script_path)
    
    def test_rom_config_string_representation(self):
        """Test ROMConfiguration __str__ method"""
        config = ROMConfiguration.objects.create(rom_file=self.rom_file)
        str_repr = str(config)
        self.assertIn('Pokemon Sapphire Usa', str_repr)
        self.assertIn('pokemon_sapphire', str_repr)