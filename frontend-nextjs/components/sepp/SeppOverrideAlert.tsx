'use client';

import { AlertTriangle, ChevronDown, ChevronUp, Home, Recycle, Building, FileText } from 'lucide-react';
import { useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface SeppProvision {
  id: string;
  name: string;
  icon: React.ReactNode;
  impact: 'high' | 'medium' | 'low';
  override: string;
  affects: string[];
  description: string;
}

interface SeppOverrideAlertProps {
  sepps: string[];
  propertyData: any;
}

export function SeppOverrideAlert({ sepps, propertyData }: SeppOverrideAlertProps) {
  const [expanded, setExpanded] = useState(false);

  // Map SEPP identifiers to detailed provisions
  const seppProvisions: SeppProvision[] = [];

  if (sepps.includes('SEPP_HOUSING_2021') || sepps.includes('SEPP_2021')) {
    seppProvisions.push({
      id: 'housing_2021',
      name: 'SEPP (Housing) 2021',
      icon: <Home className="h-5 w-5" />,
      impact: 'high',
      override: 'Bonus FSR +20%',
      affects: ['LEP Clause 4.4 - Floor Space Ratio'],
      description: 'Provides additional floor space ratio for affordable housing developments'
    });
  }

  if (sepps.includes('SEPP_SUSTAINABLE_BUILDINGS_2022') || sepps.includes('SEPP_2022')) {
    seppProvisions.push({
      id: 'sustainable_2022',
      name: 'SEPP (Sustainable Buildings) 2022',
      icon: <Recycle className="h-5 w-5" />,
      impact: 'medium',
      override: 'BASIX Water 40%',
      affects: ['DCP Water Management Standards'],
      description: 'Mandates water efficiency standards that override local DCP requirements'
    });
  }

  if (sepps.includes('SEPP_TRANSPORT_INFRASTRUCTURE_2021')) {
    seppProvisions.push({
      id: 'transport_2021',
      name: 'SEPP (Transport and Infrastructure) 2021',
      icon: <Building className="h-5 w-5" />,
      impact: 'medium',
      override: 'Development Standards',
      affects: ['Various LEP and DCP provisions'],
      description: 'May modify development standards for infrastructure-related developments'
    });
  }

  if (sepps.includes('SEPP_EXEMPT_COMPLYING_2008')) {
    seppProvisions.push({
      id: 'exempt_2008',
      name: 'SEPP (Exempt and Complying) 2008',
      icon: <FileText className="h-5 w-5" />,
      impact: 'low',
      override: 'Fast-track Approval',
      affects: ['Standard DA process'],
      description: 'Allows certain developments to proceed without full DA approval'
    });
  }

  if (seppProvisions.length === 0) {
    return null;
  }

  const highImpactCount = seppProvisions.filter(p => p.impact === 'high').length;
  const totalCount = seppProvisions.length;

  return (
    <div className="mb-6 animate-in fade-in slide-in-from-top-2 duration-500">
      {/* Main Alert Banner */}
      <Alert className="border-2 border-orange-500 bg-orange-50 shadow-lg">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3">
            <div className="mt-0.5">
              <div className="relative">
                <AlertTriangle className="h-6 w-6 text-orange-600 animate-pulse" />
                <div className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full animate-ping" />
              </div>
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-orange-900 mb-1">
                🚨 SEPP Override Alert: {totalCount} State Provision{totalCount > 1 ? 's' : ''} Apply
              </h3>
              <AlertDescription className="text-orange-800">
                {highImpactCount > 0 && (
                  <span className="font-semibold text-red-700">
                    ⚠️ {highImpactCount} High Impact Override{highImpactCount > 1 ? 's' : ''} detected.{' '}
                  </span>
                )}
                State Environmental Planning Policies override local planning controls.
              </AlertDescription>

              {/* Quick Summary Badges */}
              <div className="flex flex-wrap gap-2 mt-3">
                {seppProvisions.map((sepp) => (
                  <Badge
                    key={sepp.id}
                    variant="outline"
                    className={`
                      border-2 font-medium
                      ${sepp.impact === 'high' ? 'border-red-500 bg-red-50 text-red-800' :
                        sepp.impact === 'medium' ? 'border-orange-400 bg-orange-50 text-orange-700' :
                        'border-yellow-400 bg-yellow-50 text-yellow-700'}
                    `}
                  >
                    {sepp.icon}
                    <span className="ml-1">{sepp.override}</span>
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="text-orange-600 hover:text-orange-700 hover:bg-orange-100"
          >
            {expanded ? (
              <>Hide Details <ChevronUp className="ml-1 h-4 w-4" /></>
            ) : (
              <>Show Details <ChevronDown className="ml-1 h-4 w-4" /></>
            )}
          </Button>
        </div>
      </Alert>

      {/* Expanded Details */}
      {expanded && (
        <div className="mt-4 grid gap-4 animate-in slide-in-from-top-2 duration-300">
          {seppProvisions.map((sepp) => (
            <Card
              key={sepp.id}
              className={`
                border-2 shadow-md transition-all hover:shadow-lg
                ${sepp.impact === 'high' ? 'border-red-400 bg-red-50/50' :
                  sepp.impact === 'medium' ? 'border-orange-400 bg-orange-50/50' :
                  'border-yellow-400 bg-yellow-50/50'}
              `}
            >
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center justify-between text-lg">
                  <div className="flex items-center gap-2">
                    <div className={`
                      p-2 rounded-lg
                      ${sepp.impact === 'high' ? 'bg-red-100 text-red-600' :
                        sepp.impact === 'medium' ? 'bg-orange-100 text-orange-600' :
                        'bg-yellow-100 text-yellow-600'}
                    `}>
                      {sepp.icon}
                    </div>
                    <span className="font-bold">{sepp.name}</span>
                  </div>
                  <Badge
                    variant={sepp.impact === 'high' ? 'destructive' :
                            sepp.impact === 'medium' ? 'secondary' : 'outline'}
                  >
                    {sepp.impact.toUpperCase()} IMPACT
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-600 mb-1">Override Effect:</p>
                    <p className="text-base font-bold text-gray-900">{sepp.override}</p>
                  </div>

                  <div>
                    <p className="text-sm font-semibold text-gray-600 mb-1">Affects:</p>
                    <div className="flex flex-wrap gap-2">
                      {sepp.affects.map((affected, idx) => (
                        <Badge key={idx} variant="outline" className="bg-white">
                          {affected}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="text-sm font-semibold text-gray-600 mb-1">Description:</p>
                    <p className="text-sm text-gray-700">{sepp.description}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Statutory Hierarchy Explanation */}
          <Card className="border-gray-300 bg-gray-50/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Building className="h-5 w-5 text-gray-600" />
                Planning Hierarchy
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-orange-500 rounded" />
                  <span className="font-semibold">SEPP (State Level)</span>
                  <span className="text-gray-600">→ Overrides all lower levels</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-blue-500 rounded" />
                  <span className="font-semibold">LEP (Local Environmental Plan)</span>
                  <span className="text-gray-600">→ Primary constraints</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-500 rounded" />
                  <span className="font-semibold">DCP (Development Control Plan)</span>
                  <span className="text-gray-600">→ Design guidelines</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}