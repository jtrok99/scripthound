import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import client from '../../client'
import KPICard from '../../components/common/KPICard'
import StatusBadge from '../../components/common/StatusBadge'

type Tab = 'overview' | 'outreach'

const SPECIES_COLORS: Record<string, string> = { dog: '#2dd4bf', cat: '#60a5fa', horse: '#f59e0b', exotic: '#a78bfa', unknown: '#9ca3af' }

export default function AdherenceDashboard() {
  const [tab, setTab] = useState<Tab>('overview')
  const [filterSpecies, setFilterSpecies] = useState('')
  const [filterCondition, setFilterCondition] = useState('')

  const dashboard = useQuery({ queryKey: ['adherence-dashboard'], queryFn: () => client.get('/adherence/dashboard').then(r => r.data) })
  const overdue = useQuery({
    queryKey: ['adherence-overdue', filterSpecies, filterCondition],
    queryFn: () => {
      const params = new URLSearchParams()
      if (filterSpecies) params.set('species', filterSpecies)
      if (filterCondition) params.set('chronic_condition', filterCondition)
      return client.get(`/adherence/overdue-refills?${params}`).then(r => r.data)
    },
    enabled: tab === 'outreach',
  })
  const calc = useMutation({ mutationFn: () => client.post('/adherence/calculate').then(r => r.data) })

  const d = dashboard.data
  const speciesData = d ? Object.entries(d.species_breakdown || {}).map(([name, value]) => ({ name, value })) : []

  const tabStyle = (t: Tab) => ({
    padding: '8px 20px', cursor: 'pointer', background: 'none', border: 'none',
    borderBottom: tab === t ? '2px solid #14b8a6' : '2px solid transparent',
    color: tab === t ? '#14b8a6' : '#6b7280', fontWeight: tab === t ? 600 : 400,
  } as React.CSSProperties)

  function handleExportCSV() {
    const params = new URLSearchParams({ format: 'csv' })
    if (filterSpecies) params.set('species', filterSpecies)
    if (filterCondition) params.set('chronic_condition', filterCondition)
    window.open(`/api/adherence/outreach-list?${params}`, '_blank')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: '#0f1f35' }}>Refill Adherence</h1>
          <p className="text-sm text-gray-500">Overdue refill tracking and patient outreach</p>
        </div>
        <button onClick={() => calc.mutate()} className="px-4 py-2 text-sm font-medium text-white rounded-lg" style={{ backgroundColor: '#0f1f35' }}>
          {calc.isPending ? 'Calculating…' : 'Run Analysis'}
        </button>
      </div>

      {d && (
        <div className="grid grid-cols-4 gap-4">
          <KPICard label="Overdue Refills" value={d.overdue_count} status="red" />
          <KPICard label="Missed Monthly Revenue" value={`$${d.missed_monthly_revenue?.toLocaleString()}`} status="red" />
          <KPICard label="Chronic Patients Monitored" value={d.chronic_patients_monitored} />
          <KPICard label="Avg Days Overdue" value={`${d.average_days_overdue}d`} status={d.average_days_overdue > 10 ? 'red' : 'amber'} />
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="flex border-b border-gray-200 px-6">
          {(['overview', 'outreach'] as Tab[]).map(t => (
            <button key={t} style={tabStyle(t)} onClick={() => setTab(t)}>
              {t === 'overview' ? 'Overview' : 'Outreach List'}
            </button>
          ))}
        </div>

        <div className="p-6">
          {tab === 'overview' && (
            <div>
              <h3 className="font-semibold text-gray-700 mb-4">Overdue Patients by Species</h3>
              {speciesData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={speciesData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, value }) => `${name}: ${value}`}>
                      {speciesData.map((e, i) => <Cell key={i} fill={SPECIES_COLORS[e.name] || '#9ca3af'} />)}
                    </Pie>
                    <Legend />
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : <p className="text-center text-gray-400 py-8">Run analysis to load adherence data</p>}
            </div>
          )}

          {tab === 'outreach' && (
            <div>
              <div className="flex items-center gap-4 mb-4">
                <select value={filterSpecies} onChange={e => setFilterSpecies(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm">
                  <option value="">All Species</option>
                  {['dog', 'cat', 'horse', 'exotic'].map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <select value={filterCondition} onChange={e => setFilterCondition(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm">
                  <option value="">All Conditions</option>
                  {['hypothyroidism', 'epilepsy', 'diabetes', 'osteoarthritis', 'cardiac'].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <button onClick={handleExportCSV} className="ml-auto px-4 py-1.5 text-sm font-medium text-white rounded-lg" style={{ backgroundColor: '#14b8a6' }}>
                  Export CSV
                </button>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    {['Patient', 'Species', 'Drug', 'Condition', 'Days Overdue', 'Missed Revenue', 'Client ID', 'Priority'].map(h => (
                      <th key={h} className="text-left py-2 px-2 text-xs font-semibold text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {overdue.data?.items?.map((r: any, i: number) => (
                    <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-2 px-2 font-medium">{r.patient_name}</td>
                      <td className="py-2 px-2 capitalize text-gray-500">{r.species}</td>
                      <td className="py-2 px-2">{r.drug_name}</td>
                      <td className="py-2 px-2">{r.chronic_condition ? <StatusBadge label={r.chronic_condition} variant="blue" /> : <span className="text-gray-400">—</span>}</td>
                      <td className="py-2 px-2 font-bold text-red-600">{r.days_overdue}d</td>
                      <td className="py-2 px-2">${r.missed_revenue?.toLocaleString()}</td>
                      <td className="py-2 px-2 text-gray-500 text-xs">{r.client_id}</td>
                      <td className="py-2 px-2"><StatusBadge label={r.priority} variant={r.priority === 'HIGH' ? 'high' : 'gray'} /></td>
                    </tr>
                  ))}
                  {!overdue.data?.items?.length && <tr><td colSpan={8} className="py-8 text-center text-gray-400">Run analysis to load outreach data</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
