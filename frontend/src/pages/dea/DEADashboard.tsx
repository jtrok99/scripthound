import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import client from '../../client'
import KPICard from '../../components/common/KPICard'
import StatusBadge from '../../components/common/StatusBadge'

type Tab = 'overview' | 'discrepancies' | 'diversion'

export default function DEADashboard() {
  const [tab, setTab] = useState<Tab>('overview')

  const dashboard = useQuery({ queryKey: ['dea-dashboard'], queryFn: () => client.get('/dea/dashboard').then(r => r.data) })
  const discrepancies = useQuery({ queryKey: ['dea-discrepancies'], queryFn: () => client.get('/dea/discrepancies').then(r => r.data), enabled: tab === 'discrepancies' })
  const diversion = useQuery({ queryKey: ['dea-diversion'], queryFn: () => client.get('/dea/diversion-flags').then(r => r.data), enabled: tab === 'diversion' })

  const calc = useMutation({ mutationFn: () => client.post('/dea/calculate').then(r => r.data) })

  const d = dashboard.data

  const tabStyle = (t: Tab) => ({
    padding: '8px 20px',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    borderBottom: tab === t ? '2px solid #14b8a6' : '2px solid transparent',
    color: tab === t ? '#14b8a6' : '#6b7280',
    fontWeight: tab === t ? 600 : 400,
  } as React.CSSProperties)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: '#0f1f35' }}>DEA Compliance</h1>
          <p className="text-sm text-gray-500">Controlled substance reconciliation and diversion monitoring</p>
        </div>
        <button
          onClick={() => calc.mutate()}
          className="px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors"
          style={{ backgroundColor: '#0f1f35' }}
        >
          {calc.isPending ? 'Calculating…' : 'Run Analysis'}
        </button>
      </div>

      {tab === 'overview' && d && (
        <div className="grid grid-cols-4 gap-4">
          <KPICard label="Drugs Tracked" value={d.total_drugs_tracked} />
          <KPICard label="Discrepancies This Month" value={d.discrepancies_this_month} status={d.discrepancies_this_month > 0 ? 'red' : 'green'} />
          <KPICard label="Diversion Risk Flags" value={d.diversion_risk_flags} status={d.diversion_risk_flags > 0 ? 'red' : 'green'} />
          <KPICard label="Days Since Last Discrepancy" value={d.days_since_last_discrepancy ?? 'None'} />
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="flex border-b border-gray-200 px-6">
          {(['overview', 'discrepancies', 'diversion'] as Tab[]).map(t => (
            <button key={t} style={tabStyle(t)} onClick={() => setTab(t)}>
              {t === 'overview' ? 'Overview' : t === 'discrepancies' ? 'Discrepancies' : 'Diversion Flags'}
            </button>
          ))}
        </div>

        <div className="p-6">
          {tab === 'overview' && (
            <div className="text-center text-gray-400 py-8">
              <p>DEA Compliance Summary</p>
              {d && <p className="text-sm mt-2">Run Analysis to refresh controlled substance reconciliation data.</p>}
            </div>
          )}

          {tab === 'discrepancies' && (
            <div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    {['Drug Name', 'Schedule', 'Expected', 'Actual', 'Discrepancy', 'Date', 'Severity'].map(h => (
                      <th key={h} className="text-left py-3 px-2 text-xs font-semibold text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {discrepancies.data?.items?.map((r: any) => (
                    <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-2 font-medium">{r.drug_name}</td>
                      <td className="py-3 px-2">
                        <StatusBadge label={r.drug_schedule || 'N/A'} variant={r.drug_schedule === 'Schedule II' ? 'red' : 'amber'} />
                      </td>
                      <td className="py-3 px-2">{r.expected_count}</td>
                      <td className="py-3 px-2">{r.ending_count}</td>
                      <td className="py-3 px-2 text-red-600 font-semibold">{r.discrepancy > 0 ? '+' : ''}{r.discrepancy}</td>
                      <td className="py-3 px-2 text-gray-500">{r.transaction_date}</td>
                      <td className="py-3 px-2">
                        <StatusBadge label={r.severity} variant={r.severity === 'CRITICAL' ? 'critical' : 'high'} />
                      </td>
                    </tr>
                  ))}
                  {!discrepancies.data?.items?.length && (
                    <tr><td colSpan={7} className="py-8 text-center text-gray-400">No discrepancies found — run analysis to refresh</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {tab === 'diversion' && (
            <div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    {['Event Type', 'Drug Name', 'Dispensed By', 'Date', 'Time', 'Severity Score'].map(h => (
                      <th key={h} className="text-left py-3 px-2 text-xs font-semibold text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {diversion.data?.items?.map((r: any, i: number) => (
                    <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-2">
                        <StatusBadge
                          label={r.event_type.replace('_', ' ')}
                          variant={r.event_type === 'volume_anomaly' ? 'critical' : r.event_type === 'after_hours' ? 'high' : 'amber'}
                        />
                      </td>
                      <td className="py-3 px-2 font-medium">{r.drug_name}</td>
                      <td className="py-3 px-2">{r.dispensed_by}</td>
                      <td className="py-3 px-2 text-gray-500">{r.date}</td>
                      <td className="py-3 px-2 text-gray-500">{r.time || '—'}</td>
                      <td className="py-3 px-2">
                        <span className="font-bold text-red-600">{r.severity_score}/10</span>
                      </td>
                    </tr>
                  ))}
                  {!diversion.data?.items?.length && (
                    <tr><td colSpan={6} className="py-8 text-center text-gray-400">No diversion flags — run analysis to refresh</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
