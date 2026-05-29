import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import client from '../../client'
import StatusBadge from '../../components/common/StatusBadge'

function GaugeCard({ kpi }: { kpi: any }) {
  const statusColor = kpi.status === 'green' ? '#059669' : kpi.status === 'amber' ? '#d97706' : '#dc2626'
  const variant = kpi.status === 'green' ? 'green' : kpi.status === 'amber' ? 'amber' : 'red'

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-gray-700 text-sm">{kpi.name}</h3>
        <StatusBadge label={kpi.status.toUpperCase()} variant={variant} />
      </div>
      <p className="text-4xl font-bold" style={{ color: statusColor }}>
        {typeof kpi.actual === 'number' ? (kpi.unit === '%' ? `${kpi.actual.toFixed(1)}%` : kpi.unit === 'days' ? `${kpi.actual.toFixed(1)}d` : kpi.actual) : kpi.actual}
      </p>
      <p className="text-xs text-gray-400 mt-1">
        Target: {kpi.target_low === kpi.target_high ? kpi.target_low : `${kpi.target_low}–${kpi.target_high}`}{kpi.unit}
      </p>
      <p className="text-xs text-gray-500 mt-2">{kpi.description}</p>
      <div className="mt-3 pt-3 border-t border-gray-100">
        <p className="text-xs text-gray-400">Monthly opportunity</p>
        <p className="text-lg font-bold text-amber-600">${kpi.dollar_impact?.toLocaleString()}</p>
      </div>
    </div>
  )
}

export default function PracticeScorecard() {
  const [summary, setSummary] = useState<string | null>(null)

  const scorecard = useQuery({ queryKey: ['scorecard'], queryFn: () => client.get('/benchmarking/scorecard').then(r => r.data) })
  const dashboard = useQuery({ queryKey: ['scripts-dashboard-sc'], queryFn: () => client.get('/scripts/dashboard').then(r => r.data) })
  const inventoryDash = useQuery({ queryKey: ['inv-dashboard-sc'], queryFn: () => client.get('/inventory/dashboard').then(r => r.data) })
  const adherenceDash = useQuery({ queryKey: ['adherence-dashboard-sc'], queryFn: () => client.get('/adherence/dashboard').then(r => r.data) })
  const deaDash = useQuery({ queryKey: ['dea-dashboard-sc'], queryFn: () => client.get('/dea/dashboard').then(r => r.data) })

  const aiSummary = useMutation({
    mutationFn: async () => {
      const payload = {
        capture_rate: dashboard.data?.capture_rate ?? 0,
        monthly_leakage: dashboard.data?.monthly_leakage ?? 0,
        cogs_pct: inventoryDash.data?.cogs_pct ?? 0,
        discrepancy_count: deaDash.data?.discrepancies_this_month ?? 0,
        overdue_count: adherenceDash.data?.overdue_count ?? 0,
        missed_revenue: adherenceDash.data?.missed_monthly_revenue ?? 0,
        chronic_adherence_rate: scorecard.data?.kpis?.find((k: any) => k.key === 'chronic_adherence_rate')?.actual ?? 0,
        avg_days_overdue: adherenceDash.data?.average_days_overdue ?? 0,
        practice_name: 'Greensboro Animal Hospital',
      }
      const { data } = await client.post('/ai/monthly-summary', payload)
      return data.summary as string
    },
    onSuccess: (data) => setSummary(data),
  })

  const d = scorecard.data

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: '#0f1f35' }}>Practice Scorecard</h1>
          <p className="text-sm text-gray-500">Performance benchmarking vs. industry standards</p>
        </div>
        {d && (
          <div className="text-right">
            <p className="text-xs text-gray-400">Total Monthly Opportunity</p>
            <p className="text-2xl font-bold text-amber-600">${d.total_monthly_opportunity?.toLocaleString()}</p>
          </div>
        )}
      </div>

      {d ? (
        <div className="grid grid-cols-3 gap-4">
          {d.kpis?.map((kpi: any) => <GaugeCard key={kpi.key} kpi={kpi} />)}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">
          Loading scorecard…
        </div>
      )}

      <div className="flex justify-center">
        <button
          onClick={() => aiSummary.mutate()}
          disabled={aiSummary.isPending}
          className="px-6 py-3 text-sm font-semibold text-white rounded-lg transition-colors disabled:opacity-60"
          style={{ backgroundColor: '#14b8a6' }}
        >
          {aiSummary.isPending ? 'Generating AI Summary…' : 'Generate Monthly AI Summary'}
        </button>
      </div>

      {aiSummary.isPending && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="animate-pulse flex flex-col items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-teal-200"></div>
            <p className="text-gray-400 text-sm">Claude is analyzing your practice data…</p>
          </div>
        </div>
      )}

      {summary && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-teal-500"></div>
            <h3 className="font-semibold text-gray-700">AI Monthly Performance Summary</h3>
            <span className="text-xs text-gray-400 ml-auto">Generated by Claude (PawPrint Intelligence)</span>
          </div>
          <div className="prose prose-sm text-gray-700 max-w-none whitespace-pre-wrap">{summary}</div>
        </div>
      )}

      {aiSummary.isError && (
        <div className="bg-red-50 rounded-xl border border-red-200 p-4 text-red-600 text-sm">
          Failed to generate summary. Ensure your ANTHROPIC_API_KEY is configured in backend/.env.
        </div>
      )}
    </div>
  )
}
