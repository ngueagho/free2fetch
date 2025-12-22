'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Shield,
  Users,
  BookOpen,
  Download,
  Settings,
  BarChart3,
  CreditCard,
  Bell,
  Activity,
  Database,
  LogOut,
  Home,
  FileText,
  AlertCircle
} from 'lucide-react'

const navigation = [
  {
    name: 'Dashboard',
    href: '/admin',
    icon: Home,
  },
  {
    name: 'Users',
    href: '/admin/users',
    icon: Users,
  },
  {
    name: 'Courses',
    href: '/admin/courses',
    icon: BookOpen,
  },
  {
    name: 'Downloads',
    href: '/admin/downloads',
    icon: Download,
  },
  {
    name: 'Subscriptions',
    href: '/admin/subscriptions',
    icon: CreditCard,
  },
  {
    name: 'Analytics',
    href: '/admin/analytics',
    icon: BarChart3,
  },
  {
    name: 'System Logs',
    href: '/admin/logs',
    icon: FileText,
  },
  {
    name: 'Monitoring',
    href: '/admin/monitoring',
    icon: Activity,
  },
]

const settingsNavigation = [
  {
    name: 'System Settings',
    href: '/admin/settings',
    icon: Settings,
  },
  {
    name: 'Notifications',
    href: '/admin/notifications',
    icon: Bell,
  },
  {
    name: 'Database',
    href: '/admin/database',
    icon: Database,
  },
]

export function AdminSidebar() {
  const pathname = usePathname()

  return (
    <div className="flex flex-col w-64 bg-gray-900 text-white">
      {/* Logo */}
      <div className="flex items-center h-16 px-4 border-b border-gray-800">
        <Link href="/admin" className="flex items-center space-x-2">
          <div className="h-8 w-8 bg-gradient-to-br from-red-600 to-red-700 rounded-lg flex items-center justify-center">
            <Shield className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-lg font-bold text-white">
              Free2Fetch
            </span>
            <div className="text-xs text-red-300">Admin Panel</div>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-4 space-y-2 overflow-y-auto">
        <div className="space-y-1">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 py-2">
            Main
          </h3>
          {navigation.map((item) => {
            const isActive = pathname === item.href ||
              (item.href !== '/admin' && pathname.startsWith(item.href))
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  isActive
                    ? 'bg-red-700 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                )}
              >
                <item.icon
                  className={cn(
                    'mr-3 h-5 w-5',
                    isActive ? 'text-white' : 'text-gray-400 group-hover:text-white'
                  )}
                />
                {item.name}
              </Link>
            )
          })}
        </div>

        <div className="pt-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 py-2">
            Settings
          </h3>
          {settingsNavigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href)
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  isActive
                    ? 'bg-red-700 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                )}
              >
                <item.icon
                  className={cn(
                    'mr-3 h-5 w-5',
                    isActive ? 'text-white' : 'text-gray-400 group-hover:text-white'
                  )}
                />
                {item.name}
              </Link>
            )
          })}
        </div>

        {/* System Status */}
        <div className="pt-4 border-t border-gray-700">
          <div className="px-3 py-2">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              System Status
            </h3>
            <div className="mt-2 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Database</span>
                <div className="flex items-center">
                  <div className="h-2 w-2 bg-green-400 rounded-full mr-1"></div>
                  <span className="text-green-400">Online</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Redis</span>
                <div className="flex items-center">
                  <div className="h-2 w-2 bg-green-400 rounded-full mr-1"></div>
                  <span className="text-green-400">Online</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Celery</span>
                <div className="flex items-center">
                  <div className="h-2 w-2 bg-yellow-400 rounded-full mr-1"></div>
                  <span className="text-yellow-400">Warning</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* User section */}
      <div className="border-t border-gray-700 p-4">
        <Button
          variant="ghost"
          className="w-full justify-start text-gray-300 hover:text-white hover:bg-gray-700"
          size="sm"
        >
          <LogOut className="mr-3 h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </div>
  )
}