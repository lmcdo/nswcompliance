'use client';

/**
 * SEPP Overlay Indicator Component
 * Displays SEPP provisions as regulatory overlays, not primary constraints
 * SEPPs modify/override LEP/DCP provisions - UI reflects this hierarchy
 */

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ChevronDown, ChevronRight, AlertTriangle, Info } from 'lucide-react';
import type { ComplianceConstraint } from '@/lib/database/compliance-client';

interface SeppOverlayIndicatorProps {
  seppProvisions: ComplianceConstraint[];
  affectedConstraints?: string[]; // Which LEP/DCP constraints this SEPP modifies
  className?: string;
}

export function SeppOverlayIndicator({
  seppProvisions,
  affectedConstraints = [],
  className = ''
}: SeppOverlayIndicatorProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!seppProvisions || seppProvisions.length === 0) {
    return null;
  }

  const getSeppIcon = (seppName: string) => {
    if (seppName.includes('Housing')) return '🏠';
    if (seppName.includes('Sustainable')) return '♻️';
    if (seppName.includes('Transport')) return '🚇';
    if (seppName.includes('Biodiversity')) return '🌿';
    if (seppName.includes('Exempt')) return '⚡';
    return '📋';
  };

  const getSeppSeverity = (seppName: string) => {
    // Override provisions are more important than supplementary
    if (seppName.includes('Override') || seppName.includes('Exempt')) return 'high';
    if (seppName.includes('Sustainable') || seppName.includes('Housing')) return 'medium';
    return 'low';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'border-amber-500 bg-amber-50 text-amber-800';
      case 'medium': return 'border-amber-500 bg-amber-50 text-amber-800';
      case 'low': return 'border-blue-500 bg-blue-50 text-blue-800';
      default: return 'border-gray-500 bg-gray-50 text-gray-800';
    }
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* SEPP Summary Bar */}
      <div className="flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-lg">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          <div>
            <div className="font-medium text-amber-900">
              {seppProvisions.length} SEPP Provision{seppProvisions.length > 1 ? 's' : ''} Apply
            </div>
            <div className="text-sm text-amber-700">
              State Environmental Planning Policies override local controls
            </div>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-amber-700 hover:text-amber-900"
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          <span className="ml-1">Details</span>
        </Button>
      </div>

      {/* SEPP Badges (Always Visible) */}
      <div className="flex flex-wrap gap-2">
        {seppProvisions.map((sepp, index) => {
          const severity = getSeppSeverity(sepp.source.document);
          const seppName = sepp.source.document.replace('State Environmental Planning Policy', 'SEPP');

          return (
            <Badge
              key={index}
              variant="outline"
              className={`${getSeverityColor(severity)} text-xs font-medium px-2 py-1`}
            >
              <span className="mr-1">{getSeppIcon(sepp.source.document)}</span>
              {seppName}
            </Badge>
          );
        })}
      </div>

      {/* Override Alert */}
      {affectedConstraints.length > 0 && (
        <Alert className="border-amber-200 bg-amber-50">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          <AlertDescription className="text-amber-800">
            <strong>SEPP Override:</strong> These provisions may modify{' '}
            {affectedConstraints.join(', ')} requirements from LEP/DCP.
          </AlertDescription>
        </Alert>
      )}

      {/* Expanded SEPP Details */}
      {isExpanded && (
        <Card className="border-amber-200">
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium text-amber-900">
              <Info className="h-4 w-4" />
              SEPP Provisions Detail
            </div>

            {seppProvisions.map((sepp, index) => {
              const severity = getSeppSeverity(sepp.source.document);

              return (
                <div
                  key={index}
                  className={`p-3 rounded-lg border ${getSeverityColor(severity)}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">
                        {getSeppIcon(sepp.source.document)}
                      </span>
                      <div>
                        <div className="font-medium text-sm">
                          {sepp.source.clause}
                        </div>
                        <div className="text-xs opacity-75">
                          {sepp.source.document}
                        </div>
                      </div>
                    </div>
                    {severity === 'high' && (
                      <Badge variant="destructive" className="text-xs">
                        Override
                      </Badge>
                    )}
                  </div>

                  <div className="text-sm">
                    <strong>Requirement:</strong> {sepp.value} {sepp.unit || ''}
                  </div>

                  {sepp.provisions && sepp.provisions.length > 0 && (
                    <div className="mt-2 p-2 bg-white/50 rounded text-xs">
                      {sepp.provisions[0].provision_text?.substring(0, 200)}...
                    </div>
                  )}
                </div>
              );
            })}

            {/* Planning Note */}
            <div className="text-xs text-amber-700 bg-amber-100 p-2 rounded">
              <strong>Planning Note:</strong> SEPP provisions take precedence over Local Environmental Plan
              and Development Control Plan requirements. Consult the full SEPP text for complete requirements.
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}