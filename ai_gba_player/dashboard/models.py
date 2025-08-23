from django.db import models
from django.contrib.auth.models import User
import json


class ProcessStatus(models.TextChoices):
    STOPPED = 'stopped', 'Stopped'
    STARTING = 'starting', 'Starting'
    RUNNING = 'running', 'Running'
    ERROR = 'error', 'Error'


class Process(models.Model):
    """Model for tracking AI GBA game processes"""
    name = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=ProcessStatus.choices,
        default=ProcessStatus.STOPPED
    )
    pid = models.IntegerField(null=True, blank=True)
    port = models.IntegerField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.status})"


class MessageType(models.TextChoices):
    GIF = 'gif', 'GIF'
    SCREENSHOTS = 'screenshots', 'Screenshots'
    RESPONSE = 'response', 'Response'
    ACTION = 'action', 'Action'
    SYSTEM = 'system', 'System'


class ChatMessage(models.Model):
    """Model for storing chat messages from the AI system"""
    message_id = models.CharField(max_length=100, unique=True)
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices
    )
    source = models.CharField(max_length=100)
    content = models.JSONField()
    timestamp = models.FloatField()
    sequence = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.message_type} from {self.source} at {self.timestamp}"


class SystemLog(models.Model):
    """Model for storing system logs"""
    process_name = models.CharField(max_length=100)
    level = models.CharField(max_length=20)
    message = models.TextField()
    timestamp = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.level} from {self.process_name}: {self.message[:50]}..."


class SystemStats(models.Model):
    """Model for storing system statistics"""
    uptime = models.FloatField()
    memory_usage = models.JSONField()
    active_connections = models.IntegerField(default=0)
    message_count = models.IntegerField(default=0)
    timestamp = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']


class ManagedFile(models.Model):
    """Model for deduplicated file storage with reference counting"""
    file_hash = models.CharField(max_length=64, unique=True, help_text="SHA-256 hash for deduplication")
    original_name = models.CharField(max_length=255, help_text="Original filename when uploaded")
    file_type = models.CharField(max_length=50, help_text="File type: rom, executable, script")
    file_size = models.IntegerField(help_text="File size in bytes")
    stored_path = models.CharField(max_length=500, help_text="Path where file is stored")
    reference_count = models.IntegerField(default=0, help_text="Number of configurations using this file")
    
    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['file_hash']),
            models.Index(fields=['file_type']),
        ]
    
    def __str__(self):
        return f"{self.original_name} ({self.file_type})"
    
    def increment_reference(self):
        """Increment reference count when file is used"""
        self.reference_count += 1
        self.save(update_fields=['reference_count'])
    
    def decrement_reference(self):
        """Decrement reference count when file is no longer used"""
        if self.reference_count > 0:
            self.reference_count -= 1
            self.save(update_fields=['reference_count'])
    
    def is_orphaned(self):
        """Check if file has no references and can be cleaned up"""
        return self.reference_count == 0
    
    @classmethod
    def cleanup_orphaned_files(cls):
        """Remove orphaned files from storage and database"""
        import os
        orphaned_files = cls.objects.filter(reference_count=0)
        deleted_count = 0
        
        for file in orphaned_files:
            try:
                # Remove physical file
                if os.path.exists(file.stored_path):
                    os.remove(file.stored_path)
                
                # Remove database record
                file.delete()
                deleted_count += 1
            except Exception as e:
                # Log error but continue cleanup
                print(f"Error cleaning up {file.original_name}: {e}")
        
        return deleted_count


