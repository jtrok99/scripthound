import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const PawIcon = () => (
  <svg viewBox="0 0 100 100" className="w-16 h-16" fill="none">
    <ellipse cx="50" cy="70" rx="22" ry="18" fill="#14b8a6" />
    <ellipse cx="28" cy="48" rx="10" ry="13" fill="#14b8a6" />
    <ellipse cx="72" cy="48" rx="10" ry="13" fill="#14b8a6" />
    <ellipse cx="38" cy="34" rx="8" ry="11" fill="#14b8a6" />
    <ellipse cx="62" cy="34" rx="8" ry="11" fill="#14b8a6" />
  </svg>
)

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const form = new FormData()
      form.append('username', email)
      form.append('password', password)
      const { data } = await axios.post('/api/v1/auth/login', form)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)

      const me = await axios.get('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` },
      })
      localStorage.setItem('user_role', me.data.role)
      navigate('/dea')
    } catch {
      setError('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow-lg p-10 w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <PawIcon />
          <h1 className="text-3xl font-bold mt-3" style={{ color: '#0f1f35' }}>ScriptHound</h1>
          <p className="text-sm mt-1 font-medium" style={{ color: '#14b8a6' }}>by PawPrint Intelligence</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              placeholder="you@clinic.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              placeholder="••••••••"
            />
          </div>

          {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg text-sm font-semibold text-white transition-colors disabled:opacity-50"
            style={{ backgroundColor: loading ? '#162d4a' : '#0f1f35' }}
            onMouseOver={e => { if (!loading) (e.target as HTMLButtonElement).style.backgroundColor = '#14b8a6' }}
            onMouseOut={e => { if (!loading) (e.target as HTMLButtonElement).style.backgroundColor = '#0f1f35' }}
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-xs text-gray-400 mt-8">
          PawPrint Intelligence LLC — scripthound.vet
        </p>
      </div>
    </div>
  )
}
