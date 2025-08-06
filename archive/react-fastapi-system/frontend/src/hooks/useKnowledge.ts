import { useState, useEffect, useCallback } from 'react';

export interface Task {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'in_progress' | 'completed';
  category: string;
  location_id?: number;
  prerequisites?: string[];
  created_at?: number;
  updated_at?: number;
}

export interface KnowledgeSummary {
  character: {
    name: string;
    current_objective?: string;
    game_phase: string;
    tutorial_progress: number;
  };
  tasks: {
    total: number;
    completed: number;
    active: number;
    pending: number;
  };
  recent_activity: {
    actions: number;
    dialogues: number;
    last_action?: string;
    last_dialogue?: string;
  };
  locations: {
    discovered: number;
    current?: number;
  };
  updated_at: number;
  mock_data?: boolean;
}

export interface TutorialProgress {
  completed_steps: string[];
  current_phase: string;
  guidance: string;
  progress_summary: string;
  next_steps: string;
  total_completed: number;
  knowledge_available?: boolean;
  mock_data?: boolean;
}

export interface NPCInteraction {
  npc_name: string;
  npc_role: string;
  dialogue_text: string;
  player_response: string;
  outcome: string;
  timestamp: number;
  location_id: number;
  important_info: string[];
}

export interface UseKnowledgeReturn {
  tasks: Task[];
  summary: KnowledgeSummary | null;
  tutorialProgress: TutorialProgress | null;
  npcInteractions: NPCInteraction[];
  knowledgeAvailable: boolean;
  loading: boolean;
  error: string | null;
  refreshTasks: () => void;
  refreshSummary: () => void;
  refreshTutorial: () => void;
  refreshNPCs: () => void;
  createTask: (task: Partial<Task>) => Promise<boolean>;
  updateTaskStatus: (taskId: string, status: string) => Promise<boolean>;
}

const API_BASE = `/api/v1/knowledge`;

export const useKnowledge = (): UseKnowledgeReturn => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [summary, setSummary] = useState<KnowledgeSummary | null>(null);
  const [tutorialProgress, setTutorialProgress] = useState<TutorialProgress | null>(null);
  const [npcInteractions, setNpcInteractions] = useState<NPCInteraction[]>([]);
  const [knowledgeAvailable, setKnowledgeAvailable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleApiCall = useCallback(async <T>(
    url: string, 
    options?: RequestInit
  ): Promise<{ data: T; available: boolean }> => {
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      const available = result.knowledge_available !== false;
      
      return { data: result, available };
    } catch (err) {
      console.error('API call failed:', err);
      throw err;
    }
  }, []);

  const refreshTasks = useCallback(async () => {
    try {
      const { data, available } = await handleApiCall<{
        tasks: Task[];
        total: number;
        knowledge_available: boolean;
        message?: string;
      }>(`${API_BASE}/tasks`);

      setTasks(data.tasks || []);
      setKnowledgeAvailable(available);
      setError(null);
    } catch (err) {
      setError(`Failed to load tasks: ${err}`);
      setTasks([]);
    }
  }, [handleApiCall]);

  const refreshSummary = useCallback(async () => {
    try {
      const { data, available } = await handleApiCall<{
        summary: KnowledgeSummary;
        knowledge_available: boolean;
      }>(`${API_BASE}/summary`);

      setSummary(data.summary);
      setKnowledgeAvailable(available);
      setError(null);
    } catch (err) {
      setError(`Failed to load summary: ${err}`);
      setSummary(null);
    }
  }, [handleApiCall]);

  const refreshTutorial = useCallback(async () => {
    try {
      const { data } = await handleApiCall<TutorialProgress>(`${API_BASE}/tutorial`);
      setTutorialProgress(data);
      setError(null);
    } catch (err) {
      setError(`Failed to load tutorial: ${err}`);
      setTutorialProgress(null);
    }
  }, [handleApiCall]);

  const refreshNPCs = useCallback(async () => {
    try {
      const { data } = await handleApiCall<{
        interactions: NPCInteraction[];
        total: number;
        knowledge_available: boolean;
      }>(`${API_BASE}/npcs`);

      setNpcInteractions(data.interactions || []);
      setError(null);
    } catch (err) {
      setError(`Failed to load NPCs: ${err}`);
      setNpcInteractions([]);
    }
  }, [handleApiCall]);

  const createTask = useCallback(async (task: Partial<Task>): Promise<boolean> => {
    try {
      const { data } = await handleApiCall<{
        message: string;
        success: boolean;
        knowledge_available?: boolean;
      }>(`${API_BASE}/tasks`, {
        method: 'POST',
        body: JSON.stringify(task),
      });

      if (data.success) {
        await refreshTasks(); // Refresh tasks after creating
        return true;
      }
      return false;
    } catch (err) {
      setError(`Failed to create task: ${err}`);
      return false;
    }
  }, [handleApiCall, refreshTasks]);

  const updateTaskStatus = useCallback(async (taskId: string, status: string): Promise<boolean> => {
    try {
      const { data } = await handleApiCall<{
        message: string;
        success: boolean;
        knowledge_available?: boolean;
      }>(`${API_BASE}/tasks/${taskId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });

      if (data.success) {
        await refreshTasks(); // Refresh tasks after updating
        await refreshSummary(); // Refresh summary to update counts
        return true;
      }
      return false;
    } catch (err) {
      setError(`Failed to update task: ${err}`);
      return false;
    }
  }, [handleApiCall, refreshTasks, refreshSummary]);

  // Initial load
  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await Promise.all([
        refreshTasks(),
        refreshSummary(),
        refreshTutorial(),
        refreshNPCs(),
      ]);
      setLoading(false);
    };

    loadAll();
  }, [refreshTasks, refreshSummary, refreshTutorial, refreshNPCs]);

  // Periodic refresh
  useEffect(() => {
    const interval = setInterval(() => {
      // Refresh data every 30 seconds
      refreshTasks();
      refreshSummary();
    }, 30000);

    return () => clearInterval(interval);
  }, [refreshTasks, refreshSummary]);

  return {
    tasks,
    summary,
    tutorialProgress,
    npcInteractions,
    knowledgeAvailable,
    loading,
    error,
    refreshTasks,
    refreshSummary,
    refreshTutorial,
    refreshNPCs,
    createTask,
    updateTaskStatus,
  };
};