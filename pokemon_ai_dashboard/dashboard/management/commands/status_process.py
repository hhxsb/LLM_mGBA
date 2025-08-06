"""
Django management command to check status of Pokemon AI system processes.
"""

import psutil
import time
from django.core.management.base import BaseCommand
from dashboard.models import Process
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check status of Pokemon AI system processes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'process_name',
            nargs='?',
            choices=['game_control', 'video_capture', 'knowledge_system', 'all'],
            default='all',
            help='Name of the process to check (default: all)'
        )
        parser.add_argument(
            '--update-db',
            action='store_true',
            help='Update database with current process status'
        )
        parser.add_argument(
            '--broadcast',
            action='store_true', 
            help='Broadcast status updates via WebSocket'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed process information'
        )
    
    def handle(self, *args, **options):
        process_name = options['process_name']
        update_db = options['update_db']
        broadcast = options['broadcast']
        detailed = options['detailed']
        
        self.stdout.write('🔍 Checking process status...')
        
        if process_name == 'all':
            self._check_all_processes(update_db, broadcast, detailed)
        else:
            self._check_single_process(process_name, update_db, broadcast, detailed)
    
    def _check_all_processes(self, update_db, broadcast, detailed):
        """Check status of all processes"""
        processes = ['game_control', 'video_capture', 'knowledge_system']
        
        self.stdout.write('\n📊 System Process Status')
        self.stdout.write('=' * 50)
        
        all_status = {}
        
        for process_name in processes:
            status = self._check_single_process(process_name, update_db, False, detailed)
            all_status[process_name] = status
        
        # Show summary
        self.stdout.write('\n📋 Summary:')
        running_count = sum(1 for status in all_status.values() if status['status'] == 'running')
        self.stdout.write(f'  Running: {running_count}/{len(processes)} processes')
        
        if running_count == len(processes):
            self.stdout.write(self.style.SUCCESS('✅ All processes are running'))
        elif running_count == 0:
            self.stdout.write(self.style.ERROR('❌ No processes are running'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ Some processes are not running'))
        
        # Broadcast all status if requested
        if broadcast:
            self._broadcast_all_status(all_status)
    
    def _check_single_process(self, process_name, update_db, broadcast, detailed):
        """Check status of a single process"""
        
        try:
            process_obj = Process.objects.get(name=process_name)
        except Process.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ Process {process_name} not found in database')
            )
            return {'status': 'unknown', 'error': 'Not found in database'}
        
        # Check actual process status
        actual_status = self._get_actual_process_status(process_obj)
        
        # Display status
        status_icon = {
            'running': '▶️',
            'stopped': '⏸️',
            'error': '❌',
            'unknown': '❓'
        }.get(actual_status['status'], '❓')
        
        self.stdout.write(f'\n🔧 {process_name.upper()}')
        self.stdout.write(f'   Status: {status_icon} {actual_status["status"].title()}')
        
        if actual_status['pid']:
            self.stdout.write(f'   PID: {actual_status["pid"]}')
            
            if detailed and actual_status['status'] == 'running':
                try:
                    proc = psutil.Process(actual_status['pid'])
                    self.stdout.write(f'   CPU: {proc.cpu_percent():.1f}%')
                    mem_info = proc.memory_info()
                    self.stdout.write(f'   Memory: {mem_info.rss / 1024 / 1024:.1f} MB')
                    self.stdout.write(f'   Started: {time.ctime(proc.create_time())}')
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        
        if process_obj.port:
            self.stdout.write(f'   Port: {process_obj.port}')
        
        if actual_status.get('error'):
            self.stdout.write(f'   Error: {actual_status["error"]}')
        
        if process_obj.last_error and actual_status['status'] == 'error':
            self.stdout.write(f'   Last Error: {process_obj.last_error[:100]}...')
        
        # Update database if requested
        if update_db and (
            process_obj.status != actual_status['status'] or 
            process_obj.pid != actual_status['pid']
        ):
            process_obj.status = actual_status['status']
            process_obj.pid = actual_status['pid']
            if actual_status.get('error'):
                process_obj.last_error = actual_status['error'][:500]
            process_obj.save()
            
            self.stdout.write('   📝 Updated database')
        
        # Broadcast if requested
        if broadcast:
            self._broadcast_process_status(process_name, actual_status)
        
        return actual_status
    
    def _get_actual_process_status(self, process_obj):
        """Get the actual status of a process"""
        
        if not process_obj.pid:
            return {
                'status': 'stopped',
                'pid': None
            }
        
        try:
            process = psutil.Process(process_obj.pid)
            
            if process.is_running():
                return {
                    'status': 'running',
                    'pid': process_obj.pid
                }
            else:
                return {
                    'status': 'stopped',
                    'pid': None,
                    'error': 'Process is not running'
                }
                
        except psutil.NoSuchProcess:
            return {
                'status': 'stopped',
                'pid': None,
                'error': 'Process not found'
            }
        except psutil.AccessDenied:
            return {
                'status': 'unknown',
                'pid': process_obj.pid,
                'error': 'Access denied'
            }
        except Exception as e:
            return {
                'status': 'error',
                'pid': process_obj.pid,
                'error': str(e)
            }
    
    def _broadcast_process_status(self, process_name, status):
        """Broadcast single process status update"""
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                message = {
                    'type': 'system_status',
                    'message': {
                        'system': {
                            'processes': {
                                process_name: {
                                    'status': status['status'],
                                    'pid': status['pid'],
                                    'last_error': status.get('error', ''),
                                    'updated_at': time.time()
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
    
    def _broadcast_all_status(self, all_status):
        """Broadcast all process status updates"""
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                processes_status = {}
                for process_name, status in all_status.items():
                    processes_status[process_name] = {
                        'status': status['status'],
                        'pid': status['pid'],
                        'last_error': status.get('error', ''),
                        'updated_at': time.time()
                    }
                
                message = {
                    'type': 'system_status',
                    'message': {
                        'system': {
                            'processes': processes_status
                        },
                        'timestamp': time.time()
                    }
                }
                
                async_to_sync(channel_layer.group_send)('dashboard', message)
                self.stdout.write('\n📡 All status updates broadcasted')
                
        except Exception as e:
            self.stdout.write(f'\n⚠️ Failed to broadcast all status: {e}')