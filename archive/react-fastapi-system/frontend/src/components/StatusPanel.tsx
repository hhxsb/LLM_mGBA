import React from 'react';
import { SystemStatus } from '@/hooks/useWebSocket';

interface StatusPanelProps {
  systemStatus: SystemStatus | null;
  isConnected: boolean;
  connectionError: string | null;
}

const StatusPanel: React.FC<StatusPanelProps> = ({ 
  systemStatus, 
  isConnected, 
  connectionError 
}) => {
  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  const formatMemory = (mb: number) => {
    if (mb < 1024) return `${mb.toFixed(1)}MB`;
    return `${(mb / 1024).toFixed(2)}GB`;
  };

  const getProcessStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running': return 'text-green-600 bg-green-100';
      case 'starting': return 'text-yellow-600 bg-yellow-100';
      case 'stopped': return 'text-gray-600 bg-gray-100';
      case 'error': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getProcessIcon = (processName: string) => {
    switch (processName) {
      case 'video_capture': return '🎬';
      case 'game_control': return '🎮';
      case 'knowledge_system': return '🧠';
      default: return '⚙️';
    }
  };

  if (connectionError) {
    return (
      <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <span className="text-xl">❌</span>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
            <div className="mt-2 text-sm text-red-700">
              <p>{connectionError}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border-l-4 border-pokemon-blue p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800 flex items-center">
          <span className="mr-2">📊</span>
          System Status
        </h2>
        <div className={`px-2 py-1 rounded-full text-xs font-medium ${
          isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {isConnected ? '🟢 Online' : '🔴 Offline'}
        </div>
      </div>

      {/* Process Status */}
      {systemStatus?.system?.processes && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">🚀 Processes</h3>
          <div className="space-y-2">
            {Object.entries(systemStatus.system.processes).map(([name, process]: [string, any]) => (
              <div key={name} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="flex items-center">
                  <span className="text-lg mr-2">{getProcessIcon(name)}</span>
                  <div>
                    <div className="text-sm font-medium text-gray-800 capitalize">
                      {name.replace('_', ' ')}
                    </div>
                    {process.port && (
                      <div className="text-xs text-gray-500">Port: {process.port}</div>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getProcessStatusColor(process.status)}`}>
                    {process.status}
                  </span>
                  {process.pid && (
                    <div className="text-xs text-gray-500 mt-1">PID: {process.pid}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Metrics */}
      {systemStatus?.system && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">📈 Metrics</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-xs text-gray-500">System Uptime</div>
              <div className="text-sm font-medium text-gray-800">
                {formatUptime(systemStatus.system.uptime)}
              </div>
            </div>
            
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-xs text-gray-500">WebSocket Connections</div>
              <div className="text-sm font-medium text-gray-800">
                {systemStatus.websocket?.active_connections || 0}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Memory Usage */}
      {systemStatus?.system?.memory_usage && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">💾 Memory Usage</h3>
          <div className="space-y-2">
            {Object.entries(systemStatus.system.memory_usage).map(([process, memory]: [string, any]) => (
              <div key={process} className="flex justify-between items-center">
                <span className="text-sm text-gray-600 capitalize">
                  {process.replace('_', ' ')}
                </span>
                <span className="text-sm font-medium text-gray-800">
                  {formatMemory(memory)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* WebSocket Info */}
      {systemStatus?.websocket && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">📡 WebSocket</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-xs text-gray-500">Uptime</div>
              <div className="font-medium text-gray-800">
                {formatUptime(systemStatus.websocket.uptime)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Messages</div>
              <div className="font-medium text-gray-800">
                {systemStatus.websocket.message_count || 0}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Last Updated */}
      {systemStatus?.timestamp && (
        <div className="text-xs text-gray-500 text-center pt-2 border-t">
          Last updated: {new Date(systemStatus.timestamp * 1000).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};

export default StatusPanel;