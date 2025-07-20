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

const WS_URL = `ws://${window.location.host}/ws`;
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

  const connect = useCallback(() => {
    try {
      console.log('🔗 Connecting to WebSocket:', WS_URL);
      
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
        
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
        console.log('🔌 WebSocket disconnected:', event.code, event.reason);
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
        console.error('❌ WebSocket error:', error);
        setConnectionError('WebSocket connection error');
      };

    } catch (error) {
      console.error('❌ Failed to create WebSocket connection:', error);
      setConnectionError('Failed to establish connection');
    }
  }, []);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    console.log('📥 Received message:', message.type);

    switch (message.type) {
      case 'chat_message':
        const chatMessage = message.data.message as ChatMessage;
        setMessages(prev => [...prev, chatMessage]);
        break;

      case 'message_history':
        const historicalMessages = message.data.messages.map((msg: any) => 
          msg.data?.message || msg
        ).filter((msg: any) => msg.type && msg.content);
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