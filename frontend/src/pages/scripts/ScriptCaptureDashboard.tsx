import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, Legend } from 'recharts'
import client from '../../client'
import KPICard from '../../components/common/KPICard'

type Tab = 'overview' | 'leakage' | 'prescriptions'

const PHARMACY_COLORS: Record<string, string> = { Chewy: '#2dd4bf', CVS: '#60a5fa', PetMeds: '#f59e0b', Other: '#9ca3af' }

export default function ScriptCaptureDashboard() {
  const [tab, setTab] = useState<Tab>('overview')

  const dashboard = useQuery({ queryKey: ['scripts-dashboard'], queryFn: () => client.get('/scripts/dashboard').then(r => r.data) })
  const leakageCat = useQuery({ queryKey: ['scripts-leakage-cat'], queryFn: () => client.get('/scripts/leakage-by-category').then(r => r.data), enabled: tab === 'leakage' })
  const leakagePharm = useQuery({ queryKey: ['scripts-leakage-pharm'], queryFn: () => client.get('/scripts/leakage-by-pharmacy').then(r => r.data), enabled: tab === 'leakage' })
  const prescriptions = useQuery({ queryKey: ['scripts-prescriptions'], queryFn: () => client.get('/scripts/prescriptions').then(r => r.data), enabled: tab === 'prescriptions' })
  const calc = useMutation({ mutationFn: () => client.post('/scripts/calculate').then(r => r.data) })

  const d = dashboard.data

  const tabStyle = (t: Tab) => ({
    padding: '8px 20px', cursor: 'pointer', background: 'none', border: 'none',
    borderBottom: tab === t ? '2px solid #14b8a6' : '2px solid transparent',
    color: tab === t ? '#14b8a6' : '#6b7280', fontWeight: tab === t ? 600 : 400,
  } as React.CSSProperties)

  const catData = leakageCat.data ? Object.entries(leakageCat.data.leakage_by_category).map(([name, value]) => ({ name, value: +(value as number).toFixed(2) })) : []
  const pharmData = leakagePharm.data ? Object.entries(leakagePharm.data.leakage_by_pharmacy).map(([name, value]) => ({ name, value: +(value as number).toFixed(2) })) : []
  const trendData = d?.six_month_trend || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: '#0f1f35' }}>Script Capture</h1>
          <p className="text-sm text-gray-500">Prescription capture rate and revenue leakage analysis</p>
        </div>
        <button onClick={() => calc.mutate()} className="px-4 py-2 text-sm font-medium text-white rounded-lg" style={{ backgroundColor: '#0f1f35' }}>
          {calc.isPending ? 'Calculating…' : 'Run Analysis'}
        </button>
      </div>

      {tab === 'overview' && d && (
        <>
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col items-center">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Capture Rate</p>
              <p className="text-5xl font-bold" style={{ color: d.capture_rate >= 70 ? '#059669' : d.capture_rate >= 55 ? '#d97706' : '#dc2626' }}>
                {d.capture_rate}%
              </p>
              <p className="text-xs text-gray-400 mt-1">Target: 70–80%</p>
            </div>
            <KPICard label="Monthly Leakage" value={`$${d.monthly_leakage?.toLocaleString()}`} status="red" subtitle="Revenue to external pharmacies" />
            <KPICard label="Prescriptions Written" value={d.prescriptions_written} />
            <KPICard label="Captured In-House" value={d.prescriptions_captured} status="green" />
          </div>

          {trendData.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
              <h3 className="font-semibold text-gray-700 mb-4">6-Month Capture Rate Trend</h3>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} unit="%" />
                  <Tooltip formatter={(v: number) => `${v}%`} />
                  <Line type="monotone" dataKey="capture_rate" stroke="#14b8a6" strokeWidth={2} dot />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="flex border-b border-gray-200 px-6">
          {(['overview', 'leakage', 'prescriptions'] as Tab[]).map(t => (
            <button key={t} style={tabStyle(t)} onClick={() => setTab(t)}>
              {t === 'overview' ? 'Overview' : t === 'leakage' ? 'Leakage Analysis' : 'Prescriptions'}
            </button>
          ))}
        </div>
        <div className="p-6">
          {tab === 'leakage' && (
            <div className="grid grid-cols-2 gap-8">
              <div>
                <h3 className="font-semibold text-gray-700 mb-4">Leakage by Drug Category</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={catData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={v => `$${v}`} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={100} />
                    <Tooltip formatter={(v: number) => `$${v.toLocaleString()}`} />
                    <Bar dataKey="value" fill="#ef4444" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div>
                <h3 className="font-semibold text-gray-700 mb-4">Leakage by Pharmacy</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={pharmData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                      {pharmData.map((entry, i) => <Cell key={i} fill={PHARMACY_COLORS[entry.name] || '#9ca3af'} />)}
                    </Pie>
                    <Tooltip formatter={(v: number) => `$${v.toLocaleString()}`} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {tab === 'prescriptions' && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  {['Rx ID', 'Patient', 'Drug', 'Date Written', 'In-House', 'Pharmacy', 'Est. Revenue'].map(h => (
                    <th key={h} className="text-left py-3 px-2 text-xs font-semibold text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {prescriptions.data?.items?.map((r: any) => (
                  <tr key={r.prescription_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-2 text-gray-500">{r.prescription_id}</td>
                    <td className="py-2 px-2 font-medium">{r.patient_name || '—'}</td>
                    <td className="py-2 px-2">{r.drug_name}</td>
                    <td className="py-2 px-2 text-gray-500">{r.date_written}</td>
                    <td className="py-2 px-2">
                      {r.filled_in_house === true ? <span className="text-emerald-600 font-medium">Yes</span> : r.filled_in_house === false ? <span className="text-red-500">No</span> : <span className="text-gray-400">Unknown</span>}
                    </td>
                    <td className="py-2 px-2 text-gray-500">{r.filled_pharmacy || '—'}</td>
                    <td className="py-2 px-2">{r.retail_price_estimate ? `$${r.retail_price_estimate}` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {tab === 'overview' && <div className="text-center text-gray-400 py-4 text-sm">Overview shown above — switch tabs for detailed analysis</div>}
        </div>
      </div>
    </div>
  )
}
