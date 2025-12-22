'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Users,
  BookOpen,
  Download,
  CreditCard,
  TrendingUp,
  TrendingDown,
  Activity
} from 'lucide-react'
import { motion } from 'framer-motion'

interface AdminStatsProps {
  stats: {
    totalUsers: number
    activeUsers: number
    totalCourses: number
    totalDownloads: number
    activeDownloads: number
    totalRevenue: number
    monthlyRevenue: number
    systemLoad: number
    userGrowth: number
    downloadGrowth: number
    revenueGrowth: number
  }
}

export function AdminStatsCards({ stats }: AdminStatsProps) {
  const statsConfig = [
    {
      title: 'Total Users',
      value: stats.totalUsers.toLocaleString(),
      subtitle: `${stats.activeUsers} active`,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      growth: stats.userGrowth,
    },
    {
      title: 'Courses',
      value: stats.totalCourses.toLocaleString(),
      subtitle: 'in library',
      icon: BookOpen,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: 'Downloads',
      value: stats.totalDownloads.toLocaleString(),
      subtitle: `${stats.activeDownloads} active`,
      icon: Download,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      growth: stats.downloadGrowth,
    },
    {
      title: 'Monthly Revenue',
      value: `$${stats.monthlyRevenue.toLocaleString()}`,
      subtitle: `$${stats.totalRevenue.toLocaleString()} total`,
      icon: CreditCard,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      growth: stats.revenueGrowth,
    },
    {
      title: 'System Load',
      value: `${stats.systemLoad}%`,
      subtitle: 'CPU usage',
      icon: Activity,
      color: stats.systemLoad > 80 ? 'text-red-600' : 'text-indigo-600',
      bgColor: stats.systemLoad > 80 ? 'bg-red-50' : 'bg-indigo-50',
    },
  ]

  const getGrowthIcon = (growth: number) => {
    if (growth > 0) {
      return <TrendingUp className="h-4 w-4 text-green-500" />
    } else if (growth < 0) {
      return <TrendingDown className="h-4 w-4 text-red-500" />
    }
    return null
  }

  const getGrowthText = (growth: number) => {
    if (growth > 0) return `+${growth.toFixed(1)}%`
    if (growth < 0) return `${growth.toFixed(1)}%`
    return '0%'
  }

  const getGrowthColor = (growth: number) => {
    if (growth > 0) return 'text-green-600'
    if (growth < 0) return 'text-red-600'
    return 'text-gray-600'
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      {statsConfig.map((stat, index) => (
        <motion.div
          key={stat.title}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: index * 0.1 }}
        >
          <Card className="relative overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">
                {stat.title}
              </CardTitle>
              <div className={`h-8 w-8 rounded-full ${stat.bgColor} flex items-center justify-center`}>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900">
                {stat.value}
              </div>
              <div className="flex items-center justify-between mt-1">
                <p className="text-xs text-gray-500">
                  {stat.subtitle}
                </p>
                {stat.growth !== undefined && (
                  <div className="flex items-center space-x-1">
                    {getGrowthIcon(stat.growth)}
                    <span className={`text-xs font-medium ${getGrowthColor(stat.growth)}`}>
                      {getGrowthText(stat.growth)}
                    </span>
                  </div>
                )}
              </div>
            </CardContent>

            {/* Background decoration */}
            <div className="absolute top-0 right-0 -translate-y-1 translate-x-1">
              <div className={`h-16 w-16 rounded-full ${stat.bgColor} opacity-20`} />
            </div>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}