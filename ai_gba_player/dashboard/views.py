from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Process, ChatMessage, SystemLog, ROMConfiguration, Configuration
import time
import json
import subprocess
import os
from pathlib import Path
from django.utils import timezone


def dashboard_view(request):
    """Main dashboard view"""
    from .models import Configuration
    
    # Get system configuration
    config = Configuration.get_config()
    
    # Get unified service status
    try:
        unified_service = Process.objects.get(name='unified_service')
    except Process.DoesNotExist:
        unified_service = None
    
    context = {
        'title': 'AI GBA Player',
        'page': 'dashboard',
        'config': config,
        'unified_service': unified_service
    }
    return render(request, 'dashboard/dashboard.html', context)


def admin_panel_view(request):
    """Admin panel view"""
    # Get current process status
    processes = Process.objects.all()
    recent_logs = SystemLog.objects.all()[:20]
    roms = ROMConfiguration.objects.all()
    
    context = {
        'title': 'System Control - AI GBA Player',
        'page': 'admin',
        'processes': processes,
        'recent_logs': recent_logs,
        'roms': roms
    }
    return render(request, 'dashboard/admin_panel.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def restart_service(request):
    """API endpoint to restart the unified service"""
    try:
        # Kill any existing unified service processes
        try:
            subprocess.run(['pkill', '-f', 'unified_game_service.py'], check=False)
            time.sleep(2)  # Wait for cleanup
        except:
            pass
        
        # Start the unified service directly using subprocess
        project_root = Path(__file__).parent.parent.parent.parent
        service_script = project_root / "ai_gba_player" / "core" / "unified_game_service.py"
        config_file = project_root / "config_emulator.json"
        
        if service_script.exists() and config_file.exists():
            # Start the service in background
            process = subprocess.Popen([
                'python', str(service_script), 
                '--config', str(config_file),
                '--debug'
            ], 
            cwd=str(project_root),
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
            )
            
            # Give it a moment to start
            time.sleep(3)
            
            # Check if it's still running
            if process.poll() is None:
                # Update database status
                try:
                    unified_service, created = Process.objects.get_or_create(name='unified_service')
                    unified_service.status = 'running'
                    unified_service.pid = process.pid
                    unified_service.last_heartbeat = timezone.now()
                    unified_service.save()
                except:
                    pass  # Database update is optional
                
                return JsonResponse({
                    'success': True,
                    'message': 'Unified service started successfully!'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Unified service failed to start'
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Unified service script or config not found'
            }, status=500)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to restart service: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def launch_mgba_from_config(request):
    """API endpoint to launch mGBA using system configuration"""
    from .models import Configuration
    
    try:
        config = Configuration.get_config()
        
        # Validate ROM path exists
        if not config.rom_path or not os.path.exists(config.rom_path):
            return JsonResponse({
                'success': False,
                'message': f'ROM file not found. Please configure ROM path in System Config.'
            }, status=404)
        
        # Determine mGBA path
        if config.mgba_path and os.path.exists(config.mgba_path):
            mgba_path = config.mgba_path
        else:
            mgba_path = _find_mgba_executable()
        
        if not mgba_path or not os.path.exists(mgba_path):
            return JsonResponse({
                'success': False,
                'message': 'mGBA executable not found. Please configure mGBA path in System Config.'
            }, status=404)
        
        # Launch mGBA with ROM
        try:
            subprocess.Popen([mgba_path, config.rom_path])
            
            rom_name = config.rom_display_name or os.path.basename(config.rom_path)
            
            return JsonResponse({
                'success': True,
                'message': f'mGBA launched with {rom_name}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Failed to launch mGBA: {str(e)}'
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def launch_mgba(request):
    """API endpoint to launch mGBA with a ROM"""
    try:
        data = json.loads(request.body)
        rom_id = data.get('rom_id')
        
        if not rom_id:
            return JsonResponse({
                'success': False,
                'message': 'ROM ID is required'
            }, status=400)
        
        rom_config = get_object_or_404(ROMConfiguration, id=rom_id)
        
        # Validate ROM file exists
        if not rom_config.rom_file or not os.path.exists(rom_config.rom_file.stored_path):
            return JsonResponse({
                'success': False,
                'message': f'ROM file not found: {rom_config.rom_file.stored_path if rom_config.rom_file else "No ROM file"}'
            }, status=404)
        
        # Determine mGBA path
        if rom_config.mgba_file and os.path.exists(rom_config.mgba_file.stored_path):
            mgba_path = rom_config.mgba_file.stored_path
        else:
            mgba_path = _find_mgba_executable()
        
        if not mgba_path or not os.path.exists(mgba_path):
            return JsonResponse({
                'success': False,
                'message': 'mGBA executable not found. Please configure mGBA path in ROM settings.'
            }, status=404)
        
        # Launch mGBA with ROM
        try:
            subprocess.Popen([mgba_path, rom_config.rom_file.stored_path])
            
            # Update last used timestamp
            rom_config.last_used = timezone.now()
            rom_config.save()
            
            return JsonResponse({
                'success': True,
                'message': f'mGBA launched with {rom_config.display_name}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Failed to launch mGBA: {str(e)}'
            }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


def rom_config_view(request):
    """ROM configuration management view"""
    roms = ROMConfiguration.objects.all()
    
    # This view now only handles GET requests - ROM creation is handled by API endpoints
    context = {
        'title': 'ROM Configuration - AI GBA Player',
        'page': 'rom_config',
        'roms': roms
    }
    return render(request, 'dashboard/rom_config.html', context)


@require_http_methods(["POST"])
def delete_rom_config(request, rom_id):
    """Delete ROM configuration"""
    try:
        rom = get_object_or_404(ROMConfiguration, id=rom_id)
        rom_name = rom.display_name
        rom.delete()
        messages.success(request, f'ROM configuration "{rom_name}" deleted successfully')
    except Exception as e:
        messages.error(request, f'Error deleting ROM configuration: {str(e)}')
    
    return redirect('rom_config')


def _find_mgba_executable():
    """Try to find mGBA executable in common locations"""
    common_paths = [
        # macOS
        '/Applications/mGBA.app/Contents/MacOS/mGBA',
        # Windows
        'C:\\Program Files\\mGBA\\mGBA.exe',
        'C:\\Program Files (x86)\\mGBA\\mGBA.exe',
        # Linux
        '/usr/bin/mgba-qt',
        '/usr/local/bin/mgba-qt',
        # Homebrew on macOS
        '/opt/homebrew/bin/mgba-qt',
        '/usr/local/bin/mgba-qt'
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    # Try to find in PATH
    try:
        result = subprocess.run(['which', 'mgba-qt'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    try:
        result = subprocess.run(['which', 'mGBA'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    return None


def config_view(request):
    """Configuration management view"""
    config = Configuration.get_config()
    
    if request.method == 'POST':
        try:
            # Handle configuration updates
            action = request.POST.get('action')
            
            if action == 'update_basic':
                # Update basic settings
                config.game = request.POST.get('game', config.game)
                config.llm_provider = request.POST.get('llm_provider', config.llm_provider)
                config.host = request.POST.get('host', config.host)
                config.port = int(request.POST.get('port', config.port))
                config.decision_cooldown = int(request.POST.get('decision_cooldown', config.decision_cooldown))
                config.debug_mode = request.POST.get('debug_mode') == 'on'
                config.save()
                messages.success(request, 'Basic configuration updated successfully')
                
            elif action == 'update_paths':
                # Update file paths
                config.notepad_path = request.POST.get('notepad_path', config.notepad_path)
                config.screenshot_path = request.POST.get('screenshot_path', config.screenshot_path)
                config.video_path = request.POST.get('video_path', config.video_path)
                config.prompt_template_path = request.POST.get('prompt_template_path', config.prompt_template_path)
                config.knowledge_file = request.POST.get('knowledge_file', config.knowledge_file)
                config.save()
                messages.success(request, 'File paths updated successfully')
                
            elif action == 'update_llm':
                # Update LLM provider settings
                providers = config.providers
                provider = request.POST.get('provider')
                
                if provider in providers:
                    providers[provider]['api_key'] = request.POST.get('api_key', '')
                    providers[provider]['model_name'] = request.POST.get('model_name', '')
                    providers[provider]['max_tokens'] = int(request.POST.get('max_tokens', 1024))
                
                config.providers = providers
                config.save()
                messages.success(request, f'{provider.title()} configuration updated successfully')
                
            elif action == 'update_advanced':
                # Update advanced JSON settings
                section = request.POST.get('section')
                json_data = request.POST.get('json_data')
                
                try:
                    parsed_data = json.loads(json_data)
                    
                    if section == 'capture_system':
                        config.capture_system = parsed_data
                    elif section == 'unified_service':
                        config.unified_service = parsed_data
                    elif section == 'dashboard':
                        config.dashboard = parsed_data
                    elif section == 'storage':
                        config.storage = parsed_data
                    
                    config.save()
                    messages.success(request, f'{section.replace("_", " ").title()} configuration updated successfully')
                    
                except json.JSONDecodeError as e:
                    messages.error(request, f'Invalid JSON format: {str(e)}')
                    
            elif action == 'reset_defaults':
                # Reset to default configuration
                defaults = Configuration.get_default_config()
                for key, value in defaults.items():
                    setattr(config, key, value)
                config.save()
                messages.success(request, 'Configuration reset to defaults successfully')
                
            elif action == 'update_rom_config':
                # Update ROM configuration
                config.rom_path = request.POST.get('rom_path', config.rom_path)
                config.rom_display_name = request.POST.get('rom_display_name', config.rom_display_name)
                config.save()
                messages.success(request, 'ROM configuration updated successfully')
                
            elif action == 'update_mgba_config':
                # Update mGBA configuration  
                config.mgba_path = request.POST.get('mgba_path', config.mgba_path)
                config.save()
                messages.success(request, 'mGBA configuration updated successfully')
                
            elif action == 'import_json':
                # Import configuration from existing JSON file
                try:
                    project_root = Path(__file__).parent.parent.parent.parent
                    config_file = project_root / "config_emulator.json"
                    
                    if config_file.exists():
                        with open(config_file, 'r') as f:
                            json_config = json.load(f)
                        
                        # Map JSON config to model fields
                        config.game = json_config.get('game', config.game)
                        config.llm_provider = json_config.get('llm_provider', config.llm_provider)
                        config.providers = json_config.get('providers', config.providers)
                        config.host = json_config.get('host', config.host)
                        config.port = json_config.get('port', config.port)
                        config.notepad_path = json_config.get('notepad_path', config.notepad_path)
                        config.screenshot_path = json_config.get('screenshot_path', config.screenshot_path)
                        config.video_path = json_config.get('video_path', config.video_path)
                        config.prompt_template_path = json_config.get('prompt_template_path', config.prompt_template_path)
                        config.knowledge_file = json_config.get('knowledge_file', config.knowledge_file)
                        config.decision_cooldown = json_config.get('decision_cooldown', config.decision_cooldown)
                        config.thinking_history_max_chars = json_config.get('thinking_history_max_chars', config.thinking_history_max_chars)
                        config.thinking_history_keep_entries = json_config.get('thinking_history_keep_entries', config.thinking_history_keep_entries)
                        config.llm_timeout_seconds = json_config.get('llm_timeout_seconds', config.llm_timeout_seconds)
                        config.debug_mode = json_config.get('debug_mode', config.debug_mode)
                        config.capture_system = json_config.get('capture_system', config.capture_system)
                        config.dual_process_mode = json_config.get('dual_process_mode', config.dual_process_mode)
                        config.unified_service = json_config.get('unified_service', config.unified_service)
                        config.dashboard = json_config.get('dashboard', config.dashboard)
                        config.storage = json_config.get('storage', config.storage)
                        
                        config.save()
                        messages.success(request, 'Configuration imported from JSON file successfully')
                    else:
                        messages.error(request, 'config_emulator.json not found')
                        
                except Exception as e:
                    messages.error(request, f'Error importing JSON configuration: {str(e)}')
                    
            return redirect('config')
            
        except Exception as e:
            messages.error(request, f'Error updating configuration: {str(e)}')
    
    context = {
        'title': 'Configuration - AI GBA Player',
        'page': 'config',
        'config': config,
        'providers_json': json.dumps(config.providers, indent=2),
        'capture_system_json': json.dumps(config.capture_system, indent=2),
        'unified_service_json': json.dumps(config.unified_service, indent=2),
        'dashboard_json': json.dumps(config.dashboard, indent=2),
        'storage_json': json.dumps(config.storage, indent=2),
    }
    return render(request, 'dashboard/config.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def export_config(request):
    """API endpoint to export current configuration as JSON"""
    try:
        config = Configuration.get_config()
        config_dict = config.to_dict()
        
        response = JsonResponse(config_dict, indent=2)
        response['Content-Disposition'] = 'attachment; filename="ai_gba_player_config.json"'
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to export configuration: {str(e)}'
        }, status=500)


def get_config_json():
    """Utility function to get configuration as JSON (for backward compatibility)"""
    try:
        config = Configuration.get_config()
        return config.to_dict()
    except Exception:
        # Fallback to default configuration if database is not available
        return Configuration.get_default_config()


@csrf_exempt
@require_http_methods(["GET"])
def browse_files(request):
    """API endpoint for file browsing"""
    try:
        path = request.GET.get('path', os.path.expanduser('~'))
        file_type = request.GET.get('type', 'all')  # 'files', 'folders', 'all'
        
        # Security: Ensure path is absolute and safe
        path = os.path.abspath(path)
        if not os.path.exists(path) or not os.path.isdir(path):
            path = os.path.expanduser('~')
        
        items = []
        
        try:
            # Add parent directory option (except for root)
            parent_path = os.path.dirname(path)
            if parent_path != path:  # Not at root
                items.append({
                    'name': '.. (Parent Directory)',
                    'path': parent_path,
                    'type': 'parent',
                    'icon': '📁'
                })
            
            # List directory contents
            for item_name in sorted(os.listdir(path)):
                if item_name.startswith('.'):  # Skip hidden files
                    continue
                    
                item_path = os.path.join(path, item_name)
                
                if os.path.isdir(item_path):
                    if file_type in ['folders', 'all']:
                        items.append({
                            'name': item_name,
                            'path': item_path,
                            'type': 'folder',
                            'icon': '📁'
                        })
                else:
                    if file_type in ['files', 'all']:
                        # Determine file icon based on extension
                        icon = '📄'
                        ext = os.path.splitext(item_name)[1].lower()
                        if ext in ['.gba', '.gbc', '.gb']:
                            icon = '🎮'
                        elif ext in ['.json']:
                            icon = '⚙️'
                        elif ext in ['.txt', '.md']:
                            icon = '📝'
                        elif ext in ['.png', '.jpg', '.jpeg', '.gif']:
                            icon = '🖼️'
                        elif ext in ['.mp4', '.avi', '.mov']:
                            icon = '🎬'
                        elif ext in ['.lua']:
                            icon = '📜'
                        
                        items.append({
                            'name': item_name,
                            'path': item_path,
                            'type': 'file',
                            'icon': icon,
                            'size': os.path.getsize(item_path)
                        })
                        
        except PermissionError:
            return JsonResponse({
                'success': False,
                'message': 'Permission denied accessing directory'
            }, status=403)
            
        return JsonResponse({
            'success': True,
            'current_path': path,
            'items': items
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error browsing files: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_common_paths(request):
    """API endpoint to get common system paths"""
    try:
        path_type = request.GET.get('type', 'general')
        
        common_paths = {
            'general': {
                'Home Directory': os.path.expanduser('~'),
                'Desktop': os.path.join(os.path.expanduser('~'), 'Desktop'),
                'Documents': os.path.join(os.path.expanduser('~'), 'Documents'),
                'Downloads': os.path.join(os.path.expanduser('~'), 'Downloads'),
                'Current Project': str(Path(__file__).parent.parent.parent.parent),
            },
            'roms': {
                'Desktop': os.path.join(os.path.expanduser('~'), 'Desktop'),
                'Downloads': os.path.join(os.path.expanduser('~'), 'Downloads'),
                'Documents': os.path.join(os.path.expanduser('~'), 'Documents'),
                'ROMs Folder': os.path.join(os.path.expanduser('~'), 'ROMs'),
                'Games Folder': os.path.join(os.path.expanduser('~'), 'Games'),
            },
            'executables': {
                'Applications (macOS)': '/Applications',
                'Program Files (Windows)': 'C:\\Program Files',
                'Program Files x86 (Windows)': 'C:\\Program Files (x86)',
                '/usr/bin (Linux)': '/usr/bin',
                '/usr/local/bin (Linux)': '/usr/local/bin',
                'Homebrew': '/opt/homebrew/bin',
            }
        }
        
        paths = common_paths.get(path_type, common_paths['general'])
        
        # Filter to only existing paths
        existing_paths = {name: path for name, path in paths.items() if os.path.exists(path)}
        
        return JsonResponse({
            'success': True,
            'paths': existing_paths
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting common paths: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_file(request):
    """API endpoint for uploading ROM, mGBA, or script files with deduplication"""
    import hashlib
    import os
    from django.core.files.storage import default_storage
    from .models import ManagedFile
    
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'message': 'No file provided'
            }, status=400)
        
        uploaded_file = request.FILES['file']
        file_type = request.POST.get('file_type', 'rom')  # 'rom', 'executable', 'script'
        
        # Validate file type
        valid_types = ['rom', 'executable', 'script']
        if file_type not in valid_types:
            return JsonResponse({
                'success': False,
                'message': f'Invalid file type. Must be one of: {", ".join(valid_types)}'
            }, status=400)
        
        # Read file content and calculate hash for deduplication
        file_content = uploaded_file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check if file already exists
        try:
            existing_file = ManagedFile.objects.get(file_hash=file_hash)
            return JsonResponse({
                'success': True,
                'file_id': existing_file.id,
                'message': 'File already exists, reusing existing file',
                'existing': True,
                'file_data': {
                    'id': existing_file.id,
                    'original_name': existing_file.original_name,
                    'file_type': existing_file.file_type,
                    'file_size': existing_file.file_size,
                    'reference_count': existing_file.reference_count
                }
            })
        except ManagedFile.DoesNotExist:
            pass  # File doesn't exist, continue with upload
        
        # Create upload directory structure
        upload_dir = f'uploads/{file_type}s'
        os.makedirs(os.path.join(default_storage.location, upload_dir), exist_ok=True)
        
        # Generate unique filename using hash
        file_extension = os.path.splitext(uploaded_file.name)[1]
        stored_filename = f'{file_hash[:16]}{file_extension}'
        stored_path = os.path.join(upload_dir, stored_filename)
        
        # Save file to storage
        uploaded_file.seek(0)  # Reset file pointer
        full_path = default_storage.save(stored_path, uploaded_file)
        
        # Create ManagedFile record
        managed_file = ManagedFile.objects.create(
            file_hash=file_hash,
            original_name=uploaded_file.name,
            file_type=file_type,
            file_size=len(file_content),
            stored_path=default_storage.path(full_path),
            reference_count=0  # Will be incremented when used
        )
        
        return JsonResponse({
            'success': True,
            'file_id': managed_file.id,
            'message': 'File uploaded successfully',
            'existing': False,
            'file_data': {
                'id': managed_file.id,
                'original_name': managed_file.original_name,
                'file_type': managed_file.file_type,
                'file_size': managed_file.file_size,
                'reference_count': managed_file.reference_count
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error uploading file: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_rom_config(request):
    """API endpoint for creating ROM configuration from uploaded files"""
    from .models import ROMConfiguration, ManagedFile
    
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        rom_file_id = data.get('rom_file_id')
        mgba_file_id = data.get('mgba_file_id')
        script_file_id = data.get('script_file_id')
        
        if not rom_file_id:
            return JsonResponse({
                'success': False,
                'message': 'ROM file ID is required'
            }, status=400)
        
        try:
            rom_file = ManagedFile.objects.get(id=rom_file_id, file_type='rom')
        except ManagedFile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'ROM file not found'
            }, status=404)
        
        # Get optional files
        mgba_file = None
        if mgba_file_id:
            try:
                mgba_file = ManagedFile.objects.get(id=mgba_file_id, file_type='executable')
            except ManagedFile.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'mGBA executable not found'
                }, status=404)
        
        script_file = None
        if script_file_id:
            try:
                script_file = ManagedFile.objects.get(id=script_file_id, file_type='script')
            except ManagedFile.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Script file not found'
                }, status=404)
        
        # Create ROM configuration (auto-generation happens in save())
        rom_config = ROMConfiguration.objects.create(
            rom_file=rom_file,
            mgba_file=mgba_file,
            script_file=script_file
        )
        
        return JsonResponse({
            'success': True,
            'rom_config_id': rom_config.id,
            'message': 'ROM configuration created successfully',
            'config_data': {
                'id': rom_config.id,
                'display_name': rom_config.display_name,
                'game_type': rom_config.game_type,
                'rom_file': rom_config.rom_file.original_name,
                'mgba_file': rom_config.mgba_file.original_name if rom_config.mgba_file else None,
                'script_file': rom_config.script_file.original_name if rom_config.script_file else None,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating ROM configuration: {str(e)}'
        }, status=500)


@csrf_exempt  
@require_http_methods(["GET"])
def get_uploaded_files(request):
    """API endpoint to get list of uploaded files by type"""
    from .models import ManagedFile
    
    try:
        file_type = request.GET.get('type', 'all')  # 'rom', 'executable', 'script', 'all'
        
        if file_type == 'all':
            files = ManagedFile.objects.all()
        else:
            files = ManagedFile.objects.filter(file_type=file_type)
        
        files_data = []
        for file in files:
            files_data.append({
                'id': file.id,
                'original_name': file.original_name,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'reference_count': file.reference_count,
                'uploaded_at': file.uploaded_at.isoformat(),
                'is_orphaned': file.is_orphaned()
            })
        
        return JsonResponse({
            'success': True,
            'files': files_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting uploaded files: {str(e)}'
        }, status=500)


