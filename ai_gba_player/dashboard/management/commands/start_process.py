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
from dashboard.models import Process
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

# Import unified service  
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'ai_gba_player'))

try:
    from core.unified_game_service import get_unified_service, start_unified_service, stop_unified_service
except ImportError:
    try:
        from ai_gba_player.core.unified_game_service import get_unified_service, start_unified_service, stop_unified_service
    except ImportError as e:
        print(f"Failed to import unified service: {e}")
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
            default='config_emulator.json',
            help='Configuration file to use'
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
        config_path = project_root / config_file
        
        if not config_path.exists():
            raise CommandError(f'Config file not found: {config_path}')
        
        self.stdout.write(f'🚀 Starting service: {service_name}')
        self.stdout.write(f'📁 Project root: {project_root}')
        self.stdout.write(f'⚙️ Config file: {config_path}')
        
        if service_name in ['unified_service', 'all']:
            self._start_unified_service(str(config_path), force)
        else:
            raise CommandError(f'Unknown service: {service_name}')
    
    def _start_unified_service(self, config_path: str, force: bool):
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
            self.stdout.write(f'🚀 Starting unified service with config: {config_path}')
            
            # Start the unified service
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