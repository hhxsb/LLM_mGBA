import { useState, useEffect, useRef, useCallback } from 'react';

export interface ChatMessage {
  id: string;
  type: 'gif' | 'screenshots' | 'response' | 'action' | 'system';
  timestamp: number;
  sequence: number;
  content: {
    gif?: {
      data?: string;
      metadata: {
        frameCount: number;
        duration: number;
        size: number;
        timestamp: number;
      };
      available: boolean;
    };
    screenshots?: {
      before?: string;  // base64 image data
      after?: string;   // base64 image data
      metadata: {
        width: number;
        height: number;
        timestamp: number;
        source: string;
      };
    };
    response?: {
      text: string;
      reasoning?: string;
      confidence?: number;
      processing_time?: number;
    };
    action?: {
      buttons: string[];
      durations: number[];
      button_names: string[];
    };
    system?: {
      message: string;
      level: 'info' | 'warning' | 'error';
    };
  };
}

export interface WebSocketMessage {
  type: string;
  timestamp: number;
  data: any;
}

export interface SystemStatus {
  system: {
    processes: Record<string, any>;
    uptime: number;
    memory_usage: Record<string, number>;
  };
  websocket: {
    active_connections: number;
    uptime: number;
    message_count: number;
  };
  timestamp: number;
}

export interface ProcessLog {
  timestamp: number;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  source: string;
  process_id: string;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  messages: ChatMessage[];
  systemStatus: SystemStatus | null;
  processLogs: Record<string, ProcessLog[]>;
  sendMessage: (message: any) => void;
  clearChat: () => void;
  exportMessages: () => void;
  connectionError: string | null;
}

// WebSocket should connect to dashboard backend, not frontend dev server
const getWebSocketURL = () => {
  if (window.location.host.includes(':5173')) {
    // Development mode: frontend is on 5173, need to find dashboard backend port
    // Try ports in order: 3001 ( deprecated mock mode), just use 3000 (default)
    return ['ws://localhost:3000/ws'];
  } else {
    // Production: same host
    return [`ws://${window.location.host}/ws`];
  }
};

const WS_URLS = getWebSocketURL();
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;
const STORAGE_KEY = 'pokemon_ai_chat_messages';

// Helper functions for localStorage message management
const loadMessagesFromStorage = (): ChatMessage[] => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return Array.isArray(parsed) ? parsed : [];
    }
  } catch (error) {
    console.error('❌ Error loading messages from localStorage:', error);
  }
  return [];
};

const saveMessagesToStorage = (messages: ChatMessage[]): void => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  } catch (error) {
    console.error('❌ Error saving messages to localStorage:', error);
  }
};

const addMessageToStorage = (newMessage: ChatMessage): ChatMessage[] => {
  const currentMessages = loadMessagesFromStorage();
  
  // Check for duplicate messages by ID
  if (currentMessages.find(msg => msg.id === newMessage.id)) {
    console.log('🔄 Duplicate ignored:', newMessage.id.slice(0, 8));
    return currentMessages;
  }
  
  // Add new message to the end (append-only)
  const updatedMessages = [...currentMessages, newMessage];
  
  // Limit to last 500 messages to prevent excessive storage usage
  const limitedMessages = updatedMessages.slice(-500);
  if (limitedMessages.length < updatedMessages.length) {
    console.log(`🧹 Trimmed: ${updatedMessages.length} → ${limitedMessages.length}`);
  }
  
  saveMessagesToStorage(limitedMessages);
  return limitedMessages;
};

