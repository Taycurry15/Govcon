import { useState } from 'react'
import { Shield } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { authApi } from '../lib/api'
import { useAuthStore } from '../store/authStore'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = useAuthStore((state) => state.login)

  const loginMutation = useMutation({
    mutationFn: () => authApi.login(email, password),
    onSuccess: async (data) => {
      const user = await authApi.getCurrentUser()
      login(data.access_token, user)
      toast.success('Welcome back!')
    },
    onError: () => {
      toast.error('Invalid email or password')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    loginMutation.mutate()
  }

  // Development bypass - remove in production
  const handleDemoLogin = () => {
    const demoUser = {
      id: 'demo-user',
      email: 'admin@bronzeshield.com',
      full_name: 'Admin User',
      role: 'admin',
      is_active: true,
      can_manage_certifications: true,
    }
    login('demo-token', demoUser)
    toast.success('Logged in as demo user (Development Mode)')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 via-primary-50/20 to-gray-100 relative overflow-hidden">
      {/* Apple-style background blur effect */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary-100/40 via-transparent to-transparent" />

      <div className="w-full max-w-md relative z-10 px-4">
        <div className="bg-white/80 backdrop-blur-apple rounded-apple-2xl shadow-apple-xl p-10 border border-white/50 animate-slide-up">
          {/* Logo and Title */}
          <div className="text-center mb-10">
            <div className="flex justify-center mb-5">
              <div className="w-20 h-20 bg-gradient-to-br from-primary-500 to-primary-600 rounded-apple-xl flex items-center justify-center shadow-apple-lg transform hover:scale-105 transition-transform duration-300">
                <Shield className="w-12 h-12 text-white" />
              </div>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-gray-900 mb-2">The Bronze Shield</h1>
            <p className="text-[15px] text-gray-600 font-medium">SDVOSB | VOSB | SB</p>
            <p className="text-sm text-gray-500 mt-2">GovCon AI Pipeline</p>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-[15px] font-semibold text-gray-900 mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input w-full"
                placeholder="you@bronzeshield.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-[15px] font-semibold text-gray-900 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input w-full"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loginMutation.isPending}
              className="btn-primary w-full h-12 text-[15px] font-semibold rounded-apple-lg mt-6"
            >
              {loginMutation.isPending ? 'Signing in...' : 'Sign In'}
            </button>

            {/* Development Mode - Demo Login */}
            {import.meta.env.DEV && (
              <div className="mt-6">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-200/60" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-3 bg-white/80 backdrop-blur-sm text-gray-500 font-medium">Development Mode</span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleDemoLogin}
                  className="mt-5 w-full h-12 px-4 py-2 border border-gray-200 rounded-apple-lg text-[15px] font-semibold text-primary-600 bg-primary-50/50 hover:bg-primary-100/50 transition-all duration-200 shadow-apple-sm hover:shadow-apple active:scale-[0.98]"
                >
                  🚀 Demo Login (Skip Authentication)
                </button>
                <p className="mt-3 text-xs text-center text-gray-500 font-medium">
                  Bypass authentication for development
                </p>
              </div>
            )}
          </form>

          {/* Footer */}
          <div className="mt-8 text-center text-xs text-gray-500">
            <p className="font-medium">Production-Ready Multi-Agent Proposal System</p>
            <p className="mt-1.5 text-gray-400">Built with OpenAI Agents SDK</p>
          </div>
        </div>
      </div>
    </div>
  )
}
