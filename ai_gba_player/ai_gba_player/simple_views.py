"""
Simple views to get the dashboard UI working while debugging import issues
"""
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
import subprocess
import time
import os
import json
from pathlib import Path

# Simple configuration storage (in a real app this would be in database)
CONFIG_FILE = '/tmp/ai_gba_player_config.json'

def load_config():
    """Load configuration from file"""
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
        'cooldown': 3
    }

def save_config_to_file(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False

def dashboard_view(request):
    """Chat-based AI monitoring dashboard"""
    # Load saved configuration
    config = load_config()
    
    # Prepare template variables
    rom_path = config.get('rom_path', '')
    mgba_path = config.get('mgba_path', '')
    api_key = config.get('api_key', '')
    cooldown = config.get('cooldown', 3)
    provider = config.get('llm_provider', 'gemini')
    
    # Provider options
    gemini_selected = 'selected' if provider == 'gemini' else ''
    openai_selected = 'selected' if provider == 'openai' else ''
    anthropic_selected = 'selected' if provider == 'anthropic' else ''
    
    # Create HTML content with simple string replacement to avoid CSS brace conflicts
    html_template = '''<!DOCTYPE html>
<html>
<head>
    <title>🎮 AI GBA Player</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; height: 100vh; background: #f0f2f5; overflow: hidden; }
        .app-container { display: flex; height: 100vh; }
        .config-panel { width: 300px; background: white; border-right: 1px solid #e1e8ed; display: flex; flex-direction: column; }
        .config-header { padding: 20px; border-bottom: 1px solid #e1e8ed; background: #6366f1; color: white; }
        .config-content { padding: 20px; flex: 1; overflow-y: auto; }
        .config-section { margin-bottom: 25px; }
        .config-section h3 { font-size: 14px; font-weight: 600; margin-bottom: 10px; color: #374151; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 12px; font-weight: 500; margin-bottom: 5px; color: #6b7280; }
        .form-group input, .form-group select { width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
        .btn { width: 100%; padding: 10px; border: none; border-radius: 6px; font-weight: 500; cursor: pointer; margin-bottom: 8px; }
        .btn-primary { background: #6366f1; color: white; }
        .btn-success { background: #10b981; color: white; }
        .btn-outline { background: white; border: 1px solid #d1d5db; color: #374151; }
        .btn:hover { opacity: 0.9; }
        .status-indicator { display: inline-flex; align-items: center; font-size: 12px; padding: 4px 8px; border-radius: 4px; margin-top: 5px; }
        .status-running { background: #dcfce7; color: #166534; }
        .status-stopped { background: #fef3f2; color: #dc2626; }
        .chat-container { flex: 1; display: flex; flex-direction: column; }
        .chat-header { padding: 15px 20px; background: white; border-bottom: 1px solid #e1e8ed; display: flex; justify-content: between; align-items: center; }
        .chat-title { font-size: 18px; font-weight: 600; color: #1f2937; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 20px; background: #f9fafb; }
        .message { margin-bottom: 20px; display: flex; flex-direction: column; }
        .message-sent { align-items: flex-end; }
        .message-received { align-items: flex-start; }
        .message-bubble { max-width: 70%; padding: 12px 16px; border-radius: 18px; position: relative; }
        .message-sent .message-bubble { background: #6366f1; color: white; }
        .message-received .message-bubble { background: white; border: 1px solid #e1e8ed; }
        .message-timestamp { font-size: 11px; color: #6b7280; margin: 5px 8px; }
        .message-image { max-width: 300px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .message-actions { margin-top: 8px; padding-top: 8px; border-top: 1px solid #f3f4f6; }
        .action-item { display: inline-block; background: #f3f4f6; padding: 4px 8px; border-radius: 12px; font-size: 12px; margin: 2px; font-weight: 500; }
        .welcome-message { text-align: center; color: #6b7280; padding: 40px; }
        .chat-controls { padding: 15px 20px; background: white; border-top: 1px solid #e1e8ed; }
        .controls-row { display: flex; gap: 10px; }
        .control-btn { padding: 8px 12px; border: 1px solid #d1d5db; background: white; border-radius: 6px; font-size: 12px; cursor: pointer; }
        .control-btn:hover { background: #f9fafb; }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="config-panel">
            <div class="config-header">
                <h2>🎮 AI GBA Player</h2>
                <div class="status-indicator" id="service-status">
                    <span class="status-stopped">🔌 Connection Ready</span>
                </div>
            </div>
            <div class="config-content">
                <div class="config-section">
                    <h3>🔗 mGBA Connection</h3>
                    <button class="btn btn-success" onclick="startService()">🔗 Reset mGBA Connection</button>
                    <button class="btn btn-outline" onclick="stopService()">🔌 Stop Connection</button>
                    <button class="btn btn-primary" onclick="launchMGBA()">🎮 Launch mGBA</button>
                </div>
                <div class="config-section">
                    <h3>🎮 ROM Configuration</h3>
                    <div class="form-group">
                        <label>ROM File Path</label>
                        <input type="text" id="rom-path" value="ROM_PATH_PLACEHOLDER" placeholder="/path/to/game.gba">
                    </div>
                    <div class="form-group">
                        <label>mGBA Executable</label>
                        <input type="text" id="mgba-path" value="MGBA_PATH_PLACEHOLDER" placeholder="/Applications/mGBA.app/Contents/MacOS/mGBA">
                    </div>
                    <button class="btn btn-outline" onclick="saveConfig()">💾 Save Config</button>
                </div>
                <div class="config-section">
                    <h3>🤖 AI Settings</h3>
                    <div class="form-group">
                        <label>LLM Provider</label>
                        <select id="llm-provider">
                            <option value="gemini" GEMINI_SELECTED_PLACEHOLDER>Google Gemini</option>
                            <option value="openai" OPENAI_SELECTED_PLACEHOLDER>OpenAI</option>
                            <option value="anthropic" ANTHROPIC_SELECTED_PLACEHOLDER>Anthropic</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>API Key</label>
                        <input type="password" id="api-key" value="API_KEY_PLACEHOLDER" placeholder="Enter API key">
                    </div>
                    <div class="form-group">
                        <label>Decision Cooldown (seconds)</label>
                        <input type="number" id="cooldown" value="COOLDOWN_PLACEHOLDER" min="1" max="10">
                    </div>
                    <button class="btn btn-outline" onclick="saveAIConfig()">💾 Save AI Config</button>
                </div>
            </div>
        </div>
        <div class="chat-container">
            <div class="chat-header">
                <div class="chat-title">💬 AI Game Session</div>
            </div>
            <div class="chat-messages" id="chat-messages">
                <div class="welcome-message">
                    <h3>🎮 AI GBA Player Ready</h3>
                    <p>Configure your ROM and AI settings, then start the service to begin.</p>
                    <p>Images sent to AI and AI responses will appear here.</p>
                </div>
            </div>
            <div class="chat-controls">
                <div class="controls-row">
                    <button class="control-btn" onclick="clearChat()">🗑️ Clear Chat</button>
                    <button class="control-btn" onclick="exportChat()">📥 Export</button>
                    <button class="control-btn" onclick="toggleAutoScroll()" id="auto-scroll-btn">🔄 Auto-scroll: ON</button>
                    <span style="margin-left: auto; font-size: 12px; color: #6b7280;">
                        <span id="message-count">0</span> messages
                    </span>
                </div>
            </div>
        </div>
    </div>
    <script>
        let messageCount = 0;
        let autoScroll = true;
        let lastMessageCount = 0;
        let lastProcessedMessageId = 0;  // Track last processed message ID
        let pollingInterval = null;
        
        // Start polling for messages when page loads
        document.addEventListener('DOMContentLoaded', function() {
            startMessagePolling();
        });
        
        function startMessagePolling() {
            if (pollingInterval) {
                clearInterval(pollingInterval);
            }
            
            pollingInterval = setInterval(pollForMessages, 2000); // Poll every 2 seconds
            pollForMessages(); // Initial poll
        }
        
        function pollForMessages() {
            fetch('/api/chat-messages/')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.messages) {
                        // Handle message buffer rotation - check for message ID gaps
                        const messages = data.messages;
                        if (messages.length > 0) {
                            // Use message IDs to detect if buffer has rotated
                            const lastMessageId = messages[messages.length - 1].id;
                            if (lastMessageId && lastProcessedMessageId && lastMessageId < lastProcessedMessageId) {
                                // Buffer has rotated, clear chat and reload all messages
                                document.getElementById('chat-messages').innerHTML = '';
                                messages.forEach(message => displayMessage(message));
                                lastProcessedMessageId = lastMessageId;
                            } else {
                                // Normal incremental update
                                const newMessages = messages.filter(msg => 
                                    !lastProcessedMessageId || (msg.id && msg.id > lastProcessedMessageId)
                                );
                                newMessages.forEach(message => displayMessage(message));
                                if (newMessages.length > 0) {
                                    lastProcessedMessageId = newMessages[newMessages.length - 1].id;
                                }
                            }
                        }
                        
                        // Update service status with buffer info
                        updateServiceStatusFromData(data);
                        
                        // Show buffer status if available
                        if (data.total_messages && data.buffer_size) {
                            console.log(`Messages: ${data.buffer_size}/${data.max_buffer_size} (total: ${data.total_messages})`);
                        }
                    }
                })
                .catch(error => {
                    console.error('Error polling messages:', error);
                });
        }
        
        function displayMessage(message) {
            if (message.type === 'system') {
                addSystemMessage(message.content, message.timestamp);
            } else if (message.type === 'screenshot') {
                addScreenshotMessage(message.image_data, message.game_state, message.timestamp);
            } else if (message.type === 'ai_response') {
                addAIResponse(message.text, message.actions, message.timestamp);
            }
        }
        
        function addScreenshotMessage(imageData, gameState, timestamp = null) {
            const messagesContainer = document.getElementById('chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message message-sent';
            
            const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
            
            messageDiv.innerHTML = `
                <div class="message-bubble">
                    <div style="font-weight: 500; margin-bottom: 4px;">📤 Screenshot Sent to AI</div>
                    <img src="${imageData}" class="message-image" alt="Game screenshot">
                    <div style="font-size: 12px; margin-top: 8px; color: #6b7280;">${gameState}</div>
                </div>
                <div class="message-timestamp">${timeStr}</div>
            `;
            messagesContainer.appendChild(messageDiv);
            updateMessageCount();
            scrollToBottom();
        }
        
        function updateServiceStatusFromData(data) {
            if (data.status === 'running' && data.connected) {
                updateServiceStatus('🔗 Connected to mGBA', 'running');
            } else if (data.status === 'running' && !data.connected) {
                updateServiceStatus('⏳ Waiting for mGBA', 'running');
            } else if (data.status === 'stopped') {
                updateServiceStatus('🔌 Connection Ready', 'stopped');
            } else {
                updateServiceStatus('❌ Error', 'error');
            }
        }
        
        function startService() {
            updateServiceStatus('🔄 Connecting...', 'starting');
            fetch('/api/restart-service/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateServiceStatus('🔗 Connected', 'running');
                    addSystemMessage(data.message);
                } else {
                    updateServiceStatus('❌ Error', 'error');
                    addSystemMessage('Connection failed: ' + data.message);
                }
            })
            .catch(error => {
                updateServiceStatus('❌ Error', 'error');
                addSystemMessage('Connection error: ' + error.message);
            });
        }
        
        function stopService() {
            updateServiceStatus('🔌 Disconnecting...', 'stopping');
            fetch('/api/stop-service/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateServiceStatus('🔌 Connection Ready', 'stopped');
                    addSystemMessage(data.message);
                } else {
                    updateServiceStatus('❌ Error', 'error');
                    addSystemMessage('Failed to disconnect: ' + data.message);
                }
            })
            .catch(error => {
                updateServiceStatus('❌ Error', 'error');
                addSystemMessage('Disconnect error: ' + error.message);
            });
        }
        
        function launchMGBA() {
            fetch('/api/launch-mgba-config/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            })
            .then(response => response.json())
            .then(data => addSystemMessage(data.message))
            .catch(error => addSystemMessage('Error launching mGBA: ' + error.message));
        }
        
        function saveConfig() {
            const romPath = document.getElementById('rom-path').value;
            const mgbaPath = document.getElementById('mgba-path').value;
            
            const formData = new FormData();
            formData.append('rom_path', romPath);
            formData.append('mgba_path', mgbaPath);
            
            fetch('/api/save-rom-config/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                addSystemMessage(data.message);
            })
            .catch(error => addSystemMessage('Error saving ROM config: ' + error.message));
        }
        
        function saveAIConfig() {
            const provider = document.getElementById('llm-provider').value;
            const apiKey = document.getElementById('api-key').value;
            const cooldown = document.getElementById('cooldown').value;
            
            const formData = new FormData();
            formData.append('llm_provider', provider);
            formData.append('api_key', apiKey);
            formData.append('cooldown', cooldown);
            
            fetch('/api/save-ai-config/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                addSystemMessage(data.message);
            })
            .catch(error => addSystemMessage('Error saving AI config: ' + error.message));
        }
        
        function updateServiceStatus(text, status) {
            const statusEl = document.getElementById('service-status');
            statusEl.innerHTML = '<span class="status-' + status + '">' + text + '</span>';
        }
        
        function addSystemMessage(text, timestamp = null) {
            const messagesContainer = document.getElementById('chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message message-received';
            
            const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
            
            messageDiv.innerHTML = `
                <div class="message-bubble">
                    <div style="font-weight: 500; margin-bottom: 4px;">🤖 System</div>
                    <div>${text}</div>
                </div>
                <div class="message-timestamp">${timeStr}</div>
            `;
            
            const welcome = messagesContainer.querySelector('.welcome-message');
            if (welcome) welcome.remove();
            
            messagesContainer.appendChild(messageDiv);
            updateMessageCount();
            scrollToBottom();
        }
        
        function addImageMessage(imageUrl) {
            const messagesContainer = document.getElementById('chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message message-sent';
            messageDiv.innerHTML = `
                <div class="message-bubble">
                    <img src="${imageUrl}" class="message-image" alt="Game screenshot">
                </div>
                <div class="message-timestamp">${new Date().toLocaleTimeString()}</div>
            `;
            messagesContainer.appendChild(messageDiv);
            updateMessageCount();
            scrollToBottom();
        }
        
        function addAIResponse(response, actions, timestamp = null) {
            const messagesContainer = document.getElementById('chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message message-received';
            
            const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
            
            let actionsHtml = '';
            if (actions && actions.length > 0) {
                actionsHtml = '<div class="message-actions">' + 
                    actions.map(action => `<span class="action-item">🎮 ${action}</span>`).join('') + 
                    '</div>';
            }
            
            messageDiv.innerHTML = `
                <div class="message-bubble">
                    <div style="font-weight: 500; margin-bottom: 4px;">🤖 AI Response</div>
                    <div>${response}</div>
                    ${actionsHtml}
                </div>
                <div class="message-timestamp">${timeStr}</div>
            `;
            messagesContainer.appendChild(messageDiv);
            updateMessageCount();
            scrollToBottom();
        }
        
        function clearChat() {
            const messagesContainer = document.getElementById('chat-messages');
            messagesContainer.innerHTML = `
                <div class="welcome-message">
                    <h3>🎮 Chat Cleared</h3>
                    <p>New AI session ready to begin.</p>
                </div>
            `;
            messageCount = 0;
            lastMessageCount = 0; // Reset message tracking
            updateMessageCount();
        }
        
        function exportChat() {
            addSystemMessage('Chat export feature coming soon');
        }
        
        function toggleAutoScroll() {
            autoScroll = !autoScroll;
            const btn = document.getElementById('auto-scroll-btn');
            btn.textContent = `🔄 Auto-scroll: ${autoScroll ? 'ON' : 'OFF'}`;
        }
        
        function updateMessageCount() {
            messageCount++;
            document.getElementById('message-count').textContent = messageCount;
        }
        
        function scrollToBottom() {
            if (autoScroll) {
                const messagesContainer = document.getElementById('chat-messages');
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
        
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    </script>
</body>
</html>'''
    
    # Replace placeholders with actual values
    html_content = html_template.replace('ROM_PATH_PLACEHOLDER', rom_path)
    html_content = html_content.replace('MGBA_PATH_PLACEHOLDER', mgba_path)
    html_content = html_content.replace('API_KEY_PLACEHOLDER', api_key)
    html_content = html_content.replace('COOLDOWN_PLACEHOLDER', str(cooldown))
    html_content = html_content.replace('GEMINI_SELECTED_PLACEHOLDER', gemini_selected)
    html_content = html_content.replace('OPENAI_SELECTED_PLACEHOLDER', openai_selected)
    html_content = html_content.replace('ANTHROPIC_SELECTED_PLACEHOLDER', anthropic_selected)
    
    return HttpResponse(html_content)

def config_view(request):
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

def restart_service(request):
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

def stop_service(request):
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

def get_chat_messages(request):
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

def launch_mgba_config(request):
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
        
        # Load existing config
        config = load_config()
        
        # Update AI configuration
        config['llm_provider'] = provider
        config['api_key'] = api_key
        config['cooldown'] = cooldown
        
        # Save configuration
        if save_config_to_file(config):
            # Also update the main config_emulator.json file
            success = _update_main_config_file(provider, api_key, cooldown)
            if success:
                return JsonResponse({
                    'success': True,
                    'message': f'AI configuration saved: {provider} provider with {cooldown}s cooldown'
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': f'Configuration saved locally. Warning: Could not update main config file.'
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

def stop_service(request):
    """Stop the AI service"""
    try:
        from dashboard.ai_game_service import stop_ai_service
        
        success = stop_ai_service()
        if success:
            return JsonResponse({
                'success': True,
                'message': 'AI service stopped successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Failed to stop AI service'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error stopping service: {str(e)}'
        })

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
            'message': 'Message received'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing message: {str(e)}'
        })