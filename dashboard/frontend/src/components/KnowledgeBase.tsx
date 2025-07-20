import React, { useState } from 'react';
import { useKnowledge, Task } from '@/hooks/useKnowledge';

interface KnowledgeBaseProps {
  // Props for the knowledge base component
}

const KnowledgeBase: React.FC<KnowledgeBaseProps> = () => {
  const [activeTab, setActiveTab] = useState<'tasks' | 'detailed'>('tasks');
  const {
    tasks,
    summary,
    tutorialProgress,
    npcInteractions,
    knowledgeAvailable,
    loading,
    error,
    refreshTasks,
    updateTaskStatus
  } = useKnowledge();

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800';
      case 'pending': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'in_progress': return '🔄';
      case 'pending': return '⏳';
      default: return '❓';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'navigation': return '🗺️';
      case 'pokemon': return '🎮';
      case 'battle': return '⚔️';
      case 'items': return '🎒';
      default: return '📋';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-2xl mb-2">⏳</div>
          <div className="text-gray-600">Loading knowledge...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-2xl mb-2">❌</div>
          <div className="text-red-600 mb-2">Error loading knowledge</div>
          <div className="text-sm text-gray-500">{error}</div>
          <button 
            onClick={refreshTasks}
            className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold text-gray-800 flex items-center">
          <span className="mr-2">🧠</span>
          Knowledge Base
        </h2>
        <div className="flex items-center justify-between mt-2">
          <div className="text-sm text-gray-500">
            {tasks.filter(t => t.status !== 'completed').length} active tasks
          </div>
          {!knowledgeAvailable && (
            <div className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
              Mock Data
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Task List */}
        <div className="space-y-3">
          {tasks.map((task) => (
            <div key={task.id} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center">
                  <span className="text-lg mr-2">{getCategoryIcon(task.category)}</span>
                  <h4 className="font-medium text-gray-800">{task.title}</h4>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(task.priority)}`}>
                    {task.priority}
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                    {getStatusIcon(task.status)} {task.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
              
              <p className="text-sm text-gray-600 mb-2">{task.description}</p>
              
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span className="capitalize">📂 {task.category}</span>
                <span>ID: {task.id}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Task Statistics */}
        <div className="mt-6 bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-800 mb-3">📊 Task Overview</h4>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-600">
                {summary?.tasks.active || tasks.filter(t => t.status === 'in_progress').length}
              </div>
              <div className="text-xs text-gray-600">In Progress</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-600">
                {summary?.tasks.pending || tasks.filter(t => t.status === 'pending').length}
              </div>
              <div className="text-xs text-gray-600">Pending</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">
                {summary?.tasks.completed || tasks.filter(t => t.status === 'completed').length}
              </div>
              <div className="text-xs text-gray-600">Completed</div>
            </div>
          </div>
          
          {/* Character info if available */}
          {summary && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="text-sm text-gray-600">
                <div className="flex justify-between items-center">
                  <span>🎮 Character: {summary.character.name}</span>
                  <span>📍 Phase: {summary.character.game_phase}</span>
                </div>
                {summary.character.current_objective && (
                  <div className="mt-1 text-xs text-blue-600">
                    🎯 {summary.character.current_objective}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="text-xs text-gray-500 text-center p-4 border-t">
        🤖 AI Knowledge System - Real-time updates
      </div>
    </div>
  );
};

export default KnowledgeBase;