class ROMConfiguration(models.Model):
    """Model for storing ROM and emulator configurations with auto-generation"""
    # Auto-generated fields (no manual input needed)
    display_name = models.CharField(max_length=200, default="Unknown ROM", help_text="Auto-generated from ROM filename")
    game_type = models.CharField(max_length=100, default="unknown_gba", help_text="Auto-detected from ROM filename")
    
    # File references (deduplicated storage)
    rom_file = models.ForeignKey(ManagedFile, on_delete=models.CASCADE, related_name='rom_configs', null=True, blank=True, help_text="Reference to ROM file")
    mgba_file = models.ForeignKey(ManagedFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='mgba_configs', help_text="Reference to mGBA executable")
    script_file = models.ForeignKey(ManagedFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='script_configs', help_text="Reference to Lua script")
    
    # Game-specific settings
    settings = models.JSONField(default=dict, blank=True, help_text="Game-specific configuration")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_used', '-created_at']
    
    def __str__(self):
        return f"{self.display_name} ({self.game_type})"
    
    def clean_filename(self, filename):
        """Convert ROM filename to clean display name"""
        import re
        # Remove extension
        name = re.sub(r'\.(gba|gbc|gb|rom)$', '', filename, flags=re.IGNORECASE)
        # Replace underscores and dashes with spaces
        name = re.sub(r'[_-]+', ' ', name)
        # Clean up extra spaces
        name = re.sub(r'\s+', ' ', name).strip()
        # Title case for better readability
        return name.title()
    
    def detect_game_type(self, filename):
        """Auto-detect game type from ROM filename"""
        import re
        filename_lower = filename.lower()
        
        # Pokemon games
        pokemon_patterns = {
            'pokemon_red': [r'pokemon.*red', r'red.*pokemon', r'pkmn.*red'],
            'pokemon_blue': [r'pokemon.*blue', r'blue.*pokemon', r'pkmn.*blue'],
            'pokemon_yellow': [r'pokemon.*yellow', r'yellow.*pokemon', r'pkmn.*yellow'],
            'pokemon_ruby': [r'pokemon.*ruby', r'ruby.*pokemon', r'pkmn.*ruby'],
            'pokemon_sapphire': [r'pokemon.*sapphire', r'sapphire.*pokemon', r'pkmn.*sapphire'],
            'pokemon_emerald': [r'pokemon.*emerald', r'emerald.*pokemon', r'pkmn.*emerald'],
            'pokemon_firered': [r'pokemon.*(fire.*red|firered)', r'firered', r'pkmn.*firered'],
            'pokemon_leafgreen': [r'pokemon.*(leaf.*green|leafgreen)', r'leafgreen', r'pkmn.*leafgreen'],
        }
        
        # Other popular GBA games
        other_patterns = {
            'golden_sun': [r'golden.*sun'],
            'fire_emblem': [r'fire.*emblem'],
            'advance_wars': [r'advance.*wars'],
            'mario_kart': [r'mario.*kart'],
            'super_mario': [r'super.*mario'],
            'metroid': [r'metroid'],
            'zelda': [r'zelda', r'link.*past'],
            'final_fantasy': [r'final.*fantasy', r'ff[0-9]'],
        }
        
        # Check all patterns
        all_patterns = {**pokemon_patterns, **other_patterns}
        for game_type, patterns in all_patterns.items():
            if any(re.search(pattern, filename_lower) for pattern in patterns):
                return game_type
        
        return 'unknown_gba'
    
    def save(self, *args, **kwargs):
        # Auto-generate fields from ROM file if present
        if self.rom_file and (not self.display_name or self.display_name == "Unknown ROM"):
            self.display_name = self.clean_filename(self.rom_file.original_name)
            self.game_type = self.detect_game_type(self.rom_file.original_name)
        
        # Check if this is a new instance
        is_new = self.pk is None
        
        # Get old file references if updating
        old_rom_file = None
        old_mgba_file = None
        old_script_file = None
        
        if not is_new:
            try:
                old_instance = ROMConfiguration.objects.get(pk=self.pk)
                old_rom_file = old_instance.rom_file
                old_mgba_file = old_instance.mgba_file
                old_script_file = old_instance.script_file
            except ROMConfiguration.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Update reference counts for file management
        if is_new:
            # New instance - increment references for all files
            if self.rom_file:
                self.rom_file.increment_reference()
            if self.mgba_file:
                self.mgba_file.increment_reference()
            if self.script_file:
                self.script_file.increment_reference()
        else:
            # Updating instance - handle reference count changes
            # ROM file changes
            if old_rom_file != self.rom_file:
                if old_rom_file:
                    old_rom_file.decrement_reference()
                if self.rom_file:
                    self.rom_file.increment_reference()
            
            # mGBA file changes
            if old_mgba_file != self.mgba_file:
                if old_mgba_file:
                    old_mgba_file.decrement_reference()
                if self.mgba_file:
                    self.mgba_file.increment_reference()
            
            # Script file changes
            if old_script_file != self.script_file:
                if old_script_file:
                    old_script_file.decrement_reference()
                if self.script_file:
                    self.script_file.increment_reference()
    
    def delete(self, *args, **kwargs):
        # Decrement reference counts before deletion
        if self.rom_file:
            self.rom_file.decrement_reference()
        if self.mgba_file:
            self.mgba_file.decrement_reference()
        if self.script_file:
            self.script_file.decrement_reference()
        
        super().delete(*args, **kwargs)
    
    @property
    def rom_path(self):
        """Get ROM file path for backwards compatibility"""
        return self.rom_file.stored_path if self.rom_file else None
    
    @property
    def mgba_path(self):
        """Get mGBA file path for backwards compatibility"""
        return self.mgba_file.stored_path if self.mgba_file else None
    
    @property
    def script_path(self):
        """Get script file path for backwards compatibility"""
        return self.script_file.stored_path if self.script_file else None


