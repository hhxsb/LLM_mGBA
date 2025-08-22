"""
Primary views and API endpoints for AI GBA Player.
All HTML/CSS/JS embedded directly for simplified architecture.
"""
from django.http import JsonResponse, HttpResponse
import subprocess
import time
import os
import json
from pathlib import Path

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
    """Chat-based AI monitoring dashboard"""
    # Load saved configuration
    config = load_config()
    
    # Prepare template variables
    rom_path = config.get('rom_path', '')
    mgba_path = config.get('mgba_path', '')
    api_key = config.get('api_key', '')
    cooldown = config.get('cooldown', 3)
    provider = config.get('llm_provider', 'gemini')
    
    # Timing configuration
    base_stabilization = config.get('base_stabilization', 0.5)
    movement_multiplier = config.get('movement_multiplier', 0.8)
    interaction_multiplier = config.get('interaction_multiplier', 0.6)
    menu_multiplier = config.get('menu_multiplier', 0.4)
    max_wait_time = config.get('max_wait_time', 10.0)
    
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
        .notepad-display { border: 1px solid #e1e8ed; border-radius: 6px; background: #f8f9fa; overflow: hidden; }
        .notepad-header { background: #6366f1; color: white; padding: 8px 12px; display: flex; justify-content: space-between; font-size: 11px; }
        .notepad-status { font-weight: 500; }
        .entry-count { opacity: 0.8; }
        .notepad-content { max-height: 180px; overflow-y: auto; padding: 8px; font-family: 'Monaco', 'Menlo', monospace; font-size: 11px; line-height: 1.4; }
        .notepad-entry { background: white; border: 1px solid #e1e8ed; border-radius: 4px; padding: 6px 8px; margin-bottom: 6px; }
        .notepad-entry:last-child { margin-bottom: 0; }
        .notepad-entry-header { color: #6366f1; font-weight: 600; margin-bottom: 2px; }
        .notepad-entry-content { color: #374151; white-space: pre-wrap; }
        .notepad-entry.new { background: #fef3cd; border-color: #f59e0b; animation: highlight 2s ease-out; }
        .notepad-empty { color: #6b7280; text-align: center; padding: 20px; font-style: italic; }
        @keyframes highlight { from { background: #fbbf24; } to { background: #fef3cd; } }
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
                    
                    <details style="margin: 15px 0; border: 1px solid #e1e8ed; border-radius: 6px;">
                        <summary style="padding: 10px; cursor: pointer; background: #f8f9fa; font-weight: 500;">⏱️ Advanced Timing Settings</summary>
                        <div style="padding: 10px;">
                            <div class="form-group">
                                <label>Base Stabilization (seconds)</label>
                                <input type="number" id="base-stabilization" value="BASE_STABILIZATION_PLACEHOLDER" min="0.1" max="2.0" step="0.1">
                                <small style="color: #6b7280; font-size: 11px;">Minimum wait time for game state to stabilize</small>
                            </div>
                            <div class="form-group">
                                <label>Movement Delay (seconds)</label>
                                <input type="number" id="movement-multiplier" value="MOVEMENT_MULTIPLIER_PLACEHOLDER" min="0.1" max="1.0" step="0.1">
                                <small style="color: #6b7280; font-size: 11px;">Extra delay for movement actions (UP/DOWN/LEFT/RIGHT)</small>
                            </div>
                            <div class="form-group">
                                <label>Interaction Delay (seconds)</label>
                                <input type="number" id="interaction-multiplier" value="INTERACTION_MULTIPLIER_PLACEHOLDER" min="0.1" max="1.0" step="0.1">
                                <small style="color: #6b7280; font-size: 11px;">Extra delay for interaction actions (A/B buttons)</small>
                            </div>
                            <div class="form-group">
                                <label>Menu Delay (seconds)</label>
                                <input type="number" id="menu-multiplier" value="MENU_MULTIPLIER_PLACEHOLDER" min="0.2" max="2.0" step="0.1">
                                <small style="color: #6b7280; font-size: 11px;">Extra delay for menu actions (START/SELECT)</small>
                            </div>
                            <div class="form-group">
                                <label>Maximum Wait Time (seconds)</label>
                                <input type="number" id="max-wait-time" value="MAX_WAIT_TIME_PLACEHOLDER" min="1" max="10" step="0.5">
                                <small style="color: #6b7280; font-size: 11px;">Maximum total wait time regardless of actions</small>
                            </div>
                        </div>
                    </details>
                    
                    <button class="btn btn-outline" onclick="saveAIConfig()">💾 Save AI Config</button>
                    <button class="btn btn-outline" onclick="resetLLMSession()" style="background: #fd7e14; color: white; margin-top: 10px;">🔄 Reset LLM Session</button>
                </div>
                <div class="config-section">
                    <h3>📝 AI Memory Log</h3>
                    <div class="notepad-display" id="notepad-display">
                        <div class="notepad-header">
                            <span class="notepad-status" id="notepad-status">No updates yet</span>
                            <span class="entry-count" id="entry-count">0 entries</span>
                        </div>
                        <div class="notepad-content" id="notepad-content">
                            <div class="notepad-empty">Waiting for AI memory updates...</div>
                        </div>
                        <button class="btn btn-outline" onclick="clearNotepad()" style="background: #dc2626; color: white; margin-top: 8px; font-size: 11px; padding: 6px 12px;">🗑️ Clear Notepad</button>
                    </div>
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
        let lastNotepadUpdate = null;  // Track last notepad update time
        let lastEntryCount = 0;  // Track entry count for change detection
        
        // Start polling for messages when page loads
        document.addEventListener('DOMContentLoaded', function() {
            startMessagePolling();
        });
        
        function startMessagePolling() {
            if (pollingInterval) {
                clearInterval(pollingInterval);
            }
            
            pollingInterval = setInterval(() => {
                pollForMessages();
                pollForNotepadUpdates();
            }, 2000); // Poll every 2 seconds
            
            pollForMessages(); // Initial poll
            pollForNotepadUpdates(); // Initial notepad poll
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
        
        function pollForNotepadUpdates() {
            fetch('/api/notepad-content/')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateNotepadDisplay(data);
                    }
                })
                .catch(error => {
                    console.error('Error polling notepad:', error);
                    document.getElementById('notepad-status').textContent = 'Error loading';
                });
        }
        
        function updateNotepadDisplay(data) {
            const statusEl = document.getElementById('notepad-status');
            const countEl = document.getElementById('entry-count');
            const contentEl = document.getElementById('notepad-content');
            
            // Update status and count
            statusEl.textContent = `Last: ${data.last_updated}`;
            countEl.textContent = `${data.entry_count} entries`;
            
            // Check if there are new entries
            const hasNewEntries = data.entry_count > lastEntryCount;
            lastEntryCount = data.entry_count;
            
            // Display recent entries
            if (data.recent_entries && data.recent_entries.length > 0) {
                let entriesHtml = '';
                data.recent_entries.forEach((entry, index) => {
                    const lines = entry.split('\\n');
                    const header = lines[0]; // ## Update timestamp
                    const content = lines.slice(1).join('\\n').trim();
                    
                    const isNew = hasNewEntries && index === data.recent_entries.length - 1;
                    const newClass = isNew ? ' new' : '';
                    
                    entriesHtml += `
                        <div class="notepad-entry${newClass}">
                            <div class="notepad-entry-header">${header}</div>
                            <div class="notepad-entry-content">${content}</div>
                        </div>
                    `;
                });
                contentEl.innerHTML = entriesHtml;
                
                // Auto-scroll to bottom if new entry
                if (hasNewEntries) {
                    contentEl.scrollTop = contentEl.scrollHeight;
                }
            } else {
                contentEl.innerHTML = '<div class="notepad-empty">No memory updates yet...</div>';
            }
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
                headers: { 'Content-Type': 'application/json' }
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
                headers: { 'Content-Type': 'application/json' }
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
                headers: { 'Content-Type': 'application/json' }
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
            
            // Get timing configuration values
            const baseStabilization = document.getElementById('base-stabilization').value;
            const movementMultiplier = document.getElementById('movement-multiplier').value;
            const interactionMultiplier = document.getElementById('interaction-multiplier').value;
            const menuMultiplier = document.getElementById('menu-multiplier').value;
            const maxWaitTime = document.getElementById('max-wait-time').value;
            
            const formData = new FormData();
            formData.append('llm_provider', provider);
            formData.append('api_key', apiKey);
            formData.append('cooldown', cooldown);
            
            // Add timing configuration
            formData.append('base_stabilization', baseStabilization);
            formData.append('movement_multiplier', movementMultiplier);
            formData.append('interaction_multiplier', interactionMultiplier);
            formData.append('menu_multiplier', menuMultiplier);
            formData.append('max_wait_time', maxWaitTime);
            
            fetch('/api/save-ai-config/', {
                method: 'POST',
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
        
        function resetLLMSession() {
            fetch('/api/reset-llm-session/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                addSystemMessage(data.message);
            })
            .catch(error => addSystemMessage('Error resetting LLM session: ' + error.message));
        }
        
        function clearNotepad() {
            fetch('/api/clear-notepad/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                addSystemMessage(data.message);
                // Immediately refresh notepad display
                pollForNotepadUpdates();
            })
            .catch(error => addSystemMessage('Error clearing notepad: ' + error.message));
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
    
    # Replace timing configuration placeholders
    html_content = html_content.replace('BASE_STABILIZATION_PLACEHOLDER', str(base_stabilization))
    html_content = html_content.replace('MOVEMENT_MULTIPLIER_PLACEHOLDER', str(movement_multiplier))
    html_content = html_content.replace('INTERACTION_MULTIPLIER_PLACEHOLDER', str(interaction_multiplier))
    html_content = html_content.replace('MENU_MULTIPLIER_PLACEHOLDER', str(menu_multiplier))
    html_content = html_content.replace('MAX_WAIT_TIME_PLACEHOLDER', str(max_wait_time))
    
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

def reset_llm_session(request):
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

def get_notepad_content(request):
    """Get current notepad content for real-time display"""
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # Read notepad file directly
        notepad_path = Path("/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/notepad.txt")
        
        if notepad_path.exists():
            with open(notepad_path, 'r') as f:
                content = f.read()
            
            # Get file modification time
            last_modified = notepad_path.stat().st_mtime
            import datetime
            last_updated = datetime.datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M:%S")
            
            # Count entries (lines starting with ##)
            entry_count = content.count('## Update')
            
            # Get last 5 entries for display
            lines = content.split('\n')
            recent_entries = []
            current_entry = []
            
            for line in lines:
                if line.startswith('## Update') and current_entry:
                    # Save previous entry
                    recent_entries.append('\n'.join(current_entry))
                    current_entry = [line]
                elif line.startswith('## Update'):
                    current_entry = [line]
                elif current_entry:
                    current_entry.append(line)
            
            # Add the last entry
            if current_entry:
                recent_entries.append('\n'.join(current_entry))
            
            # Keep only last 5 entries
            recent_entries = recent_entries[-5:] if len(recent_entries) > 5 else recent_entries
            
            return JsonResponse({
                'success': True,
                'content': content,
                'recent_entries': recent_entries,
                'last_updated': last_updated,
                'entry_count': entry_count
            })
        else:
            return JsonResponse({
                'success': True,
                'content': "# Pokémon Red Game Progress\n\nGame just started. No progress recorded yet.",
                'recent_entries': [],
                'last_updated': 'Never',
                'entry_count': 0
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'❌ Error reading notepad: {str(e)}',
            'content': '',
            'recent_entries': [],
            'last_updated': 'Error',
            'entry_count': 0
        })

def clear_notepad(request):
    """Clear the notepad content"""
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # Clear notepad file
        notepad_path = Path("/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/notepad.txt")
        
        # Create fresh notepad content
        fresh_content = "# Pokémon Red Game Progress\n\nGame session reset. Starting fresh.\n"
        
        # Ensure directory exists
        notepad_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(notepad_path, 'w') as f:
            f.write(fresh_content)
        
        return JsonResponse({
            'success': True,
            'message': '🗑️ Notepad cleared - fresh memory!'
        })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'❌ Error clearing notepad: {str(e)}'
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