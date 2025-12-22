'use client'

import { useState, useEffect } from 'react'
import { AdminLayout } from '@/components/admin/admin-layout'
import { AdminStatsCards } from '@/components/admin/stats-cards'
import { UsersTable } from '@/components/admin/users-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  RefreshCw,
  TrendingUp,
  AlertCircle,
  Activity,
  Users,
  Download,
  Server,
  AlertTriangle
} from 'lucide-react'

// Mock data
const mockStats = {
  totalUsers: 15247,
  activeUsers: 8943,
  totalCourses: 2156,
  totalDownloads: 45632,
  activeDownloads: 23,
  totalRevenue: 125840,
  monthlyRevenue: 18240,
  systemLoad: 67,
  userGrowth: 12.5,
  downloadGrowth: 8.7,
  revenueGrowth: 15.2
}

const mockUsers = [
  {
    id: '1',
    email: 'john.doe@example.com',
    firstName: 'John',
    lastName: 'Doe',
    subscriptionTier: 'premium' as const,
    isActive: true,
    totalDownloads: 156,
    storageUsed: 15.2 * 1024 * 1024 * 1024,
    lastLogin: new Date('2024-01-15'),
    joinDate: new Date('2023-12-01'),
    isStaff: false
  },
  {
    id: '2',
    email: 'jane.smith@example.com',
    firstName: 'Jane',
    lastName: 'Smith',
    subscriptionTier: 'enterprise' as const,
    isActive: true,
    totalDownloads: 324,
    storageUsed: 47.8 * 1024 * 1024 * 1024,
    lastLogin: new Date('2024-01-14'),
    joinDate: new Date('2023-11-15'),
    isStaff: false
  },
  {
    id: '3',
    email: 'mike.wilson@example.com',
    firstName: 'Mike',
    lastName: 'Wilson',
    subscriptionTier: 'free' as const,
    isActive: false,
    totalDownloads: 12,
    storageUsed: 2.1 * 1024 * 1024 * 1024,
    lastLogin: new Date('2024-01-10'),
    joinDate: new Date('2024-01-05'),
    isStaff: false
  },
  {
    id: '4',
    email: 'admin@free2fetch.com',
    firstName: 'Admin',
    lastName: 'User',
    subscriptionTier: 'enterprise' as const,
    isActive: true,
    totalDownloads: 0,
    storageUsed: 0,
    lastLogin: new Date('2024-01-15'),
    joinDate: new Date('2023-10-01'),
    isStaff: true
  }
]

const mockAlerts = [
  {
    id: '1',
    type: 'warning' as const,
    title: 'High CPU Usage',
    message: 'System CPU usage is at 87%',
    timestamp: new Date('2024-01-15T10:30:00')
  },
  {
    id: '2',
    type: 'error' as const,
    title: 'Failed Download',
    message: '5 downloads failed in the last hour',
    timestamp: new Date('2024-01-15T09:45:00')
  },
  {
    id: '3',
    type: 'info' as const,
    title: 'New User Registration',
    message: '25 new users registered today',
    timestamp: new Date('2024-01-15T08:00:00')
  }
]

export default function AdminDashboard() {
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [stats, setStats] = useState(mockStats)
  const [users, setUsers] = useState(mockUsers)
  const [alerts, setAlerts] = useState(mockAlerts)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000))
    setIsRefreshing(false)
  }

  const handleViewUser = (userId: string) => {
    console.log('View user:', userId)
    // TODO: Navigate to user details page
  }

  const handleBanUser = (userId: string) => {
    console.log('Ban user:', userId)
    setUsers(prev => prev.map(user =>
      user.id === userId ? { ...user, isActive: false } : user
    ))
  }

  const handleUnbanUser = (userId: string) => {
    console.log('Unban user:', userId)
    setUsers(prev => prev.map(user =>
      user.id === userId ? { ...user, isActive: true } : user
    ))
  }

  const handleSendEmail = (userId: string) => {
    console.log('Send email to user:', userId)
    // TODO: Open email compose modal
  }

  const handleUpgradeUser = (userId: string, tier: string) => {
    console.log('Upgrade user:', userId, 'to', tier)
    setUsers(prev => prev.map(user =>
      user.id === userId ? { ...user, subscriptionTier: tier as any } : user
    ))
  }

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      default:
        return <Activity className="h-4 w-4 text-blue-500" />
    }
  }

  const getAlertBadge = (type: string) => {
    switch (type) {
      case 'error':
        return <Badge variant="destructive">Error</Badge>
      case 'warning':
        return <Badge variant="warning">Warning</Badge>
      default:
        return <Badge variant="default">Info</Badge>
    }
  }

  return (
    <AdminLayout
      title="Admin Dashboard"
      subtitle="Monitor and manage your Free2Fetch platform"
      actions={
        <Button
          variant="outline"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      }
    >
      <div className="space-y-8">
        {/* Stats Overview */}
        <AdminStatsCards stats={stats} />

        {/* Main Content Grid */}
        <div className="grid gap-8 lg:grid-cols-3">
          {/* System Alerts */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5" />
                  Recent Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {alerts.map((alert) => (
                    <div key={alert.id} className="flex items-start space-x-3 p-3 rounded-lg border">
                      {getAlertIcon(alert.type)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-sm">{alert.title}</p>
                          {getAlertBadge(alert.type)}
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {alert.timestamp.toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  ))}
                  <Button variant="outline" size="sm" className="w-full">
                    View All Alerts
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Server className="h-5 w-5" />
                  Quick Actions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Button variant="outline" className="h-20 flex flex-col items-center gap-2">
                    <Users className="h-5 w-5" />
                    <span className="text-xs">Manage Users</span>
                  </Button>
                  <Button variant="outline" className="h-20 flex flex-col items-center gap-2">
                    <Download className="h-5 w-5" />
                    <span className="text-xs">View Downloads</span>
                  </Button>
                  <Button variant="outline" className="h-20 flex flex-col items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    <span className="text-xs">Analytics</span>
                  </Button>
                  <Button variant="outline" className="h-20 flex flex-col items-center gap-2">
                    <Activity className="h-5 w-5" />
                    <span className="text-xs">System Health</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Recent Users */}
        <UsersTable
          users={users}
          onViewUser={handleViewUser}
          onBanUser={handleBanUser}
          onUnbanUser={handleUnbanUser}
          onSendEmail={handleSendEmail}
          onUpgradeUser={handleUpgradeUser}
        />

        {/* System Status */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Database Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 bg-green-500 rounded-full"></div>
                  <span className="text-sm">Online</span>
                </div>
                <span className="text-sm text-gray-500">99.9% uptime</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Redis Cache</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 bg-green-500 rounded-full"></div>
                  <span className="text-sm">Online</span>
                </div>
                <span className="text-sm text-gray-500">2.1GB used</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Celery Workers</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 bg-yellow-500 rounded-full"></div>
                  <span className="text-sm">Warning</span>
                </div>
                <span className="text-sm text-gray-500">3/5 workers</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Storage</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                  <span className="text-sm">68% used</span>
                </div>
                <span className="text-sm text-gray-500">1.2TB / 1.8TB</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AdminLayout>
  )
}