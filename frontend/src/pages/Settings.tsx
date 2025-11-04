import { useState } from 'react'
import { Save, Key, Bell, Shield, Database, Settings as SettingsIcon } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore'

export default function Settings() {
  const { user } = useAuthStore()
  const [activeTab, setActiveTab] = useState<'general' | 'api' | 'notifications' | 'security'>('general')

  const handleSaveSettings = () => {
    toast.success('Settings updated successfully')
  }

  const tabs = [
    { key: 'general', label: 'General', icon: SettingsIcon },
    { key: 'api', label: 'API Keys', icon: Key },
    { key: 'notifications', label: 'Notifications', icon: Bell },
    { key: 'security', label: 'Security', icon: Shield },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">Manage system configuration and preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Tabs */}
        <div className="lg:col-span-1">
          <div className="card p-2">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key as any)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === tab.key
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <tab.icon className="w-5 h-5" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content Area */}
        <div className="lg:col-span-3">
          {activeTab === 'general' && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">General Settings</h2>
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Company Name
                  </label>
                  <input
                    type="text"
                    defaultValue="The Bronze Shield"
                    className="input w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Set-Aside Designations
                  </label>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2">
                      <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                      <span className="text-sm text-gray-700">SDVOSB (Service-Disabled Veteran-Owned Small Business)</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                      <span className="text-sm text-gray-700">VOSB (Veteran-Owned Small Business)</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                      <span className="text-sm text-gray-700">SB (Small Business)</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Target NAICS Codes
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Enter comma-separated NAICS codes (e.g., 541511, 541512, 541519)"
                    className="input w-full"
                    defaultValue="541511, 541512, 541519, 541611, 541618"
                  />
                  <p className="text-xs text-gray-500 mt-1">Opportunities matching these codes will be prioritized</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Target PSC Codes
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Enter comma-separated PSC codes (e.g., D302, R408, R425)"
                    className="input w-full"
                    defaultValue="D302, D307, R408, R425, 7030"
                  />
                  <p className="text-xs text-gray-500 mt-1">Product/Service codes your company specializes in</p>
                </div>

                <button onClick={handleSaveSettings} className="btn-primary h-10 px-4 gap-2">
                  <Save className="w-4 h-4" />
                  Save Changes
                </button>
              </div>
            </div>
          )}

          {activeTab === 'api' && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">API Configuration</h2>
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    SAM.gov API Key
                  </label>
                  <input
                    type="password"
                    placeholder="Enter your SAM.gov API key"
                    className="input w-full"
                    defaultValue="••••••••••••••••"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Required for opportunity discovery. Get your key at{' '}
                    <a href="https://sam.gov" target="_blank" rel="noopener noreferrer" className="text-primary-600">
                      sam.gov
                    </a>
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    OpenAI API Key
                  </label>
                  <input
                    type="password"
                    placeholder="Enter your OpenAI API key"
                    className="input w-full"
                    defaultValue="••••••••••••••••"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Required for AI agent operations
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    BLS API Key (Optional)
                  </label>
                  <input
                    type="password"
                    placeholder="Enter your BLS API key"
                    className="input w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    For enhanced labor rate data in pricing
                  </p>
                </div>

                <div className="flex items-center gap-2 p-4 bg-blue-50 rounded-lg">
                  <Database className="w-5 h-5 text-blue-600" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-blue-900">Database Connection</p>
                    <p className="text-xs text-blue-700">PostgreSQL connected successfully</p>
                  </div>
                  <span className="badge badge-success">Active</span>
                </div>

                <button onClick={handleSaveSettings} className="btn-primary h-10 px-4 gap-2">
                  <Save className="w-4 h-4" />
                  Save API Keys
                </button>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Notification Preferences</h2>
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3">Email Notifications</h3>
                  <div className="space-y-2">
                    <label className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">New opportunities discovered</span>
                      <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                    </label>
                    <label className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">Bid/No-Bid recommendations</span>
                      <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                    </label>
                    <label className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">Workflow stage completions</span>
                      <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                    </label>
                    <label className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">Proposal review requests</span>
                      <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                    </label>
                    <label className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">Approaching deadlines</span>
                      <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                    </label>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3">In-App Notifications</h3>
                  <div className="space-y-2">
                    <label className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">System alerts</span>
                      <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                    </label>
                    <label className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">Team mentions</span>
                      <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Notification Email
                  </label>
                  <input
                    type="email"
                    defaultValue={user?.email}
                    className="input w-full"
                  />
                </div>

                <button onClick={handleSaveSettings} className="btn-primary h-10 px-4 gap-2">
                  <Save className="w-4 h-4" />
                  Save Preferences
                </button>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Security Settings</h2>
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3">Password</h3>
                  <div className="space-y-3">
                    <input
                      type="password"
                      placeholder="Current password"
                      className="input w-full"
                    />
                    <input
                      type="password"
                      placeholder="New password"
                      className="input w-full"
                    />
                    <input
                      type="password"
                      placeholder="Confirm new password"
                      className="input w-full"
                    />
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3">Two-Factor Authentication</h3>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-gray-900">2FA Status</p>
                      <p className="text-xs text-gray-500">Add an extra layer of security</p>
                    </div>
                    <button className="btn-secondary h-8 px-3 text-sm">
                      Enable 2FA
                    </button>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3">Compliance</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4 text-green-600" />
                        <span className="text-sm font-medium text-green-900">CMMC Level 2</span>
                      </div>
                      <span className="badge badge-success">Aligned</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4 text-green-600" />
                        <span className="text-sm font-medium text-green-900">NIST 800-171</span>
                      </div>
                      <span className="badge badge-success">Aligned</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3">Session Management</h3>
                  <div className="space-y-2">
                    <label className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">Auto-logout after inactivity</span>
                      <select className="input w-32 h-8 text-sm">
                        <option>15 minutes</option>
                        <option>30 minutes</option>
                        <option>1 hour</option>
                        <option>Never</option>
                      </select>
                    </label>
                  </div>
                </div>

                <button onClick={handleSaveSettings} className="btn-primary h-10 px-4 gap-2">
                  <Save className="w-4 h-4" />
                  Save Security Settings
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
