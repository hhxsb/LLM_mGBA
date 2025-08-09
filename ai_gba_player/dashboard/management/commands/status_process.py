"""
Django management command to check status of AI GBA Player unified service.
"""

import sys
import time
from pathlib import Path
from django.core.management.base import BaseCommand
from dashboard.models import Process
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

# Import unified service
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'ai_gba_player'))

try:
    from core.unified_game_service import get_unified_service
except ImportError:
    try:
        from ai_gba_player.core.unified_game_service import get_unified_service
    except ImportError as e:
        print(f"Failed to import unified service: {e}")
        def get_unified_service(): raise ImportError("Unified service not available")

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check status of AI GBA Player system processes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'service_name',
            nargs='?',
            choices=['unified_service', 'all'],
            default='all',
            help='Name of the service to check (default: all)'
        )
        parser.add_argument(
            '--update-db',
            action='store_true',
            help='Update database with current service status'
        )
        parser.add_argument(
            '--broadcast',
            action='store_true', 
            help='Broadcast status updates via WebSocket'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed service information'
        )
    
    def handle(self, *args, **options):
        service_name = options['service_name']
        update_db = options['update_db']
        broadcast = options['broadcast']
        detailed = options['detailed']
        
        self.stdout.write('🔍 Checking service status...')
        
        if service_name in ['unified_service', 'all']:
            self._check_unified_service(update_db, broadcast, detailed)
        else:
            self.stdout.write(self.style.ERROR(f'❌ Unknown service: {service_name}'))
    
    def _check_unified_service(self, update_db, broadcast, detailed):
        """Check status of unified service"""
        service_name = 'unified_service'
        
        self.stdout.write('\n📊 Unified Game Service Status')
        self.stdout.write('=' * 50)
        
        try:
            process_obj = Process.objects.get(name=service_name)
        except Process.DoesNotExist:
            # Create service record if it doesn't exist
            process_obj = Process.objects.create(
                name=service_name,
                status='stopped'
            )
            self.stdout.write(f'📝 Created new service record for {service_name}')
        
        # Get actual service status
        actual_status = self._get_unified_service_status()
        
        # Display status
        status_icon = {
            'running': '▶️',
            'stopped': '⏸️',
            'error': '❌',
            'unknown': '❓'
        }.get(actual_status['status'], '❓')
        
        self.stdout.write(f'\n🔧 {service_name.upper()}')
        self.stdout.write(f'   Status: {status_icon} {actual_status["status"].title()}')
        
        if detailed and actual_status['status'] == 'running':
            service_info = actual_status.get('service_info', {})
            self.stdout.write(f'   Video Thread: {"✅ Alive" if service_info.get("video_thread_alive") else "❌ Dead"}')
            self.stdout.write(f'   Game Thread: {"✅ Alive" if service_info.get("game_thread_alive") else "❌ Dead"}')
            
            video_status = service_info.get('video_capture', {})
            if video_status:
                self.stdout.write(f'   Video Frames: {video_status.get("frame_count", 0)}')
                self.stdout.write(f'   Buffer Duration: {video_status.get("buffer_duration", 0):.1f}s')
        
        if actual_status.get('error'):
            self.stdout.write(f'   Error: {actual_status["error"]}')
        
        # Update database if requested
        if update_db and process_obj.status != actual_status['status']:
            process_obj.status = actual_status['status']
            if actual_status.get('error'):
                process_obj.last_error = actual_status['error'][:500]
            process_obj.save()
            self.stdout.write('   📝 Updated database')
        
        # Show summary
        self.stdout.write('\n📋 Summary:')
        if actual_status['status'] == 'running':
            self.stdout.write(self.style.SUCCESS('✅ Unified service is running'))
        elif actual_status['status'] == 'stopped':
            self.stdout.write(self.style.WARNING('⏸️ Unified service is stopped'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ Unified service status: {actual_status["status"]}'))
        
        # Broadcast status if requested
        if broadcast:
            self._broadcast_service_status(service_name, actual_status)
    
    def _get_unified_service_status(self):
        """Get the actual status of the unified service"""
        try:
            service = get_unified_service()
            
            if service.running:
                # Service is running, get detailed status
                service_status = service.get_status()
                return {
                    'status': 'running',
                    'service_info': service_status
                }
            else:
                return {
                    'status': 'stopped'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _broadcast_service_status(self, service_name, status):
        """Broadcast service status update"""
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                message = {
                    'type': 'system_status',
                    'message': {
                        'system': {
                            'processes': {
                                service_name: {
                                    'status': status['status'],
                                    'pid': None,  # Unified service doesn't use PIDs
                                    'last_error': status.get('error', ''),
                                    'updated_at': time.time(),
                                    'service_info': status.get('service_info', {})
                                }
                            }
                        },
                        'timestamp': time.time()
                    }
                }
                
                async_to_sync(channel_layer.group_send)('dashboard', message)
                self.stdout.write('   📡 Status broadcasted')
                
        except Exception as e:
            self.stdout.write(f'   ⚠️ Failed to broadcast: {e}')