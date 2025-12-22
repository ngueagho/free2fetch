// User and Authentication Types
export interface User {
  id: string
  email: string
  username: string
  firstName?: string
  lastName?: string
  avatar?: string
  isVerified: boolean
  isPremium: boolean
  createdAt: string
  updatedAt: string
  profile?: UserProfile
  subscription?: Subscription
}

export interface UserProfile {
  bio?: string
  phone?: string
  timezone: string
  language: string
  location?: string
  website?: string
  publicProfile: boolean
  emailNotifications: boolean
  newsletterSubscription: boolean
  totalDownloads: number
  totalStorageUsed: number
}

// Subscription Types
export type PlanType = 'free' | 'basic' | 'premium' | 'enterprise'
export type SubscriptionStatus = 'active' | 'trialing' | 'past_due' | 'cancelled' | 'expired' | 'suspended'
export type BillingPeriod = 'monthly' | 'quarterly' | 'yearly' | 'lifetime'

export interface SubscriptionPlan {
  id: string
  name: string
  slug: string
  planType: PlanType
  description: string
  shortDescription: string
  features: string[]
  price: number
  currency: string
  billingPeriod: BillingPeriod
  monthlyDownloadLimit: number
  storageLimit: number
  maxConcurrentDownloads: number
  streamingEnabled: boolean
  sharingEnabled: boolean
  apiAccess: boolean
  prioritySupport: boolean
  advancedAnalytics: boolean
  isPopular: boolean
  trialDays: number
}

export interface Subscription {
  id: string
  plan: SubscriptionPlan
  status: SubscriptionStatus
  startDate: string
  endDate?: string
  trialEndDate?: string
  downloadsUsed: number
  storageUsed: number
  cancelAtPeriodEnd: boolean
  autoRenew: boolean
}

// Course Types
export type CourseLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert'
export type CourseStatus = 'active' | 'draft' | 'archived'
export type CurriculumItemType = 'lecture' | 'quiz' | 'practice' | 'assignment'

export interface Course {
  id: string
  udemyCourseId: string
  title: string
  slug: string
  description: string
  headline: string
  instructorName: string
  level: CourseLevel
  language: string
  category: string
  subcategory: string
  rating: number
  numReviews: number
  numStudents: number
  durationSeconds: number
  numLectures: number
  hasCaptions: boolean
  hasCodingExercises: boolean
  hasQuizzes: boolean
  imageUrl: string
  price: number
  currency: string
  status: CourseStatus
  lastUpdated: string
  downloadCount: number
  viewCount: number
  createdAt: string
  updatedAt: string
}

export interface Curriculum {
  id: string
  courseId: string
  udemyItemId: string
  title: string
  description: string
  itemType: CurriculumItemType
  sectionTitle: string
  orderIndex: number
  sectionIndex: number
  durationSeconds: number
  isFree: boolean
  videoUrl: string
  videoQuality: string
  isDownloadable: boolean
  downloadCount: number
}

export interface UserCourse {
  id: string
  course: Course
  enrollmentDate: string
  progressPercentage: number
  lastAccessed?: string
  completedLectures: number
  userRating?: number
  userReview?: string
  isFavorite: boolean
  preferredQuality: string
  downloadSubtitles: boolean
}

// Download Types
export type DownloadStatus = 'pending' | 'queued' | 'downloading' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'paused'
export type DownloadPriority = 'low' | 'normal' | 'high' | 'urgent'
export type VideoQuality = '360p' | '480p' | '720p' | '1080p' | 'auto'
export type DownloadItemType = 'video' | 'subtitle' | 'attachment' | 'thumbnail'
export type DownloadItemStatus = 'pending' | 'downloading' | 'completed' | 'failed' | 'skipped'

export interface DownloadJob {
  id: string
  course: Course
  status: DownloadStatus
  priority: DownloadPriority
  quality: VideoQuality
  includeSubtitles: boolean
  includeAttachments: boolean
  selectedLectures: string[]
  totalItems: number
  completedItems: number
  failedItems: number
  progressPercentage: number
  totalSizeBytes: number
  downloadedSizeBytes: number
  storagePath: string
  downloadSpeedMbps: number
  estimatedTimeRemaining: number
  errorMessage?: string
  retryCount: number
  maxRetries: number
  celeryTaskId?: string
  createdAt: string
  startedAt?: string
  completedAt?: string
  updatedAt: string
}

export interface DownloadItem {
  id: string
  downloadJobId: string
  curriculumItem?: Curriculum
  itemType: DownloadItemType
  title: string
  filename: string
  sourceUrl: string
  localPath: string
  fileSizeBytes: number
  downloadedBytes: number
  fileFormat: string
  quality: string
  status: DownloadItemStatus
  progressPercentage: number
  downloadSpeedKbps: number
  errorMessage?: string
  retryCount: number
  createdAt: string
  startedAt?: string
  completedAt?: string
}

// Analytics Types
export type UserAction = 'login' | 'logout' | 'course_view' | 'course_download' | 'search' | 'profile_update' | 'subscription_change' | 'share_course' | 'stream_video' | 'api_request'

export interface UserActivity {
  id: string
  user?: User
  action: UserAction
  description: string
  metadata: Record<string, any>
  ipAddress?: string
  userAgent: string
  country?: string
  city?: string
  deviceType?: string
  browser?: string
  responseTime?: number
  createdAt: string
}

