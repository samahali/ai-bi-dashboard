import { cn } from '@/utils/helpers'

interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'sm' | 'md' | 'lg'
}

const paddingMap = { sm: 'p-4', md: 'p-6', lg: 'p-8' }

export default function Card({ children, className, padding = 'md' }: CardProps) {
  return (
    <div
      className={cn(
        'bg-white border border-border rounded-xl shadow-[var(--shadow-card)]',
        paddingMap[padding],
        className
      )}
    >
      {children}
    </div>
  )
}
