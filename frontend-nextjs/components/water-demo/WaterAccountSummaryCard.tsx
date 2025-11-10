/**
 * Water Account Summary Card
 * Displays farmer's total allocation, usage, and remaining water
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Droplet, TrendingUp, Calendar, AlertCircle } from 'lucide-react';

interface WaterAccountSummaryProps {
  totalAllocationML: number;
  usedML: number;
  remainingML: number;
  usedPct: number;
  status: 'compliant' | 'warning' | 'danger';
  lastUpdated: string;
  nextAnnouncementDate?: string;
}

export function WaterAccountSummaryCard({
  totalAllocationML,
  usedML,
  remainingML,
  usedPct,
  status,
  lastUpdated,
  nextAnnouncementDate,
}: WaterAccountSummaryProps) {
  const statusConfig = {
    compliant: {
      badge: '✅ Compliant',
      variant: 'default' as const,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    warning: {
      badge: '⚠️ Near Limit',
      variant: 'secondary' as const,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
    },
    danger: {
      badge: '❌ Over Limit',
      variant: 'destructive' as const,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    },
  };

  const config = statusConfig[status];

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;
    return date.toLocaleDateString('en-AU', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const getProgressColor = () => {
    if (usedPct >= 90) return 'bg-red-500';
    if (usedPct >= 70) return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Droplet className="h-5 w-5 text-blue-600" />
            <CardTitle>Water Account Summary</CardTitle>
          </div>
          <Badge variant={config.variant}>{config.badge}</Badge>
        </div>
        <CardDescription>Updated: {formatDate(lastUpdated)}</CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Main Statistics */}
        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Total Allocation</p>
            <p className="text-2xl font-bold">{totalAllocationML.toLocaleString()} ML</p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Used to Date</p>
            <p className="text-2xl font-bold">
              {usedML.toLocaleString()} ML
              <span className="text-sm font-normal text-muted-foreground ml-2">({usedPct}%)</span>
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Remaining</p>
            <p className={`text-2xl font-bold ${config.color}`}>
              {remainingML.toLocaleString()} ML
              <span className="text-sm font-normal text-muted-foreground ml-2">
                ({100 - usedPct}%)
              </span>
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Usage Progress</span>
            <span className="font-medium">{usedPct}% used</span>
          </div>
          <div className="relative">
            <Progress value={usedPct} className="h-3" />
            <div
              className={`absolute top-0 left-0 h-3 rounded-full transition-all ${getProgressColor()}`}
              style={{ width: `${usedPct}%` }}
            />
          </div>
        </div>

        {/* Next Announcement */}
        {nextAnnouncementDate && (
          <div className={`flex items-start gap-3 p-3 rounded-lg ${config.bgColor}`}>
            <Calendar className="h-5 w-5 mt-0.5 text-blue-600" />
            <div>
              <p className="text-sm font-medium">Next Allocation Announcement</p>
              <p className="text-sm text-muted-foreground">
                {new Date(nextAnnouncementDate).toLocaleDateString('en-AU', {
                  weekday: 'long',
                  month: 'long',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </p>
            </div>
          </div>
        )}

        {/* Warning Message */}
        {status === 'warning' && (
          <div className="flex items-start gap-3 p-3 rounded-lg bg-yellow-50 border border-yellow-200">
            <AlertCircle className="h-5 w-5 mt-0.5 text-yellow-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-yellow-900">Approaching Allocation Limit</p>
              <p className="text-sm text-yellow-700">
                You've used {usedPct}% of your allocation. Consider monitoring usage closely or
                purchasing additional water.
              </p>
            </div>
          </div>
        )}

        {status === 'danger' && (
          <div className="flex items-start gap-3 p-3 rounded-lg bg-red-50 border border-red-200">
            <AlertCircle className="h-5 w-5 mt-0.5 text-red-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-900">Over Allocation Limit</p>
              <p className="text-sm text-red-700">
                You have exceeded your water allocation. Contact WaterNSW immediately to avoid
                penalties up to $264,000.
              </p>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="flex gap-3 pt-2">
          <Button variant="default" className="flex-1">
            <TrendingUp className="mr-2 h-4 w-4" />
            View Entitlements
          </Button>
          <Button variant="outline" className="flex-1">
            <Droplet className="mr-2 h-4 w-4" />
            Log Water Use
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
