import { NavLink, useNavigate } from 'react-router-dom'
import { ShieldCheck, Pill, Package, Heart, BarChart3, Settings, LogOut } from 'lucide-react'
import clsx from 'clsx'

const PawIcon = () => (
  <svg viewBox="0 0 100 100" className="w-8 h-8" fill="none">
    <ellipse cx="50" cy="70" rx="22" ry="18" fill="#14b8a6" />
    <ellipse cx="28" cy="48" rx="10" ry="13" fill="#14b8a6" />
    <ellipse cx="72" cy="48" rx="10" ry="13" fill="#14b8a6" />
    <ellipse cx="38" cy="34" rx="8" ry="11" fill="#14b8a6" />
    <ellipse cx="62" cy="34" rx="8" ry="11" fill="#14b8a6" />
  </svg>
)

const navItems = [
  { to: '/dea', label: 'DEA Compliance', icon: ShieldCheck },
  { to: '/scripts', label: 'Script Capture', icon: Pill },
  { to: '/inventory', label: 'Inventory & COGS', icon: Package },
  { to: '/adherence', label: 'Refill Adherence', icon: Heart },
  { to: '/scorecard', label: 'Practice Scorecard', icon: BarChart3 },
]

export default function Sidebar() {
  const navigate = useNavigate()
  const role = localStorage.getItem('user_role')

  function handleLogout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_role')
    navigate('/login')
  }

  return (
    <aside className="w-64 bg-navy-800 flex flex-col h-full" style={{ backgroundColor: '#0f1f35' }}>
      <div className="p-5 border-b border-navy-700" style={{ borderColor: '#162d4a' }}>
        <div className="flex items-center gap-3 mb-1">
          <PawIcon />
          <span className="text-white font-bold text-xl">ScriptHound</span>
        </div>
        <p className="text-xs ml-11" style={{ color: '#14b8a6' }}>by PawPrint Intelligence</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-teal-600 text-white'
                  : 'text-gray-300 hover:bg-navy-700 hover:text-white'
              )
            }
            style={({ isActive }) => isActive ? { backgroundColor: '#0d9488' } : {}}
          >
            <Icon className="w-5 h-5 shrink-0" />
            {label}
          </NavLink>
        ))}
        {role === 'superadmin' && (
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              clsx('flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive ? 'bg-teal-600 text-white' : 'text-gray-300 hover:bg-navy-700 hover:text-white')
            }
            style={({ isActive }) => isActive ? { backgroundColor: '#0d9488' } : {}}
          >
            <Settings className="w-5 h-5 shrink-0" />
            Admin
          </NavLink>
        )}
      </nav>

      <div className="p-4 border-t" style={{ borderColor: '#162d4a' }}>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-gray-400 hover:text-white text-sm w-full px-3 py-2 rounded-lg hover:bg-red-900 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
        <p className="text-xs text-gray-500 mt-3 px-3">PawPrint Intelligence LLC<br />scripthound.vet</p>
      </div>
    </aside>
  )
}
