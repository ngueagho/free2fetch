'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import {
  Download,
  Pause,
  Play,
  X,
  Clock,
  CheckCircle,
  AlertCircle,
  RotateCcw
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { DownloadJob } from '@/types'

interface DownloadQueueProps {
  downloads: DownloadJob[]
  onPause: (downloadId: string) => void
  onResume: (downloadId: string) => void
  onCancel: (downloadId: string) => void
  onRetry: (downloadId: string) => void
}

export function DownloadQueue({
  downloads,
  onPause,
  onResume,
  onCancel,
  onRetry
}: DownloadQueueProps) {
  const [collapsedItems, setCollapsedItems] = useState<{ [key: string]: boolean }>({})

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'downloading':
        return <Download className="h-4 w-4 text-blue-500 animate-bounce" />
      case 'paused':
        return <Pause className="h-4 w-4 text-yellow-500" />
      case 'pending':
        return <Clock className="h-4 w-4 text-gray-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success">Completed</Badge>
      case 'downloading':
        return <Badge variant="default">Downloading</Badge>
      case 'paused':
        return <Badge variant="warning">Paused</Badge>
      case 'pending':
        return <Badge variant="secondary">Pending</Badge>
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>
      default:
        return <Badge variant="outline">Unknown</Badge>
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatTimeRemaining = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  }

  const activeDownloads = downloads.filter(d => ['downloading', 'pending', 'paused'].includes(d.status))
  const completedDownloads = downloads.filter(d => d.status === 'completed')
  const failedDownloads = downloads.filter(d => d.status === 'failed')

  return (
    <div className="space-y-6">
      {/* Active Downloads */}
      {activeDownloads.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              Active Downloads ({activeDownloads.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <AnimatePresence>
              {activeDownloads.map((download) => (
                <motion.div
                  key={download.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="border rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(download.status)}
                        <h4 className="font-medium">{download.courseTitle}</h4>
                        {getStatusBadge(download.status)}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">
                        {download.totalItems} items • {formatFileSize(download.totalSize)}
                      </p>
                    </div>

                    <div className="flex gap-1">
                      {download.status === 'downloading' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onPause(download.id)}
                        >
                          <Pause className="h-4 w-4" />
                        </Button>
                      )}
                      {download.status === 'paused' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onResume(download.id)}
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onCancel(download.id)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {download.status === 'downloading' && (
                    <div>
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>{download.currentItem}</span>
                        <span>{download.progress}%</span>
                      </div>
                      <Progress value={download.progress} className="h-2" />
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>
                          {formatFileSize(download.downloadedSize)} / {formatFileSize(download.totalSize)}
                        </span>
                        {download.estimatedTimeRemaining && (
                          <span>
                            {formatTimeRemaining(download.estimatedTimeRemaining)} remaining
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {download.status === 'pending' && (
                    <div className="text-sm text-gray-600">
                      Waiting to start... Position {download.queuePosition || 0} in queue
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </CardContent>
        </Card>
      )}

      {/* Failed Downloads */}
      {failedDownloads.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <AlertCircle className="h-5 w-5" />
              Failed Downloads ({failedDownloads.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {failedDownloads.map((download) => (
              <div
                key={download.id}
                className="border border-red-200 rounded-lg p-4 bg-red-50"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-red-500" />
                      <h4 className="font-medium text-red-900">{download.courseTitle}</h4>
                    </div>
                    <p className="text-sm text-red-700 mt-1">
                      {download.errorMessage || 'Download failed'}
                    </p>
                  </div>

                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onRetry(download.id)}
                    >
                      <RotateCcw className="h-4 w-4 mr-1" />
                      Retry
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onCancel(download.id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Recent Completed Downloads */}
      {completedDownloads.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              Recently Completed ({completedDownloads.slice(0, 5).length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {completedDownloads.slice(0, 5).map((download) => (
              <div
                key={download.id}
                className="border border-green-200 rounded-lg p-3 bg-green-50"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <div>
                      <h4 className="font-medium text-green-900">{download.courseTitle}</h4>
                      <p className="text-sm text-green-700">
                        Completed {new Date(download.completedAt!).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onCancel(download.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {downloads.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center">
            <Download className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No downloads yet</h3>
            <p className="text-gray-600">
              Start downloading your courses to see them here
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}