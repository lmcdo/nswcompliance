/**
 * Water Rights MVP - Usage Tracking Page
 * Manual water usage entry and history visualization
 */

'use client';

import { useState } from 'react';
import { UsageHistoryChart } from '@/components/water-demo/UsageHistoryChart';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import Link from 'next/link';
import {
  ArrowLeft,
  Plus,
  Download,
  Calendar,
  Droplet,
  Activity,
  Upload,
  Wifi,
} from 'lucide-react';
import {
  demoFarmer,
  demoEntitlements,
  usageHistory,
  monthlyUsageSummary,
} from '@/lib/demo-data';

export default function UsageTrackingPage() {
  const [showEntryForm, setShowEntryForm] = useState(false);

  // Get recent usage entries (last 30 days)
  const recentEntries = usageHistory.slice(0, 10);

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
                <h1 className="text-2xl font-bold text-gray-900">Water Usage Tracking</h1>
                <p className="text-sm text-gray-600">{demoFarmer.farmName}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm">
                <Upload className="mr-2 h-4 w-4" />
                Import CSV
              </Button>
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" />
                Export Report
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={() => setShowEntryForm(!showEntryForm)}
              >
                <Plus className="mr-2 h-4 w-4" />
                Log Water Use
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {/* Data Source Info */}
        <Card className="mb-6 bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-full bg-green-100">
                <Wifi className="h-6 w-6 text-green-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-lg mb-1">Telemetry Connected</h3>
                <p className="text-sm text-gray-700 mb-2">
                  Your water meter readings are updated automatically every 15 minutes via Observant
                  telemetry. Latest update: Today at 8:15 AM (220.0 ML cumulative).
                </p>
                <Badge variant="default" className="bg-green-600">
                  <Activity className="h-3 w-3 mr-1" />
                  Active
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Manual Entry Form */}
        {showEntryForm && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Log Water Use</CardTitle>
              <CardDescription>
                Manually record water usage for dates not covered by telemetry
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="date">Date</Label>
                    <Input
                      id="date"
                      type="date"
                      defaultValue={new Date().toISOString().split('T')[0]}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="entitlement">Water Source</Label>
                    <select
                      id="entitlement"
                      className="w-full p-2 border rounded-md bg-white"
                    >
                      {demoEntitlements.map(e => (
                        <option key={e.id} value={e.id}>
                          {e.category} - {e.valley}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="volume">Volume Used (ML)</Label>
                    <Input
                      id="volume"
                      type="number"
                      step="0.1"
                      placeholder="e.g., 5.2"
                      className="text-lg"
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="purpose">Purpose (optional)</Label>
                    <Textarea
                      id="purpose"
                      placeholder="e.g., Rice paddock 3 irrigation"
                      className="h-24"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="meterReading">Meter Reading (optional)</Label>
                    <Input
                      id="meterReading"
                      type="number"
                      step="0.1"
                      placeholder="Cumulative ML"
                    />
                    <p className="text-xs text-muted-foreground">
                      Enter the cumulative meter reading if available
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <Button variant="default">
                  <Plus className="mr-2 h-4 w-4" />
                  Save Entry
                </Button>
                <Button variant="outline" onClick={() => setShowEntryForm(false)}>
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Usage History Chart */}
        <div className="mb-6">
          <UsageHistoryChart data={monthlyUsageSummary} />
        </div>

        {/* Recent Usage Entries */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Water Usage</CardTitle>
                <CardDescription>Last 30 days of usage entries</CardDescription>
              </div>
              <Button variant="outline" size="sm">
                View All History
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentEntries.map(entry => {
                const entitlement = demoEntitlements.find(e => e.id === entry.entitlementId);
                const sourceIcon =
                  entry.source === 'telemetry'
                    ? '📡'
                    : entry.source === 'manual'
                    ? '✏️'
                    : '🌐';

                return (
                  <div
                    key={entry.id}
                    className="flex items-center justify-between p-4 rounded-lg border bg-white hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start gap-4 flex-1">
                      <div className="text-2xl">{sourceIcon}</div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-semibold">
                            {new Date(entry.date).toLocaleDateString('en-AU', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                            })}
                          </p>
                          <Badge variant="secondary" className="text-xs">
                            {entry.source}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600">{entry.purpose}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {entitlement?.category} - {entitlement?.valley}
                        </p>
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="text-2xl font-bold text-blue-600">
                        {entry.volumeML.toFixed(1)}
                        <span className="text-sm font-normal text-muted-foreground ml-1">ML</span>
                      </p>
                      {entry.meterReading && (
                        <p className="text-xs text-muted-foreground">
                          Reading: {entry.meterReading.toFixed(1)} ML
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Empty State for No Usage */}
            {recentEntries.length === 0 && (
              <div className="text-center py-12">
                <Droplet className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-lg font-semibold text-gray-900 mb-2">No usage recorded yet</p>
                <p className="text-sm text-gray-600 mb-4">
                  Start logging your water usage to track allocation compliance
                </p>
                <Button variant="default" onClick={() => setShowEntryForm(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Log First Entry
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Help Card */}
        <Card className="mt-6 bg-blue-50 border-blue-200">
          <CardHeader>
            <CardTitle className="text-lg">About Usage Tracking</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              <strong>Automatic Telemetry:</strong> If you have a telemetry-enabled water meter,
              readings are synced automatically every 15 minutes. This is the most accurate method.
            </p>
            <p>
              <strong>Manual Entry:</strong> For dates or meters without telemetry, you can manually
              log water usage. This is useful for historical records or backup meters.
            </p>
            <p>
              <strong>CSV Import:</strong> Bulk import usage data from spreadsheets or other
              systems. Download the template to ensure correct formatting.
            </p>
            <p>
              <strong>Compliance Reporting:</strong> Export usage reports for annual compliance
              audits, water trading records, or tax purposes.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
