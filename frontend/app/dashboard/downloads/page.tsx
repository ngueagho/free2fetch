'use client'

import { useState } from 'react'
import { DashboardLayout } from '@/components/dashboard/layout'
import { DownloadQueue } from '@/components/dashboard/download-queue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Download,
  Pause,
  Play,
  RotateCcw,
  Trash2,
  Filter,
  Calendar,
  BarChart3,
  HardDrive
} from 'lucide-react'
import { DownloadJob } from '@/types'

// Extended mock data for downloads
const mockDownloads: DownloadJob[] = [
  {
    id: '1',
    courseId: '1',
    courseTitle: 'Complete React Developer Course',
    status: 'downloading',
    progress: 65,
    totalItems: 156,
    currentItem: 'Section 8: Redux Fundamentals - Lecture 45',
    totalSize: 2.1 * 1024 * 1024 * 1024, // 2.1GB
    downloadedSize: 1.36 * 1024 * 1024 * 1024, // 1.36GB
    estimatedTimeRemaining: 1850, // 30 minutes in seconds
    queuePosition: 1,
    createdAt: new Date('2024-01-15T10:00:00'),
    updatedAt: new Date()
  },
  {
    id: '2',
    courseId: '4',
    courseTitle: 'TypeScript Masterclass',
    status: 'pending',
    progress: 0,
    totalItems: 89,
    totalSize: 1.5 * 1024 * 1024 * 1024, // 1.5GB
    downloadedSize: 0,
    queuePosition: 2,
    createdAt: new Date('2024-01-15T11:00:00'),
    updatedAt: new Date()
  },
  {
    id: '3',
    courseId: '2',
    courseTitle: 'Advanced Node.js Development',
    status: 'completed',
    progress: 100,
    totalItems: 98,
    totalSize: 1.8 * 1024 * 1024 * 1024, // 1.8GB
    downloadedSize: 1.8 * 1024 * 1024 * 1024,
    completedAt: new Date('2024-01-14T15:30:00'),
    createdAt: new Date('2024-01-14T12:00:00'),
    updatedAt: new Date()
  },
  {
    id: '4',
    courseId: '6',
    courseTitle: 'Complete Web Design Course',
    status: 'completed',
    progress: 100,
    totalItems: 134,
    totalSize: 2.3 * 1024 * 1024 * 1024, // 2.3GB
    downloadedSize: 2.3 * 1024 * 1024 * 1024,
    completedAt: new Date('2024-01-13T09:15:00'),
    createdAt: new Date('2024-01-13T06:00:00'),
    updatedAt: new Date()
  },
  {
    id: '5',
    courseId: '5',
    courseTitle: 'Docker & Kubernetes Complete Guide',
    status: 'failed',
    progress: 23,
    totalItems: 187,
    errorMessage: 'Network connection lost during download',
    totalSize: 3.2 * 1024 * 1024 * 1024, // 3.2GB
    downloadedSize: 0.7 * 1024 * 1024 * 1024, // 0.7GB
    createdAt: new Date('2024-01-12T14:00:00'),
    updatedAt: new Date()
  },
  {
    id: '6',
    courseId: '3',
    courseTitle: 'Python for Data Science',
    status: 'paused',
    progress: 45,
    totalItems: 215,
    currentItem: 'Section 12: Machine Learning - Lecture 98',
    totalSize: 2.8 * 1024 * 1024 * 1024, // 2.8GB
    downloadedSize: 1.26 * 1024 * 1024 * 1024, // 1.26GB
    createdAt: new Date('2024-01-11T16:00:00'),
    updatedAt: new Date()
  }
]

