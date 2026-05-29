import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import client from '../../client'
import KPICard from '../../components/common/KPICard'
import StatusBadge from '../../components/common/StatusBadge'

type Tab = 'cogs' | 'expiration' | 'reorder'

export default function InventoryDashboard() {
  const [tab, setTab] = useState<Tab>('cogs')

  const dashboard = useQuery({ queryKey: ['inv-dashboard'], queryFn: () => client.get('/inventory/dashboard').then(r => r.data) })
  const cogsByDrug = useQuery({ queryKey: ['inv-cogs-drug'], queryFn: () => client.get('/inventory/cogs-by-drug').then(r => r.data) })
  const markup = useQuery({ queryKey: ['inv-markup'], queryFn: () => client.get('/inventory/markup-opportunities').then(r => r.data) })
  const expiration = useQuery({ queryKey: ['inv-expiration'], queryFn: () => client.get('/inventory/expiration-alerts').then(r => r.data), enabled: tab === 'expiration' })
  const reorder = useQuery({ queryKey: ['inv-reorder'], queryFn: () => client.get('/inventory/reorder-list').then(r => r.data), enabled: tab === 'reorder' })
  const calc = useMutation({ mutationFn: () => client.post('/inventory/calculate').then(r => r.data) })

  const d = dashboard.data

  const tabStyle = (t: Tab) => ({
    padding: '8px 20px', cursor: 'pointer', background: 'none', border: 'none',
    borderBottom: tab === t ? '2px solid #14b8a6' : '2px solid transparent',
    color: tab === t ? '#14b8a6' : '#6b7280', fontWeight: tab === t ? 600 : 400,
  } as React.CSSProperties)

  const cogsStatus = d?.cogs_status
  const cogsColor = cogsStatus === 'green' ? '#059669' : cogsStatus === 'amber' ? '#d97706' : '#dc2626'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: '#0f1f35' }}>Inventory & COGS</h1>
          <p className="text-sm text-gray-500">Cost of goods, expiration alerts, and reorder management</p>
        </div>
        <button onClick={() => calc.mutate()} className="px-4 py-2 text-sm font-medium text-white rounded-lg" style={{ backgroundColor: '#0f1f35' }}>
          {calc.isPending ? 'Calculating…' : 'Run Analysis'}
        </button>
      </div>

      {d && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col items-center">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">COGS %</p>
            <p className="text-5xl font-bold" style={{ color: cogsColor }}>{d.cogs_pct}%</p>
            <p className="text-xs mt-1" style={{ color: cogsColor }}>{cogsStatus?.toUpperCase()}</p>
            <p className="text-xs text-gray-400">Target: 18–25%</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Expiration Alerts</p>
            <div className="space-y-1">
              <div className="flex justify-between text-sm"><span className="text-red-600 font-medium">Critical (&lt;30d)</span><span className="font-bold">{d.expiration_alert_counts?.critical || 0}</span></div>
              <div className="flex justify-between text-sm"><span className="text-amber-500 font-medium">High (31–60d)</span><span className="font-bold">{d.expiration_alert_counts?.high || 0}</span></div>
              <div className="flex justify-between text-sm"><span className="text-yellow-500 font-medium">Moderate (61–90d)</span><span className="font-bold">{d.expiration_alert_counts?.moderate || 0}</span></div>
            </div>
          </div>
          <KPICard label="Estimated Waste Cost" value={`$${d.estimated_waste_cost?.toLocaleString()}`} status="amber" />
          <KPICard label="Reorder Items" value={d.reorder_items_count} status={d.reorder_items_count > 5 ? 'red' : 'amber'} />
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="flex border-b border-gray-200 px-6">
          {(['cogs', 'expiration', 'reorder'] as Tab[]).map(t => (
            <button key={t} style={tabStyle(t)} onClick={() => setTab(t)}>
              {t === 'cogs' ? 'COGS Overview' : t === 'expiration' ? 'Expiration Alerts' : 'Reorder List'}
            </button>
          ))}
        </div>

        <div className="p-6">
          {tab === 'cogs' && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Top 10 Drugs by COGS %</h3>
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-gray-200">{['Drug Name', 'COGS %', 'Total COGS', 'Total Revenue'].map(h => <th key={h} className="text-left py-2 px-2 text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr></thead>
                  <tbody>
                    {cogsByDrug.data?.top10?.map((r: any) => (
                      <tr key={r.drug_name} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-2 px-2 font-medium">{r.drug_name}</td>
                        <td className="py-2 px-2"><span style={{ color: r.cogs_pct > 30 ? '#dc2626' : r.cogs_pct > 25 ? '#d97706' : '#059669' }} className="font-bold">{r.cogs_pct}%</span></td>
                        <td className="py-2 px-2">${r.total_cogs?.toLocaleString()}</td>
                        <td className="py-2 px-2">${r.total_retail?.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Markup Opportunities (COGS &gt;30%)</h3>
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-gray-200">{['Drug Name', 'COGS %', 'Opportunity'].map(h => <th key={h} className="text-left py-2 px-2 text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr></thead>
                  <tbody>
                    {markup.data?.items?.map((r: any) => (
                      <tr key={r.drug_name} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-2 px-2 font-medium">{r.drug_name}</td>
                        <td className="py-2 px-2 text-red-600 font-bold">{r.cogs_pct}%</td>
                        <td className="py-2 px-2 text-amber-600">Increase retail price</td>
                      </tr>
                    ))}
                    {!markup.data?.items?.length && <tr><td colSpan={3} className="py-4 text-center text-gray-400">No markup opportunities — run analysis to refresh</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tab === 'expiration' && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-gray-200">{['Drug Name', 'Expiration Date', 'Days Left', 'Stock', 'Waste Cost', 'Severity'].map(h => <th key={h} className="text-left py-2 px-2 text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr></thead>
              <tbody>
                {expiration.data?.items?.map((r: any, i: number) => (
                  <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-2 font-medium">{r.drug_name}</td>
                    <td className="py-2 px-2">{r.expiration_date}</td>
                    <td className="py-2 px-2 font-bold" style={{ color: r.days_until_expiration <= 30 ? '#dc2626' : r.days_until_expiration <= 60 ? '#d97706' : '#ca8a04' }}>{r.days_until_expiration}d</td>
                    <td className="py-2 px-2">{r.current_stock}</td>
                    <td className="py-2 px-2 text-red-600">${r.waste_cost?.toLocaleString()}</td>
                    <td className="py-2 px-2"><StatusBadge label={r.severity} variant={r.severity === 'CRITICAL' ? 'critical' : r.severity === 'HIGH' ? 'high' : 'moderate'} /></td>
                  </tr>
                ))}
                {!expiration.data?.items?.length && <tr><td colSpan={6} className="py-8 text-center text-gray-400">Run analysis to load expiration data</td></tr>}
              </tbody>
            </table>
          )}

          {tab === 'reorder' && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-gray-200">{['Drug Name', 'Current Stock', 'Reorder Point', 'Gap', 'Supplier', 'Urgency'].map(h => <th key={h} className="text-left py-2 px-2 text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr></thead>
              <tbody>
                {reorder.data?.items?.map((r: any, i: number) => (
                  <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-2 font-medium">{r.drug_name}</td>
                    <td className="py-2 px-2" style={{ color: r.current_stock === 0 ? '#dc2626' : '#d97706' }}>{r.current_stock}</td>
                    <td className="py-2 px-2">{r.reorder_point}</td>
                    <td className="py-2 px-2 text-red-600 font-bold">{r.gap}</td>
                    <td className="py-2 px-2 text-gray-500">{r.supplier}</td>
                    <td className="py-2 px-2"><StatusBadge label={r.urgency} variant={r.urgency === 'CRITICAL' ? 'critical' : 'high'} /></td>
                  </tr>
                ))}
                {!reorder.data?.items?.length && <tr><td colSpan={6} className="py-8 text-center text-gray-400">Run analysis to load reorder data</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
