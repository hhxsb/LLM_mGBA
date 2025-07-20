import React, { useState } from 'react';
import ChatInterface from '@/components/ChatInterface';
import StatusPanel from '@/components/StatusPanel';
import KnowledgeBase from '@/components/KnowledgeBase';
import AdminPanel from '@/components/AdminPanel';
import { useWebSocket } from '@/hooks/useWebSocket';
import './App.css';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'admin'>('dashboard');
  const { 
    isConnected, 
    messages, 
    systemStatus, 
    connectionError,
    clearChat 
  } = useWebSocket();

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo and Title */}
            <div className="flex items-center">
              <img 
                src="/static/images/ai-pokemon-trainer-banner.png" 
                alt="AI Pokemon Trainer" 
                className="h-12 w-auto"
                onError={(e) => {
                  // Fallback if image doesn't load
                  e.currentTarget.style.display = 'none';
                }}
              />
              <div className="ml-4">
                <h1 className="text-xl font-bold text-gray-900">
                  AI Pokemon Trainer Dashboard
                </h1>
                <p className="text-sm text-gray-500">
                  Real-time AI gameplay monitoring
                </p>
              </div>
            </div>

            {/* Header Actions */}
            <div className="flex items-center space-x-4">
              {/* Tab Switcher */}
              <div className="flex space-x-1">
                <button
                  onClick={() => setActiveTab('dashboard')}
                  className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                    activeTab === 'dashboard'
                      ? 'bg-pokemon-blue text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  📊 Dashboard
                </button>
                <button
                  onClick={() => setActiveTab('admin')}
                  className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                    activeTab === 'admin'
                      ? 'bg-red-500 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  ⚙️ Admin
                </button>
              </div>

              {/* Connection Status */}
              <div className={`flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                isConnected 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                <div className={`w-2 h-2 rounded-full mr-2 ${
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                }`}></div>
                {isConnected ? 'Connected' : 'Disconnected'}
              </div>

              {/* Clear Chat Button */}
              {activeTab === 'dashboard' && (
                <button
                  onClick={clearChat}
                  disabled={!isConnected || messages.length === 0}
                  className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  🗑️ Clear Chat
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' ? (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-8rem)]">
            
            {/* Chat Interface - Main Area */}
            <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border overflow-hidden">
              <div className="bg-pokemon-blue text-white px-4 py-3">
                <h2 className="text-lg font-semibold flex items-center">
                  <span className="mr-2">💬</span>
                  AI Interaction Chat
                </h2>
                <p className="text-sm text-blue-100">
                  Live feed of game footage, AI responses, and actions
                </p>
              </div>
              <ChatInterface 
                messages={messages} 
                isConnected={isConnected}
              />
            </div>

            {/* Status Panel */}
            <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
              <div className="bg-pokemon-yellow text-gray-800 px-4 py-3">
                <h2 className="text-lg font-semibold flex items-center">
                  <span className="mr-2">📊</span>
                  System Status
                </h2>
              </div>
              <div className="h-[calc(100%-4rem)] overflow-y-auto">
                <StatusPanel 
                  systemStatus={systemStatus}
                  isConnected={isConnected}
                  connectionError={connectionError}
                />
              </div>
            </div>

            {/* Knowledge Base */}
            <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
              <div className="bg-pokemon-green text-white px-4 py-3">
                <h2 className="text-lg font-semibold flex items-center">
                  <span className="mr-2">🧠</span>
                  Knowledge Base
                </h2>
              </div>
              <div className="h-[calc(100%-4rem)]">
                <KnowledgeBase />
              </div>
            </div>

          </div>
        ) : (
          /* Admin Panel */
          <div className="h-[calc(100vh-8rem)]">
            <div className="bg-white rounded-lg shadow-sm border overflow-hidden h-full">
              <AdminPanel 
                systemStatus={systemStatus}
                isConnected={isConnected}
              />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <div className="flex items-center space-x-4">
              <span>🎮 AI Pokemon Trainer v1.0.0</span>
              <span>•</span>
              <span>📡 WebSocket: {isConnected ? 'Connected' : 'Disconnected'}</span>
              <span>•</span>
              <span>💬 Messages: {messages.length}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span>Powered by FastAPI + React</span>
              <span>⚡</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;