'use client'

import { useState, useEffect } from 'react'
import { DashboardLayout } from '@/components/dashboard/layout'
import { CourseGrid } from '@/components/dashboard/course-grid'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Filter,
  Search,
  SortAsc,
  SortDesc,
  RefreshCw,
  BookOpen,
  Download,
  Grid,
  List
} from 'lucide-react'
import { Course } from '@/types'

// Extended mock data with more courses
const mockCourses: Course[] = [
  {
    id: '1',
    udemyId: 'udemy-1',
    title: 'Complete React Developer Course',
    instructor: 'John Doe',
    description: 'Learn React from scratch with hooks, context, and more',
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
    description: 'Master Node.js, Express, MongoDB, and REST APIs',
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
    description: 'Learn Python, Pandas, NumPy, Matplotlib for data analysis',
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
  },
  {
    id: '4',
    udemyId: 'udemy-4',
    title: 'TypeScript Masterclass',
    instructor: 'Sarah Wilson',
    description: 'Complete guide to TypeScript from basics to advanced',
    thumbnail: '/api/placeholder/400/225',
    duration: '16h 20m',
    rating: 4.6,
    enrolledStudents: 67000,
    totalLectures: 89,
    downloadStatus: 'pending',
    lastAccessed: new Date('2024-01-12'),
    isPublic: false,
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date()
  },
  {
    id: '5',
    udemyId: 'udemy-5',
    title: 'Docker & Kubernetes Complete Guide',
    instructor: 'Alex Chen',
    description: 'DevOps essentials with Docker containers and Kubernetes',
    thumbnail: '/api/placeholder/400/225',
    duration: '28h 10m',
    rating: 4.9,
    enrolledStudents: 156000,
    totalLectures: 187,
    downloadStatus: 'failed',
    lastAccessed: new Date('2024-01-11'),
    isPublic: false,
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date()
  },
  {
    id: '6',
    udemyId: 'udemy-6',
    title: 'Complete Web Design Course',
    instructor: 'Emma Davis',
    description: 'HTML, CSS, JavaScript, and modern web design principles',
    thumbnail: '/api/placeholder/400/225',
    duration: '21h 45m',
    rating: 4.5,
    enrolledStudents: 98000,
    totalLectures: 134,
    downloadStatus: 'completed',
    lastAccessed: new Date('2024-01-10'),
    isPublic: false,
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date()
  }
]

type SortOption = 'title' | 'instructor' | 'duration' | 'rating' | 'lastAccessed'
type FilterOption = 'all' | 'available' | 'downloading' | 'completed' | 'pending' | 'failed'
type ViewMode = 'grid' | 'list'

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>(mockCourses)
  const [filteredCourses, setFilteredCourses] = useState<Course[]>(mockCourses)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('lastAccessed')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [filterBy, setFilterBy] = useState<FilterOption>('all')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    let result = [...courses]

    // Apply search filter
    if (searchTerm) {
      result = result.filter(course =>
        course.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        course.instructor.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    // Apply status filter
    if (filterBy !== 'all') {
      result = result.filter(course => course.downloadStatus === filterBy)
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal: any = a[sortBy]
      let bVal: any = b[sortBy]

      if (sortBy === 'lastAccessed') {
        aVal = new Date(aVal).getTime()
        bVal = new Date(bVal).getTime()
      } else if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase()
        bVal = bVal.toLowerCase()
      }

      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1
      } else {
        return aVal < bVal ? 1 : -1
      }
    })

    setFilteredCourses(result)
  }, [courses, searchTerm, sortBy, sortDirection, filterBy])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    // TODO: Fetch courses from API
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

  const toggleSort = (field: SortOption) => {
    if (sortBy === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortDirection('asc')
    }
  }

  const getStatusCounts = () => {
    const counts = {
      all: courses.length,
      available: 0,
      downloading: 0,
      completed: 0,
      pending: 0,
      failed: 0
    }

    courses.forEach(course => {
      if (course.downloadStatus in counts) {
        counts[course.downloadStatus as keyof typeof counts]++
      }
    })

    return counts
  }

  const statusCounts = getStatusCounts()

  return (
    <DashboardLayout
      title="My Courses"
      subtitle={`${filteredCourses.length} of ${courses.length} courses`}
      actions={
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
          >
            {viewMode === 'grid' ? <List className="h-4 w-4" /> : <Grid className="h-4 w-4" />}
          </Button>
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Filters and Search */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col lg:flex-row gap-4">
              {/* Search */}
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search courses or instructors..."
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
              </div>

              {/* Status Filter */}
              <div className="flex gap-2 flex-wrap">
                {Object.entries(statusCounts).map(([status, count]) => (
                  <Button
                    key={status}
                    variant={filterBy === status ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFilterBy(status as FilterOption)}
                    className="flex items-center gap-1"
                  >
                    {status === 'all' && <BookOpen className="h-3 w-3" />}
                    {status === 'downloading' && <Download className="h-3 w-3" />}
                    <span className="capitalize">{status}</span>
                    <Badge variant="secondary" className="ml-1 text-xs">
                      {count}
                    </Badge>
                  </Button>
                ))}
              </div>

              {/* Sort */}
              <div className="flex gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleSort('title')}
                  className="flex items-center gap-1"
                >
                  Title
                  {sortBy === 'title' && (
                    sortDirection === 'asc' ? <SortAsc className="h-3 w-3" /> : <SortDesc className="h-3 w-3" />
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleSort('lastAccessed')}
                  className="flex items-center gap-1"
                >
                  Recent
                  {sortBy === 'lastAccessed' && (
                    sortDirection === 'asc' ? <SortAsc className="h-3 w-3" /> : <SortDesc className="h-3 w-3" />
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Course Grid */}
        {filteredCourses.length > 0 ? (
          <CourseGrid
            courses={filteredCourses}
            onDownload={handleDownload}
            onPlay={handlePlay}
            onShare={handleShare}
          />
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {searchTerm || filterBy !== 'all' ? 'No courses found' : 'No courses yet'}
              </h3>
              <p className="text-gray-600 mb-4">
                {searchTerm || filterBy !== 'all'
                  ? 'Try adjusting your search or filter criteria'
                  : 'Connect your Udemy account to start downloading courses'
                }
              </p>
              {!searchTerm && filterBy === 'all' && (
                <Button>
                  Connect Udemy Account
                </Button>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}