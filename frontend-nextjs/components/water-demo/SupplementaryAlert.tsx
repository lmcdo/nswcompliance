/**
 * Supplementary Alert Component
 * Displays urgent supplementary water access alert with countdown timer
 */

'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, Clock, Droplet, ExternalLink, TrendingUp } from 'lucide-react';

interface SupplementaryAlertProps {
  title: string;
  message: string;
  expiresAt: string;
  entitlementML: number;
  actionUrl?: string;
}

export function SupplementaryAlert({
  title,
  message,
  expiresAt,
  entitlementML,
  actionUrl,
}: SupplementaryAlertProps) {
  const [timeRemaining, setTimeRemaining] = useState('');
  const [urgencyLevel, setUrgencyLevel] = useState<'high' | 'medium' | 'low'>('medium');

  useEffect(() => {
    const calculateTimeRemaining = () => {
      const now = new Date().getTime();
      const expiry = new Date(expiresAt).getTime();
      const diff = expiry - now;

      if (diff <= 0) {
        setTimeRemaining('Expired');
        return;
      }

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

      // Set urgency level
      if (hours < 6) {
        setUrgencyLevel('high');
      } else if (hours < 24) {
        setUrgencyLevel('medium');
      } else {
        setUrgencyLevel('low');
      }

      setTimeRemaining(`${hours}h ${minutes}m`);
    };

    calculateTimeRemaining();
    const interval = setInterval(calculateTimeRemaining, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [expiresAt]);

  const urgencyConfig = {
    high: {
      bgGradient: 'from-red-50 to-orange-50',
      border: 'border-red-300',
      iconBg: 'bg-red-100',
      iconColor: 'text-red-600',
      badgeColor: 'bg-red-600',
      pulse: true,
    },
    medium: {
      bgGradient: 'from-orange-50 to-yellow-50',
      border: 'border-orange-300',
      iconBg: 'bg-orange-100',
      iconColor: 'text-orange-600',
      badgeColor: 'bg-orange-600',
      pulse: false,
    },
    low: {
      bgGradient: 'from-yellow-50 to-amber-50',
      border: 'border-yellow-300',
      iconBg: 'bg-yellow-100',
      iconColor: 'text-yellow-600',
      badgeColor: 'bg-yellow-600',
      pulse: false,
    },
  };

  const config = urgencyConfig[urgencyLevel];

  return (
    <Card className={`${config.border} bg-gradient-to-r ${config.bgGradient}`}>
      <CardContent className="pt-6">
        <div className="flex items-start gap-4">
          {/* Icon */}
          <div className={`p-3 rounded-full ${config.iconBg} ${config.pulse ? 'animate-pulse' : ''}`}>
            <AlertCircle className={`h-6 w-6 ${config.iconColor}`} />
          </div>

          {/* Content */}
          <div className="flex-1">
            {/* Title & Timer */}
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-bold text-xl">
                {title}
              </h3>
              <Badge className={`${config.badgeColor} text-white`}>
                <Clock className="h-3 w-3 mr-1" />
                {timeRemaining}
              </Badge>
            </div>

            {/* Message */}
            <p className="text-gray-700 mb-4">{message}</p>

            {/* Details Grid */}
            <div className="grid grid-cols-2 gap-4 mb-4 p-4 bg-white/50 rounded-lg">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Your Entitlement</p>
                <p className="text-lg font-bold">
                  <Droplet className="inline h-4 w-4 mr-1 text-blue-600" />
                  {entitlementML} ML
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Window Closes</p>
                <p className="text-lg font-bold">
                  {new Date(expiresAt).toLocaleDateString('en-AU', {
                    month: 'short',
                    day: 'numeric',
                  })}{' '}
                  at{' '}
                  {new Date(expiresAt).toLocaleTimeString('en-AU', {
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </p>
              </div>
            </div>

            {/* Conditions */}
            <div className="mb-4 p-3 bg-white/70 rounded-lg">
              <p className="text-sm font-medium mb-2">Current Conditions:</p>
              <ul className="text-sm space-y-1 text-gray-700">
                <li>✓ Flow rate at Wagga Wagga weir: 15,000 ML/day</li>
                <li>✓ Environmental flows satisfied</li>
                <li>✓ Delivery may take 3-5 days</li>
              </ul>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              {actionUrl && (
                <Button variant="default" size="lg" className="flex-1" asChild>
                  <a href={actionUrl} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Order Water via WaterNSW
                  </a>
                </Button>
              )}
              <Button variant="outline" size="lg">
                <TrendingUp className="mr-2 h-4 w-4" />
                View History
              </Button>
            </div>

            {/* Historical Context */}
            <p className="text-xs text-gray-600 mt-3">
              📊 Historical: Last supplementary event was October 2024 (3 months ago). Average: 2-4
              events per year in Murrumbidgee.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
