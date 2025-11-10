/**
 * Usage History Chart Component
 * Displays monthly water usage as a bar chart
 */

'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BarChart3, TrendingUp } from 'lucide-react';

interface UsageDataPoint {
  month: string;
  year: number;
  totalML: number;
  avgDailyML: number;
}

interface UsageHistoryChartProps {
  data: UsageDataPoint[];
  title?: string;
}

export function UsageHistoryChart({ data, title = 'Monthly Water Usage' }: UsageHistoryChartProps) {
  const maxUsage = Math.max(...data.map(d => d.totalML));
  const totalUsage = data.reduce((sum, d) => sum + d.totalML, 0);
  const avgMonthlyUsage = Math.round(totalUsage / data.length);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-blue-600" />
              {title}
            </CardTitle>
            <CardDescription>Water Year 2024-25 (Jul - Dec)</CardDescription>
          </div>
          <Badge variant="secondary">
            <TrendingUp className="h-3 w-3 mr-1" />
            {avgMonthlyUsage} ML/month avg
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {/* Chart */}
        <div className="space-y-4">
          <div className="flex items-end justify-between h-64 gap-2">
            {data.map((point, idx) => {
              const heightPct = (point.totalML / maxUsage) * 100;
              const isCurrentMonth = idx === data.length - 1;

              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2">
                  {/* Bar */}
                  <div className="w-full flex flex-col justify-end h-full">
                    <div
                      className={`w-full rounded-t-lg transition-all hover:opacity-80 cursor-pointer ${
                        isCurrentMonth
                          ? 'bg-gradient-to-t from-blue-600 to-blue-400'
                          : 'bg-gradient-to-t from-blue-500 to-blue-300'
                      }`}
                      style={{ height: `${heightPct}%` }}
                      title={`${point.month} ${point.year}: ${point.totalML} ML`}
                    >
                      <div className="flex items-start justify-center pt-2">
                        <span className="text-xs font-semibold text-white">
                          {point.totalML}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Label */}
                  <div className="text-center">
                    <p className={`text-xs ${isCurrentMonth ? 'font-bold' : 'font-medium'}`}>
                      {point.month}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {point.avgDailyML.toFixed(1)}/day
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="grid grid-cols-3 gap-4 pt-4 border-t">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Total Usage</p>
              <p className="text-lg font-bold">{totalUsage} ML</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Average/Month</p>
              <p className="text-lg font-bold">{avgMonthlyUsage} ML</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Peak Month</p>
              <p className="text-lg font-bold">
                {data.reduce((max, d) => (d.totalML > max.totalML ? d : max)).month}
                {' '}
                ({maxUsage} ML)
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
