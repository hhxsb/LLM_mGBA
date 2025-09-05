from django.test import TestCase
from unittest.mock import patch, MagicMock, mock_open
import logging
import tempfile
import os
from pathlib import Path
from io import StringIO

from core.logging_config import EmojiFormatter, setup_logging, get_logger


class EmojiFormatterTest(TestCase):
    """Test EmojiFormatter functionality"""
    
    def setUp(self):
        self.formatter = EmojiFormatter('%(emoji)s %(name)s: %(message)s')
        
    def test_format_with_debug_level(self):
        """Test DEBUG level gets correct emoji"""
        record = logging.LogRecord(
            name='test_logger',
            level=logging.DEBUG,
            pathname='',
            lineno=0,
            msg='Test debug message',
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        self.assertIn('🔍', formatted)
        self.assertIn('Test debug message', formatted)
        
    def test_format_with_info_level(self):
        """Test INFO level gets correct emoji"""
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test info message',
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        self.assertIn('📝', formatted)
        self.assertIn('Test info message', formatted)
        
    def test_format_with_warning_level(self):
        """Test WARNING level gets correct emoji"""
        record = logging.LogRecord(
            name='test_logger',
            level=logging.WARNING,
            pathname='',
            lineno=0,
            msg='Test warning message',
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        self.assertIn('⚠️', formatted)
        self.assertIn('Test warning message', formatted)
        
    def test_format_with_error_level(self):
        """Test ERROR level gets correct emoji"""
        record = logging.LogRecord(
            name='test_logger',
            level=logging.ERROR,
            pathname='',
            lineno=0,
            msg='Test error message',
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        self.assertIn('❌', formatted)
        self.assertIn('Test error message', formatted)
        
    def test_format_with_critical_level(self):
        """Test CRITICAL level gets correct emoji"""
        record = logging.LogRecord(
            name='test_logger',
            level=logging.CRITICAL,
            pathname='',
            lineno=0,
            msg='Test critical message',
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        self.assertIn('🚨', formatted)
        self.assertIn('Test critical message', formatted)
        
    def test_format_with_unknown_level(self):
        """Test unknown level gets default emoji"""
        record = logging.LogRecord(
            name='test_logger',
            level=25,  # Custom level between INFO and WARNING
            pathname='',
            lineno=0,
            msg='Test custom level message',
            args=(),
            exc_info=None
        )
        record.levelname = 'CUSTOM'
        
        formatted = self.formatter.format(record)
        self.assertIn('📝', formatted)  # Default emoji
        self.assertIn('Test custom level message', formatted)


class SetupLoggingTest(TestCase):
    """Test setup_logging functionality"""
    
    def tearDown(self):
        """Clean up loggers after each test"""
        # Remove all handlers from the test logger
        logger = logging.getLogger('ai_gba_player')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
    
    def test_setup_logging_basic(self):
        """Test basic logging setup"""
        logger = setup_logging(level=logging.DEBUG, log_to_file=False)
        
        self.assertEqual(logger.name, 'ai_gba_player')
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertGreater(len(logger.handlers), 0)
        
        # Test console handler is added
        console_handler = logger.handlers[0]
        self.assertIsInstance(console_handler, logging.StreamHandler)
        self.assertIsInstance(console_handler.formatter, EmojiFormatter)
        
    def test_setup_logging_prevents_duplicate_handlers(self):
        """Test that setup_logging doesn't add duplicate handlers"""
        logger1 = setup_logging(level=logging.INFO, log_to_file=False)
        handler_count_1 = len(logger1.handlers)
        
        logger2 = setup_logging(level=logging.DEBUG, log_to_file=False)
        handler_count_2 = len(logger2.handlers)
        
        self.assertEqual(handler_count_1, handler_count_2)
        self.assertIs(logger1, logger2)  # Same logger instance
    
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_setup_logging_with_file_handler(self, mock_file, mock_mkdir):
        """Test file handler setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(
                level=logging.INFO, 
                log_to_file=True, 
                log_dir=temp_dir
            )
            
            # Should have console handler + file handler
            self.assertEqual(len(logger.handlers), 2)
            
            # Check file handler exists and has correct formatter
            file_handler = logger.handlers[1]
            self.assertIsInstance(file_handler, logging.FileHandler)
            self.assertEqual(file_handler.level, logging.DEBUG)
            
            # Verify the formatter is not EmojiFormatter (plain text for files)
            self.assertNotIsInstance(file_handler.formatter, EmojiFormatter)
    
    @patch('pathlib.Path.mkdir', side_effect=PermissionError("Permission denied"))
    def test_setup_logging_file_handler_error(self, mock_mkdir):
        """Test graceful handling of file handler setup errors"""
        with patch('logging.Logger.warning') as mock_warning:
            logger = setup_logging(level=logging.INFO, log_to_file=True)
            
            # Should only have console handler when file setup fails
            self.assertEqual(len(logger.handlers), 1)
            self.assertIsInstance(logger.handlers[0], logging.StreamHandler)
            
            # Should log a warning about file logging failure
            mock_warning.assert_called_once()
            warning_call_args = mock_warning.call_args[0][0]
            self.assertIn("Could not set up file logging", warning_call_args)
    
    def test_setup_logging_different_levels(self):
        """Test setup with different logging levels"""
        levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]
        
        for level in levels:
            # Clean up previous logger
            logger = logging.getLogger('ai_gba_player')
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
                handler.close()
                
            test_logger = setup_logging(level=level, log_to_file=False)
            self.assertEqual(test_logger.level, level)
            
            console_handler = test_logger.handlers[0]
            self.assertEqual(console_handler.level, level)
    
    def test_setup_logging_file_naming(self):
        """Test that log files are named with current date"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('core.logging_config.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = '20240901'
                
                logger = setup_logging(
                    level=logging.INFO,
                    log_to_file=True,
                    log_dir=temp_dir
                )
                
                # Check that datetime.now().strftime('%Y%m%d') was called
                mock_datetime.now.assert_called_once()
                mock_datetime.now.return_value.strftime.assert_called_with('%Y%m%d')


class GetLoggerTest(TestCase):
    """Test get_logger functionality"""
    
    def setUp(self):
        # Ensure the main logger is set up
        setup_logging(level=logging.DEBUG, log_to_file=False)
    
    def tearDown(self):
        """Clean up loggers after each test"""
        logger = logging.getLogger('ai_gba_player')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
    
    def test_get_logger_returns_child_logger(self):
        """Test get_logger returns properly named child logger"""
        test_logger = get_logger('test_module')
        
        self.assertEqual(test_logger.name, 'ai_gba_player.test_module')
        self.assertIsInstance(test_logger, logging.Logger)
    
    def test_get_logger_inherits_parent_config(self):
        """Test child logger inherits parent configuration"""
        # Set up parent logger with specific level
        setup_logging(level=logging.WARNING, log_to_file=False)
        
        child_logger = get_logger('child_module')
        
        # Child should inherit effective level from parent
        self.assertEqual(child_logger.name, 'ai_gba_player.child_module')
        # The child logger will inherit the parent's level through propagation
        self.assertTrue(child_logger.parent.name.startswith('ai_gba_player'))
    
    def test_get_logger_multiple_modules(self):
        """Test get_logger works correctly for multiple modules"""
        logger1 = get_logger('module1')
        logger2 = get_logger('module2')
        
        self.assertEqual(logger1.name, 'ai_gba_player.module1')
        self.assertEqual(logger2.name, 'ai_gba_player.module2')
        self.assertIsNot(logger1, logger2)  # Different instances
        
        # Both should have the same parent
        self.assertEqual(logger1.parent, logger2.parent)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_logger_actual_logging(self, mock_stdout):
        """Test that get_logger actually works for logging messages"""
        test_logger = get_logger('test_logging')
        
        test_logger.info('Test info message')
        test_logger.warning('Test warning message')
        
        output = mock_stdout.getvalue()
        
        # Should contain emoji formatting and module name
        self.assertIn('📝', output)  # Info emoji
        self.assertIn('⚠️', output)  # Warning emoji
        self.assertIn('ai_gba_player.test_logging', output)
        self.assertIn('Test info message', output)
        self.assertIn('Test warning message', output)


class DefaultLoggerTest(TestCase):
    """Test the default_logger module variable"""
    
    def tearDown(self):
        """Clean up loggers after each test"""
        logger = logging.getLogger('ai_gba_player')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
    
    def test_default_logger_exists(self):
        """Test that default_logger is created on module import"""
        from core.logging_config import default_logger
        
        self.assertIsInstance(default_logger, logging.Logger)
        self.assertEqual(default_logger.name, 'ai_gba_player')
    
    def test_default_logger_has_handlers(self):
        """Test that default_logger is properly configured"""
        from core.logging_config import default_logger
        
        self.assertGreater(len(default_logger.handlers), 0)
        
        # Should have at least a console handler with emoji formatter
        console_handler = default_logger.handlers[0]
        self.assertIsInstance(console_handler, logging.StreamHandler)
        self.assertIsInstance(console_handler.formatter, EmojiFormatter)