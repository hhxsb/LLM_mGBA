import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '@/hooks/useWebSocket';

interface ChatInterfaceProps {
  messages: ChatMessage[];
  isConnected: boolean;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ messages, isConnected }) => {
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    console.log('🔍 ChatInterface messages updated:', {
      messageCount: messages.length,
      messages: messages.map(m => ({ id: m?.id, type: m?.type, hasContent: !!m?.content }))
    });
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatDuration = (duration: number) => {
    return `${duration.toFixed(1)}s`;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  const renderGifMessage = (message: ChatMessage) => {
    const gif = message.content.gif;
    if (!gif) return null;

    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-md">
          <div className="bg-chat-gif border-l-4 border-pokemon-yellow p-4 rounded-lg shadow-md">
            <div className="flex items-center mb-2">
              <span className="text-2xl mr-2">🎮</span>
              <span className="font-semibold text-gray-800">Game Footage</span>
              <span className="ml-auto text-xs text-gray-500">
                {formatTimestamp(message.timestamp)}
              </span>
            </div>
            
            {gif.available && gif.data ? (
              <div className="space-y-2">
                <img
                  src={`data:image/gif;base64,${gif.data}`}
                  alt="Game GIF"
                  className="w-full rounded border-2 border-gray-200"
                  style={{ maxWidth: '320px' }}
                />
                <div className="text-xs text-gray-600 bg-gray-100 p-2 rounded">
                  <div className="grid grid-cols-2 gap-2">
                    <span>📊 {gif.metadata.frameCount} frames</span>
                    <span>⏱️ {formatDuration(gif.metadata.duration)}</span>
                    <span>📁 {formatFileSize(gif.metadata.size)}</span>
                    <span>🎬 {message.id.split('_')[1]}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-gray-100 border-2 border-dashed border-gray-300 p-8 rounded text-center">
                <span className="text-gray-500 text-sm">
                  📼 GIF no longer available
                </span>
                <div className="text-xs text-gray-400 mt-1">
                  {gif.metadata.frameCount} frames, {formatDuration(gif.metadata.duration)}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderResponseMessage = (message: ChatMessage) => {
    const response = message.content.response;
    if (!response) return null;

    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-2xl">
          <div className="bg-chat-ai border-l-4 border-pokemon-blue p-4 rounded-lg shadow-md">
            <div className="flex items-center mb-2">
              <span className="text-2xl mr-2">🤖</span>
              <span className="font-semibold text-gray-800">AI Response</span>
              <span className="ml-auto text-xs text-gray-500">
                {formatTimestamp(message.timestamp)}
              </span>
            </div>
            
            <div className="space-y-2">
              <div className="text-gray-800 leading-relaxed">
                {response.text}
              </div>
              
              {response.reasoning && (
                <details className="text-sm">
                  <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                    💭 Reasoning
                  </summary>
                  <div className="mt-2 p-2 bg-blue-50 rounded text-gray-700">
                    {response.reasoning}
                  </div>
                </details>
              )}
              
              {(response.confidence || response.processing_time) && (
                <div className="text-xs text-gray-500 bg-gray-100 p-2 rounded">
                  <div className="flex justify-between">
                    {response.confidence && (
                      <span>🎯 Confidence: {(response.confidence * 100).toFixed(1)}%</span>
                    )}
                    {response.processing_time && (
                      <span>⚡ {response.processing_time.toFixed(3)}s</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderActionMessage = (message: ChatMessage) => {
    const action = message.content.action;
    if (!action) return null;

    const buttonNames = action.button_names.length > 0 ? action.button_names : action.buttons;

    return (
      <div className="flex justify-center mb-4">
        <div className="max-w-md">
          <div className="bg-chat-action border-l-4 border-pokemon-green p-4 rounded-lg shadow-md">
            <div className="flex items-center mb-2">
              <span className="text-2xl mr-2">🎯</span>
              <span className="font-semibold text-gray-800">Actions</span>
              <span className="ml-auto text-xs text-gray-500">
                {formatTimestamp(message.timestamp)}
              </span>
            </div>
            
            <div className="space-y-2">
              <div className="flex flex-wrap gap-2">
                {buttonNames.map((button, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-green-200 text-green-800 rounded-full text-sm font-medium"
                  >
                    {button}
                  </span>
                ))}
              </div>
              
              {action.durations.length > 0 && (
                <div className="text-xs text-gray-600 bg-gray-100 p-2 rounded">
                  <span>⏱️ Duration: </span>
                  {action.durations.map((duration, index) => (
                    <span key={index} className="mr-2">
                      {buttonNames[index] || action.buttons[index]}: {formatDuration(duration)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderSystemMessage = (message: ChatMessage) => {
    const system = message.content.system;
    if (!system) return null;

    const levelColors = {
      info: 'bg-chat-system border-purple-400',
      warning: 'bg-yellow-100 border-yellow-400',
      error: 'bg-red-100 border-red-400'
    };

    const levelIcons = {
      info: 'ℹ️',
      warning: '⚠️',
      error: '❌'
    };

    return (
      <div className="flex justify-center mb-4">
        <div className="max-w-md">
          <div className={`${levelColors[system.level]} border-l-4 p-3 rounded-lg shadow-sm`}>
            <div className="flex items-center">
              <span className="text-lg mr-2">{levelIcons[system.level]}</span>
              <span className="text-sm text-gray-700">{system.message}</span>
              <span className="ml-auto text-xs text-gray-500">
                {formatTimestamp(message.timestamp)}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderMessage = (message: ChatMessage) => {
    if (!message || !message.type || !message.content) {
      console.error('❌ Invalid message in renderMessage:', message);
      return null;
    }
    
    console.log('📸 FRONTEND: Rendering message in ChatInterface component');
    console.log('🎨 Rendering message:', { id: message.id, type: message.type, hasContent: !!message.content });
    
    switch (message.type) {
      case 'gif':
        console.log('📸 FRONTEND: Displaying GIF message in UI');
        console.log('🎬 Rendering GIF message:', message.id);
        return renderGifMessage(message);
      case 'response':
        console.log('📸 FRONTEND: Displaying AI response message in UI');
        console.log('🤖 Rendering response message:', message.id);
        return renderResponseMessage(message);
      case 'action':
        console.log('📸 FRONTEND: Displaying action message in UI');
        console.log('🎯 Rendering action message:', message.id);
        return renderActionMessage(message);
      case 'system':
        console.log('📸 FRONTEND: Displaying system message in UI');
        console.log('ℹ️ Rendering system message:', message.id);
        return renderSystemMessage(message);
      default:
        console.log('❓ Unknown message type:', message.type);
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Connection Status */}
      <div className={`px-4 py-2 text-sm ${isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
        <div className="flex items-center">
          <div className={`w-2 h-2 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          {isConnected ? '🟢 Connected to AI System' : '🔴 Disconnected'}
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {(() => {
          console.log('🖼️ ChatInterface render - total messages:', messages.length);
          
          if (messages.length === 0) {
            console.log('📋 No messages to display, showing empty state');
            return (
              <div className="text-center text-gray-500 mt-8">
                <div className="text-6xl mb-4">🎮</div>
                <h3 className="text-lg font-semibold mb-2">AI Pokemon Trainer Ready</h3>
                <p className="text-sm">
                  Waiting for the AI to start playing Pokemon Red...
                  <br />
                  Game footage, AI responses, and actions will appear here.
                </p>
              </div>
            );
          }
          
          const filteredMessages = messages.filter((message) => message && message.id && message.type);
          console.log('🔍 Filtered messages for rendering:', {
            original: messages.length,
            filtered: filteredMessages.length,
            filtered_ids: filteredMessages.map(m => m.id)
          });
          
          return filteredMessages.map((message) => {
            console.log('🎭 Mapping message for render:', message.id);
            return (
              <React.Fragment key={message.id}>
                {renderMessage(message)}
              </React.Fragment>
            );
          });
        })()}
        <div ref={chatEndRef} />
      </div>

      {/* Chat Info */}
      <div className="bg-gray-100 px-4 py-2 text-xs text-gray-600 border-t">
        <div className="flex justify-between items-center">
          <span>💬 {messages.length} messages in chat</span>
          <span>🔄 Auto-scroll enabled</span>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;