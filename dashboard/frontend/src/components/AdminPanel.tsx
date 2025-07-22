import React, { useState, useEffect } from 'react';

interface ProcessLog {
  timestamp: number;
  level: 'INFO' | 'ERROR' | 'WARNING' | 'DEBUG';
  message: string;
  source: string;
  process_id: string;
}

interface ProcessInfo {
  name: string;
  status: 'running' | 'stopped' | 'error' | 'starting';
  pid?: number;
  port?: number;
  last_error?: string;
}

interface AdminPanelProps {
  systemStatus: any;
  processLogs: Record<string, ProcessLog[]>;
  isConnected: boolean;
}

const AdminPanel: React.FC<AdminPanelProps> = ({ systemStatus, processLogs, isConnected }) => {
  const [selectedProcess, setSelectedProcess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const processes = systemStatus?.system?.processes || {};
  
  // Get logs for selected process from real-time stream
  const selectedProcessLogs = selectedProcess ? (processLogs[selectedProcess] || []) : [];

  const restartProcess = async (processName: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/processes/${processName}/restart-force`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          alert(`✅ ${processName} restarted successfully`);
        } else {
          alert(`❌ Failed to restart ${processName}: ${data.message}`);
        }
      } else {
        alert(`❌ Failed to restart ${processName}: Server error`);
      }
    } catch (error) {
      alert(`❌ Failed to restart ${processName}: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const startProcess = async (processName: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/processes/${processName}/start`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          alert(`✅ ${processName} started successfully`);
        } else {
          alert(`❌ Failed to start ${processName}: ${data.message}`);
        }
      }
    } catch (error) {
      alert(`❌ Failed to start ${processName}: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const stopProcess = async (processName: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/processes/${processName}/stop`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          alert(`✅ ${processName} stopped successfully`);
        } else {
          alert(`❌ Failed to stop ${processName}: ${data.message}`);
        }
      }
    } catch (error) {
      alert(`❌ Failed to stop ${processName}: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'running': return 'text-green-600 bg-green-100';
      case 'starting': return 'text-yellow-600 bg-yellow-100';
      case 'stopped': return 'text-gray-600 bg-gray-100';
      case 'error': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-600';
      case 'WARNING': return 'text-yellow-600';
      case 'INFO': return 'text-blue-600';
      case 'DEBUG': return 'text-gray-600';
      default: return 'text-gray-800';
    }
  };

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString();
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b bg-red-50">
        <h2 className="text-lg font-semibold text-gray-800 flex items-center">
          <span className="mr-2">⚙️</span>
          Admin Panel
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Process management and debugging tools
        </p>
      </div>

      <div className="flex-1 flex">
        {/* Process List */}
        <div className="w-1/3 border-r">
          <div className="p-3 bg-gray-50 border-b">
            <h3 className="font-medium text-gray-800">Processes</h3>
          </div>
          <div className="space-y-2 p-3">
            {Object.entries(processes).map(([name, info]: [string, any]) => (
              <div
                key={name}
                className={`p-3 border rounded cursor-pointer transition-colors ${
                  selectedProcess === name ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'
                }`}
                onClick={() => {
                  setSelectedProcess(name);
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm capitalize">
                    {name.replace('_', ' ')}
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(info.status)}`}>
                    {info.status}
                  </span>
                </div>
                
                {info.pid && (
                  <div className="text-xs text-gray-500">PID: {info.pid}</div>
                )}
                
                {info.port && (
                  <div className="text-xs text-gray-500">Port: {info.port}</div>
                )}
                
                {/* Display log file path for debugging */}
                <div className="text-xs text-gray-500 mt-1">
                  📁 Log: /tmp/pokemon_ai_logs/{name}.log
                </div>
                
                {info.last_error && (
                  <div className="text-xs text-red-600 mt-1 truncate">
                    ❌ {info.last_error.split('\n')[0]}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Process Details */}
        <div className="flex-1 flex flex-col">
          {selectedProcess ? (
            <>
              {/* Process Controls */}
              <div className="p-3 bg-gray-50 border-b">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-800 capitalize">
                    {selectedProcess.replace('_', ' ')} Controls
                  </h3>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => startProcess(selectedProcess)}
                      disabled={loading}
                      className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
                    >
                      ▶️ Start
                    </button>
                    <button
                      onClick={() => stopProcess(selectedProcess)}
                      disabled={loading}
                      className="px-3 py-1 text-sm bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50"
                    >
                      ⏹️ Stop
                    </button>
                    <button
                      onClick={() => restartProcess(selectedProcess)}
                      disabled={loading}
                      className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                    >
                      🔄 Restart
                    </button>
                    <div className="text-xs text-gray-500">
                      📡 Real-time logs ({selectedProcessLogs.length} entries)
                    </div>
                  </div>
                </div>
              </div>

              {/* Process Logs */}
              <div className="flex-1 overflow-y-auto">
                <div className="p-3">
                  <h4 className="font-medium text-gray-800 mb-2">
                    Real-time Logs 
                    {isConnected ? (
                      <span className="text-green-600 text-sm ml-2">🟢 Live</span>
                    ) : (
                      <span className="text-red-600 text-sm ml-2">🔴 Disconnected</span>
                    )}
                  </h4>
                  {selectedProcessLogs.length > 0 ? (
                    <div className="space-y-1 bg-black text-green-400 p-3 rounded font-mono text-xs max-h-96 overflow-y-auto">
                      {selectedProcessLogs.map((log, index) => (
                        <div key={index} className="flex">
                          <span className="text-gray-400 w-20 flex-shrink-0">
                            {formatTimestamp(log.timestamp)}
                          </span>
                          <span className={`w-16 flex-shrink-0 ${getLogLevelColor(log.level)}`}>
                            [{log.level}]
                          </span>
                          <span className="flex-1 break-all">
                            {log.message}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-gray-500 text-center py-8">
                      {isConnected 
                        ? `No logs received for ${selectedProcess} yet` 
                        : 'Waiting for connection to receive logs...'
                      }
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-gray-500">
                <div className="text-4xl mb-2">⚙️</div>
                <p>Select a process to view logs and controls</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="text-xs text-gray-500 text-center p-2 border-t bg-gray-50">
        ⚠️ Admin Panel - Use with caution
      </div>
    </div>
  );
};

export default AdminPanel;