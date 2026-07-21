import { useLocation } from 'react-router-dom'
import { Menu } from 'lucide-react'

const titles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/datasets':  'Datasets',
  '/reports':   'Reports',
  '/query':     'Query Builder',
  '/insights':  'Insights',
}

interface HeaderProps {
  onMenuClick: () => void
}

export default function Header({ onMenuClick }: HeaderProps) {
  const { pathname } = useLocation()
  const title = Object.entries(titles).find(([path]) => pathname.startsWith(path))?.[1] ?? 'AI BI Dashboard'

  return (
    <header className="h-14 px-4 sm:px-6 flex items-center gap-3 justify-between bg-white border-b border-border shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onMenuClick}
          className="md:hidden p-1.5 -ml-1.5 rounded-lg text-muted hover:bg-surface hover:text-[#1f2328] shrink-0"
          aria-label="Toggle navigation menu"
        >
          <Menu size={20} />
        </button>
        <h1 className="text-base font-semibold text-[#1f2328] truncate">{title}</h1>
      </div>
    </header>
  )
}
