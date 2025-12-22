'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Settings,
  Download,
  Database,
  Shield,
  Globe,
  Mail,
  Save,
  RefreshCw
} from 'lucide-react'

interface SystemSettings {
  // Download Settings
  maxConcurrentDownloads: number
  downloadTimeout: number
  retryAttempts: number
  defaultVideoQuality: string
  allowSubtitleDownload: boolean

  // User Limits
  freeDownloadLimit: number
  premiumDownloadLimit: number
  enterpriseDownloadLimit: number
  freeStorageLimit: number
  premiumStorageLimit: number
  enterpriseStorageLimit: number

  // System Settings
  maintenanceMode: boolean
  newRegistrations: boolean
  udemyOauthEnabled: boolean
  emailNotifications: boolean

  // Rate Limiting
  apiRateLimit: number
  downloadRateLimit: number

  // Email Settings
  smtpHost: string
  smtpPort: number
  smtpUser: string
  emailFromAddress: string

  // Security
  sessionTimeout: number
  passwordMinLength: number
  requireEmailVerification: boolean

  // Storage
  storageType: string
  maxFileSize: number
  cleanupInterval: number
}

interface SystemSettingsProps {
  settings: SystemSettings
  onSave: (settings: SystemSettings) => void
}

export function SystemSettings({ settings, onSave }: SystemSettingsProps) {
  const [formSettings, setFormSettings] = useState<SystemSettings>(settings)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('downloads')

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(formSettings)
    } finally {
      setSaving(false)
    }
  }

  const updateSetting = (key: keyof SystemSettings, value: any) => {
    setFormSettings(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const tabs = [
    { id: 'downloads', name: 'Downloads', icon: Download },
    { id: 'limits', name: 'User Limits', icon: Shield },
    { id: 'system', name: 'System', icon: Settings },
    { id: 'email', name: 'Email', icon: Mail },
    { id: 'storage', name: 'Storage', icon: Database },
    { id: 'security', name: 'Security', icon: Globe },
  ]

  return (
    <div className="space-y-6">
      {/* Settings Tabs */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <Button
                key={tab.id}
                variant={activeTab === tab.id ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveTab(tab.id)}
                className="flex items-center gap-2"
              >
                <tab.icon className="h-4 w-4" />
                {tab.name}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Download Settings */}
      {activeTab === 'downloads' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              Download Settings
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="maxConcurrentDownloads">Max Concurrent Downloads</Label>
                <Input
                  id="maxConcurrentDownloads"
                  type="number"
                  value={formSettings.maxConcurrentDownloads}
                  onChange={(e) => updateSetting('maxConcurrentDownloads', parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="downloadTimeout">Download Timeout (seconds)</Label>
                <Input
                  id="downloadTimeout"
                  type="number"
                  value={formSettings.downloadTimeout}
                  onChange={(e) => updateSetting('downloadTimeout', parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="retryAttempts">Retry Attempts</Label>
                <Input
                  id="retryAttempts"
                  type="number"
                  value={formSettings.retryAttempts}
                  onChange={(e) => updateSetting('retryAttempts', parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="defaultVideoQuality">Default Video Quality</Label>
                <Select
                  value={formSettings.defaultVideoQuality}
                  onValueChange={(value) => updateSetting('defaultVideoQuality', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="360p">360p</SelectItem>
                    <SelectItem value="480p">480p</SelectItem>
                    <SelectItem value="720p">720p (HD)</SelectItem>
                    <SelectItem value="1080p">1080p (Full HD)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="allowSubtitleDownload"
                checked={formSettings.allowSubtitleDownload}
                onCheckedChange={(checked) => updateSetting('allowSubtitleDownload', checked)}
              />
              <Label htmlFor="allowSubtitleDownload">Allow subtitle download by default</Label>
            </div>
          </CardContent>
        </Card>
      )}

      {/* User Limits */}
      {activeTab === 'limits' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              User Limits
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Free Tier */}
              <div className="space-y-4">
                <h3 className="font-medium flex items-center gap-2">
                  Free Tier
                  <Badge variant="outline">Free</Badge>
                </h3>
                <div className="space-y-2">
                  <Label>Download Limit/Month</Label>
                  <Input
                    type="number"
                    value={formSettings.freeDownloadLimit}
                    onChange={(e) => updateSetting('freeDownloadLimit', parseInt(e.target.value))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Storage Limit (GB)</Label>
                  <Input
                    type="number"
                    value={formSettings.freeStorageLimit}
                    onChange={(e) => updateSetting('freeStorageLimit', parseInt(e.target.value))}
                  />
                </div>
              </div>

              {/* Premium Tier */}
              <div className="space-y-4">
                <h3 className="font-medium flex items-center gap-2">
                  Premium Tier
                  <Badge variant="default" className="bg-purple-500">Premium</Badge>
                </h3>
                <div className="space-y-2">
                  <Label>Download Limit/Month</Label>
                  <Input
                    type="number"
                    value={formSettings.premiumDownloadLimit}
                    onChange={(e) => updateSetting('premiumDownloadLimit', parseInt(e.target.value))}
                    placeholder="-1 for unlimited"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Storage Limit (GB)</Label>
                  <Input
                    type="number"
                    value={formSettings.premiumStorageLimit}
                    onChange={(e) => updateSetting('premiumStorageLimit', parseInt(e.target.value))}
                    placeholder="-1 for unlimited"
                  />
                </div>
              </div>

              {/* Enterprise Tier */}
              <div className="space-y-4">
                <h3 className="font-medium flex items-center gap-2">
                  Enterprise Tier
                  <Badge variant="default" className="bg-yellow-500">Enterprise</Badge>
                </h3>
                <div className="space-y-2">
                  <Label>Download Limit/Month</Label>
                  <Input
                    type="number"
                    value={formSettings.enterpriseDownloadLimit}
                    onChange={(e) => updateSetting('enterpriseDownloadLimit', parseInt(e.target.value))}
                    placeholder="-1 for unlimited"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Storage Limit (GB)</Label>
                  <Input
                    type="number"
                    value={formSettings.enterpriseStorageLimit}
                    onChange={(e) => updateSetting('enterpriseStorageLimit', parseInt(e.target.value))}
                    placeholder="-1 for unlimited"
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* System Settings */}
      {activeTab === 'system' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              System Settings
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="maintenanceMode">Maintenance Mode</Label>
                  <p className="text-sm text-gray-500">Prevent new downloads and user access</p>
                </div>
                <Switch
                  id="maintenanceMode"
                  checked={formSettings.maintenanceMode}
                  onCheckedChange={(checked) => updateSetting('maintenanceMode', checked)}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="newRegistrations">Allow New Registrations</Label>
                  <p className="text-sm text-gray-500">Allow new users to register</p>
                </div>
                <Switch
                  id="newRegistrations"
                  checked={formSettings.newRegistrations}
                  onCheckedChange={(checked) => updateSetting('newRegistrations', checked)}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="udemyOauthEnabled">Udemy OAuth</Label>
                  <p className="text-sm text-gray-500">Enable Udemy OAuth integration</p>
                </div>
                <Switch
                  id="udemyOauthEnabled"
                  checked={formSettings.udemyOauthEnabled}
                  onCheckedChange={(checked) => updateSetting('udemyOauthEnabled', checked)}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="emailNotifications">Email Notifications</Label>
                  <p className="text-sm text-gray-500">Send email notifications to users</p>
                </div>
                <Switch
                  id="emailNotifications"
                  checked={formSettings.emailNotifications}
                  onCheckedChange={(checked) => updateSetting('emailNotifications', checked)}
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label>API Rate Limit (requests/minute)</Label>
                <Input
                  type="number"
                  value={formSettings.apiRateLimit}
                  onChange={(e) => updateSetting('apiRateLimit', parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label>Download Rate Limit (MB/s)</Label>
                <Input
                  type="number"
                  value={formSettings.downloadRateLimit}
                  onChange={(e) => updateSetting('downloadRateLimit', parseInt(e.target.value))}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Save Settings
        </Button>
      </div>
    </div>
  )
}