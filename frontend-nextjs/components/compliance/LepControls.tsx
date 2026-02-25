import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LandUseZoningCard } from './LandUseZoningCard';
import { LocalProvisionsCard } from './LocalProvisionsCard';
import { HeritageProvisionsCard } from './HeritageProvisionsCard';
import { NotApplicableCard } from './NotApplicableCard';
import { PlanningConstraints, PlanningLayer } from '@/lib/nsw-planning-portal';
import { AuthorityColors } from '@/lib/design-tokens';
import { Building2, Ruler, AlertTriangle, Droplets, Flame, FlaskConical, ExternalLink, Plane } from 'lucide-react';

interface LepControlsProps {
  propertyData?: any; // Keep for now - full PropertyData type would require extensive refactoring
  planningLayers: PlanningLayer[];
  constraints: PlanningConstraints;
  formerCouncil?: string;
}

export function LepControls({
  propertyData,
  planningLayers,
  constraints,
  formerCouncil
}: LepControlsProps) {
  const lepName = constraints?.lga 
    ? `${constraints.lga} Local Environmental Plan 2022` 
    : 'Local Environmental Plan';

  // Extract layer metadata for child cards
  const landZoningLayer = planningLayers?.find(
    (layer) => layer.layerName === 'Land Zoning Map'
  );
  const zoneResult = landZoningLayer?.results?.[0];

  return (
    <div className="space-y-6">
      <Card className="border-blue-200 bg-blue-50/30">
        <CardHeader>
          <CardTitle className="text-lg text-blue-900">
            Local Environmental Plan
          </CardTitle>
          <Badge className="bg-blue-100 text-blue-800 mt-2">
            {lepName}
          </Badge>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            The LEP sets the framework for how land can be used and developed in the {constraints?.lga || 'local'} area.
          </p>
        </CardContent>
      </Card>

      {/* Land Use Zoning Card */}
      {constraints?.zone && (
        <LandUseZoningCard
          zone={constraints.zone}
          zoneDescription={constraints.zoneDescription}
          lga={constraints.lga}
          legislationUrl={zoneResult?.['legislationUrl']}
          epiName={zoneResult?.['EPI Name']}
          amendment={zoneResult?.['Amendment']}
          legislativeClause={zoneResult?.['Legislative Clause']}
        />
      )}

      {/* Development Standards Card */}
      <Card className="border-blue-200 bg-blue-50/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-blue-700" />
            <CardTitle className="text-lg text-blue-900">
              Development Standards
            </CardTitle>
          </div>
          <Badge className="bg-blue-100 text-blue-800 mt-2">LEP Part 4</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-blue-700">
            Numerical controls that limit the size and height of development on this property.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Height of Buildings */}
            {constraints?.maxHeight && (
              <div className="bg-white border border-blue-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Building2 className="h-4 w-4 text-blue-600" />
                  <span className="text-xs font-medium text-blue-700">Maximum Height</span>
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {constraints.maxHeight}m
                </div>
                <div className="text-xs text-gray-500">
                  LEP Clause 4.3
                </div>
              </div>
            )}

            {/* Floor Space Ratio */}
            {constraints?.maxFsr && (
              <div className="bg-white border border-blue-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Ruler className="h-4 w-4 text-blue-600" />
                  <span className="text-xs font-medium text-blue-700">Floor Space Ratio</span>
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {constraints.maxFsr}:1
                </div>
                <div className="text-xs text-gray-500">
                  LEP Clause 4.4
                </div>
              </div>
            )}

            {/* Minimum Lot Size */}
            {constraints?.minLotSize && (
              <div className="bg-white border border-blue-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Ruler className="h-4 w-4 text-blue-600" />
                  <span className="text-xs font-medium text-blue-700">Minimum Lot Size</span>
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {constraints.minLotSize}m²
                </div>
                <div className="text-xs text-gray-500">
                  LEP Clause 4.1
                </div>
              </div>
            )}
          </div>

          {/* Link to legislation */}
          {zoneResult?.['legislationUrl'] && (
            <div className="pt-3 border-t border-blue-100">
              <a
                href={zoneResult['legislationUrl']}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline"
              >
                <ExternalLink className="h-3 w-3" />
                View full LEP Part 4 on NSW Legislation
              </a>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Environmental Constraints Card */}
      <Card className="border-blue-200 bg-blue-50/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-blue-700" />
            <CardTitle className="text-lg text-blue-900">
              Environmental Constraints
            </CardTitle>
          </div>
          <Badge className="bg-blue-100 text-blue-800 mt-2">LEP Part 5</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-blue-700">
            Environmental and natural hazard provisions that apply to this property.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Flood Prone Land */}
            <div className={`border rounded-lg p-3 ${
              constraints?.floodProne
                ? 'bg-amber-50 border-amber-200'
                : 'bg-white border-blue-100'
            }`}>
              <div className="flex items-center gap-2 mb-1">
                <Droplets className={`h-4 w-4 ${constraints?.floodProne ? 'text-amber-600' : 'text-gray-400'}`} />
                <span className="text-sm font-medium">Flood Prone Land</span>
              </div>
              <div className={`text-lg font-bold ${constraints?.floodProne ? 'text-amber-900' : 'text-gray-500'}`}>
                {constraints?.floodProne ? 'Yes' : 'No'}
              </div>
              {constraints?.floodProne && (
                <p className="text-xs text-amber-700 mt-1">
                  LEP Clause 5.21 - Additional controls apply
                </p>
              )}
            </div>

            {/* Bushfire Prone Land */}
            <div className={`border rounded-lg p-3 ${
              constraints?.bushfireProne
                ? 'bg-orange-50 border-orange-200'
                : 'bg-white border-blue-100'
            }`}>
              <div className="flex items-center gap-2 mb-1">
                <Flame className={`h-4 w-4 ${constraints?.bushfireProne ? 'text-orange-600' : 'text-gray-400'}`} />
                <span className="text-sm font-medium">Bushfire Prone Land</span>
              </div>
              <div className={`text-lg font-bold ${constraints?.bushfireProne ? 'text-orange-900' : 'text-gray-500'}`}>
                {constraints?.bushfireProne ? 'Yes' : 'No'}
              </div>
              {constraints?.bushfireProne && (
                <p className="text-xs text-orange-700 mt-1">
                  LEP Clause 5.17 - Bushfire protection measures required
                </p>
              )}
            </div>

            {/* Acid Sulfate Soils */}
            {constraints?.acidSulfateSoils && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <FlaskConical className="h-4 w-4 text-purple-600" />
                  <span className="text-sm font-medium">Acid Sulfate Soils</span>
                </div>
                <div className="text-lg font-bold text-purple-900">
                  Class {constraints.acidSulfateSoils}
                </div>
                <p className="text-xs text-purple-700 mt-1">
                  LEP Clause 6.1 - Acid sulfate soils management plan may be required
                </p>
              </div>
            )}

            {/* Aircraft Noise (ANEF) */}
            {propertyData?.anefData?.inAnefZone && (
              <div className="bg-sky-50 border border-sky-200 rounded-lg p-3 md:col-span-2">
                <div className="flex items-center gap-2 mb-2">
                  <Plane className="h-4 w-4 text-sky-700" />
                  <span className="text-sm font-semibold text-sky-900">Aircraft Noise Exposure Forecast (ANEF)</span>
                  <Badge className={`text-xs ${
                    propertyData.anefData.anefLevel && propertyData.anefData.anefLevel >= 25
                      ? 'bg-orange-100 text-orange-800 border-orange-300'
                      : 'bg-sky-100 text-sky-800 border-sky-300'
                  }`}>
                    ANEF {propertyData.anefData.anefLevel}
                  </Badge>
                </div>
                <div className="text-xs text-sky-800 space-y-1">
                  <p>
                    <span className="font-medium">{propertyData.anefData.airport?.name}</span>
                    {propertyData.anefData.airport?.version && (
                      <span className="text-sky-600 ml-1">({propertyData.anefData.airport.version})</span>
                    )}
                  </p>
                  {propertyData.anefData.buildingAcceptability && (
                    <div className="mt-2 pt-2 border-t border-sky-200">
                      <p className="font-medium mb-1">Building Acceptability (AS2021:2015):</p>
                      <div className="grid grid-cols-2 gap-1">
                        {propertyData.anefData.buildingAcceptability
                          .filter((b: any) => b.buildingType === 'house' || b.buildingType === 'commercial')
                          .map((b: any) => (
                            <div key={b.buildingType} className="flex items-center gap-1">
                              <span className={`w-2 h-2 rounded-full ${
                                b.status === 'acceptable' ? 'bg-green-500' :
                                b.status === 'conditional' ? 'bg-amber-500' : 'bg-red-500'
                              }`} />
                              <span className="truncate">{b.displayName.split(',')[0]}: {b.status}</span>
                            </div>
                          ))
                        }
                      </div>
                    </div>
                  )}
                  <p className="text-xs text-sky-700 mt-2 italic">
                    Aircraft noise controls apply - acoustic design requirements may be triggered
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Link to Planning Portal */}
          <div className="pt-3 border-t border-blue-100">
            <a
              href="https://www.planningportal.nsw.gov.au/property"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline"
            >
              <ExternalLink className="h-3 w-3" />
              View all environmental layers on NSW Planning Portal
            </a>
          </div>
        </CardContent>
      </Card>

      {/* Local Provisions Card */}
      {constraints?.localProvisions && constraints.localProvisions.length > 0 ? (
        <LocalProvisionsCard
          localProvisions={constraints.localProvisions}
        />
      ) : (
        <NotApplicableCard
          title="Additional Local Provisions"
          reason="No site-specific local provisions (LEP Part 6) or key site controls apply to this address."
          color="blue"
        />
      )}

      {/* Heritage Provisions Card */}
      {constraints?.heritage ? (
        <HeritageProvisionsCard
          heritage={constraints.heritage}
          heritageType={constraints.heritageType}
          heritageItemName={constraints.heritageItemName}
          heritageItemNumber={constraints.heritageItemNumber}
          heritageLegislativeClause={constraints.heritageLegislativeClause}
          heritageSignificance={constraints.heritageSignificance}
          heritageLegislationUrl={constraints.heritageLegislationUrl}
          formerCouncil={formerCouncil}
        />
      ) : (
        <NotApplicableCard
          title="Heritage Conservation"
          reason="This property is not in a Heritage Conservation Area and is not listed as a heritage item."
          color="blue"
        />
      )}
    </div>
  );
}
