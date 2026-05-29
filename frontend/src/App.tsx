import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/auth/Login'
import DEADashboard from './pages/dea/DEADashboard'
import ScriptCaptureDashboard from './pages/scripts/ScriptCaptureDashboard'
import InventoryDashboard from './pages/inventory/InventoryDashboard'
import AdherenceDashboard from './pages/adherence/AdherenceDashboard'
import PracticeScorecard from './pages/benchmarking/PracticeScorecard'
import TenantManagement from './pages/admin/TenantManagement'
import Sidebar from './components/layout/Sidebar'

function AuthLayout({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token')
  if (!token) return <Navigate to="/login" replace />
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<AuthLayout><Navigate to="/dea" replace /></AuthLayout>} />
        <Route path="/dea" element={<AuthLayout><DEADashboard /></AuthLayout>} />
        <Route path="/scripts" element={<AuthLayout><ScriptCaptureDashboard /></AuthLayout>} />
        <Route path="/inventory" element={<AuthLayout><InventoryDashboard /></AuthLayout>} />
        <Route path="/adherence" element={<AuthLayout><AdherenceDashboard /></AuthLayout>} />
        <Route path="/scorecard" element={<AuthLayout><PracticeScorecard /></AuthLayout>} />
        <Route path="/admin" element={<AuthLayout><TenantManagement /></AuthLayout>} />
        <Route path="*" element={<Navigate to="/dea" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
