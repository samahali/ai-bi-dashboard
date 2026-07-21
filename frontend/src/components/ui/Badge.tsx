import { cn } from '@/utils/helpers'

type Variant = 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'purple'

const styles: Record<Variant, string> = {
  success: 'bg-green-50  text-green-700',
  warning: 'bg-yellow-50 text-yellow-700',
  error:   'bg-red-50    text-red-700',
  info:    'bg-blue-50   text-blue-700',
  neutral: 'bg-surface   text-muted',
  purple:  'bg-purple-50 text-purple-700',
}

interface BadgeProps {
  variant?: Variant
  children: React.ReactNode
  className?: string
}

export default function Badge({ variant = 'neutral', children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
        styles[variant],
        className
      )}
    >
      {children}
    </span>
  )
}