export default function DownloadsPage() {
  const [downloads, setDownloads] = useState<DownloadJob[]>(mockDownloads)
  const [selectedStatus, setSelectedStatus] = useState<string>('all')

  const handlePauseDownload = (downloadId: string) => {
    setDownloads(prev => prev.map(d =>
      d.id === downloadId ? { ...d, status: 'paused' } : d
    ))
  }

  const handleResumeDownload = (downloadId: string) => {
    setDownloads(prev => prev.map(d =>
      d.id === downloadId ? { ...d, status: 'downloading' } : d
    ))
  }

  const handleCancelDownload = (downloadId: string) => {
    setDownloads(prev => prev.filter(d => d.id !== downloadId))
  }

  const handleRetryDownload = (downloadId: string) => {
    setDownloads(prev => prev.map(d =>
      d.id === downloadId ? { ...d, status: 'pending', progress: 0, errorMessage: undefined } : d
    ))
  }

  const handlePauseAll = () => {
    setDownloads(prev => prev.map(d =>
      d.status === 'downloading' ? { ...d, status: 'paused' } : d
    ))
  }

  const handleResumeAll = () => {
    setDownloads(prev => prev.map(d =>
      d.status === 'paused' ? { ...d, status: 'downloading' } : d
    ))
  }

  const handleClearCompleted = () => {
    setDownloads(prev => prev.filter(d => d.status !== 'completed'))
  }

  const getStats = () => {
    const activeDownloads = downloads.filter(d => ['downloading', 'pending', 'paused'].includes(d.status))
    const completedDownloads = downloads.filter(d => d.status === 'completed')
    const failedDownloads = downloads.filter(d => d.status === 'failed')

    const totalSize = downloads.reduce((sum, d) => sum + d.totalSize, 0)
    const downloadedSize = downloads.reduce((sum, d) => sum + d.downloadedSize, 0)

    const overallProgress = totalSize > 0 ? (downloadedSize / totalSize) * 100 : 0

    return {
      active: activeDownloads.length,
      completed: completedDownloads.length,
      failed: failedDownloads.length,
      totalSize,
      downloadedSize,
      overallProgress: Math.round(overallProgress)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const filteredDownloads = selectedStatus === 'all'
    ? downloads
    : downloads.filter(d => d.status === selectedStatus)

  const stats = getStats()

  const statusCounts = {
    all: downloads.length,
    downloading: downloads.filter(d => d.status === 'downloading').length,
    pending: downloads.filter(d => d.status === 'pending').length,
    paused: downloads.filter(d => d.status === 'paused').length,
    completed: downloads.filter(d => d.status === 'completed').length,
    failed: downloads.filter(d => d.status === 'failed').length,
  }

  return (
    <DashboardLayout
      title="Downloads"
      subtitle="Manage your course downloads and view progress"
      actions={
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handlePauseAll}
            disabled={downloads.filter(d => d.status === 'downloading').length === 0}
          >
            <Pause className="h-4 w-4 mr-2" />
            Pause All
          </Button>
          <Button
            variant="outline"
            onClick={handleResumeAll}
            disabled={downloads.filter(d => d.status === 'paused').length === 0}
          >
            <Play className="h-4 w-4 mr-2" />
            Resume All
          </Button>
          <Button
            variant="outline"
            onClick={handleClearCompleted}
            disabled={stats.completed === 0}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Clear Completed
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Download Statistics */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Downloads</CardTitle>
              <Download className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.active}</div>
              <p className="text-xs text-muted-foreground">
                Currently downloading or queued
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <BarChart3 className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.completed}</div>
              <p className="text-xs text-muted-foreground">
                Successfully downloaded
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Storage Used</CardTitle>
              <HardDrive className="h-4 w-4 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatFileSize(stats.downloadedSize)}</div>
              <p className="text-xs text-muted-foreground">
                Total downloaded content
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Overall Progress</CardTitle>
              <Calendar className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.overallProgress}%</div>
              <Progress value={stats.overallProgress} className="mt-2" />
            </CardContent>
          </Card>
        </div>

        {/* Status Filter */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-2">
              {Object.entries(statusCounts).map(([status, count]) => (
                <Button
                  key={status}
                  variant={selectedStatus === status ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedStatus(status)}
                  className="flex items-center gap-1"
                >
                  {status === 'downloading' && <Download className="h-3 w-3" />}
                  {status === 'paused' && <Pause className="h-3 w-3" />}
                  {status === 'failed' && <RotateCcw className="h-3 w-3" />}
                  <span className="capitalize">{status}</span>
                  <Badge variant="secondary" className="ml-1 text-xs">
                    {count}
                  </Badge>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Download Queue */}
        <DownloadQueue
          downloads={filteredDownloads}
          onPause={handlePauseDownload}
          onResume={handleResumeDownload}
          onCancel={handleCancelDownload}
          onRetry={handleRetryDownload}
        />

        {/* Download History Summary */}
        {stats.completed > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Download Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
                  <p className="text-sm text-gray-600">Courses Downloaded</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {formatFileSize(stats.downloadedSize)}
                  </div>
                  <p className="text-sm text-gray-600">Total Data Downloaded</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {downloads.filter(d => d.completedAt).reduce((total, d) => {
                      if (d.completedAt && d.createdAt) {
                        return total + (d.completedAt.getTime() - d.createdAt.getTime())
                      }
                      return total
                    }, 0) / (1000 * 60 * 60)}h
                  </div>
                  <p className="text-sm text-gray-600">Time Saved</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}