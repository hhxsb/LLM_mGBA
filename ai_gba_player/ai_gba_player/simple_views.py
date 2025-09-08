"""
Primary views and API endpoints for AI GBA Player.
All HTML/CSS/JS embedded directly for simplified architecture.
"""
from django.http import JsonResponse, HttpResponse
import time
import os
import json

from core.logging_config import get_logger
logger = get_logger(__name__)

# Simple configuration storage (in a real app this would be in database)
CONFIG_FILE = '/tmp/ai_gba_player_config.json'

def load_config():
    """Load configuration from database (primary) or file (fallback)"""
    try:
        # Try to load from database first
        from dashboard.models import Configuration
        db_config = Configuration.objects.first()
        if db_config:
            config_dict = db_config.to_dict()
            return {
                'rom_path': config_dict.get('rom_path', ''),
                'mgba_path': config_dict.get('mgba_path', ''),
                'llm_provider': config_dict.get('llm_provider', 'google'),
                'api_key': config_dict.get('providers', {}).get(config_dict.get('llm_provider', 'google'), {}).get('api_key', ''),
                'cooldown': config_dict.get('decision_cooldown', 3),
                'base_stabilization': 0.5,  # Not in DB model yet
                'movement_multiplier': 0.8,  # Not in DB model yet  
                'interaction_multiplier': 0.6,  # Not in DB model yet
                'menu_multiplier': 0.4,  # Not in DB model yet
                'max_wait_time': 10.0  # Not in DB model yet
            }
    except Exception as e:
        print(f"Database config failed, using file fallback: {e}")
        
    # Fallback to file-based config
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {
        'rom_path': '',
        'mgba_path': '',
        'llm_provider': 'gemini',
        'api_key': '',
        'cooldown': 3,
        'base_stabilization': 0.5,
        'movement_multiplier': 0.8,
        'interaction_multiplier': 0.6,
        'menu_multiplier': 0.4,
        'max_wait_time': 10.0
    }

def save_config_to_file(config):
    """Save configuration to database (primary) and file (backup)"""
    try:
        # Save to database first
        from dashboard.models import Configuration
        db_config = Configuration.objects.first()
        if not db_config:
            db_config = Configuration.objects.create()
        
        # Update database fields
        if 'rom_path' in config:
            db_config.rom_path = config['rom_path']
        if 'mgba_path' in config:
            db_config.mgba_path = config['mgba_path']
        if 'llm_provider' in config:
            db_config.llm_provider = config['llm_provider']
        if 'cooldown' in config:
            db_config.decision_cooldown = config['cooldown']
        
        # Update API key in providers JSON
        if 'api_key' in config and 'llm_provider' in config:
            providers = db_config.providers or {}
            provider_key = 'google' if config['llm_provider'] == 'gemini' else config['llm_provider']
            if provider_key not in providers:
                providers[provider_key] = {}
            providers[provider_key]['api_key'] = config['api_key']
            db_config.providers = providers
            
        db_config.save()
        
        # Also save to file as backup
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def dashboard_view(request):
    """Chat-based AI monitoring dashboard using Django templates"""
    from django.shortcuts import render
    
    # Load saved configuration
    config = load_config()
    
    # Prepare template context
    context = {
        'config': {
            'rom_path': config.get('rom_path', ''),
            'mgba_path': config.get('mgba_path', ''),
            'api_key': config.get('api_key', ''),
            'cooldown': config.get('cooldown', 3),
            'llm_provider': config.get('llm_provider', 'gemini'),
            'base_stabilization': config.get('base_stabilization', 0.5),
            'movement_multiplier': config.get('movement_multiplier', 0.8),
            'interaction_multiplier': config.get('interaction_multiplier', 0.6),
            'menu_multiplier': config.get('menu_multiplier', 0.4),
            'max_wait_time': config.get('max_wait_time', 10.0),
        }
    }
    
    return render(request, 'dashboard/simple_dashboard.html', context)


