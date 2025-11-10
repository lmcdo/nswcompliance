/**
 * Entitlement Card Component
 * Displays individual water entitlement with allocation details
 */

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Droplet, TrendingUp, MapPin, FileText } from 'lucide-react';
import type { Entitlement } from '@/lib/demo-data';

interface EntitlementCardProps {
  entitlement: Entitlement;
  showActions?: boolean;
}

export function EntitlementCard({ entitlement, showActions = true }: EntitlementCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'compliant':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'danger':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getProgressColor = () => {
    if (entitlement.usedPct >= 90) return 'bg-red-500';
    if (entitlement.usedPct >= 70) return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  const getCategoryIcon = (category: string) => {
    if (category.includes('High Security')) return '🔒';
    if (category.includes('General Security')) return '💧';
    if (category.includes('Supplementary')) return '⚡';
    return '💧';
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className="text-3xl mt-1">{getCategoryIcon(entitlement.category)}</div>
            <div>
              <h3 className="font-bold text-xl mb-1">
                {entitlement.category}
              </h3>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <MapPin className="h-3 w-3" />
                <span>{entitlement.valley}</span>
                <span className="text-xs">•</span>
                <span>{entitlement.source}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                WAL: {entitlement.walNumber}
              </p>
            </div>
          </div>
          <Badge
            variant={
              entitlement.status === 'compliant'
                ? 'default'
                : entitlement.status === 'warning'
                ? 'secondary'
                : 'destructive'
            }
            className="text-sm px-3 py-1"
          >
            {entitlement.usedPct}% used
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Entitlement Volume</p>
            <p className="text-lg font-bold">{entitlement.volumeML.toLocaleString()} ML</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Allocation Percentage</p>
            <p className="text-lg font-bold">
              {entitlement.allocationPct}%
              {entitlement.category.includes('Supplementary') && entitlement.allocationPct === 0 && (
                <span className="text-sm font-normal text-muted-foreground ml-1">
                  (awaiting flow event)
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Allocation Breakdown */}
        {entitlement.allocationPct > 0 && (
          <>
            <div className="p-3 rounded-lg bg-gray-50 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Total Allocation</span>
                <span className="font-semibold">{entitlement.allocationML.toLocaleString()} ML</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Used to Date</span>
                <span className="font-semibold">{entitlement.usedML.toLocaleString()} ML</span>
              </div>
              <div className="h-px bg-gray-300 my-2" />
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Remaining</span>
                <span className="font-bold text-blue-600 text-base">
                  {entitlement.remainingML.toLocaleString()} ML
                </span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>0 ML</span>
                <span className="font-medium text-gray-900">{entitlement.usedPct}% used</span>
                <span>{entitlement.allocationML.toLocaleString()} ML</span>
              </div>
              <div className="relative">
                <Progress value={entitlement.usedPct} className="h-3" />
                <div
                  className={`absolute top-0 left-0 h-3 rounded-full transition-all ${getProgressColor()}`}
                  style={{ width: `${entitlement.usedPct}%` }}
                />
              </div>
            </div>
          </>
        )}

        {/* Supplementary Notice */}
        {entitlement.category.includes('Supplementary') && entitlement.allocationPct === 0 && (
          <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
            <p className="text-sm text-blue-900 font-medium mb-1">
              Awaiting Supplementary Flow Event
            </p>
            <p className="text-xs text-blue-700">
              You'll receive an alert when supplementary access is declared. Last event was 3 months
              ago (Oct 2024).
            </p>
          </div>
        )}

        {/* Status Message */}
        {entitlement.status === 'warning' && entitlement.usedPct > 70 && (
          <div className={`p-3 rounded-lg border ${getStatusColor(entitlement.status)}`}>
            <p className="text-sm font-medium mb-1">Approaching Limit</p>
            <p className="text-xs">
              You've used {entitlement.usedPct}% of your allocation. Consider reducing usage or
              purchasing additional water.
            </p>
          </div>
        )}

        {entitlement.status === 'danger' && (
          <div className={`p-3 rounded-lg border ${getStatusColor(entitlement.status)}`}>
            <p className="text-sm font-medium mb-1">Over Allocation</p>
            <p className="text-xs">
              You have exceeded your allocation. Contact WaterNSW immediately to avoid penalties.
            </p>
          </div>
        )}

        {/* Action Buttons */}
        {showActions && entitlement.allocationPct > 0 && (
          <div className="flex gap-2 pt-2">
            <Button variant="outline" size="sm" className="flex-1">
              <FileText className="mr-2 h-3 w-3" />
              View History
            </Button>
            <Button variant="outline" size="sm" className="flex-1">
              <TrendingUp className="mr-2 h-3 w-3" />
              Buy Water
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
