'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Download,
  BookOpen,
  Clock,
  HardDrive,
  TrendingUp,
  Users
} from 'lucide-react'
import { motion } from 'framer-motion'

interface StatsOverviewProps {
  stats: {
    totalCourses: number
    downloadedCourses: number
    totalDownloadTime: string
    storageUsed: string
    storageLimit: string
    activeDownloads: number
    sharedCourses: number
    streamingHours: number
  }
}

const statsConfig = [
  {
    title: 'Total Courses',
    value: 'totalCourses',
    icon: BookOpen,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
  },
  {
    title: 'Downloaded',
    value: 'downloadedCourses',
    icon: Download,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  {
    title: 'Active Downloads',
    value: 'activeDownloads',
    icon: TrendingUp,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
  },
  {
    title: 'Storage Used',
    value: 'storageUsed',
    icon: HardDrive,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    subtitle: 'storageLimit'
  },
  {
    title: 'Total Time Saved',
    value: 'totalDownloadTime',
    icon: Clock,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
  },
  {
    title: 'Shared Courses',
    value: 'sharedCourses',
    icon: Users,
    color: 'text-pink-600',
    bgColor: 'bg-pink-50',
  },
]

export function StatsOverview({ stats }: StatsOverviewProps) {
  const getStatValue = (key: string) => {
    return stats[key as keyof typeof stats]
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {statsConfig.map((stat, index) => (
        <motion.div
          key={stat.title}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: index * 0.1 }}
        >
          <Card>
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
                {getStatValue(stat.value)}
                {stat.subtitle && (
                  <span className="text-sm font-normal text-gray-500 ml-1">
                    / {getStatValue(stat.subtitle)}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {stat.title === 'Storage Used' && 'of your storage limit'}
                {stat.title === 'Total Time Saved' && 'hours saved from downloading'}
                {stat.title === 'Active Downloads' && 'currently in progress'}
                {stat.title === 'Shared Courses' && 'courses shared with others'}
                {stat.title === 'Total Courses' && 'available in your library'}
                {stat.title === 'Downloaded' && 'ready for offline viewing'}
              </p>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}