def config_view(_request):
    """Simple config view"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>⚙️ Configuration - AI GBA Player</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-primary { background: #3498db; color: white; }
            .btn-secondary { background: #95a5a6; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚙️ System Configuration</h1>
                <a href="/" style="color: white;">← Back to Dashboard</a>
            </div>
            
            <div class="card">
                <h2>🎮 ROM Configuration</h2>
                <form>
                    <div class="form-group">
                        <label for="rom_path">ROM File Path:</label>
                        <input type="text" id="rom_path" placeholder="/full/path/to/your/pokemon.gba">
                    </div>
                    <div class="form-group">
                        <label for="rom_name">Display Name:</label>
                        <input type="text" id="rom_name" placeholder="Pokemon Red">
                    </div>
                    <button type="submit" class="btn btn-primary">💾 Save ROM Config</button>
                </form>
            </div>
            
            <div class="card">
                <h2>🔧 mGBA Configuration</h2>
                <form>
                    <div class="form-group">
                        <label for="mgba_path">mGBA Executable Path:</label>
                        <input type="text" id="mgba_path" placeholder="/Applications/mGBA.app/Contents/MacOS/mGBA">
                        <small>Common paths: /Applications/mGBA.app/Contents/MacOS/mGBA (macOS)</small>
                    </div>
                    <button type="submit" class="btn btn-primary">💾 Save mGBA Config</button>
                </form>
            </div>
            
            <div class="card">
                <h2>📝 Instructions</h2>
                <p>1. Set the path to your GBA ROM file</p>
                <p>2. Configure the mGBA executable location</p>
                <p>3. Return to dashboard and launch the service</p>
                <p>4. Load the ROM in mGBA and run the Lua script</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html_content)

def restart_service(_request):
    """Start/restart the AI Game Service"""
    try:
        # Import the new AI service
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from dashboard.ai_game_service import start_ai_service, stop_ai_service, is_ai_service_running
        
        # Stop any existing service
        if is_ai_service_running():
            stop_ai_service()
            time.sleep(1)
        
        # Start the AI service
        success = start_ai_service()
        
        if success:
            return JsonResponse({
                'success': True,
                'message': '✅ mGBA connection ready!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '❌ Failed to start AI service'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'❌ Error: {str(e)}'
        })

def stop_service(_request):
    """Stop the AI Game Service"""
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from dashboard.ai_game_service import stop_ai_service, is_ai_service_running
        
        if is_ai_service_running():
            success = stop_ai_service()
            if success:
                return JsonResponse({
                    'success': True,
                    'message': '⏸️ mGBA connection stopped'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': '❌ Failed to stop AI service'
                })
        else:
            return JsonResponse({
                'success': True,
                'message': '⏸️ Service was not running'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'❌ Error: {str(e)}'
        })

def reset_llm_session(_request):
    """Reset the LLM session to clear conversation history"""
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from dashboard.ai_game_service import get_ai_service
        
        # Get the current AI service instance
        ai_service = get_ai_service()
        if ai_service:
            ai_service.reset_llm_session()
            return JsonResponse({
                'success': True,
                'message': '🔄 LLM session reset - fresh start!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '❌ No AI service running to reset'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'❌ Error resetting session: {str(e)}'
        })


def get_chat_messages(_request):
    """Get recent chat messages and service status"""
    try:
        from dashboard.ai_game_service import get_ai_service
        
        service = get_ai_service()
        if service and service.is_alive():
            # Get messages from service
            messages = getattr(service, 'chat_messages', [])
            message_counter = getattr(service, 'message_counter', 0)
            max_messages = getattr(service, 'max_messages', 100)
            
            return JsonResponse({
                'success': True,
                'messages': messages,
                'connected': service.mgba_connected,
                'decision_count': getattr(service, 'decision_count', 0),
                'total_messages': message_counter,
                'buffer_size': len(messages),
                'max_buffer_size': max_messages,
                'status': 'running'
            })
        else:
            return JsonResponse({
                'success': True, 
                'messages': [],
                'connected': False,
                'decision_count': 0,
                'status': 'stopped'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'messages': [],
            'connected': False,
            'decision_count': 0,
            'status': 'error'
        })

def launch_mgba_config(_request):
    """Launch mGBA with configured ROM"""
    try:
        # Load saved configuration
        config = load_config()
        mgba_path = config.get('mgba_path', '')
        rom_path = config.get('rom_path', '')
        
        # Function to resolve executable path for macOS app bundles
        def resolve_executable_path(path):
            if path.endswith('.app'):
                # It's a macOS app bundle, find the executable inside
                executable_name = os.path.basename(path).replace('.app', '')
                executable_path = os.path.join(path, 'Contents', 'MacOS', executable_name)
                if os.path.exists(executable_path):
                    return executable_path
                # Try common executable names for mGBA
                for name in ['mGBA', 'mgba-qt', 'mgba']:
                    executable_path = os.path.join(path, 'Contents', 'MacOS', name)
                    if os.path.exists(executable_path):
                        return executable_path
                return None
            return path if os.path.exists(path) else None
        
        # If no configured mGBA path, try to find it
        if not mgba_path:
            common_paths = [
                '/Applications/mGBA.app',  # macOS app bundle
                '/Applications/mGBA.app/Contents/MacOS/mGBA',  # macOS executable
                '/opt/homebrew/bin/mgba-qt',  # Homebrew
                '/usr/local/bin/mgba-qt',  # Local install
                '/usr/bin/mgba-qt',  # System install
            ]
            
            for path in common_paths:
                resolved_path = resolve_executable_path(path)
                if resolved_path and os.path.exists(resolved_path):
                    mgba_path = resolved_path
                    break
        else:
            # Resolve the configured path
            resolved_path = resolve_executable_path(mgba_path)
            if resolved_path:
                mgba_path = resolved_path
        
        if not mgba_path or not os.path.exists(mgba_path):
            return JsonResponse({
                'success': False,
                'message': 'mGBA executable not found. Please install mGBA or configure the correct executable path.'
            })
        
        # Check if the path is executable
        if not os.access(mgba_path, os.X_OK):
            return JsonResponse({
                'success': False,
                'message': f'mGBA executable found but not executable: {mgba_path}. Check file permissions.'
            })
        
        # Launch mGBA
        import subprocess
        launch_args = [mgba_path]
        
        # Add ROM if configured and exists
        if rom_path and os.path.exists(rom_path):
            launch_args.append(rom_path)
            message = f'mGBA launched with ROM: {os.path.basename(rom_path)}'
        else:
            message = 'mGBA launched. Load your ROM file manually.'
        
        process = subprocess.Popen(launch_args, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        return JsonResponse({
            'success': True,
            'message': f'{message} (PID: {process.pid})'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to launch mGBA: {str(e)}'
        })

def save_rom_config(request):
    """Save ROM configuration"""
    try:
        rom_path = request.POST.get('rom_path', '').strip()
        mgba_path = request.POST.get('mgba_path', '').strip()
        
        # Load existing config
        config = load_config()
        
        # Update ROM configuration
        config['rom_path'] = rom_path
        config['mgba_path'] = mgba_path
        
        # Validate paths
        validation_messages = []
        if rom_path and not os.path.exists(rom_path):
            validation_messages.append(f'⚠️ ROM file not found: {rom_path}')
        if mgba_path and not os.path.exists(mgba_path):
            validation_messages.append(f'⚠️ mGBA executable not found: {mgba_path}')
        
        # Save configuration
        if save_config_to_file(config):
            message = 'ROM configuration saved successfully!'
            if validation_messages:
                message += ' ' + ' '.join(validation_messages)
            
            return JsonResponse({
                'success': True,
                'message': message
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Failed to save configuration file'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving ROM config: {str(e)}'
        })

def save_ai_config(request):
    """Save AI configuration"""
    try:
        provider = request.POST.get('llm_provider', 'gemini')
        api_key = request.POST.get('api_key', '').strip()
        cooldown = int(request.POST.get('cooldown', '3'))
        
        # Get timing configuration values
        base_stabilization = float(request.POST.get('base_stabilization', '0.5'))
        movement_multiplier = float(request.POST.get('movement_multiplier', '0.8'))
        interaction_multiplier = float(request.POST.get('interaction_multiplier', '0.6'))
        menu_multiplier = float(request.POST.get('menu_multiplier', '0.4'))
        max_wait_time = float(request.POST.get('max_wait_time', '10.0'))
        
        # Load existing config
        config = load_config()
        
        # Update AI configuration
        config['llm_provider'] = provider
        config['api_key'] = api_key
        config['cooldown'] = cooldown
        
        # Update timing configuration
        config['base_stabilization'] = base_stabilization
        config['movement_multiplier'] = movement_multiplier
        config['interaction_multiplier'] = interaction_multiplier
        config['menu_multiplier'] = menu_multiplier
        config['max_wait_time'] = max_wait_time
        
        # Save configuration
        if save_config_to_file(config):
            # Also update the main config_emulator.json file
            success = _update_main_config_file(provider, api_key, cooldown)
            
            # Reload timing configuration in the running AI service
            try:
                from dashboard.ai_game_service import reload_ai_service_timing_config
                reload_ai_service_timing_config()
            except Exception as e:
                print(f"Warning: Could not reload AI service timing config: {e}")
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': f'AI configuration saved: {provider} provider with {cooldown}s cooldown + timing settings updated'
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': f'Configuration saved locally + timing settings updated. Warning: Could not update main config file.'
                })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Failed to save configuration file'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving AI config: {str(e)}'
        })

def _update_main_config_file(provider, api_key, cooldown):
    """Update the main config_emulator.json file with proper values"""
    try:
        import os
        from pathlib import Path
        
        # Find the project root (where config_emulator.json should be)
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent  # Go up two levels from ai_gba_player/ai_gba_player/
        config_path = project_root / 'config_emulator.json'
        
        if not config_path.exists():
            return False
        
        # Read the current config
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Update the configuration
        config_data['llm_provider'] = provider
        config_data['decision_cooldown'] = cooldown
        
        # Update the appropriate provider's API key
        if provider == 'gemini' or provider == 'google':
            config_data['providers']['google']['api_key'] = api_key
            config_data['llm_provider'] = 'google'  # Normalize to 'google'
        elif provider == 'openai':
            config_data['providers']['openai']['api_key'] = api_key
        elif provider == 'anthropic':
            config_data['providers']['anthropic']['api_key'] = api_key
        
        # Write back the updated config
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error updating main config: {e}")
        return False

# Duplicate stop_service function removed - kept the one above with better error handling

def chat_message(request):
    """Handle incoming chat messages (WebSocket alternative for now)"""
    try:
        message_type = request.POST.get('type', '')
        content = request.POST.get('content', '')
        
        # This would normally be handled by WebSocket
        # For now, return a mock response
        
        if message_type == 'image':
            return JsonResponse({
                'success': True,
                'message': 'Image received by AI',
                'response': 'I can see the game screen. Analyzing...',
                'actions': ['Press A', 'Move UP']
            })
        
        return JsonResponse({
            'success': True,
            'message': f'Message received: {content}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing message: {str(e)}'
        })

def save_memory_config(request):
    """Save memory system configuration"""
    try:
        # Get memory system configuration parameters
        enabled = request.POST.get('memory_enabled', 'true').lower() == 'true'
        system_type = request.POST.get('memory_system_type', 'auto')
        llm_provider = request.POST.get('memory_llm_provider', 'inherit')
        
        # Get API keys for different providers
        api_keys = {}
        if request.POST.get('memory_google_api_key', '').strip():
            api_keys['google'] = request.POST.get('memory_google_api_key').strip()
        if request.POST.get('memory_openai_api_key', '').strip():
            api_keys['openai'] = request.POST.get('memory_openai_api_key').strip()
        if request.POST.get('memory_anthropic_api_key', '').strip():
            api_keys['anthropic'] = request.POST.get('memory_anthropic_api_key').strip()
        
        # Get Neo4j configuration
        neo4j_uri = request.POST.get('memory_neo4j_uri', 'bolt://localhost:7687').strip()
        neo4j_username = request.POST.get('memory_neo4j_username', 'neo4j').strip()
        neo4j_password = request.POST.get('memory_neo4j_password', '').strip()
        neo4j_database = request.POST.get('memory_neo4j_database', 'neo4j').strip()
        
        # Get Graphiti configuration
        graphiti_llm_model = request.POST.get('memory_graphiti_llm_model', 'gemini-2.0-flash').strip()
        graphiti_embedding_model = request.POST.get('memory_graphiti_embedding_model', 'embedding-001').strip()
        graphiti_reranker_model = request.POST.get('memory_graphiti_reranker_model', 'gemini-2.5-flash-lite-preview-06-17').strip()
        
        # Get fallback configuration
        auto_fallback = request.POST.get('memory_auto_fallback', 'true').lower() == 'true'
        fallback_on_error = request.POST.get('memory_fallback_on_error', 'true').lower() == 'true'
        retry_attempts = int(request.POST.get('memory_retry_attempts', '3'))
        
        # Get or create Configuration instance
        from dashboard.models import Configuration
        config = Configuration.get_config()
        
        # Update memory configuration
        memory_config_update = {
            'enabled': enabled,
            'system_type': system_type,
            'llm_provider': llm_provider,
            'api_keys': api_keys,
            'neo4j': {
                'uri': neo4j_uri,
                'username': neo4j_username,
                'password': neo4j_password,
                'database': neo4j_database
            },
            'graphiti_config': {
                'llm_model': graphiti_llm_model,
                'embedding_model': graphiti_embedding_model,
                'reranker_model': graphiti_reranker_model
            },
            'fallback_config': {
                'auto_fallback': auto_fallback,
                'fallback_on_error': fallback_on_error,
                'retry_attempts': retry_attempts
            }
        }
        
        # Update and save configuration
        config.update_memory_config(memory_config_update)
        config.save()
        
        # Try to initialize or reinitialize memory system
        try:
            from core.memory_service import initialize_global_memory_system
            memory_system = initialize_global_memory_system()
            
            if memory_system:
                system_name = type(memory_system).__name__
                return JsonResponse({
                    'success': True,
                    'message': f'Memory system configuration saved and {system_name} initialized successfully'
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'Memory system configuration saved but system is disabled by configuration'
                })
        except Exception as init_error:
            return JsonResponse({
                'success': True,
                'message': f'Memory configuration saved but initialization failed: {str(init_error)}'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving memory config: {str(e)}'
        })

def get_memory_config(request):
    """Get current memory system configuration"""
    try:
        from dashboard.models import Configuration
        config = Configuration.get_config()
        memory_config = config.memory_system_config
        
        # Get memory system status
        try:
            from core.memory_service import get_global_memory_system, get_memory_stats
            memory_system = get_global_memory_system()
            stats = get_memory_stats()
            
            if memory_system:
                system_name = type(memory_system).__name__
                status = 'active'
            else:
                system_name = 'None'
                status = 'inactive'
        except Exception:
            system_name = 'Unknown'
            status = 'error'
            stats = {'status': 'error'}
        
        return JsonResponse({
            'success': True,
            'config': memory_config,
            'status': {
                'system_name': system_name,
                'status': status,
                'stats': stats
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting memory config: {str(e)}'
        })

def test_memory_connection(request):
    """Test memory system connections (Neo4j, API keys)"""
    try:
        from dashboard.models import Configuration
        config = Configuration.get_config()
        memory_config = config.memory_system_config
        
        results = {
            'neo4j': {'status': 'untested', 'message': ''},
            'api_key': {'status': 'untested', 'message': ''},
            'graphiti': {'status': 'untested', 'message': ''}
        }
        
        # Test Neo4j connection
        try:
            from neo4j import GraphDatabase
            neo4j_config = memory_config.get('neo4j', {})
            driver = GraphDatabase.driver(
                neo4j_config.get('uri', 'bolt://localhost:7687'),
                auth=(
                    neo4j_config.get('username', 'neo4j'),
                    neo4j_config.get('password', '')
                )
            )
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                if record and record['test'] == 1:
                    results['neo4j'] = {'status': 'success', 'message': 'Connected successfully'}
                else:
                    results['neo4j'] = {'status': 'error', 'message': 'Unexpected response'}
            driver.close()
        except ImportError:
            results['neo4j'] = {'status': 'error', 'message': 'neo4j package not installed'}
        except Exception as e:
            results['neo4j'] = {'status': 'error', 'message': str(e)}
        
        # Test API key availability
        llm_provider = memory_config.get('llm_provider', 'inherit')
        if llm_provider == 'inherit':
            # Check main configuration
            main_provider = config.llm_provider
            api_key = config.providers.get(main_provider, {}).get('api_key')
            if api_key:
                results['api_key'] = {'status': 'success', 'message': f'Using {main_provider} API key from main config'}
            else:
                results['api_key'] = {'status': 'error', 'message': f'No API key found for {main_provider} in main config'}
        else:
            # Check memory-specific API key
            api_keys = memory_config.get('api_keys', {})
            api_key = api_keys.get(llm_provider)
            if api_key:
                results['api_key'] = {'status': 'success', 'message': f'{llm_provider} API key configured'}
            else:
                results['api_key'] = {'status': 'error', 'message': f'No API key configured for {llm_provider}'}
        
        # Test Graphiti availability and Gemini support
        try:
            import graphiti_core
            # Check if Gemini components are available
            try:
                from graphiti_core.llm_client.gemini_client import GeminiClient
                from graphiti_core.embedder.gemini import GeminiEmbedder
                from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient
                results['graphiti'] = {'status': 'success', 'message': 'Graphiti with Google Gemini support available'}
            except ImportError:
                results['graphiti'] = {'status': 'warning', 'message': 'Graphiti available but missing Google Gemini support - install with: pip install "graphiti-core[google-genai]"'}
        except ImportError:
            results['graphiti'] = {'status': 'warning', 'message': 'Graphiti package not installed - will use SimpleMemorySystem'}
        
        # Overall status
        success_count = sum(1 for r in results.values() if r['status'] == 'success')
        total_tests = len(results)
        
        return JsonResponse({
            'success': True,
            'results': results,
            'summary': f'{success_count}/{total_tests} tests passed'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error testing memory connections: {str(e)}'
        })

def reset_memory_system(request):
    """Reset and reinitialize the memory system"""
    try:
        # Force reset the global memory system
        from core.memory_service import initialize_global_memory_system
        import core.memory_service
        
        # Clear the global instance
        core.memory_service._global_memory_system = None
        
        # Reinitialize
        memory_system = initialize_global_memory_system()
        
        if memory_system:
            system_name = type(memory_system).__name__
            return JsonResponse({
                'success': True,
                'message': f'Memory system reset and {system_name} initialized successfully'
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'Memory system reset - system is disabled by configuration'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error resetting memory system: {str(e)}'
        })