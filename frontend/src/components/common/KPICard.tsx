interface KPICardProps {
  label: string
  value: string | number
  subtitle?: string
  status?: 'green' | 'amber' | 'red' | 'neutral'
}

const statusStyles = {
  green: 'text-emerald-600',
  amber: 'text-amber-500',
  red: 'text-red-600',
  neutral: 'text-navy-600',
}

export default function KPICard({ label, value, subtitle, status = 'neutral' }: KPICardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${statusStyles[status]}`} style={status === 'neutral' ? { color: '#1e3a5f' } : {}}>
        {value}
      </p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  )
}