export interface DownloadAnalytics {
  id: string
  course: Course
  status: 'started' | 'completed' | 'failed' | 'cancelled'
  qualityRequested: string
  totalFiles: number
  completedFiles: number
  totalSizeMb: number
  downloadSpeedMbps: number
  totalDurationSeconds: number
  errorCount: number
  retryCount: number
  userCancelled: boolean
  userPaused: boolean
  startedAt: string
  completedAt?: string
}

// Notification Types
export type NotificationStatus = 'pending' | 'sent' | 'delivered' | 'failed' | 'cancelled'
export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent'
export type NotificationType = 'info' | 'success' | 'warning' | 'error' | 'announcement'
export type NotificationCategory = 'welcome' | 'download_complete' | 'download_failed' | 'quota_warning' | 'quota_exceeded' | 'subscription_expiry' | 'payment_success' | 'payment_failed'

export interface Notification {
  id: string
  subject: string
  content: string
  htmlContent?: string
  recipientEmail: string
  status: NotificationStatus
  priority: NotificationPriority
  sentAt?: string
  deliveredAt?: string
  openedAt?: string
  clickedAt?: string
  failureReason?: string
  retryCount: number
  scheduledAt?: string
  createdAt: string
}

export interface InAppNotification {
  id: string
  title: string
  message: string
  type: NotificationType
  actionText?: string
  actionUrl?: string
  isRead: boolean
  readAt?: string
  isDismissed: boolean
  dismissedAt?: string
  expiresAt?: string
  createdAt: string
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message?: string
  errors?: Record<string, string[]>
  meta?: {
    pagination?: PaginationMeta
    total?: number
  }
}

export interface PaginationMeta {
  page: number
  pageSize: number
  totalPages: number
  totalCount: number
  hasNext: boolean
  hasPrevious: boolean
}

export interface ApiError {
  message: string
  code?: string
  details?: Record<string, any>
}

// Form Types
export interface LoginForm {
  email: string
  password: string
  rememberMe?: boolean
}

export interface RegisterForm {
  email: string
  username: string
  password: string
  confirmPassword: string
  firstName?: string
  lastName?: string
  acceptTerms: boolean
}

export interface ProfileForm {
  firstName?: string
  lastName?: string
  bio?: string
  phone?: string
  location?: string
  website?: string
  timezone: string
  language: string
  publicProfile: boolean
  emailNotifications: boolean
  newsletterSubscription: boolean
}

export interface PasswordChangeForm {
  currentPassword: string
  newPassword: string
  confirmNewPassword: string
}

export interface DownloadForm {
  courseId: string
  quality: VideoQuality
  includeSubtitles: boolean
  includeAttachments: boolean
  selectedLectures?: string[]
  priority: DownloadPriority
}

// Share Types
export type SharePermission = 'view' | 'download'

export interface CourseShare {
  id: string
  course: Course
  sharedBy: User
  sharedWith?: User
  shareLink: string
  permissionLevel: SharePermission
  isPublic: boolean
  expiresAt?: string
  maxAccessCount?: number
  currentAccessCount: number
  passwordProtected: boolean
  isActive: boolean
  createdAt: string
}

// System Types
export interface SystemSettings {
  key: string
  value: string
  valueType: 'string' | 'integer' | 'float' | 'boolean' | 'json'
  name: string
  description: string
  category: string
  isPublic: boolean
  isEditable: boolean
}

export interface Feature {
  key: string
  name: string
  description: string
  isEnabled: boolean
  isStaffOnly: boolean
  rolloutPercentage: number
  conditions: Record<string, any>
}

// Dashboard Types
export interface DashboardStats {
  totalCourses: number
  totalDownloads: number
  storageUsed: number
  storageLimit: number
  downloadsThisMonth: number
  downloadLimit: number
  activeDownloads: number
  completedDownloads: number
  failedDownloads: number
  averageDownloadSpeed: number
}

export interface RecentActivity {
  id: string
  action: string
  description: string
  timestamp: string
  metadata?: Record<string, any>
}

// Utility Types
export type LoadingState = 'idle' | 'loading' | 'success' | 'error'

export interface AsyncState<T = any> {
  data: T | null
  loading: boolean
  error: string | null
}

export interface TableColumn<T = any> {
  key: keyof T
  title: string
  sortable?: boolean
  render?: (value: any, record: T) => React.ReactNode
  width?: string
  align?: 'left' | 'center' | 'right'
}

export interface FilterOption {
  label: string
  value: string
  count?: number
}

export interface SearchFilters {
  query?: string
  category?: string
  level?: CourseLevel
  language?: string
  rating?: number
  duration?: {
    min?: number
    max?: number
  }
  price?: {
    min?: number
    max?: number
  }
}

// Error Types
export class AppError extends Error {
  code: string
  statusCode: number
  isOperational: boolean

  constructor(message: string, code: string, statusCode: number = 500, isOperational: boolean = true) {
    super(message)
    this.code = code
    this.statusCode = statusCode
    this.isOperational = isOperational

    Object.setPrototypeOf(this, AppError.prototype)
  }
}

// Event Types
export interface WebSocketEvent {
  type: string
  data: any
  timestamp: string
}

export interface DownloadProgressEvent extends WebSocketEvent {
  type: 'download_progress'
  data: {
    jobId: string
    progress: number
    speed: number
    eta: number
    status: DownloadStatus
  }
}

export interface NotificationEvent extends WebSocketEvent {
  type: 'notification'
  data: InAppNotification
}