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