const exportMessages = (): void => {
  try {
    const messages = loadMessagesFromStorage();
    const exportData = {
      exported_at: new Date().toISOString(),
      message_count: messages.length,
      messages: messages
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pokemon-ai-chat-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    console.log('📥 Messages exported successfully');
  } catch (error) {
    console.error('❌ Error exporting messages:', error);
  }
};

export const useWebSocket = (): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadMessagesFromStorage());
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [processLogs, setProcessLogs] = useState<Record<string, ProcessLog[]>>({});
  const [connectionError, setConnectionError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const currentUrlIndex = useRef(0);

  const connect = useCallback(() => {
    const tryConnection = (urlIndex: number) => {
      if (urlIndex >= WS_URLS.length) {
        setConnectionError('Could not connect to any dashboard backend port');
        return;
      }

      const WS_URL = WS_URLS[urlIndex];
      try {
        console.log(`🔗 Trying WebSocket connection ${urlIndex + 1}/${WS_URLS.length}:`, WS_URL);
        
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log(`✅ WebSocket connected to ${WS_URL}`);
          setIsConnected(true);
          setConnectionError(null);
          reconnectAttempts.current = 0;
          currentUrlIndex.current = urlIndex; // Remember successful URL
          
          // Send ping to test connection
          ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            handleMessage(message);
          } catch (error) {
            console.error('❌ Error parsing WebSocket message:', error);
          }
        };

        ws.onclose = (event) => {
          console.log(`🔌 WebSocket disconnected from ${WS_URL}:`, event.code, event.reason);
          setIsConnected(false);
          wsRef.current = null;

          // Attempt reconnection if not a normal close
          if (event.code !== 1000 && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
            setConnectionError(`Connection lost. Reconnecting... (${reconnectAttempts.current + 1}/${MAX_RECONNECT_ATTEMPTS})`);
            reconnectAttempts.current++;
            
            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, RECONNECT_DELAY);
          } else if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
            setConnectionError('Connection failed after multiple attempts. Please refresh the page.');
          }
        };

        ws.onerror = (error) => {
          console.error(`❌ WebSocket error on ${WS_URL}:`, error);
          // Try next URL in the list
          tryConnection(urlIndex + 1);
        };

      } catch (error) {
        console.error(`❌ Failed to create WebSocket connection to ${WS_URL}:`, error);
        // Try next URL in the list
        tryConnection(urlIndex + 1);
      }
    };

    // Start trying connections from the first URL
    tryConnection(0);
  }, []);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    console.log('📥 WS MSG |', message.type);

    switch (message.type) {
      case 'chat_message':
        // Simplified parsing - unified messages have consistent structure
        const unifiedMessage = message.data;
        
        if (unifiedMessage && unifiedMessage.id && unifiedMessage.type && unifiedMessage.content) {
          console.log('✅ MSG PROCESSED |', unifiedMessage.type, '|', unifiedMessage.id.slice(0, 8));
          
          // Convert to frontend ChatMessage format
          const chatMessage: ChatMessage = {
            id: unifiedMessage.id,
            type: unifiedMessage.type,
            timestamp: unifiedMessage.timestamp,
            sequence: unifiedMessage.sequence || 0,
            content: unifiedMessage.content
          };
          
          // Add to localStorage and get updated message list
          const updatedMessages = addMessageToStorage(chatMessage);
          
          // Update React state with the complete message list from localStorage
          setMessages(updatedMessages);
          
          console.log('📱 UI UPDATED | total:', updatedMessages.length);
        } else {
          console.error('❌ Invalid unified message structure:', unifiedMessage);
        }
        break;


      case 'system_status':
        setSystemStatus(message.data);
        break;

      case 'log_stream':
        const logEntry: ProcessLog = {
          timestamp: message.data.timestamp || Date.now() / 1000,
          level: message.data.level || 'INFO',
          message: message.data.message || '',
          source: message.data.source || 'unknown',
          process_id: message.data.process_id || 'unknown'
        };
        
        setProcessLogs(prev => {
          const processName = logEntry.source;
          const currentLogs = prev[processName] || [];
          
          // Keep max 100 logs per process (FIFO queue)
          const newLogs = [...currentLogs, logEntry];
          if (newLogs.length > 100) {
            newLogs.shift(); // Remove oldest
          }
          
          return {
            ...prev,
            [processName]: newLogs
          };
        });
        break;

      case 'gif_expired':
        const gifId = message.data.gif_id;
        setMessages(prev => prev.map(msg => {
          if (msg.id === gifId && msg.content.gif) {
            return {
              ...msg,
              content: {
                ...msg.content,
                gif: {
                  ...msg.content.gif,
                  data: undefined,
                  available: false
                }
              }
            };
          }
          return msg;
        }));
        break;

      case 'chat_cleared':
        // Clear both React state and localStorage
        setMessages([]);
        saveMessagesToStorage([]);
        console.log('🗑️ Chat cleared from both state and localStorage');
        break;

      case 'ping':
        // Respond to server ping
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
        }
        break;
        
      case 'pong':
        // Handle ping response
        break;

      default:
        console.log('ℹ️ Unknown message type:', message.type);
    }
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('⚠️ WebSocket not connected, cannot send message');
    }
  }, []);

  const clearChat = useCallback(() => {
    // Clear immediately in frontend (don't wait for server)
    setMessages([]);
    saveMessagesToStorage([]);
    console.log('🗑️ Chat cleared locally');
    
    // Optionally notify server (but don't depend on it)
    sendMessage({ type: 'clear_chat', timestamp: Date.now() });
  }, [sendMessage]);

  // Connect on mount
  useEffect(() => {
    connect();

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [connect]);

  return {
    isConnected,
    messages,
    systemStatus,
    processLogs,
    sendMessage,
    clearChat,
    exportMessages,
    connectionError
  };
};