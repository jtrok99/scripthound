import clsx from 'clsx'

interface StatusBadgeProps {
  label: string
  variant?: 'critical' | 'high' | 'moderate' | 'green' | 'amber' | 'red' | 'blue' | 'gray'
}

const variants = {
  critical: 'bg-red-100 text-red-700 border border-red-200',
  high: 'bg-amber-100 text-amber-700 border border-amber-200',
  moderate: 'bg-yellow-100 text-yellow-700 border border-yellow-200',
  green: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
  amber: 'bg-amber-100 text-amber-700 border border-amber-200',
  red: 'bg-red-100 text-red-700 border border-red-200',
  blue: 'bg-blue-100 text-blue-700 border border-blue-200',
  gray: 'bg-gray-100 text-gray-600 border border-gray-200',
}

export default function StatusBadge({ label, variant = 'gray' }: StatusBadgeProps) {
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', variants[variant])}>
      {label}
    </span>
  )
}
