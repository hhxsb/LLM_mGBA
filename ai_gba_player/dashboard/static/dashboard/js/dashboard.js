// Dashboard JavaScript for AI GBA Player
// Handles real-time chat, configuration, and narration functionality

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
    } else if (message.type === 'screenshot_comparison') {
        addScreenshotComparisonMessage(message);
    } else if (message.type === 'ai_response') {
        addAIResponse(message.text, message.actions, message.timestamp, message.error_details);
    } else if (message.type === 'narration') {
        addNarrationMessage(message);
        updateNarrationBanner(message);
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

function addAIResponse(response, actions, timestamp = null, error_details = null) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-received';
    
    const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    
    let actionsHtml = '';
    if (actions && actions.length > 0) {
        actionsHtml = '<div class="message-actions">' + 
            actions.map(action => `<span class="action-item">🎮 ${action}</span>`).join('') + 
            '</div>';
    } else if (error_details) {
        // Show "No actions" for errors
        actionsHtml = '<div class="message-actions"><span class="action-item error">⏸️ No actions (error occurred)</span></div>';
    }
    
    // Check if this is an error message
    const isError = response.includes('⚠️ An error occurred');
    const messageClass = isError ? 'error-message' : '';
    
    let errorDetailsHtml = '';
    if (isError && error_details) {
        const detailsId = 'error-details-' + Date.now() + Math.random().toString(36).substr(2, 9);
        errorDetailsHtml = `
            <div class="error-expandable" style="margin-top: 8px;">
                <div class="error-toggle" onclick="toggleErrorDetails('${detailsId}')" style="cursor: pointer; font-size: 12px; color: #ef4444;">
                    ▶ Show error details
                </div>
                <div id="${detailsId}" class="error-details" style="display: none; margin-top: 4px; padding: 8px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 4px; font-size: 11px; font-family: monospace; color: #b91c1c;">
                    ${error_details}
                </div>
            </div>
        `;
    }
    
    messageDiv.innerHTML = `
        <div class="message-bubble ${messageClass}">
            <div style="font-weight: 500; margin-bottom: 4px;">${isError ? '❌ AI Error' : '🤖 AI Response'}</div>
            <div>${response}</div>
            ${actionsHtml}
            ${errorDetailsHtml}
        </div>
        <div class="message-timestamp">${timeStr}</div>
    `;
    messagesContainer.appendChild(messageDiv);
    updateMessageCount();
    scrollToBottom();
}

function toggleErrorDetails(detailsId) {
    const details = document.getElementById(detailsId);
    const toggle = details.previousElementSibling;
    
    if (details.style.display === 'none') {
        details.style.display = 'block';
        toggle.innerHTML = '▼ Hide error details';
    } else {
        details.style.display = 'none';
        toggle.innerHTML = '▶ Show error details';
    }
}

function addScreenshotComparisonMessage(message) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-sent';
    
    const timeStr = new Date(message.timestamp).toLocaleTimeString();
    
    messageDiv.innerHTML = `
        <div class="message-bubble">
            <div style="font-weight: 500; margin-bottom: 8px;">📤 Screenshots Sent to AI</div>
            <div style="margin-bottom: 8px;">${message.game_state}</div>
            
            <div class="screenshot-comparison">
                <div class="before-after-container">
                    <div class="screenshot-side">
                        <label>PREVIOUS:</label>
                        <img src="${message.previous_image_data}" class="comparison-image" alt="Previous screenshot">
                    </div>
                    <div class="screenshot-side">
                        <label>CURRENT:</label>
                        <img src="${message.current_image_data}" class="comparison-image" alt="Current screenshot">
                    </div>
                </div>
            </div>
        </div>
        <div class="message-timestamp">${timeStr}</div>
    `;
    
    const welcome = messagesContainer.querySelector('.welcome-message');
    if (welcome) welcome.remove();
    
    messagesContainer.appendChild(messageDiv);
    updateMessageCount();
    scrollToBottom();
}

