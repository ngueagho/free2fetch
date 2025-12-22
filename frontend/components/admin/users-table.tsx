'use client'

import { useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  MoreHorizontal,
  Eye,
  Ban,
  UserCheck,
  Mail,
  Download,
  Crown,
  Shield
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  subscriptionTier: 'free' | 'premium' | 'enterprise'
  isActive: boolean
  totalDownloads: number
  storageUsed: number
  lastLogin: Date
  joinDate: Date
  isStaff: boolean
}

interface UsersTableProps {
  users: User[]
  onViewUser: (userId: string) => void
  onBanUser: (userId: string) => void
  onUnbanUser: (userId: string) => void
  onSendEmail: (userId: string) => void
  onUpgradeUser: (userId: string, tier: string) => void
}

export function UsersTable({
  users,
  onViewUser,
  onBanUser,
  onUnbanUser,
  onSendEmail,
  onUpgradeUser
}: UsersTableProps) {
  const [selectedUsers, setSelectedUsers] = useState<string[]>([])

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'enterprise':
        return <Badge variant="default" className="bg-yellow-500"><Crown className="h-3 w-3 mr-1" />Enterprise</Badge>
      case 'premium':
        return <Badge variant="default" className="bg-purple-500">Premium</Badge>
      case 'free':
        return <Badge variant="outline">Free</Badge>
      default:
        return <Badge variant="outline">Unknown</Badge>
    }
  }

  const getStatusBadge = (isActive: boolean) => {
    return isActive ? (
      <Badge variant="success">Active</Badge>
    ) : (
      <Badge variant="destructive">Banned</Badge>
    )
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 GB'
    const gb = bytes / (1024 * 1024 * 1024)
    return `${gb.toFixed(1)} GB`
  }

  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }).format(new Date(date))
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            User Management
          </CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              Export Users
            </Button>
            <Button size="sm">
              <Mail className="h-4 w-4 mr-2" />
              Bulk Email
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <input
                    type="checkbox"
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedUsers(users.map(u => u.id))
                      } else {
                        setSelectedUsers([])
                      }
                    }}
                    checked={selectedUsers.length === users.length}
                  />
                </TableHead>
                <TableHead>User</TableHead>
                <TableHead>Subscription</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Downloads</TableHead>
                <TableHead>Storage</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedUsers.includes(user.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedUsers([...selectedUsers, user.id])
                        } else {
                          setSelectedUsers(selectedUsers.filter(id => id !== user.id))
                        }
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-3">
                      <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                        <span className="text-sm font-medium text-white">
                          {user.firstName.charAt(0)}{user.lastName.charAt(0)}
                        </span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-gray-900">
                            {user.firstName} {user.lastName}
                          </p>
                          {user.isStaff && (
                            <Shield className="h-3 w-3 text-red-500" title="Staff" />
                          )}
                        </div>
                        <p className="text-sm text-gray-500">{user.email}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getTierBadge(user.subscriptionTier)}
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(user.isActive)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Download className="h-4 w-4 text-gray-400" />
                      <span>{user.totalDownloads}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {formatFileSize(user.storageUsed)}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-gray-600">
                      {formatDate(user.lastLogin)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-gray-600">
                      {formatDate(user.joinDate)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => onViewUser(user.id)}>
                          <Eye className="h-4 w-4 mr-2" />
                          View Details
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onSendEmail(user.id)}>
                          <Mail className="h-4 w-4 mr-2" />
                          Send Email
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        {user.subscriptionTier === 'free' && (
                          <>
                            <DropdownMenuItem onClick={() => onUpgradeUser(user.id, 'premium')}>
                              <Crown className="h-4 w-4 mr-2" />
                              Upgrade to Premium
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onUpgradeUser(user.id, 'enterprise')}>
                              <Crown className="h-4 w-4 mr-2" />
                              Upgrade to Enterprise
                            </DropdownMenuItem>
                          </>
                        )}
                        <DropdownMenuSeparator />
                        {user.isActive ? (
                          <DropdownMenuItem
                            onClick={() => onBanUser(user.id)}
                            className="text-red-600 focus:text-red-600"
                          >
                            <Ban className="h-4 w-4 mr-2" />
                            Ban User
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem
                            onClick={() => onUnbanUser(user.id)}
                            className="text-green-600 focus:text-green-600"
                          >
                            <UserCheck className="h-4 w-4 mr-2" />
                            Unban User
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Bulk actions */}
        {selectedUsers.length > 0 && (
          <div className="mt-4 p-3 bg-blue-50 rounded-md border border-blue-200">
            <div className="flex items-center justify-between">
              <span className="text-sm text-blue-800">
                {selectedUsers.length} user(s) selected
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  <Mail className="h-4 w-4 mr-2" />
                  Send Email
                </Button>
                <Button variant="outline" size="sm">
                  Export Selected
                </Button>
                <Button variant="destructive" size="sm">
                  <Ban className="h-4 w-4 mr-2" />
                  Ban Selected
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}