'use client'

import { useState, useEffect } from 'react'
import { DashboardLayout } from '@/components/dashboard/layout'
import { StatsOverview } from '@/components/dashboard/stats-overview'
import { SubscriptionStatus } from '@/components/dashboard/subscription-status'
import { CourseGrid } from '@/components/dashboard/course-grid'
import { DownloadQueue } from '@/components/dashboard/download-queue'
import { Button } from '@/components/ui/button'
import { Plus, RefreshCw } from 'lucide-react'
import Link from 'next/link'
import { Course, DownloadJob, UserSubscription } from '@/types'

// Mock data - replace with real API calls
const mockStats = {
  totalCourses: 24,
  downloadedCourses: 18,
  totalDownloadTime: '47.5',
  storageUsed: '15.2 GB',
  storageLimit: '50 GB',
  activeDownloads: 2,
  sharedCourses: 5,
  streamingHours: 127
}

const mockSubscription: UserSubscription = {
  id: '1',
  userId: '1',
  tier: 'free',
  isActive: true,
  willRenew: false,
  currentPeriodStart: new Date('2024-01-01'),
  currentPeriodEnd: new Date('2024-02-01'),
  downloadLimit: 10,
  downloadsUsed: 8,
  storageLimit: 50 * 1024, // 50GB in MB
  storageUsed: 15.2 * 1024, // 15.2GB in MB
  createdAt: new Date('2024-01-01'),
  updatedAt: new Date()
}

const mockCourses: Course[] = [
  {
    id: '1',
    udemyId: 'udemy-1',
    title: 'Complete React Developer Course',
    instructor: 'John Doe',
    description: 'Learn React from scratch',
    thumbnail: '/api/placeholder/400/225',
    duration: '24h 30m',
    rating: 4.8,
    enrolledStudents: 125000,
    totalLectures: 156,
    downloadStatus: 'downloading',
    downloadProgress: 65,
    lastAccessed: new Date('2024-01-15'),
    isPublic: false,
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date()
  },
  {
    id: '2',
    udemyId: 'udemy-2',
    title: 'Advanced Node.js Development',
    instructor: 'Jane Smith',
    description: 'Master Node.js and Express',
    thumbnail: '/api/placeholder/400/225',
    duration: '18h 45m',
    rating: 4.9,
    enrolledStudents: 89000,
    totalLectures: 98,
    downloadStatus: 'completed',
    lastAccessed: new Date('2024-01-14'),
    isPublic: false,
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date()
  },
  {
    id: '3',
    udemyId: 'udemy-3',
    title: 'Python for Data Science',
    instructor: 'Mike Johnson',
    description: 'Learn Python for data analysis',
    thumbnail: '/api/placeholder/400/225',
    duration: '32h 15m',
    rating: 4.7,
    enrolledStudents: 200000,
    totalLectures: 215,
    downloadStatus: 'available',
    lastAccessed: new Date('2024-01-13'),
    isPublic: false,
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date()
  }
]

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
  }
]

export default function DashboardPage() {
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [courses, setCourses] = useState<Course[]>(mockCourses)
  const [downloads, setDownloads] = useState<DownloadJob[]>(mockDownloads)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000))
    setIsRefreshing(false)
  }

  const handleDownload = async (courseId: string) => {
    console.log('Starting download for course:', courseId)
    // TODO: Implement actual download logic
  }

  const handlePlay = (courseId: string) => {
    console.log('Playing course:', courseId)
    // TODO: Navigate to streaming page
  }

  const handleShare = (courseId: string) => {
    console.log('Sharing course:', courseId)
    // TODO: Open share modal
  }

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
      d.id === downloadId ? { ...d, status: 'pending', progress: 0 } : d
    ))
  }

  return (
    <DashboardLayout
      title="Dashboard"
      subtitle="Welcome back! Here's what's happening with your courses."
      actions={
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button asChild>
            <Link href="/dashboard/courses">
              <Plus className="h-4 w-4 mr-2" />
              Add Course
            </Link>
          </Button>
        </div>
      }
    >
      <div className="space-y-8">
        {/* Stats Overview */}
        <StatsOverview stats={mockStats} />

        {/* Two column layout */}
        <div className="grid gap-8 lg:grid-cols-3">
          {/* Main content - Recent courses */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Recent Courses</h2>
              <Link
                href="/dashboard/courses"
                className="text-sm text-purple-600 hover:text-purple-700"
              >
                View all →
              </Link>
            </div>
            <CourseGrid
              courses={courses.slice(0, 4)}
              onDownload={handleDownload}
              onPlay={handlePlay}
              onShare={handleShare}
            />
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Subscription Status */}
            <SubscriptionStatus subscription={mockSubscription} />
          </div>
        </div>

        {/* Download Queue */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Download Queue</h2>
          <DownloadQueue
            downloads={downloads}
            onPause={handlePauseDownload}
            onResume={handleResumeDownload}
            onCancel={handleCancelDownload}
            onRetry={handleRetryDownload}
          />
        </div>
      </div>
    </DashboardLayout>
  )
}