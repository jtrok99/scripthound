import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '../../client'

export default function TenantManagement() {
  const qc = useQueryClient()
  const [tenantForm, setTenantForm] = useState({ name: '', slug: '', plan_tier: 'starter' })
  const [userForm, setUserForm] = useState({ email: '', full_name: '', password: '', role: 'user', tenant_id: '' })
  const [activeTab, setActiveTab] = useState<'tenants' | 'users'>('tenants')

  const tenants = useQuery({ queryKey: ['admin-tenants'], queryFn: () => client.get('/v1/admin/tenants').then(r => r.data) })
  const users = useQuery({ queryKey: ['admin-users'], queryFn: () => client.get('/v1/admin/users').then(r => r.data), enabled: activeTab === 'users' })

  const createTenant = useMutation({
    mutationFn: (body: any) => client.post('/v1/admin/tenants', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-tenants'] }); setTenantForm({ name: '', slug: '', plan_tier: 'starter' }) },
  })

  const createUser = useMutation({
    mutationFn: (body: any) => client.post('/v1/admin/users', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-users'] }); setUserForm({ email: '', full_name: '', password: '', role: 'user', tenant_id: '' }) },
  })

  const tabStyle = (t: string) => ({
    padding: '8px 20px', cursor: 'pointer', background: 'none', border: 'none',
    borderBottom: activeTab === t ? '2px solid #14b8a6' : '2px solid transparent',
    color: activeTab === t ? '#14b8a6' : '#6b7280', fontWeight: activeTab === t ? 600 : 400,
  } as React.CSSProperties)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: '#0f1f35' }}>Admin — Tenant Management</h1>
        <p className="text-sm text-gray-500">Manage tenants and users (superadmin only)</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="flex border-b border-gray-200 px-6">
          <button style={tabStyle('tenants')} onClick={() => setActiveTab('tenants')}>Tenants</button>
          <button style={tabStyle('users')} onClick={() => setActiveTab('users')}>Users</button>
        </div>

        <div className="p-6">
          {activeTab === 'tenants' && (
            <div className="space-y-6">
              <form onSubmit={e => { e.preventDefault(); createTenant.mutate(tenantForm) }} className="bg-gray-50 rounded-lg p-4 space-y-3">
                <h3 className="font-semibold text-gray-700">Create New Tenant</h3>
                <div className="grid grid-cols-3 gap-3">
                  <input placeholder="Practice Name" value={tenantForm.name} onChange={e => setTenantForm(f => ({...f, name: e.target.value}))} required className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                  <input placeholder="slug (e.g. greensboro-animal)" value={tenantForm.slug} onChange={e => setTenantForm(f => ({...f, slug: e.target.value}))} required className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                  <select value={tenantForm.plan_tier} onChange={e => setTenantForm(f => ({...f, plan_tier: e.target.value}))} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    <option value="starter">Starter</option>
                    <option value="professional">Professional</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
                <button type="submit" disabled={createTenant.isPending} className="px-4 py-2 text-sm font-medium text-white rounded-lg" style={{ backgroundColor: '#14b8a6' }}>
                  {createTenant.isPending ? 'Creating…' : 'Create Tenant'}
                </button>
                {createTenant.isError && <p className="text-red-600 text-sm">Error creating tenant</p>}
              </form>

              <table className="w-full text-sm">
                <thead><tr className="border-b border-gray-200">{['Name', 'Slug', 'Plan', 'Active'].map(h => <th key={h} className="text-left py-2 px-2 text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr></thead>
                <tbody>
                  {tenants.data?.map((t: any) => (
                    <tr key={t.id} className="border-b border-gray-100">
                      <td className="py-2 px-2 font-medium">{t.name}</td>
                      <td className="py-2 px-2 text-gray-500">{t.slug}</td>
                      <td className="py-2 px-2">{t.plan_tier}</td>
                      <td className="py-2 px-2">{t.is_active ? <span className="text-emerald-600">Active</span> : <span className="text-red-500">Inactive</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="space-y-6">
              <form onSubmit={e => { e.preventDefault(); createUser.mutate(userForm) }} className="bg-gray-50 rounded-lg p-4 space-y-3">
                <h3 className="font-semibold text-gray-700">Create New User</h3>
                <div className="grid grid-cols-2 gap-3">
                  <input placeholder="Email" type="email" value={userForm.email} onChange={e => setUserForm(f => ({...f, email: e.target.value}))} required className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                  <input placeholder="Full Name" value={userForm.full_name} onChange={e => setUserForm(f => ({...f, full_name: e.target.value}))} required className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                  <input placeholder="Password" type="password" value={userForm.password} onChange={e => setUserForm(f => ({...f, password: e.target.value}))} required className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                  <select value={userForm.role} onChange={e => setUserForm(f => ({...f, role: e.target.value}))} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                    <option value="superadmin">Superadmin</option>
                  </select>
                  <select value={userForm.tenant_id} onChange={e => setUserForm(f => ({...f, tenant_id: e.target.value}))} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    <option value="">No Tenant (superadmin)</option>
                    {tenants.data?.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                </div>
                <button type="submit" disabled={createUser.isPending} className="px-4 py-2 text-sm font-medium text-white rounded-lg" style={{ backgroundColor: '#14b8a6' }}>
                  {createUser.isPending ? 'Creating…' : 'Create User'}
                </button>
                {createUser.isError && <p className="text-red-600 text-sm">Error creating user</p>}
              </form>

              <table className="w-full text-sm">
                <thead><tr className="border-b border-gray-200">{['Email', 'Full Name', 'Role', 'Tenant'].map(h => <th key={h} className="text-left py-2 px-2 text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr></thead>
                <tbody>
                  {users.data?.map((u: any) => (
                    <tr key={u.id} className="border-b border-gray-100">
                      <td className="py-2 px-2">{u.email}</td>
                      <td className="py-2 px-2 font-medium">{u.full_name}</td>
                      <td className="py-2 px-2">{u.role}</td>
                      <td className="py-2 px-2 text-gray-500">{u.tenant_id || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
