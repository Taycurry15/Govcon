/**
 * API Service Layer - Maps all backend endpoints
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        // Handle errors globally
        console.error('API Error:', error);
        return Promise.reject(error);
      }
    );
  }

  // System endpoints
  async getSystemHealth() {
    return this.client.get('/api/system/health');
  }

  async getSystemMetrics() {
    return this.client.get('/api/system/metrics');
  }

  async getSystemInfo() {
    return this.client.get('/api/system/info');
  }

  async getSystemLogs(params?: { limit?: number; level?: string; component?: string }) {
    return this.client.get('/api/system/logs', { params });
  }

  async getServiceStatuses() {
    return this.client.get('/api/system/services');
  }

  async getSystemConfig() {
    return this.client.get('/api/system/config');
  }

  async updateSystemConfig(key: string, value: any) {
    return this.client.put(`/api/system/config/${key}`, { value });
  }

  async getDatabaseStatus() {
    return this.client.get('/api/system/database/status');
  }

  async backupDatabase() {
    return this.client.post('/api/system/database/backup');
  }

  async restartSystem() {
    return this.client.post('/api/system/restart');
  }

  // Agent endpoints
  async listAgents() {
    return this.client.get('/api/agents');
  }

  async getAgentStatus(agentName: string) {
    return this.client.get(`/api/agents/${agentName}/status`);
  }

  async getAllAgentStatuses() {
    return this.client.get('/api/agents/status/all');
  }

  async executeAgent(agentName: string, params: any) {
    return this.client.post(`/api/agents/${agentName}/execute`, {
      agent_name: agentName,
      parameters: params,
      async_execution: false,
    });
  }

  async stopAgent(agentName: string) {
    return this.client.post(`/api/agents/${agentName}/stop`);
  }

  async getAgentMetrics(agentName: string) {
    return this.client.get(`/api/agents/${agentName}/metrics`);
  }

  async getAgentConfig(agentName: string) {
    return this.client.get(`/api/agents/${agentName}/config`);
  }

  async updateAgentConfig(agentName: string, config: any) {
    return this.client.put(`/api/agents/${agentName}/config`, config);
  }

  async getAgentLogs(agentName: string, params?: { limit?: number; offset?: number }) {
    return this.client.get(`/api/agents/${agentName}/logs`, { params });
  }

  // Monitoring endpoints
  async startMonitoring() {
    return this.client.post('/api/monitoring/start');
  }

  async stopMonitoring() {
    return this.client.post('/api/monitoring/stop');
  }

  async getMonitoringStatus() {
    return this.client.get('/api/monitoring/status');
  }

  async getMonitoringReport() {
    return this.client.get('/api/monitoring/report');
  }

  async updateMonitoringConfig(config: any) {
    return this.client.put('/api/monitoring/config', config);
  }

  async getDetectedErrors(limit?: number) {
    return this.client.get('/api/monitoring/errors', { params: { limit } });
  }

  // Error endpoints
  async getErrorLogs(params?: { limit?: number; resolved?: boolean; component?: string }) {
    return this.client.get('/api/system/errors', { params });
  }

  async resolveError(errorId: string) {
    return this.client.post(`/api/system/errors/${errorId}/resolve`);
  }

  // Opportunities endpoints
  async getOpportunities(params?: any) {
    return this.client.get('/api/opportunities', { params });
  }

  async getOpportunity(id: string) {
    return this.client.get(`/api/opportunities/${id}`);
  }

  async createOpportunity(data: any) {
    return this.client.post('/api/opportunities', data);
  }

  async updateOpportunity(id: string, data: any) {
    return this.client.put(`/api/opportunities/${id}`, data);
  }

  async deleteOpportunity(id: string) {
    return this.client.delete(`/api/opportunities/${id}`);
  }

  // Proposals endpoints
  async getProposals(params?: any) {
    return this.client.get('/api/proposals', { params });
  }

  async getProposal(id: string) {
    return this.client.get(`/api/proposals/${id}`);
  }

  async createProposal(data: any) {
    return this.client.post('/api/proposals', data);
  }

  async updateProposal(id: string, data: any) {
    return this.client.put(`/api/proposals/${id}`, data);
  }

  async deleteProposal(id: string) {
    return this.client.delete(`/api/proposals/${id}`);
  }

  // Workflow endpoints
  async executeWorkflow(workflowName: string, params: any) {
    return this.client.post('/api/workflow/execute', {
      workflow_name: workflowName,
      parameters: params,
    });
  }

  async getWorkflowStatus(workflowId: string) {
    return this.client.get(`/api/workflow/${workflowId}/status`);
  }

  // Users endpoints
  async getCurrentUser() {
    return this.client.get('/api/users/me');
  }

  async getUsers(params?: any) {
    return this.client.get('/api/users', { params });
  }

  async getUser(id: string) {
    return this.client.get(`/api/users/${id}`);
  }

  async createUser(data: any) {
    return this.client.post('/api/users', data);
  }

  async updateUser(id: string, data: any) {
    return this.client.put(`/api/users/${id}`, data);
  }

  async deleteUser(id: string) {
    return this.client.delete(`/api/users/${id}`);
  }

  // Generic request method for custom endpoints
  async request<T = any>(config: AxiosRequestConfig): Promise<T> {
    const response = await this.client.request(config);
    return response.data;
  }
}

// Export singleton instance
export const api = new ApiService();

// Export types
export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  uptime_seconds: number;
  services: Record<string, string>;
}

export interface SystemMetrics {
  cpu_count: number;
  cpu_percent: number;
  memory_total_gb: number;
  memory_used_gb: number;
  memory_percent: number;
  disk_total_gb: number;
  disk_used_gb: number;
  disk_percent: number;
  network_sent_mb: number;
  network_recv_mb: number;
}

export interface AgentStatus {
  agent_name: string;
  status: 'idle' | 'running' | 'error' | 'completed';
  last_run?: string;
  last_error?: string;
  execution_count: number;
  average_duration_seconds?: number;
}

export interface AgentMetrics {
  agent_name: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_duration_seconds: number;
  last_24h_executions: number;
  error_rate: number;
}

export interface ErrorLog {
  id: string;
  timestamp: string;
  level: string;
  component: string;
  message: string;
  traceback?: string;
  resolved: boolean;
}

export interface MonitoringStatus {
  is_running: boolean;
  check_interval_seconds?: number;
  detected_errors_count?: number;
}
