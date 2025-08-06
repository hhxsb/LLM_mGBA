/**
 * Dashboard WebSocket Client
 * Handles real-time communication with Django Channels
 */

class DashboardWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 3000;
        this.isConnected = false;
        this.messageHistory = [];
        this.maxHistory = 500;
        
        // Bind methods to preserve 'this' context
        this.connect = this.connect.bind(this);
        this.disconnect = this.disconnect.bind(this);
        this.send = this.send.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
        this.handleOpen = this.handleOpen.bind(this);
        this.handleClose = this.handleClose.bind(this);
        this.handleError = this.handleError.bind(this);
        
        console.log('🔌 DashboardWebSocket initialized');
    }
    
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('⚠️ WebSocket already connected');
            return;
        }
        
        // Construct WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/dashboard/`;
        
        console.log(`🔗 Connecting to WebSocket: ${wsUrl}`);
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = this.handleOpen;
            this.ws.onmessage = this.handleMessage;
            this.ws.onclose = this.handleClose;
            this.ws.onerror = this.handleError;
            
        } catch (error) {
            console.error('❌ Error creating WebSocket connection:', error);
            this.scheduleReconnect();
        }
    }
    
    disconnect() {
        console.log('🔌 Disconnecting WebSocket...');
        if (this.ws) {
            this.ws.close(1000, 'User disconnecting');
        }
    }
    
    send(message) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.warn('⚠️ WebSocket not connected, cannot send message');
            return false;
        }
        
        try {
            this.ws.send(JSON.stringify(message));
            console.log('📤 Sent message:', message.type);
            return true;
        } catch (error) {
            console.error('❌ Error sending message:', error);
            return false;
        }
    }
    
    handleOpen() {
        console.log('✅ WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // Update connection status in UI
        this.updateConnectionStatus(true);
        
        // Send ping to test connection
        this.send({
            type: 'ping',
            timestamp: Date.now()
        });
        
        // Request initial data
        this.send({
            type: 'get_status'
        });
        
        this.send({
            type: 'get_recent_messages'
        });
    }
    
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('📥 Received message:', message.type);
            
            // Add to message history
            this.addToHistory(message);
            
            // Handle different message types
            switch (message.type) {
                case 'chat_message':
                    this.handleChatMessage(message.data);
                    break;
                case 'system_status':
                    this.handleSystemStatus(message.data);
                    break;
                case 'log_stream':
                    this.handleLogMessage(message.data);
                    break;
                case 'chat_cleared':
                    this.handleChatCleared();
                    break;
                case 'pong':
                    console.log('🏓 Received pong');
                    break;
                default:
                    console.log('ℹ️ Unknown message type:', message.type);
            }
            
        } catch (error) {
            console.error('❌ Error parsing WebSocket message:', error);
        }
    }
    
    handleClose(event) {
        console.log(`🔌 WebSocket disconnected: ${event.code} ${event.reason}`);
        this.isConnected = false;
        this.ws = null;
        
        // Update connection status in UI
        this.updateConnectionStatus(false);
        
        // Attempt reconnection if not a normal close
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
        }
    }
    
    handleError(error) {
        console.error('❌ WebSocket error:', error);
        this.updateConnectionStatus(false, 'Connection error');
    }
    
    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
        
        console.log(`🔄 Scheduling reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
        
        this.updateConnectionStatus(false, `Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            if (this.reconnectAttempts <= this.maxReconnectAttempts) {
                this.connect();
            } else {
                this.updateConnectionStatus(false, 'Connection failed. Please refresh.');
            }
        }, delay);
    }
    
    updateConnectionStatus(connected, message = null) {
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        if (statusIndicator && statusText) {
            if (connected) {
                statusIndicator.textContent = '🟢';
                statusText.textContent = 'Connected';
            } else {
                statusIndicator.textContent = '🔴';
                statusText.textContent = message || 'Disconnected';
            }
        }
    }
    
    addToHistory(message) {
        this.messageHistory.push({
            ...message,
            receivedAt: Date.now()
        });
        
        // Keep only recent messages
        if (this.messageHistory.length > this.maxHistory) {
            this.messageHistory = this.messageHistory.slice(-this.maxHistory);
        }
    }
    
    handleChatMessage(messageData) {
        if (!messageData || !messageData.type) {
            console.error('❌ Invalid chat message data:', messageData);
            return;
        }
        
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            console.warn('⚠️ Chat messages container not found');
            return;
        }
        
        // Remove welcome message if it exists
        const welcomeMessage = chatMessages.querySelector('.message-welcome');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        // Create message element based on type
        let messageElement;
        switch (messageData.type) {
            case 'gif':
                messageElement = this.createGifMessage(messageData);
                break;
            case 'screenshots':
                messageElement = this.createScreenshotsMessage(messageData);
                break;
            case 'response':
                messageElement = this.createResponseMessage(messageData);
                break;
            case 'action':
                messageElement = this.createActionMessage(messageData);
                break;
            case 'system':
                messageElement = this.createSystemMessage(messageData);
                break;
            default:
                console.warn('⚠️ Unknown message type:', messageData.type);
                return;
        }
        
        if (messageElement) {
            chatMessages.appendChild(messageElement);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Update message count
            this.updateMessageCount();
        }
    }
    
    createGifMessage(data) {
        const template = document.getElementById('gifMessageTemplate');
        if (!template) return null;
        
        const element = template.content.cloneNode(true);
        const messageDiv = element.querySelector('.message');
        
        // Set timestamp
        const timeElement = element.querySelector('.message-time');
        timeElement.textContent = this.formatTimestamp(data.timestamp);
        
        // Set GIF data
        const gifImg = element.querySelector('.gif-image');
        const gif = data.content.gif;
        
        if (gif && gif.available && gif.data) {
            gifImg.src = `data:image/gif;base64,${gif.data}`;
            
            // Set metadata
            const metadata = element.querySelector('.gif-metadata');
            metadata.innerHTML = `
                <span>📊 ${gif.metadata.frameCount} frames</span>
                <span>⏱️ ${this.formatDuration(gif.metadata.duration)}</span>
                <span>📁 ${this.formatFileSize(gif.metadata.size)}</span>
                <span>🎬 ${data.id.split('_')[1] || 'N/A'}</span>
            `;
        } else {
            // GIF not available
            gifImg.remove();
            const content = element.querySelector('.message-content');
            content.innerHTML = `
                <div class="gif-unavailable">
                    <span>📼 GIF no longer available</span>
                    <div class="metadata-text">
                        ${gif ? gif.metadata.frameCount : 0} frames, 
                        ${gif ? this.formatDuration(gif.metadata.duration) : '0s'}
                    </div>
                </div>
            `;
        }
        
        messageDiv.id = `message-${data.id}`;
        return element;
    }
    
    createScreenshotsMessage(data) {
        const template = document.getElementById('screenshotsMessageTemplate');
        if (!template) return null;
        
        const element = template.content.cloneNode(true);
        const messageDiv = element.querySelector('.message');
        
        // Set timestamp
        const timeElement = element.querySelector('.message-time');
        timeElement.textContent = this.formatTimestamp(data.timestamp);
        
        // Set screenshot data
        const screenshots = data.content.screenshots;
        if (screenshots) {
            const beforeImg = element.querySelector('.screenshot-before .screenshot-image');
            const afterImg = element.querySelector('.screenshot-after .screenshot-image');
            
            if (screenshots.before) {
                beforeImg.src = `data:image/png;base64,${screenshots.before}`;
            } else {
                element.querySelector('.screenshot-before').style.display = 'none';
            }
            
            if (screenshots.after) {
                afterImg.src = `data:image/png;base64,${screenshots.after}`;
            } else {
                element.querySelector('.screenshot-after').style.display = 'none';
            }
            
            // Set metadata
            const metadata = element.querySelector('.screenshots-metadata');
            metadata.innerHTML = `
                <span>📏 ${screenshots.metadata.width}×${screenshots.metadata.height}</span>
                <span>📋 ${screenshots.metadata.source}</span>
                <span>🔢 ${screenshots.before && screenshots.after ? '2' : '1'} screenshot(s)</span>
                <span>🎬 ${data.id.split('_')[1] || 'N/A'}</span>
            `;
        }
        
        messageDiv.id = `message-${data.id}`;
        return element;
    }
    
    createResponseMessage(data) {
        const template = document.getElementById('responseMessageTemplate');
        if (!template) return null;
        
        const element = template.content.cloneNode(true);
        const messageDiv = element.querySelector('.message');
        
        // Set timestamp
        const timeElement = element.querySelector('.message-time');
        timeElement.textContent = this.formatTimestamp(data.timestamp);
        
        // Set response data
        const response = data.content.response;
        if (response) {
            const textElement = element.querySelector('.response-text');
            textElement.textContent = response.text || '';
            
            // Set reasoning if available
            const reasoningDetails = element.querySelector('.response-reasoning');
            const reasoningContent = element.querySelector('.reasoning-content');
            
            if (response.reasoning) {
                reasoningContent.textContent = response.reasoning;
            } else {
                reasoningDetails.style.display = 'none';
            }
            
            // Set metadata
            const metadata = element.querySelector('.response-metadata');
            const confidenceSpan = metadata.querySelector('.confidence');
            const processingTimeSpan = metadata.querySelector('.processing-time');
            
            if (response.confidence) {
                confidenceSpan.textContent = `🎯 Confidence: ${(response.confidence * 100).toFixed(1)}%`;
            }
            
            if (response.processing_time) {
                processingTimeSpan.textContent = `⚡ ${response.processing_time.toFixed(3)}s`;
            }
        }
        
        messageDiv.id = `message-${data.id}`;
        return element;
    }
    
    createActionMessage(data) {
        const template = document.getElementById('actionMessageTemplate');
        if (!template) return null;
        
        const element = template.content.cloneNode(true);
        const messageDiv = element.querySelector('.message');
        
        // Set timestamp
        const timeElement = element.querySelector('.message-time');
        timeElement.textContent = this.formatTimestamp(data.timestamp);
        
        // Set action data
        const action = data.content.action;
        if (action) {
            const buttonsContainer = element.querySelector('.action-buttons');
            const buttonNames = action.button_names || action.buttons;
            
            buttonNames.forEach(button => {
                const buttonElement = document.createElement('span');
                buttonElement.className = 'action-button';
                buttonElement.textContent = button;
                buttonsContainer.appendChild(buttonElement);
            });
            
            // Set durations if available
            const durationsContainer = element.querySelector('.action-durations');
            if (action.durations && action.durations.length > 0) {
                const durationsText = buttonNames.map((button, index) => 
                    `${button}: ${this.formatDuration(action.durations[index] || 0)}`
                ).join(', ');
                durationsContainer.innerHTML = `⏱️ Duration: ${durationsText}`;
            } else {
                durationsContainer.style.display = 'none';
            }
        }
        
        messageDiv.id = `message-${data.id}`;
        return element;
    }
    
    createSystemMessage(data) {
        const template = document.getElementById('systemMessageTemplate');
        if (!template) return null;
        
        const element = template.content.cloneNode(true);
        const messageDiv = element.querySelector('.message');
        
        // Set timestamp
        const timeElement = element.querySelector('.message-time');
        timeElement.textContent = this.formatTimestamp(data.timestamp);
        
        // Set system data
        const system = data.content.system;
        if (system) {
            const iconElement = element.querySelector('.message-icon');
            const textElement = element.querySelector('.system-text');
            
            // Set icon based on level
            const levelIcons = {
                info: 'ℹ️',
                warning: '⚠️',
                error: '❌'
            };
            
            iconElement.textContent = levelIcons[system.level] || 'ℹ️';
            textElement.textContent = system.message || '';
            
            // Add level class
            messageDiv.classList.add(`system-${system.level}`);
        }
        
        messageDiv.id = `message-${data.id}`;
        return element;
    }
    
    handleSystemStatus(statusData) {
        if (!statusData) return;
        
        // Update process status
        if (statusData.system && statusData.system.processes) {
            const processes = statusData.system.processes;
            
            // Update status indicators
            this.updateProcessStatus('gameControlStatus', processes.game_control);
            this.updateProcessStatus('videoCaptureStatus', processes.video_capture);
            this.updateProcessStatus('knowledgeSystemStatus', processes.knowledge_system);
        }
        
        // Update memory usage
        if (statusData.system && statusData.system.memory_usage) {
            const memoryElement = document.getElementById('memoryUsage');
            if (memoryElement) {
                memoryElement.textContent = `${statusData.system.memory_usage.percent || 0}%`;
            }
        }
        
        // Update footer stats
        if (statusData.websocket) {
            const uptimeElement = document.getElementById('uptime');
            if (uptimeElement && statusData.websocket.uptime) {
                uptimeElement.textContent = `Uptime: ${this.formatDuration(statusData.websocket.uptime)}`;
            }
        }
    }
    
    updateProcessStatus(elementId, processData) {
        const element = document.getElementById(elementId);
        if (!element || !processData) return;
        
        const statusIcons = {
            running: '▶️ Running',
            stopped: '⏸️ Stopped',
            starting: '🔄 Starting',
            error: '❌ Error'
        };
        
        element.textContent = statusIcons[processData.status] || '❓ Unknown';
        element.className = `status-indicator status-${processData.status}`;
    }
    
    handleLogMessage(logData) {
        // Log messages can be displayed in admin panel or console
        console.log(`📋 ${logData.level} [${logData.process_name}]:`, logData.message);
    }
    
    handleChatCleared() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = `
                <div class="message-welcome">
                    <div class="welcome-icon">🎮</div>
                    <h3>AI Pokemon Trainer Ready</h3>
                    <p>Waiting for the AI to start playing Pokemon Red...</p>
                    <p>Game footage, AI responses, and actions will appear here.</p>
                </div>
            `;
            this.updateMessageCount();
        }
    }
    
    updateMessageCount() {
        const chatMessages = document.getElementById('chatMessages');
        const countElement = document.getElementById('chatMessageCount');
        const footerCount = document.getElementById('messageCount');
        
        if (chatMessages) {
            const messageCount = chatMessages.querySelectorAll('.message:not(.message-welcome)').length;
            
            if (countElement) {
                countElement.textContent = `${messageCount} messages in chat`;
            }
            
            if (footerCount) {
                footerCount.textContent = `${messageCount} messages`;
            }
        }
    }
    
    // Public methods for UI interaction
    clearChat() {
        this.send({
            type: 'clear_chat',
            timestamp: Date.now()
        });
    }
    
    exportMessages() {
        const exportData = {
            exported_at: new Date().toISOString(),
            message_count: this.messageHistory.length,
            messages: this.messageHistory
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { 
            type: 'application/json' 
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pokemon-ai-chat-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        console.log('📥 Messages exported successfully');
    }
    
    // Utility functions
    formatTimestamp(timestamp) {
        return new Date(timestamp * 1000).toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
    
    formatDuration(duration) {
        return `${duration.toFixed(1)}s`;
    }
    
    formatFileSize(bytes) {
        if (bytes < 1024) return `${bytes}B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
    }
}