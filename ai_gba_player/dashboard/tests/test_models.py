from django.test import TestCase
from unittest.mock import patch, MagicMock
from dashboard.models import Configuration, Process, ProcessStatus, ChatMessage, MessageType


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
        self.assertIsInstance(config.providers, dict)
        self.assertIn('google', config.providers)
    
    def test_to_dict_method(self):
        """Test configuration serialization"""
        config = Configuration.get_config()
        config_dict = config.to_dict()
        
        # Test required fields are present
        required_fields = ['game', 'llm_provider', 'providers', 'host', 'port']
        for field in required_fields:
            self.assertIn(field, config_dict)
    
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


class ProcessModelTest(TestCase):
    """Test Process model functionality"""
    
    def setUp(self):
        self.process_data = {
            'name': 'test_ai_service',
            'status': ProcessStatus.RUNNING,
            'pid': 12345,
            'port': 8888
        }
    
    def test_process_creation(self):
        """Test process model creation"""
        process = Process.objects.create(**self.process_data)
        self.assertEqual(process.name, 'test_ai_service')
        self.assertEqual(process.status, ProcessStatus.RUNNING)
        self.assertEqual(process.pid, 12345)
        self.assertEqual(process.port, 8888)
    
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