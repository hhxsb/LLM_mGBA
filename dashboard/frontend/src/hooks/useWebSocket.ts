import { useState, useEffect, useRef, useCallback } from 'react';

export interface ChatMessage {
  id: string;
  type: 'gif' | 'response' | 'action' | 'system';
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

export interface UseWebSocketReturn {
  isConnected: boolean;
  messages: ChatMessage[];
  systemStatus: SystemStatus | null;
  sendMessage: (message: any) => void;
  clearChat: () => void;
  connectionError: string | null;
}

// WebSocket should connect to dashboard backend, not frontend dev server
const getWebSocketURL = () => {
  if (window.location.host.includes(':5173')) {
    // Development mode: frontend is on 5173, need to find dashboard backend port
    // Try ports in order: 3001 (mock mode), 3000 (default)
    return ['ws://localhost:3001/ws', 'ws://localhost:3000/ws'];
  } else {
    // Production: same host
    return [`ws://${window.location.host}/ws`];
  }
};

const WS_URLS = getWebSocketURL();
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

export const useWebSocket = (): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
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
    console.log('📥 Received message:', message.type, message);
    
    // DEBUG LOGGING: Frontend message reception tracking
    console.log('📸 FRONTEND: Message received via WebSocket:', message.type);

    switch (message.type) {
      case 'chat_message':
        console.log('📸 FRONTEND: Processing chat_message for display');
        console.log('🔍 Chat message data structure:', message.data);
        
        // Handle potentially double-nested structure from AI processes
        let chatMessage: ChatMessage;
        if (message.data.data && message.data.data.message) {
          // Double-nested from AI process
          chatMessage = message.data.data.message as ChatMessage;
        } else if (message.data.message) {
          // Single-nested from backend handler
          chatMessage = message.data.message as ChatMessage;
        } else {
          // Direct message
          chatMessage = message.data as ChatMessage;
        }
        
        console.log('💬 Processing chat message:', chatMessage);
        if (chatMessage && chatMessage.type && chatMessage.content) {
          console.log('📸 FRONTEND: Valid chat message, updating React state for display');
          console.log('✅ Adding message to state:', chatMessage.id, chatMessage.type);
          setMessages(prev => {
            const newMessages = [...prev, chatMessage];
            console.log('📸 FRONTEND: React state updated, triggering component re-render');
            console.log('📚 Updated messages state:', {
              previousCount: prev.length,
              newCount: newMessages.length,
              latestMessage: chatMessage.id
            });
            return newMessages;
          });
        } else {
          console.error('❌ Invalid chat message structure:', chatMessage);
        }
        break;

      case 'message_history':
        const historicalMessages = message.data.messages.map((msg: any) => 
          msg.data?.message || msg
        ).filter((msg: any) => msg.type && msg.content);
        console.log('📚 Loading message history:', historicalMessages.length, 'messages');
        console.log('📚 Historical messages details:', historicalMessages.map(m => ({ id: m.id, type: m.type })));
        setMessages(historicalMessages);
        break;

      case 'system_status':
        setSystemStatus(message.data);
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
        setMessages([]);
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
    // Send clear request to server
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
    sendMessage,
    clearChat,
    connectionError
  };
};