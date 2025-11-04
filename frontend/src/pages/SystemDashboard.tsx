/**
 * System Dashboard - Apple-inspired monitoring interface
 */

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, Cpu, HardDrive, Zap, AlertCircle, CheckCircle } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { api, SystemHealth, SystemMetrics, AgentStatus } from '../services/api';
import { websocket, WS_CHANNELS } from '../services/websocket';

const SystemDashboard: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [monitoringStatus, setMonitoringStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);

    // Connect to WebSocket for real-time updates
    websocket.connect(WS_CHANNELS.SYSTEM, () => {
      console.log('Connected to system updates');
    });

    websocket.connect(WS_CHANNELS.AGENTS, () => {
      console.log('Connected to agent updates');
    });

    // Subscribe to updates
    const unsubscribeSystem = websocket.subscribe(WS_CHANNELS.SYSTEM, (data) => {
      if (data.type === 'system_update') {
        console.log('System update received:', data);
        fetchData();
      }
    });

    const unsubscribeAgents = websocket.subscribe(WS_CHANNELS.AGENTS, (data) => {
      if (data.type === 'agent_update') {
        console.log('Agent update received:', data);
        fetchAgents();
      }
    });

    return () => {
      clearInterval(interval);
      unsubscribeSystem();
      unsubscribeAgents();
      websocket.disconnect(WS_CHANNELS.SYSTEM);
      websocket.disconnect(WS_CHANNELS.AGENTS);
    };
  }, []);

  const fetchData = async () => {
    try {
      const [healthRes, metricsRes, monitoringRes] = await Promise.all([
        api.getSystemHealth(),
        api.getSystemMetrics(),
        api.getMonitoringStatus(),
      ]);

      setHealth(healthRes.data);
      setMetrics(metricsRes.data);
      setMonitoringStatus(monitoringRes.data);

      await fetchAgents();
      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setLoading(false);
    }
  };

  const fetchAgents = async () => {
    try {
      const res = await api.getAllAgentStatuses();
      setAgents(res.data);
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  };

  const handleStartMonitoring = async () => {
    try {
      await api.startMonitoring();
      await fetchData();
    } catch (error) {
      console.error('Error starting monitoring:', error);
    }
  };

  const handleStopMonitoring = async () => {
    try {
      await api.stopMonitoring();
      await fetchData();
    } catch (error) {
      console.error('Error stopping monitoring:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'completed':
      case 'idle':
        return 'text-green-600';
      case 'degraded':
      case 'running':
        return 'text-yellow-600';
      case 'unhealthy':
      case 'error':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'completed':
        return <CheckCircle className="w-5 h-5" />;
      case 'degraded':
      case 'running':
        return <Activity className="w-5 h-5 animate-pulse" />;
      case 'unhealthy':
      case 'error':
        return <AlertCircle className="w-5 h-5" />;
      default:
        return <Activity className="w-5 h-5" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <Activity className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-gray-900">System Dashboard</h1>
              <p className="text-gray-600 mt-1">Real-time monitoring and control</p>
            </div>
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 ${getStatusColor(health?.status || 'unknown')}`}>
                {getStatusIcon(health?.status || 'unknown')}
                <span className="font-medium capitalize">{health?.status || 'Unknown'}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* System Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card elevated hoverable>
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-xl">
                <Cpu className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">CPU Usage</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {metrics?.cpu_percent?.toFixed(1)}%
                </p>
              </div>
            </div>
          </Card>

          <Card elevated hoverable>
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-xl">
                <Activity className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Memory Usage</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {metrics?.memory_percent?.toFixed(1)}%
                </p>
              </div>
            </div>
          </Card>

          <Card elevated hoverable>
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-100 rounded-xl">
                <HardDrive className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Disk Usage</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {metrics?.disk_percent?.toFixed(1)}%
                </p>
              </div>
            </div>
          </Card>

          <Card elevated hoverable>
            <div className="flex items-center gap-4">
              <div className="p-3 bg-orange-100 rounded-xl">
                <Zap className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Active Agents</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {agents.filter(a => a.status === 'running').length}
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* Monitoring Agent Control */}
        <Card className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Autonomous Monitoring Agent</h2>
              <p className="text-gray-600 mt-1">
                Auto-detect and fix errors in real-time
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 ${monitoringStatus?.is_running ? 'text-green-600' : 'text-gray-400'}`}>
                <div className={`w-3 h-3 rounded-full ${monitoringStatus?.is_running ? 'bg-green-600 animate-pulse' : 'bg-gray-400'}`} />
                <span className="font-medium">
                  {monitoringStatus?.is_running ? 'Running' : 'Stopped'}
                </span>
              </div>
              {monitoringStatus?.is_running ? (
                <Button variant="danger" onClick={handleStopMonitoring}>
                  Stop Monitoring
                </Button>
              ) : (
                <Button variant="primary" onClick={handleStartMonitoring}>
                  Start Monitoring
                </Button>
              )}
            </div>
          </div>
          {monitoringStatus?.is_running && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Check Interval</p>
                  <p className="text-lg font-medium text-gray-900">
                    {monitoringStatus.check_interval_seconds}s
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Detected Errors</p>
                  <p className="text-lg font-medium text-gray-900">
                    {monitoringStatus.detected_errors_count || 0}
                  </p>
                </div>
              </div>
            </div>
          )}
        </Card>

        {/* Agents Status */}
        <Card>
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Agent Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <motion.div
                key={agent.agent_name}
                className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors"
                whileHover={{ scale: 1.02 }}
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-gray-900 capitalize">
                    {agent.agent_name.replace('_', ' ')}
                  </h3>
                  <div className={`flex items-center gap-1 ${getStatusColor(agent.status)}`}>
                    {getStatusIcon(agent.status)}
                  </div>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Status:</span>
                    <span className={`font-medium capitalize ${getStatusColor(agent.status)}`}>
                      {agent.status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Executions:</span>
                    <span className="font-medium text-gray-900">{agent.execution_count}</span>
                  </div>
                  {agent.average_duration_seconds && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Avg Duration:</span>
                      <span className="font-medium text-gray-900">
                        {agent.average_duration_seconds.toFixed(2)}s
                      </span>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default SystemDashboard;
