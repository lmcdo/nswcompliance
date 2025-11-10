/**
 * Water Rights MVP - Dashboard Home
 * Main allocation overview page for demo purposes
 */

'use client';

import { WaterAccountSummaryCard } from '@/components/water-demo/WaterAccountSummaryCard';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Droplet,
  TrendingUp,
  AlertCircle,
  Calendar,
  Activity,
  DollarSign,
  Bell,
} from 'lucide-react';
import Link from 'next/link';
import {
  demoFarmer,
  demoEntitlements,
  totalAllocationSummary,
  recentAnnouncements,
  demoAlerts,
  getUnreadAlerts,
  currentDamLevels,
  waterMarketPrices,
} from '@/lib/demo-data';

export default function WaterDemoDashboard() {
  const unreadAlerts = getUnreadAlerts();
  const latestAnnouncement = recentAnnouncements[0];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-cyan-50">
      {/* Header */}
      <div className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-600">
                <Droplet className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">WaterRight</h1>
                <p className="text-sm text-gray-600">Water Allocation Management</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="sm" className="relative">
                <Bell className="h-5 w-5" />
                {unreadAlerts.length > 0 && (
                  <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-red-500 text-white text-xs flex items-center justify-center">
                    {unreadAlerts.length}
                  </span>
                )}
              </Button>
              <div className="text-right">
                <p className="font-semibold">{demoFarmer.firstName} {demoFarmer.lastName}</p>
                <p className="text-sm text-gray-600">{demoFarmer.farmName}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {/* Urgent Alerts */}
        {demoAlerts.filter(a => a.severity === 'urgent' && !a.read).length > 0 && (
          <div className="mb-6">
            <Card className="border-red-300 bg-gradient-to-r from-red-50 to-orange-50">
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-full bg-red-100">
                    <AlertCircle className="h-6 w-6 text-red-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-lg mb-1">
                      {demoAlerts.find(a => a.severity === 'urgent')?.title}
                    </h3>
                    <p className="text-gray-700 mb-4">
                      {demoAlerts.find(a => a.severity === 'urgent')?.message}
                    </p>
                    <div className="flex gap-3">
                      <Button variant="default" size="sm">
                        Order Water Now
                      </Button>
                      <Button variant="outline" size="sm">
                        View Details
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Left Column - Summary Card */}
          <div className="lg:col-span-2">
            <WaterAccountSummaryCard
              totalAllocationML={totalAllocationSummary.totalAllocationML}
              usedML={totalAllocationSummary.totalUsedML}
              remainingML={totalAllocationSummary.totalRemainingML}
              usedPct={totalAllocationSummary.overallUsedPct}
              status={totalAllocationSummary.overallStatus}
              lastUpdated={totalAllocationSummary.lastUpdated}
              nextAnnouncementDate="2025-01-02"
            />
          </div>

          {/* Right Column - Quick Stats */}
          <div className="space-y-4">
            {/* Active Entitlements */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  Active Entitlements
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{demoEntitlements.length}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Across {new Set(demoEntitlements.map(e => e.valley)).size} valleys
                </p>
              </CardContent>
            </Card>

            {/* Market Price */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  Market Price (Murr.)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">
                  ${waterMarketPrices.murrumbidgee.temporaryAllocation.currentPrice}
                  <span className="text-sm font-normal text-muted-foreground">/ML</span>
                </p>
                <Badge variant="secondary" className="mt-2">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +${waterMarketPrices.murrumbidgee.temporaryAllocation.change24h} (24h)
                </Badge>
              </CardContent>
            </Card>

            {/* Alerts */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Bell className="h-4 w-4" />
                  Unread Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{unreadAlerts.length}</p>
                <Button variant="link" className="px-0 mt-2" size="sm">
                  View All Alerts →
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Entitlements Breakdown */}
        <div className="mb-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>My Water Entitlements</CardTitle>
                  <CardDescription>Current allocation status across all sources</CardDescription>
                </div>
                <Link href="/water-demo/entitlements">
                  <Button variant="outline" size="sm">
                    View Details
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {demoEntitlements.map(entitlement => (
                  <div
                    key={entitlement.id}
                    className="p-4 rounded-lg border bg-white hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold text-lg">
                          {entitlement.category} - {entitlement.valley}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          Entitlement: {entitlement.volumeML.toLocaleString()} ML | Allocation:{' '}
                          {entitlement.allocationPct}%
                        </p>
                      </div>
                      <Badge
                        variant={
                          entitlement.status === 'compliant'
                            ? 'default'
                            : entitlement.status === 'warning'
                            ? 'secondary'
                            : 'destructive'
                        }
                      >
                        {entitlement.usedPct}% used
                      </Badge>
                    </div>

                    <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
                      <div>
                        <p className="text-muted-foreground">Allocated</p>
                        <p className="font-semibold">
                          {entitlement.allocationML.toLocaleString()} ML
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Used</p>
                        <p className="font-semibold">{entitlement.usedML.toLocaleString()} ML</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Remaining</p>
                        <p className="font-semibold text-blue-600">
                          {entitlement.remainingML.toLocaleString()} ML
                        </p>
                      </div>
                    </div>

                    <Progress value={entitlement.usedPct} className="h-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Dam Levels & Latest Announcement */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Dam Levels */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Droplet className="h-5 w-5 text-blue-600" />
                Dam Storage Levels
              </CardTitle>
              <CardDescription>Current capacity - Updated 6 hours ago</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {currentDamLevels.slice(0, 3).map(dam => (
                  <div key={dam.name} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{dam.name}</span>
                      <span className="text-sm font-semibold">{dam.currentPct}%</span>
                    </div>
                    <Progress value={dam.currentPct} className="h-2" />
                    <p className="text-xs text-muted-foreground">
                      {dam.currentVolumeGL.toLocaleString()} GL / {dam.capacityGL.toLocaleString()}{' '}
                      GL capacity
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Latest Announcement */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-blue-600" />
                Latest Announcement
              </CardTitle>
              <CardDescription>
                {new Date(latestAnnouncement.date).toLocaleDateString('en-AU', {
                  month: 'long',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <h3 className="font-semibold">{latestAnnouncement.valley}</h3>
                {latestAnnouncement.allocations.map((alloc, idx) => (
                  <div key={idx} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{alloc.category}:</span>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{alloc.percentage}%</span>
                      {alloc.trend === 'up' && (
                        <Badge variant="default" className="text-xs">
                          ▲ +{alloc.change}%
                        </Badge>
                      )}
                      {alloc.trend === 'down' && (
                        <Badge variant="destructive" className="text-xs">
                          ▼ {alloc.change}%
                        </Badge>
                      )}
                      {alloc.trend === 'unchanged' && (
                        <Badge variant="secondary" className="text-xs">
                          →
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
                <Button variant="outline" size="sm" className="w-full mt-4">
                  View Full Statement
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
