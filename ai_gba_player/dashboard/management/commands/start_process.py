"""
Django management command to start AI GBA Player unified service.
"""

import subprocess
import sys
import time
import signal
import psutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from dashboard.models import Process, Configuration
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

# Import unified service using proper Django app path
try:
    # Add project root to Python path
    import os
    project_root = Path(__file__).parent.parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from ai_gba_player.core.unified_game_service import get_unified_service, start_unified_service, stop_unified_service
    print("✅ Unified Game Service integration ready")
except ImportError as e:
    print(f"⚠️ Warning: Could not import unified service: {e}")
    try:
        # Try alternative import path
        from core.unified_game_service import get_unified_service, start_unified_service, stop_unified_service
        print("✅ Unified Game Service integration ready (alternative path)")
    except ImportError as e2:
        print(f"⚠️ Warning: Could not import project core modules: {e2}")
        print("Unified service may not function properly without core modules")
        def get_unified_service(): raise ImportError("Unified service not available")
        def start_unified_service(config_path): raise ImportError("Unified service not available") 
        def stop_unified_service(): raise ImportError("Unified service not available")

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start AI GBA Player system processes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'process_name',
            choices=['unified_service', 'all'],
            help='Name of the service to start'
        )
        parser.add_argument(
            '--config',
            type=str,
            help='Configuration file to use (optional - will use database config if not provided)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force start even if service is already running'
        )
    
    def handle(self, *args, **options):
        service_name = options['process_name']
        config_file = options['config']
        force = options['force']
        
        # Get project root directory
        project_root = Path(__file__).parent.parent.parent.parent.parent
        
        # Use database configuration unless JSON file is explicitly provided
        if config_file:
            config_path = str(project_root / config_file)
            if not Path(config_path).exists():
                raise CommandError(f'Config file not found: {config_path}')
            config_source = f'JSON file: {config_path}'
            use_db_config = False
        else:
            # Use database configuration
            config_path = None
            config_source = 'database configuration'
            use_db_config = True
        
        self.stdout.write(f'🚀 Starting service: {service_name}')
        self.stdout.write(f'📁 Project root: {project_root}')
        self.stdout.write(f'⚙️ Config source: {config_source}')
        
        if service_name in ['unified_service', 'all']:
            self._start_unified_service(config_path, force, use_db_config)
        else:
            raise CommandError(f'Unknown service: {service_name}')
    
    def _start_unified_service(self, config_path: str, force: bool, use_db_config: bool):
        """Start the unified service."""
        service_name = 'unified_service'
        
        # Check if service is already running
        try:
            process_obj = Process.objects.get(name=service_name)
            if not force and process_obj.status == 'running':
                service = get_unified_service()
                if service.running:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ Unified service is already running')
                    )
                    return
        except Process.DoesNotExist:
            # Create process record if it doesn't exist
            process_obj = Process.objects.create(
                name=service_name,
                status='stopped'
            )
        
        # Update status to starting
        process_obj.status = 'starting'
        process_obj.last_error = ''
        process_obj.save()
        
        # Broadcast status update
        self._broadcast_process_status(service_name, 'starting')
        
        try:
            if use_db_config:
                # Get configuration from database
                try:
                    db_config = Configuration.get_config()
                    config_dict = db_config.to_dict()
                    self.stdout.write('🚀 Starting unified service with database configuration')
                except Exception as e:
                    raise CommandError(f'Failed to get database configuration: {e}')
            else:
                # Use JSON file configuration
                self.stdout.write(f'🚀 Starting unified service with config: {config_path}')
                config_dict = None  # Will be loaded by start_unified_service from file
            
            # Start the unified service
            if use_db_config:
                success = start_unified_service(config_dict)
            else:
                success = start_unified_service(config_path)
            
            if success:
                # Service started successfully
                process_obj.status = 'running'
                process_obj.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Started unified service successfully')
                )
                
                # Broadcast success
                self._broadcast_process_status(service_name, 'running')
                
            else:
                # Service failed to start
                error_msg = 'Unified service failed to start'
                
                process_obj.status = 'error'
                process_obj.last_error = error_msg
                process_obj.save()
                
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to start unified service: {error_msg}')
                )
                
                # Broadcast error
                self._broadcast_process_status(service_name, 'error', error=error_msg)
                
        except Exception as e:
            process_obj.status = 'error'
            process_obj.last_error = str(e)[:500]
            process_obj.save()
            
            self.stdout.write(
                self.style.ERROR(f'❌ Exception starting unified service: {e}')
            )
            
            # Broadcast error
            self._broadcast_process_status(service_name, 'error', error=str(e))
            raise CommandError(f'Failed to start unified service: {e}')
    
    
    def _broadcast_process_status(self, process_name, status, pid=None, error=None):
        """Broadcast process status update via Django Channels"""
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                message = {
                    'type': 'system_status',
                    'message': {
                        'system': {
                            'processes': {
                                process_name: {
                                    'status': status,
                                    'pid': pid,
                                    'last_error': error,
                                    'updated_at': time.time()
                                }
                            }
                        },
                        'timestamp': time.time()
                    }
                }
                
                async_to_sync(channel_layer.group_send)('dashboard', message)
                self.stdout.write(f'📡 Broadcasted {process_name} status: {status}')
                
        except Exception as e:
            self.stdout.write(f'⚠️ Failed to broadcast status: {e}')