'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import {
  Crown,
  Zap,
  Download,
  Calendar,
  TrendingUp
} from 'lucide-react'
import Link from 'next/link'
import { UserSubscription } from '@/types'

interface SubscriptionStatusProps {
  subscription: UserSubscription
}

export function SubscriptionStatus({ subscription }: SubscriptionStatusProps) {
  const isFreePlan = subscription.tier === 'free'
  const isPremium = subscription.tier === 'premium'
  const isEnterprise = subscription.tier === 'enterprise'

  const getUsagePercentage = (used: number, limit: number) => {
    if (limit === -1) return 0 // Unlimited
    return Math.round((used / limit) * 100)
  }

  const formatLimit = (limit: number) => {
    return limit === -1 ? 'Unlimited' : limit.toString()
  }

  const getStatusColor = () => {
    if (isEnterprise) return 'from-yellow-500 to-yellow-600'
    if (isPremium) return 'from-purple-500 to-purple-600'
    return 'from-gray-400 to-gray-500'
  }

  const getStatusIcon = () => {
    if (isEnterprise) return <Crown className="h-5 w-5" />
    if (isPremium) return <Zap className="h-5 w-5" />
    return <Download className="h-5 w-5" />
  }

  const getPlanName = () => {
    if (isEnterprise) return 'Enterprise'
    if (isPremium) return 'Premium'
    return 'Free'
  }

  const downloadUsagePercentage = getUsagePercentage(
    subscription.downloadsUsed,
    subscription.downloadLimit
  )

  const storageUsagePercentage = getUsagePercentage(
    subscription.storageUsed,
    subscription.storageLimit
  )

  const isNearLimit = downloadUsagePercentage > 80 || storageUsagePercentage > 80
  const hasExceededLimit = downloadUsagePercentage >= 100 || storageUsagePercentage >= 100

  return (
    <div className="space-y-6">
      {/* Plan Status Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`h-10 w-10 rounded-lg bg-gradient-to-r ${getStatusColor()} flex items-center justify-center text-white`}>
                {getStatusIcon()}
              </div>
              <div>
                <CardTitle className="text-lg">{getPlanName()} Plan</CardTitle>
                <p className="text-sm text-gray-600">
                  {subscription.isActive ? 'Active' : 'Inactive'} subscription
                </p>
              </div>
            </div>
            <Badge
              variant={subscription.isActive ? 'success' : 'destructive'}
            >
              {subscription.isActive ? 'Active' : 'Inactive'}
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Downloads Usage */}
          <div>
            <div className="flex justify-between text-sm font-medium mb-2">
              <span>Downloads this month</span>
              <span>
                {subscription.downloadsUsed} / {formatLimit(subscription.downloadLimit)}
              </span>
            </div>
            <Progress
              value={downloadUsagePercentage}
              variant={hasExceededLimit ? 'error' : isNearLimit ? 'warning' : 'success'}
              className="h-2"
            />
            {isNearLimit && subscription.downloadLimit !== -1 && (
              <p className="text-xs text-yellow-600 mt-1">
                You're approaching your download limit
              </p>
            )}
            {hasExceededLimit && subscription.downloadLimit !== -1 && (
              <p className="text-xs text-red-600 mt-1">
                You've reached your download limit
              </p>
            )}
          </div>

          {/* Storage Usage */}
          <div>
            <div className="flex justify-between text-sm font-medium mb-2">
              <span>Storage used</span>
              <span>
                {(subscription.storageUsed / 1024).toFixed(1)} GB / {formatLimit(Math.round(subscription.storageLimit / 1024))} GB
              </span>
            </div>
            <Progress
              value={storageUsagePercentage}
              variant={hasExceededLimit ? 'error' : isNearLimit ? 'warning' : 'success'}
              className="h-2"
            />
          </div>

          {/* Plan Features */}
          <div className="pt-4 border-t">
            <h4 className="font-medium mb-2">Plan Features</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
              <div className="flex items-center space-x-2">
                <Download className="h-4 w-4 text-blue-500" />
                <span>
                  {subscription.downloadLimit === -1 ? 'Unlimited' : subscription.downloadLimit} downloads/month
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <Calendar className="h-4 w-4 text-green-500" />
                <span>
                  {subscription.storageLimit === -1 ? 'Unlimited' : `${Math.round(subscription.storageLimit / 1024)} GB`} storage
                </span>
              </div>
              {isPremium || isEnterprise ? (
                <>
                  <div className="flex items-center space-x-2">
                    <TrendingUp className="h-4 w-4 text-purple-500" />
                    <span>Priority downloads</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Zap className="h-4 w-4 text-yellow-500" />
                    <span>HD quality downloads</span>
                  </div>
                </>
              ) : null}
            </div>
          </div>

          {/* Renewal/Upgrade */}
          <div className="pt-4 border-t">
            {subscription.isActive ? (
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm font-medium">
                    {subscription.willRenew ? 'Renews on' : 'Expires on'}
                  </p>
                  <p className="text-sm text-gray-600">
                    {new Date(subscription.currentPeriodEnd).toLocaleDateString()}
                  </p>
                </div>
                {isFreePlan && (
                  <Button asChild>
                    <Link href="/dashboard/upgrade">
                      Upgrade Plan
                    </Link>
                  </Button>
                )}
              </div>
            ) : (
              <div className="text-center">
                <p className="text-sm text-gray-600 mb-3">
                  Your subscription has expired
                </p>
                <Button asChild>
                  <Link href="/dashboard/upgrade">
                    Reactivate Subscription
                  </Link>
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Upgrade Notification */}
      {isFreePlan && isNearLimit && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="p-4">
            <div className="flex items-start space-x-3">
              <TrendingUp className="h-5 w-5 text-yellow-600 mt-0.5" />
              <div className="flex-1">
                <h4 className="font-medium text-yellow-800">
                  Consider upgrading your plan
                </h4>
                <p className="text-sm text-yellow-700 mt-1">
                  You're running low on downloads. Upgrade to Premium for unlimited access to all features.
                </p>
                <Button size="sm" className="mt-2" asChild>
                  <Link href="/dashboard/upgrade">
                    View Plans
                  </Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}