class Configuration(models.Model):
    """Model for storing system configuration settings"""
    
    # Singleton pattern - only one configuration record should exist
    name = models.CharField(max_length=100, default="AI GBA Player Config", unique=True)
    
    # Game Settings
    game = models.CharField(max_length=50, default="pokemon_red", help_text="Game type to play")
    game_override = models.CharField(max_length=50, blank=True, help_text="Manual game override (overrides auto-detection)")
    detected_game = models.CharField(max_length=50, blank=True, help_text="Auto-detected game from ROM")
    detection_source = models.CharField(max_length=20, default="default", help_text="Source of game detection: auto, manual, or default")
    llm_provider = models.CharField(max_length=50, default="google", help_text="LLM provider to use")
    
    # API Configuration (JSON field for complex nested data)
    providers = models.JSONField(default=dict, help_text="LLM provider configurations")
    
    # Network Settings
    host = models.CharField(max_length=100, default="127.0.0.1", help_text="Host address")
    port = models.IntegerField(default=8888, help_text="Port number for game control")
    
    # File Paths
    notepad_path = models.CharField(max_length=500, default="notepad.txt", help_text="Path to notepad file")
    screenshot_path = models.CharField(max_length=500, default="data/screenshots/screenshot.png", help_text="Screenshot save path")
    video_path = models.CharField(max_length=500, default="data/videos/video_sequence.mp4", help_text="Video save path")
    prompt_template_path = models.CharField(max_length=500, default="data/prompt_template.txt", help_text="Prompt template path")
    knowledge_file = models.CharField(max_length=500, default="data/knowledge_graph.json", help_text="Knowledge graph file path")
    
    # ROM and mGBA Configuration
    rom_path = models.CharField(max_length=500, default="", blank=True, help_text="Path to ROM file")
    rom_display_name = models.CharField(max_length=200, default="", blank=True, help_text="Display name for ROM")
    mgba_path = models.CharField(max_length=500, default="", blank=True, help_text="Path to mGBA executable")
    
    # Timing Settings
    decision_cooldown = models.IntegerField(default=5, help_text="Cooldown between decisions (seconds)")
    thinking_history_max_chars = models.IntegerField(default=20000, help_text="Max characters in thinking history")
    thinking_history_keep_entries = models.IntegerField(default=5, help_text="Number of thinking history entries to keep")
    llm_timeout_seconds = models.IntegerField(default=60, help_text="LLM request timeout (seconds)")
    
    # Debug Settings
    debug_mode = models.BooleanField(default=True, help_text="Enable debug mode")
    
    # Complex Configuration (JSON fields for nested settings)
    capture_system = models.JSONField(default=dict, help_text="Capture system configuration")
    dual_process_mode = models.JSONField(default=dict, help_text="Dual process mode settings")
    unified_service = models.JSONField(default=dict, help_text="Unified service configuration")
    dashboard = models.JSONField(default=dict, help_text="Dashboard configuration")
    storage = models.JSONField(default=dict, help_text="Storage configuration")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"
    
    def __str__(self):
        return f"Configuration: {self.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one configuration exists (singleton pattern)
        if not self.pk and Configuration.objects.exists():
            raise ValueError("Only one configuration record is allowed")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Get the single configuration instance, creating default if needed"""
        config, created = cls.objects.get_or_create(
            name="AI GBA Player Config",
            defaults=cls.get_default_config()
        )
        return config
    
    @classmethod
    def get_default_config(cls):
        """Get default configuration values"""
        return {
            'game': 'pokemon_red',
            'llm_provider': 'google',
            'providers': {
                'google': {
                    'api_key': '',
                    'model_name': 'gemini-2.5-flash',
                    'max_tokens': 4096
                },
                'openai': {
                    'api_key': '',
                    'model_name': 'gpt-4',
                    'max_tokens': 1024
                },
                'anthropic': {
                    'api_key': '',
                    'model_name': 'claude-3-sonnet-20240229',
                    'max_tokens': 1024
                }
            },
            'host': '127.0.0.1',
            'port': 8888,
            'notepad_path': 'notepad.txt',
            'screenshot_path': 'data/screenshots/screenshot.png',
            'video_path': 'data/videos/video_sequence.mp4',
            'prompt_template_path': 'data/prompt_template.txt',
            'knowledge_file': 'data/knowledge_graph.json',
            'decision_cooldown': 5,
            'thinking_history_max_chars': 20000,
            'thinking_history_keep_entries': 5,
            'llm_timeout_seconds': 60,
            'debug_mode': True,
            'capture_system': {
                'type': 'screen',
                'screen_capture_method': 'auto',
                'capture_region': None,
                'capture_fps': 30,
                'frame_enhancement': {
                    'scale_factor': 3,
                    'contrast': 1.5,
                    'saturation': 1.8,
                    'brightness': 1.1
                },
                'video_analysis': {
                    'frame_sampling': 'keyframes',
                    'max_analysis_frames': 5,
                    'motion_threshold': 0.1
                },
                'auto_cleanup': {
                    'enabled': True,
                    'keep_recent_captures': 3,
                    'save_video_segments': False,
                    'save_ai_frames': True
                },
                'gif_optimization': {
                    'max_gif_frames': 150,
                    'gif_width': 320,
                    'target_gif_duration': 10.0,
                    'max_gif_duration': 20.0
                }
            },
            'dual_process_mode': {
                'enabled': False,
                'video_capture_port': 8889,
                'rolling_window_seconds': 20,
                'process_communication_timeout': 25
            },
            'unified_service': {
                'enabled': True,
                'thread_startup_delay': 2,
                'thread_communication_timeout': 30
            },
            'dashboard': {
                'enabled': True,
                'port': 3000,
                'websocket_port': 3000,
                'chat_history_limit': 100,
                'gif_retention_minutes': 30,
                'auto_start_processes': True,
                'theme': 'pokemon',
                'streaming_mode': False,
                'auto_restart': True
            },
            'storage': {
                'enabled': True,
                'database_path': 'data/pokemon_ai.db',
                'wal_mode': True,
                'auto_vacuum': 'incremental',
                'cache_size': 10000,
                'gif_storage_threshold_mb': 1,
                'compression_level': 6,
                'retention_policy': {
                    'keep_sessions_days': 30,
                    'archive_old_sessions': True,
                    'max_database_size_gb': 5
                }
            }
        }
    
    def to_dict(self):
        """Convert configuration to dictionary format"""
        return {
            'game': self.game,
            'game_override': self.game_override,
            'detected_game': self.detected_game,
            'detection_source': self.detection_source,
            'llm_provider': self.llm_provider,
            'providers': self.providers,
            'host': self.host,
            'port': self.port,
            'notepad_path': self.notepad_path,
            'screenshot_path': self.screenshot_path,
            'video_path': self.video_path,
            'prompt_template_path': self.prompt_template_path,
            'knowledge_file': self.knowledge_file,
            'rom_path': self.rom_path,
            'rom_display_name': self.rom_display_name,
            'mgba_path': self.mgba_path,
            'decision_cooldown': self.decision_cooldown,
            'thinking_history_max_chars': self.thinking_history_max_chars,
            'thinking_history_keep_entries': self.thinking_history_keep_entries,
            'llm_timeout_seconds': self.llm_timeout_seconds,
            'debug_mode': self.debug_mode,
            'capture_system': self.capture_system,
            'dual_process_mode': self.dual_process_mode,
            'unified_service': self.unified_service,
            'dashboard': self.dashboard,
            'storage': self.storage,
        }
