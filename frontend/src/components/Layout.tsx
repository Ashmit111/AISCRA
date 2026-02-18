import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { 
  LayoutDashboard, 
  Building2, 
  AlertTriangle, 
  MessageSquare, 
  FileText,
  Bell 
} from 'lucide-react'
import { useAlertStore } from '@/stores/alertStore'
import { useWebSocket } from '@/hooks/useWebSocket'
import { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Suppliers', href: '/suppliers', icon: Building2 },
  { name: 'Alerts', href: '/alerts', icon: AlertTriangle },
  { name: 'AI Agent', href: '/agent', icon: MessageSquare },
  { name: 'Reports', href: '/reports', icon: FileText },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const unreadCount = useAlertStore(state => state.unreadCount)
  
  // Connect to WebSocket for real-time alerts
  useWebSocket()

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center">
          <div className="mr-8 flex items-center space-x-2">
            <Building2 className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">Supply Chain Risk</span>
          </div>

          <nav className="flex items-center space-x-6 text-sm font-medium flex-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center space-x-2 text-muted-foreground transition-colors hover:text-foreground',
                    isActive && 'text-foreground'
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  <span>{item.name}</span>
                  {item.name === 'Alerts' && unreadCount > 0 && (
                    <span className="ml-1 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-xs text-destructive-foreground">
                      {unreadCount}
                    </span>
                  )}
                </Link>
              )
            })}
          </nav>

          <div className="flex items-center space-x-4">
            <button className="relative">
              <Bell className="h-5 w-5 text-muted-foreground hover:text-foreground" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-xs text-destructive-foreground">
                  {unreadCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-6">
        {children}
      </main>
    </div>
  )
}
