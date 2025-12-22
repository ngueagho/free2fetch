'use client'

import { useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import {
  Download,
  Play,
  Share2,
  MoreVertical,
  Clock,
  Users,
  Star
} from 'lucide-react'
import { motion } from 'framer-motion'
import { Course, DownloadStatus } from '@/types'

interface CourseGridProps {
  courses: Course[]
  onDownload: (courseId: string) => void
  onPlay: (courseId: string) => void
  onShare: (courseId: string) => void
}

export function CourseGrid({ courses, onDownload, onPlay, onShare }: CourseGridProps) {
  const [loadingStates, setLoadingStates] = useState<{ [key: string]: boolean }>({})

  const handleDownload = async (courseId: string) => {
    setLoadingStates(prev => ({ ...prev, [courseId]: true }))
    await onDownload(courseId)
    setLoadingStates(prev => ({ ...prev, [courseId]: false }))
  }

  const getStatusBadge = (status: DownloadStatus) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success">Downloaded</Badge>
      case 'downloading':
        return <Badge variant="warning">Downloading</Badge>
      case 'pending':
        return <Badge variant="secondary">Pending</Badge>
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>
      default:
        return <Badge variant="outline">Available</Badge>
    }
  }

  const getDownloadProgress = (course: Course) => {
    if (course.downloadStatus === 'downloading' && course.downloadProgress) {
      return course.downloadProgress
    }
    return course.downloadStatus === 'completed' ? 100 : 0
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {courses.map((course, index) => (
        <motion.div
          key={course.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: index * 0.1 }}
        >
          <Card className="overflow-hidden hover:shadow-lg transition-shadow">
            <div className="relative">
              <Image
                src={course.thumbnail}
                alt={course.title}
                width={400}
                height={225}
                className="w-full h-48 object-cover"
              />
              <div className="absolute top-2 right-2">
                {getStatusBadge(course.downloadStatus)}
              </div>
              <div className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
                {course.duration}
              </div>
            </div>

            <CardContent className="p-4">
              <h3 className="font-semibold text-lg mb-2 line-clamp-2">
                {course.title}
              </h3>

              <p className="text-sm text-gray-600 mb-2 line-clamp-1">
                By {course.instructor}
              </p>

              <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {course.totalLectures} lectures
                </span>
                <span className="flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {course.enrolledStudents?.toLocaleString()}
                </span>
                <span className="flex items-center gap-1">
                  <Star className="h-3 w-3" />
                  {course.rating}
                </span>
              </div>

              {(course.downloadStatus === 'downloading' || course.downloadStatus === 'completed') && (
                <div className="mb-3">
                  <div className="flex justify-between text-xs text-gray-600 mb-1">
                    <span>Download Progress</span>
                    <span>{getDownloadProgress(course)}%</span>
                  </div>
                  <Progress
                    value={getDownloadProgress(course)}
                    className="h-2"
                    variant={course.downloadStatus === 'completed' ? 'success' : 'default'}
                  />
                </div>
              )}

              <div className="flex gap-2">
                {course.downloadStatus === 'completed' ? (
                  <Button
                    size="sm"
                    variant="default"
                    className="flex-1"
                    onClick={() => onPlay(course.id)}
                  >
                    <Play className="h-4 w-4 mr-1" />
                    Play
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1"
                    onClick={() => handleDownload(course.id)}
                    disabled={loadingStates[course.id] || course.downloadStatus === 'downloading'}
                  >
                    <Download className="h-4 w-4 mr-1" />
                    {loadingStates[course.id]
                      ? 'Starting...'
                      : course.downloadStatus === 'downloading'
                      ? 'Downloading'
                      : 'Download'
                    }
                  </Button>
                )}

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onShare(course.id)}
                >
                  <Share2 className="h-4 w-4" />
                </Button>

                <Button
                  size="sm"
                  variant="ghost"
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </div>

              {course.lastAccessed && (
                <p className="text-xs text-gray-400 mt-2">
                  Last accessed: {new Date(course.lastAccessed).toLocaleDateString()}
                </p>
              )}
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}