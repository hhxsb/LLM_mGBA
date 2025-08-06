from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
import psutil
import time
from dashboard.models import Process, ChatMessage, SystemLog, ProcessStatus

logger = logging.getLogger(__name__)


@api_view(['GET'])
def health_check(request):
    """Health check endpoint"""
    return Response({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'ai_gba_player'
    })


@api_view(['GET'])
def system_status(request):
    """Get current system status"""
    try:
        # Get process information
        processes = {}
        for process in Process.objects.all():
            processes[process.name] = {
                'status': process.status,
                'pid': process.pid,
                'port': process.port,
                'last_error': process.last_error,
                'updated_at': process.updated_at.isoformat() if process.updated_at else None
            }
        
        # Get system stats
        memory_usage = {}
        try:
            memory = psutil.virtual_memory()
            memory_usage = {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used
            }
        except Exception:
            pass
        
        return Response({
            'system': {
                'processes': processes,
                'uptime': time.time(),  # Simplified
                'memory_usage': memory_usage
            },
            'websocket': {
                'active_connections': 1,  # Simplified
                'uptime': time.time(),
                'message_count': ChatMessage.objects.count()
            },
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def process_status(request):
    """Get status of all processes"""
    try:
        processes = []
        for process in Process.objects.all():
            processes.append({
                'name': process.name,
                'status': process.status,
                'pid': process.pid,
                'port': process.port,
                'last_error': process.last_error,
                'created_at': process.created_at.isoformat(),
                'updated_at': process.updated_at.isoformat()
            })
        return Response({'processes': processes})
    except Exception as e:
        logger.error(f"Error getting process status: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def start_process(request, process_name):
    """Start a specific process"""
    try:
        if process_name not in ['game_control', 'video_capture', 'all']:
            return Response({'error': 'Invalid process name'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Use Django management command to start process
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        # Capture command output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            call_command('start_process', process_name, verbosity=1)
            output = captured_output.getvalue()
            sys.stdout = old_stdout
            
            # Get updated process status
            process = Process.objects.get(name=process_name)
            
            return Response({
                'message': f'Process {process_name} start initiated',
                'status': process.status,
                'pid': process.pid,
                'output': output
            })
        except Exception as cmd_error:
            sys.stdout = old_stdout
            logger.error(f"Error starting process {process_name}: {cmd_error}")
            return Response({
                'error': f'Failed to start {process_name}: {str(cmd_error)}',
                'output': captured_output.getvalue()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Error starting process {process_name}: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def stop_process(request, process_name):
    """Stop a specific process"""
    try:
        if process_name not in ['game_control', 'video_capture', 'all']:
            return Response({'error': 'Invalid process name'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Use Django management command to stop process
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        # Capture command output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            call_command('stop_process', process_name, verbosity=1)
            output = captured_output.getvalue()
            sys.stdout = old_stdout
            
            # Get updated process status
            try:
                process = Process.objects.get(name=process_name)
                return Response({
                    'message': f'Process {process_name} stop initiated',
                    'status': process.status,
                    'output': output
                })
            except Process.DoesNotExist:
                return Response({
                    'message': f'Process {process_name} stop initiated',
                    'status': 'stopped',
                    'output': output
                })
                
        except Exception as cmd_error:
            sys.stdout = old_stdout
            logger.error(f"Error stopping process {process_name}: {cmd_error}")
            return Response({
                'error': f'Failed to stop {process_name}: {str(cmd_error)}',
                'output': captured_output.getvalue()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Error stopping process {process_name}: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def restart_process(request, process_name):
    """Restart a specific process"""
    try:
        if process_name not in ['game_control', 'video_capture', 'all']:
            return Response({'error': 'Invalid process name'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Use Django management command to restart process
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        # Capture command output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            call_command('restart_process', process_name, verbosity=1)
            output = captured_output.getvalue()
            sys.stdout = old_stdout
            
            # Get updated process status
            try:
                process = Process.objects.get(name=process_name)
                return Response({
                    'message': f'Process {process_name} restart initiated',
                    'status': process.status,
                    'pid': process.pid,
                    'output': output
                })
            except Process.DoesNotExist:
                return Response({
                    'message': f'Process {process_name} restart initiated',
                    'status': 'unknown',
                    'output': output
                })
                
        except Exception as cmd_error:
            sys.stdout = old_stdout
            logger.error(f"Error restarting process {process_name}: {cmd_error}")
            return Response({
                'error': f'Failed to restart {process_name}: {str(cmd_error)}',
                'output': captured_output.getvalue()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Error restarting process {process_name}: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def recent_messages(request):
    """Get recent chat messages"""
    try:
        count = int(request.GET.get('count', 50))
        messages = []
        for msg in ChatMessage.objects.all()[:count]:
            messages.append({
                'id': msg.message_id,
                'type': msg.message_type,
                'source': msg.source,
                'content': msg.content,
                'timestamp': msg.timestamp,
                'sequence': msg.sequence,
                'created_at': msg.created_at.isoformat()
            })
        return Response({'messages': list(reversed(messages))})  # Oldest first
    except Exception as e:
        logger.error(f"Error getting recent messages: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def clear_messages(request):
    """Clear all chat messages"""
    try:
        count = ChatMessage.objects.count()
        ChatMessage.objects.all().delete()
        return Response({'message': f'Cleared {count} messages'})
    except Exception as e:
        logger.error(f"Error clearing messages: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def system_logs(request):
    """Get recent system logs"""
    try:
        count = int(request.GET.get('count', 100))
        process_name = request.GET.get('process')
        
        logs_query = SystemLog.objects.all()
        if process_name:
            logs_query = logs_query.filter(process_name=process_name)
        
        logs = []
        for log in logs_query[:count]:
            logs.append({
                'process_name': log.process_name,
                'level': log.level,
                'message': log.message,
                'timestamp': log.timestamp,
                'created_at': log.created_at.isoformat()
            })
        
        return Response({'logs': list(reversed(logs))})  # Oldest first
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