function addActionAnalysis(message) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-received';
    
    const timeStr = new Date(message.timestamp * 1000).toLocaleTimeString();
    
    messageDiv.innerHTML = `
        <div class="message-bubble">
            <div style="font-weight: 500; margin-bottom: 8px;">🔍 Action Analysis</div>
            
            <div class="screenshot-comparison">
                <div class="before-after-container">
                    <div class="screenshot-side">
                        <label>BEFORE:</label>
                        <img src="${message.before_image_data}" class="comparison-image" alt="Before screenshot">
                    </div>
                    <div class="screenshot-side">
                        <label>AFTER:</label>
                        <img src="${message.after_image_data}" class="comparison-image" alt="After screenshot">
                    </div>
                </div>
            </div>
            
            <div class="results-analysis">
                <strong>Analysis:</strong> ${message.results_analysis}
            </div>
        </div>
        <div class="message-timestamp">${timeStr}</div>
    `;
    
    const welcome = messagesContainer.querySelector('.welcome-message');
    if (welcome) welcome.remove();
    
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

// ===== NARRATION SYSTEM FUNCTIONS =====

function addNarrationMessage(message) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-received';
    
    const timeStr = new Date(message.timestamp).toLocaleTimeString();
    
    // Handle NarrationAgent response format
    // Message may contain direct fields or nested narration object
    const narrationData = message.narration || message;
    
    const narrationText = narrationData.narration || narrationData.narration_content || 'No narration content';
    const dialogueReading = narrationData.dialogue_reading || '';
    const sceneDescription = narrationData.scene_description || '';
    const excitementLevel = narrationData.excitement_level || 'neutral';
    const hasError = !narrationData.success || narrationData.error;
    const ttsStatus = message.tts_status || (message.tts_active ? 'Playing' : 'Silent');
    
    // Show primary narration content
    let contentHtml = `<div class="narration-content-detail">${narrationText}</div>`;
    
    // Add dialogue reading if available and different from narration
    if (dialogueReading && dialogueReading !== narrationText) {
        contentHtml += `<div class="narration-dialogue" style="margin-top: 8px; padding: 6px 10px; background: rgba(255,255,255,0.15); border-radius: 4px; font-style: italic;">📖 "${dialogueReading}"</div>`;
    }
    
    // Add scene description if available
    if (sceneDescription) {
        contentHtml += `<div class="narration-scene" style="margin-top: 6px; font-size: 11px; opacity: 0.7;">🎬 ${sceneDescription}</div>`;
    }
    
    messageDiv.innerHTML = `
        <div class="message-bubble narration-message ${hasError ? 'error-message' : ''}">
            <div style="font-weight: 500; margin-bottom: 8px;">${hasError ? '❌ Narration Error' : '🎤 AI Narration'}</div>
            ${contentHtml}
            <div class="narration-meta-detail">
                <span>Energy: ${excitementLevel}</span>
                <span>🔊 ${ttsStatus}</span>
            </div>
        </div>
        <div class="message-timestamp">${timeStr}</div>
    `;
    
    const welcome = messagesContainer.querySelector('.welcome-message');
    if (welcome) welcome.remove();
    
    messagesContainer.appendChild(messageDiv);
    updateMessageCount();
    scrollToBottom();
}

function updateNarrationBanner(message) {
    const banner = document.getElementById('narrationBanner');
    const mainText = document.getElementById('narrationMain');
    const energyLevel = document.getElementById('energyLevel');
    const ttsStatus = document.getElementById('ttsStatus');
    
    if (banner && mainText && energyLevel && ttsStatus) {
        // Handle NarrationAgent response format
        const narrationData = message.narration || message;
        
        const narrationText = narrationData.narration || narrationData.narration_content || 'Narration loading...';
        const excitementLevel = narrationData.excitement_level || 'neutral';
        const audioStatus = message.tts_status || (message.tts_active ? '🔊 Playing' : '🔇 Silent');
        
        // Use dialogue_reading for banner if available (more TTS-friendly)
        const displayText = narrationData.dialogue_reading || narrationText;
        
        mainText.textContent = displayText;
        energyLevel.textContent = excitementLevel;
        ttsStatus.textContent = audioStatus;
        
        // Show the banner with animation
        banner.style.display = 'block';
        
        // Auto-hide after 8 seconds (or longer for epic moments)
        const hideTimeout = excitementLevel === 'epic' ? 12000 : 8000;
        setTimeout(() => {
            if (banner.style.display !== 'none') {
                banner.style.display = 'none';
            }
        }, hideTimeout);
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