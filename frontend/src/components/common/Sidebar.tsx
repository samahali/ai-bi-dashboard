import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Database,
  FileText,
  LogOut,
  BrainCircuit,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth.store'
import { cn } from '@/utils/helpers'

// Query and Insights are per-dataset routes (/query/:datasetId,
// /insights/:datasetId) reached from a dataset's detail page — there's no
// bare top-level route for them, so they're intentionally not listed here.
const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/datasets',  label: 'Datasets',  icon: Database },
  { to: '/reports',   label: 'Reports',   icon: FileText },
]

interface SidebarProps {
  className?: string
}

export default function Sidebar({ className }: SidebarProps) {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  return (
    <aside className={cn('w-64 h-full flex flex-col bg-white border-r border-border shrink-0', className)}>
      {/* Logo */}
      <div className="px-6 py-5 border-b border-border flex items-center gap-2">
        <BrainCircuit size={22} className="text-accent shrink-0" />
        <div>
          <p className="text-sm font-semibold text-[#1f2328] leading-tight">AI BI Dashboard</p>
          <p className="text-xs text-muted">AI-powered insights</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-accent/10 text-accent font-medium'
                  : 'text-muted hover:bg-surface hover:text-[#1f2328]'
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="px-4 py-4 border-t border-border">
        <p className="text-sm font-medium text-[#1f2328] truncate">{user?.username}</p>
        <p className="text-xs text-muted truncate mb-3">{user?.email}</p>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-xs text-muted hover:text-red-500 transition-colors"
        >
          <LogOut size={13} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
