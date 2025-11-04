import { Routes, Route, Navigate } from 'react-router-dom'
// Toast notifications (used in JSX at line 44)
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Opportunities from './pages/Opportunities'
import OpportunityDetail from './pages/OpportunityDetail'
import PreSolicitations from './pages/PreSolicitations'
import Proposals from './pages/Proposals'
import ProposalDetail from './pages/ProposalDetail'
import Workflow from './pages/Workflow'
import Settings from './pages/Settings'
// System monitoring pages (used in Routes at lines 39-40)
import SystemDashboard from './pages/SystemDashboard'
import AdminPanel from './pages/AdminPanel'

function App() {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="opportunities" element={<Opportunities />} />
          <Route path="opportunities/:id" element={<OpportunityDetail />} />
          <Route path="pre-solicitations" element={<PreSolicitations />} />
          <Route path="proposals" element={<Proposals />} />
          <Route path="proposals/:id" element={<ProposalDetail />} />
          <Route path="workflow" element={<Workflow />} />
          <Route path="settings" element={<Settings />} />
          <Route path="system" element={<SystemDashboard />} />
          <Route path="admin" element={<AdminPanel />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#fff',
            color: '#171717',
            borderRadius: '12px',
            padding: '16px',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
          },
        }}
      />
    </>
  )
}

export default App
