"""
Django management command to stop Pokemon AI system processes.
"""

import signal
import time
import psutil
from django.core.management.base import BaseCommand, CommandError
from dashboard.models import Process
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Stop Pokemon AI system processes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'process_name',
            choices=['game_control', 'video_capture', 'knowledge_system', 'all'],
            help='Name of the process to stop'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force kill process if graceful shutdown fails'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=10,
            help='Timeout for graceful shutdown (seconds)'
        )
    
    def handle(self, *args, **options):
        process_name = options['process_name']
        force = options['force']
        timeout = options['timeout']
        
        self.stdout.write(f'🛑 Stopping process: {process_name}')
        
        if process_name == 'all':
            self._stop_all_processes(force, timeout)
        else:
            self._stop_single_process(process_name, force, timeout)
    
    def _stop_all_processes(self, force, timeout):
        """Stop all processes in reverse dependency order"""
        processes = ['knowledge_system', 'game_control', 'video_capture']
        
        for process_name in processes:
            try:
                self._stop_single_process(process_name, force, timeout)
                time.sleep(1)  # Brief pause between stops
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to stop {process_name}: {e}')
                )
                # Continue with other processes
                continue
        
        self.stdout.write(self.style.SUCCESS('✅ All processes stop sequence completed'))
    
    def _stop_single_process(self, process_name, force, timeout):
        """Stop a single process"""
        
        try:
            process_obj = Process.objects.get(name=process_name)
        except Process.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f'⚠️ Process {process_name} not found in database')
            )
            return
        
        if process_obj.status == 'stopped':
            self.stdout.write(
                self.style.WARNING(f'⚠️ Process {process_name} is already stopped')
            )
            return
        
        if not process_obj.pid:
            self.stdout.write(
                self.style.WARNING(f'⚠️ No PID found for process {process_name}')
            )
            # Update status anyway
            process_obj.status = 'stopped'
            process_obj.pid = None
            process_obj.save()
            self._broadcast_process_status(process_name, 'stopped')
            return
        
        # Check if process is actually running
        if not self._is_process_running(process_obj.pid):
            self.stdout.write(
                self.style.WARNING(f'⚠️ Process {process_name} (PID: {process_obj.pid}) is not running')
            )
            # Clean up database record
            process_obj.status = 'stopped'
            process_obj.pid = None
            process_obj.save()
            self._broadcast_process_status(process_name, 'stopped')
            return
        
        self.stdout.write(f'🔄 Stopping {process_name} (PID: {process_obj.pid})')
        
        # Broadcast stopping status
        self._broadcast_process_status(process_name, 'stopping')
        
        try:
            process = psutil.Process(process_obj.pid)
            
            # Try graceful shutdown first
            if not force:
                self.stdout.write(f'🤝 Attempting graceful shutdown...')
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=timeout)
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Process {process_name} stopped gracefully')
                    )
                except psutil.TimeoutExpired:
                    if force:
                        self.stdout.write(f'⚡ Graceful shutdown timed out, force killing...')
                        process.kill()
                        process.wait(timeout=5)  # Wait for force kill
                        self.stdout.write(
                            self.style.WARNING(f'⚠️ Process {process_name} force killed')
                        )
                    else:
                        raise CommandError(
                            f'Process {process_name} did not stop gracefully within {timeout}s. '
                            f'Use --force to kill it.'
                        )
            else:
                # Force kill immediately
                self.stdout.write(f'⚡ Force killing process...')
                process.kill()
                process.wait(timeout=5)
                self.stdout.write(
                    self.style.WARNING(f'⚠️ Process {process_name} force killed')
                )
            
            # Update database
            process_obj.status = 'stopped'
            process_obj.pid = None
            process_obj.save()
            
            # Broadcast success
            self._broadcast_process_status(process_name, 'stopped')
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Process {process_name} stopped successfully')
            )
            
        except psutil.NoSuchProcess:
            # Process already dead
            self.stdout.write(
                self.style.WARNING(f'⚠️ Process {process_name} was already dead')
            )
            process_obj.status = 'stopped'
            process_obj.pid = None
            process_obj.save()
            self._broadcast_process_status(process_name, 'stopped')
            
        except psutil.AccessDenied:
            error_msg = f'Access denied when trying to stop process {process_name}'
            self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
            
            process_obj.status = 'error'
            process_obj.last_error = error_msg
            process_obj.save()
            self._broadcast_process_status(process_name, 'error', error=error_msg)
            
            raise CommandError(error_msg)
            
        except Exception as e:
            error_msg = str(e)
            self.stdout.write(self.style.ERROR(f'❌ Exception stopping {process_name}: {error_msg}'))
            
            process_obj.status = 'error'
            process_obj.last_error = error_msg[:500]
            process_obj.save()
            self._broadcast_process_status(process_name, 'error', error=error_msg)
            
            raise CommandError(f'Failed to stop {process_name}: {error_msg}')
    
    def _is_process_running(self, pid):
        """Check if a process is running by PID"""
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _broadcast_process_status(self, process_name, status, error=None):
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
                                    'pid': None if status == 'stopped' else 'unknown',
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