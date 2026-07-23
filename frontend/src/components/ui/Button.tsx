import { Loader2 } from 'lucide-react'

import { cn } from '@/utils/helpers'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg' | 'icon'
  loading?: boolean
  children: React.ReactNode
}

const variantStyles = {
  primary:   'bg-accent text-white hover:bg-blue-600',
  secondary: 'border border-border bg-white text-[#1f2328] hover:bg-surface',
  ghost:     'bg-transparent text-muted hover:bg-surface hover:text-[#1f2328]',
  danger:    'bg-red-50 text-red-600 hover:bg-red-100',
}

const sizeStyles = {
  sm:   'px-3 py-1.5 text-xs gap-1.5',
  md:   'px-4 py-2 text-sm gap-2',
  lg:   'px-5 py-2.5 text-base gap-2',
  icon: 'p-2',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center rounded-lg font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {loading && <Loader2 size={14} className="animate-spin" />}
      {children}
    </button>
  )
}
