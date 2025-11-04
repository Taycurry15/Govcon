/**
 * Admin Panel - Backend configuration and management
 */

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Settings,
  Database,
  Server,
  Code,
  Save,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { api } from '../services/api';
import toast from 'react-hot-toast';

interface ConfigItem {
  key: string;
  value: any;
  category: string;
  description: string;
  editable: boolean;
}

const AdminPanel: React.FC = () => {
  const [config, setConfig] = useState<ConfigItem[]>([]);
  const [dbStatus, setDbStatus] = useState<any>(null);
  const [systemInfo, setSystemInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editedValues, setEditedValues] = useState<Record<string, any>>({});

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [configRes, dbRes, infoRes] = await Promise.all([
        api.getSystemConfig(),
        api.getDatabaseStatus(),
        api.getSystemInfo(),
      ]);

      setConfig(configRes.data);
      setDbStatus(dbRes.data);
      setSystemInfo(infoRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching admin data:', error);
      toast.error('Failed to load admin panel');
      setLoading(false);
    }
  };

  const handleValueChange = (key: string, value: any) => {
    setEditedValues((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSaveConfig = async (key: string) => {
    try {
      await api.updateSystemConfig(key, editedValues[key]);
      toast.success(`Configuration ${key} updated successfully`);

      // Remove from edited values
      const newEditedValues = { ...editedValues };
      delete newEditedValues[key];
      setEditedValues(newEditedValues);

      // Refresh config
      await fetchData();
    } catch (error) {
      console.error('Error saving config:', error);
      toast.error('Failed to save configuration');
    }
  };

  const handleBackupDatabase = async () => {
    try {
      const res = await api.backupDatabase();
      toast.success(`Database backup created: ${res.data.backup_id}`);
    } catch (error) {
      console.error('Error backing up database:', error);
      toast.error('Failed to backup database');
    }
  };

  const handleRestartSystem = async () => {
    if (!window.confirm('Are you sure you want to restart the system?')) {
      return;
    }

    try {
      await api.restartSystem();
      toast.success('System restart initiated');
    } catch (error) {
      console.error('Error restarting system:', error);
      toast.error('Failed to restart system');
    }
  };

  const groupConfigByCategory = () => {
    const grouped: Record<string, ConfigItem[]> = {};
    config.forEach((item) => {
      if (!grouped[item.category]) {
        grouped[item.category] = [];
      }
      grouped[item.category].push(item);
    });
    return grouped;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading admin panel...</p>
        </div>
      </div>
    );
  }

  const groupedConfig = groupConfigByCategory();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-gray-900">Admin Panel</h1>
              <p className="text-gray-600 mt-1">
                Manage backend configuration and system settings
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" onClick={() => fetchData()}>
                <RefreshCw className="w-4 h-4" />
                Refresh
              </Button>
              <Button variant="danger" onClick={handleRestartSystem}>
                <AlertTriangle className="w-4 h-4" />
                Restart System
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* System Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card elevated>
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-blue-100 rounded-xl">
                <Server className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">System Info</h3>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Platform:</span>
                <span className="font-medium text-gray-900">{systemInfo?.platform}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Architecture:</span>
                <span className="font-medium text-gray-900">{systemInfo?.architecture}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Python:</span>
                <span className="font-medium text-gray-900">{systemInfo?.python_version}</span>
              </div>
            </div>
          </Card>

          <Card elevated>
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-green-100 rounded-xl">
                <Database className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Database</h3>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <span className="font-medium text-green-600">{dbStatus?.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Tables:</span>
                <span className="font-medium text-gray-900">{dbStatus?.tables?.length || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Connections:</span>
                <span className="font-medium text-gray-900">{dbStatus?.total_connections || 0}</span>
              </div>
            </div>
            <Button variant="secondary" size="sm" className="mt-4 w-full" onClick={handleBackupDatabase}>
              Create Backup
            </Button>
          </Card>

          <Card elevated>
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-purple-100 rounded-xl">
                <Code className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">API</h3>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Version:</span>
                <span className="font-medium text-gray-900">1.0.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <span className="font-medium text-green-600">Operational</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Endpoints:</span>
                <span className="font-medium text-gray-900">45+</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Configuration Sections */}
        {Object.entries(groupedConfig).map(([category, items]) => (
          <Card key={category} className="mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Settings className="w-5 h-5 text-blue-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900">{category}</h2>
            </div>

            <div className="space-y-4">
              {items.map((item) => (
                <motion.div
                  key={item.key}
                  className="p-4 bg-gray-50 rounded-lg border border-gray-200"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h4 className="font-medium text-gray-900">{item.key}</h4>
                        {!item.editable && (
                          <span className="px-2 py-0.5 bg-gray-200 text-gray-600 text-xs rounded">
                            Read-only
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{item.description}</p>

                      {item.editable ? (
                        <div className="flex items-center gap-3">
                          <input
                            type="text"
                            value={
                              editedValues[item.key] !== undefined
                                ? editedValues[item.key]
                                : Array.isArray(item.value)
                                ? item.value.join(', ')
                                : item.value
                            }
                            onChange={(e) => handleValueChange(item.key, e.target.value)}
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                          {editedValues[item.key] !== undefined && (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleSaveConfig(item.key)}
                            >
                              <Save className="w-4 h-4" />
                              Save
                            </Button>
                          )}
                        </div>
                      ) : (
                        <div className="px-3 py-2 bg-white border border-gray-200 rounded-lg">
                          <code className="text-sm text-gray-900">
                            {Array.isArray(item.value) ? item.value.join(', ') : item.value}
                          </code>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default AdminPanel;
