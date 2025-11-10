/**
 * Water Rights MVP - Entitlements Page
 * Detailed breakdown of all water entitlements
 */

'use client';

import { EntitlementCard } from '@/components/water-demo/EntitlementCard';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import {
  Droplet,
  ArrowLeft,
  Plus,
  Download,
  TrendingUp,
  MapPin,
  Activity,
} from 'lucide-react';
import { demoEntitlements, totalAllocationSummary, demoFarmer } from '@/lib/demo-data';

export default function EntitlementsPage() {
  // Group entitlements by valley
  const entitlementsByValley = demoEntitlements.reduce((acc, entitlement) => {
    if (!acc[entitlement.valley]) {
      acc[entitlement.valley] = [];
    }
    acc[entitlement.valley].push(entitlement);
    return acc;
  }, {} as Record<string, typeof demoEntitlements>);

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
                <h1 className="text-2xl font-bold text-gray-900">My Water Entitlements</h1>
                <p className="text-sm text-gray-600">{demoFarmer.farmName}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" />
                Export Report
              </Button>
              <Button variant="default" size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add Entitlement
              </Button>
            </div>
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
                <Activity className="h-4 w-4 text-blue-600" />
                Total Entitlements
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{demoEntitlements.length}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Across {Object.keys(entitlementsByValley).length} valleys
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Droplet className="h-4 w-4 text-blue-600" />
                Total Allocation
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">
                {totalAllocationSummary.totalAllocationML.toLocaleString()}
                <span className="text-sm font-normal text-muted-foreground ml-1">ML</span>
              </p>
              <p className="text-xs text-muted-foreground mt-1">Current water year</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-blue-600" />
                Used to Date
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">
                {totalAllocationSummary.totalUsedML.toLocaleString()}
                <span className="text-sm font-normal text-muted-foreground ml-1">ML</span>
              </p>
              <Badge variant="secondary" className="mt-2">
                {totalAllocationSummary.overallUsedPct}% of allocation
              </Badge>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Droplet className="h-4 w-4 text-green-600" />
                Remaining
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-green-600">
                {totalAllocationSummary.totalRemainingML.toLocaleString()}
                <span className="text-sm font-normal text-muted-foreground ml-1">ML</span>
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {100 - totalAllocationSummary.overallUsedPct}% available
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Entitlements by Valley */}
        {Object.entries(entitlementsByValley).map(([valley, entitlements]) => (
          <div key={valley} className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <MapPin className="h-5 w-5 text-blue-600" />
              <h2 className="text-2xl font-bold">{valley} Valley</h2>
              <Badge variant="secondary">{entitlements.length} entitlements</Badge>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {entitlements.map(entitlement => (
                <EntitlementCard key={entitlement.id} entitlement={entitlement} />
              ))}
            </div>
          </div>
        ))}

        {/* Info Card */}
        <Card className="bg-blue-50 border-blue-200">
          <CardHeader>
            <CardTitle className="text-lg">About Water Entitlements</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              <strong>Water Access Licenses (WALs)</strong> specify your legal right to extract
              water from a specific water source.
            </p>
            <p>
              <strong>Allocation percentage</strong> is announced by NSW DPIE and determines how much
              water you can use from your entitlement each year. Allocations vary based on dam
              storage levels, rainfall, and environmental requirements.
            </p>
            <p>
              <strong>General Security</strong> typically has lower reliability (40-70% average) but
              costs less. <strong>High Security</strong> has higher reliability (95-100% average) but
              higher costs.
            </p>
            <p>
              <strong>Supplementary water</strong> is only available during high river flow events,
              typically after significant rainfall. These events are announced with short notice
              (24-72 hours).
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
