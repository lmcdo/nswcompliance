/**
 * Water Rights MVP - Alerts Center
 * Centralized notification and alert management
 */

'use client';

import { useState } from 'react';
import { SupplementaryAlert } from '@/components/water-demo/SupplementaryAlert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import Link from 'next/link';
import {
  ArrowLeft,
  Bell,
  BellOff,
  CheckCircle2,
  AlertCircle,
  Info,
  Settings,
  Mail,
  Smartphone,
  MessageSquare,
} from 'lucide-react';
import { demoAlerts, demoFarmer, getActiveAlerts } from '@/lib/demo-data';

export default function AlertsPage() {
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [smsEnabled, setSmsEnabled] = useState(true);
  const [pushEnabled, setPushEnabled] = useState(true);

  const activeAlerts = getActiveAlerts();
  const urgentAlerts = demoAlerts.filter(a => a.severity === 'urgent');
  const warningAlerts = demoAlerts.filter(a => a.severity === 'warning');
  const infoAlerts = demoAlerts.filter(a => a.severity === 'info');

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'supplementary':
        return '⚡';
      case 'allocation_change':
        return '📊';
      case 'usage_warning':
        return '⚠️';
      case 'compliance':
        return '✅';
      case 'system':
        return '🔧';
      default:
        return '🔔';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString('en-AU', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-cyan-50">
      {/* Header */}
      <div className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/water-demo">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to Dashboard
                </Button>
              </Link>
              <div className="h-6 w-px bg-gray-300" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Alerts & Notifications</h1>
                <p className="text-sm text-gray-600">{demoFarmer.farmName}</p>
              </div>
            </div>
            <Button variant="outline" size="sm">
              <Settings className="mr-2 h-4 w-4" />
              Alert Settings
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-600" />
                Urgent
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-red-600">{urgentAlerts.length}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-yellow-600" />
                Warning
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-yellow-600">{warningAlerts.length}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Info className="h-4 w-4 text-blue-600" />
                Info
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-blue-600">{infoAlerts.length}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Bell className="h-4 w-4 text-gray-600" />
                Total Active
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{activeAlerts.length}</p>
            </CardContent>
          </Card>
        </div>

        {/* Urgent Alerts */}
        {urgentAlerts.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
              <AlertCircle className="h-6 w-6 text-red-600" />
              Urgent Alerts
            </h2>
            <div className="space-y-4">
              {urgentAlerts.map(alert => (
                <SupplementaryAlert
                  key={alert.id}
                  title={alert.title}
                  message={alert.message}
                  expiresAt={alert.expiresAt || new Date(Date.now() + 86400000).toISOString()}
                  entitlementML={150}
                  actionUrl={alert.actionUrl}
                />
              ))}
            </div>
          </div>
        )}

        {/* All Alerts */}
        <Card className="mb-8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>All Alerts</CardTitle>
                <CardDescription>Recent notifications and system messages</CardDescription>
              </div>
              <Button variant="outline" size="sm">
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Mark All Read
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {demoAlerts.map(alert => (
                <div
                  key={alert.id}
                  className={`p-4 rounded-lg border transition-all hover:shadow-md ${
                    !alert.read ? 'bg-blue-50 border-blue-200' : 'bg-white'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className="text-2xl mt-1">{getAlertIcon(alert.type)}</div>

                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className={`font-semibold ${!alert.read ? 'text-blue-900' : ''}`}>
                            {alert.title}
                          </h3>
                          <p className="text-xs text-muted-foreground">
                            {formatTimestamp(alert.timestamp)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {!alert.read && (
                            <Badge variant="default" className="text-xs">
                              New
                            </Badge>
                          )}
                          <Badge
                            variant={
                              alert.severity === 'urgent'
                                ? 'destructive'
                                : alert.severity === 'warning'
                                ? 'secondary'
                                : 'outline'
                            }
                            className="text-xs"
                          >
                            {alert.severity}
                          </Badge>
                        </div>
                      </div>

                      <p className="text-sm text-gray-700 mb-3">{alert.message}</p>

                      {alert.actionLabel && alert.actionUrl && (
                        <Button variant="outline" size="sm">
                          {alert.actionLabel} →
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Notification Settings
            </CardTitle>
            <CardDescription>Choose how you want to receive alerts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Email Notifications */}
              <div className="flex items-center justify-between p-4 rounded-lg border bg-white">
                <div className="flex items-center gap-3">
                  <Mail className="h-5 w-5 text-blue-600" />
                  <div>
                    <p className="font-medium">Email Notifications</p>
                    <p className="text-sm text-muted-foreground">{demoFarmer.email}</p>
                  </div>
                </div>
                <Switch checked={emailEnabled} onCheckedChange={setEmailEnabled} />
              </div>

              {/* SMS Notifications */}
              <div className="flex items-center justify-between p-4 rounded-lg border bg-white">
                <div className="flex items-center gap-3">
                  <Smartphone className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="font-medium">SMS Notifications</p>
                    <p className="text-sm text-muted-foreground">{demoFarmer.phone}</p>
                  </div>
                </div>
                <Switch checked={smsEnabled} onCheckedChange={setSmsEnabled} />
              </div>

              {/* Push Notifications */}
              <div className="flex items-center justify-between p-4 rounded-lg border bg-white">
                <div className="flex items-center gap-3">
                  <MessageSquare className="h-5 w-5 text-purple-600" />
                  <div>
                    <p className="font-medium">Push Notifications</p>
                    <p className="text-sm text-muted-foreground">Mobile app alerts</p>
                  </div>
                </div>
                <Switch checked={pushEnabled} onCheckedChange={setPushEnabled} />
              </div>

              {/* Alert Types */}
              <div className="pt-4 border-t">
                <h3 className="font-semibold mb-3">Alert Types to Receive</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="supplementary" className="cursor-pointer">
                      Supplementary water access (urgent)
                    </Label>
                    <Switch id="supplementary" defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="allocation" className="cursor-pointer">
                      Allocation changes
                    </Label>
                    <Switch id="allocation" defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="usage" className="cursor-pointer">
                      Usage warnings (approaching limit)
                    </Label>
                    <Switch id="usage" defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="compliance" className="cursor-pointer">
                      Compliance status updates
                    </Label>
                    <Switch id="compliance" defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="system" className="cursor-pointer">
                      System notifications (telemetry updates)
                    </Label>
                    <Switch id="system" defaultChecked />
                  </div>
                </div>
              </div>

              <Button variant="default" className="w-full">
                Save Settings
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
