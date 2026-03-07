import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LandUseZoningCard } from './LandUseZoningCard';
import { LocalProvisionsCard } from './LocalProvisionsCard';
import { HeritageProvisionsCard } from './HeritageProvisionsCard';
import { NotApplicableCard } from './NotApplicableCard';
import { PlanningConstraints, PlanningLayer } from '@/lib/nsw-planning-portal';
import { AuthorityColors } from '@/lib/design-tokens';
import { Building2, Ruler, AlertTriangle, Droplets, Flame, FlaskConical, ExternalLink, Plane, TreePine, Waves, MapPin, CheckCircle2, AlertCircle, XCircle } from 'lucide-react';
import { calculateGFA, anefStatusConfig, floodBlockTypeAnnotation, bushfireCategoryAnnotation } from '@/lib/see/propertyUtils';

interface LepControlsProps {
  propertyData?: any; // Keep for now - full PropertyData type would require extensive refactoring
  planningLayers: PlanningLayer[];
  constraints: PlanningConstraints;
  formerCouncil?: string;
  lotArea?: number;
}

export function LepControls({
  propertyData,
  planningLayers,
  constraints,
  formerCouncil,
  lotArea,
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
                {lotArea && (
                  <div className="text-sm font-semibold text-blue-700 mb-1">
                    = {calculateGFA(constraints.maxFsr, lotArea).toLocaleString()}m² GFA
                  </div>
                )}
                <div className="text-xs text-gray-500">
                  LEP Clause 4.4{lotArea ? ` · Lot area ${lotArea.toLocaleString()}m²` : ''}
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
        <CardContent className="p-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="h-4 w-4 text-blue-700" />
            <span className="text-sm font-semibold text-blue-900">Environmental Constraints</span>
            <Badge className="bg-blue-100 text-blue-800 text-xs ml-auto">LEP Part 5</Badge>
          </div>

          <div className="grid grid-cols-2 gap-1">
            {/* Flood Prone Land */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.floodProne ? 'bg-amber-50 border-amber-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <Droplets className={`h-3 w-3 flex-shrink-0 ${constraints?.floodProne ? 'text-amber-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Flood Prone</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.floodProne ? 'text-amber-800' : 'text-gray-400'}`}>
                {constraints?.floodProne ? (constraints.floodInfo?.blockType || 'Yes') : 'No'}
              </span>
            </div>

            {/* Bushfire Prone Land */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.bushfireProne ? 'bg-orange-50 border-orange-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <Flame className={`h-3 w-3 flex-shrink-0 ${constraints?.bushfireProne ? 'text-orange-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Bushfire Prone</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.bushfireProne ? 'text-orange-800' : 'text-gray-400'}`}>
                {constraints?.bushfireProne ? (constraints.bushfireCategory || 'Yes') : 'No'}
              </span>
            </div>

            {/* Acid Sulfate Soils */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.acidSulfateSoils ? 'bg-purple-50 border-purple-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <FlaskConical className={`h-3 w-3 flex-shrink-0 ${constraints?.acidSulfateSoils ? 'text-purple-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Acid Sulfate Soils</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.acidSulfateSoils ? 'text-purple-800' : 'text-gray-400'}`}>
                {constraints?.acidSulfateSoils ? `Class ${constraints.acidSulfateSoils}` : 'No'}
              </span>
            </div>

            {/* Aircraft Noise */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              propertyData?.anefData?.inAnefZone ? 'bg-sky-50 border-sky-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <Plane className={`h-3 w-3 flex-shrink-0 ${propertyData?.anefData?.inAnefZone ? 'text-sky-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Aircraft Noise</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${propertyData?.anefData?.inAnefZone ? 'text-sky-800' : 'text-gray-400'}`}>
                {propertyData?.anefData?.inAnefZone ? `ANEF ${propertyData.anefData.anefLevel}` : 'No'}
              </span>
            </div>

            {/* Mine Subsidence */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.mineSubsidence?.inDistrict ? 'bg-indigo-50 border-indigo-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <AlertTriangle className={`h-3 w-3 flex-shrink-0 ${constraints?.mineSubsidence?.inDistrict ? 'text-indigo-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Mine Subsidence</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.mineSubsidence?.inDistrict ? 'text-indigo-800' : 'text-gray-400'}`}>
                {constraints?.mineSubsidence?.inDistrict ? (constraints.mineSubsidence.districtName || 'Yes') : 'No'}
              </span>
            </div>

            {/* Landslide Risk */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.landslideRisk?.hasRisk ? 'bg-amber-50 border-amber-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <AlertTriangle className={`h-3 w-3 flex-shrink-0 ${constraints?.landslideRisk?.hasRisk ? 'text-amber-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Landslide Risk</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.landslideRisk?.hasRisk ? 'text-amber-800' : 'text-gray-400'}`}>
                {constraints?.landslideRisk?.hasRisk ? 'Yes' : 'No'}
              </span>
            </div>

            {/* Contaminated Land */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.contaminatedLand?.hasNotifiedSites ? 'bg-red-50 border-red-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <MapPin className={`h-3 w-3 flex-shrink-0 ${constraints?.contaminatedLand?.hasNotifiedSites ? 'text-red-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Contaminated Land</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.contaminatedLand?.hasNotifiedSites ? 'text-red-800' : 'text-gray-400'}`}>
                {constraints?.contaminatedLand?.hasNotifiedSites
                  ? `${constraints.contaminatedLand.nearestSite?.distance}m`
                  : 'No'}
              </span>
            </div>

            {/* Drinking Water Catchment */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.drinkingWaterCatchment?.inCatchment ? 'bg-blue-50 border-blue-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <Droplets className={`h-3 w-3 flex-shrink-0 ${constraints?.drinkingWaterCatchment?.inCatchment ? 'text-blue-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Drinking Water</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.drinkingWaterCatchment?.inCatchment ? 'text-blue-800' : 'text-gray-400'}`}>
                {constraints?.drinkingWaterCatchment?.inCatchment ? 'Yes' : 'No'}
              </span>
            </div>

            {/* Terrestrial Biodiversity */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.terrestrialBiodiversity?.inBiodiversityArea ? 'bg-green-50 border-green-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <TreePine className={`h-3 w-3 flex-shrink-0 ${constraints?.terrestrialBiodiversity?.inBiodiversityArea ? 'text-green-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Biodiversity</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.terrestrialBiodiversity?.inBiodiversityArea ? 'text-green-800' : 'text-gray-400'}`}>
                {constraints?.terrestrialBiodiversity?.inBiodiversityArea ? 'Yes' : 'No'}
              </span>
            </div>

            {/* Coastal Management */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.coastalEnvironment?.inCoastalArea && constraints.coastalEnvironment.zones?.length
                ? 'bg-cyan-50 border-cyan-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <Waves className={`h-3 w-3 flex-shrink-0 ${constraints?.coastalEnvironment?.inCoastalArea ? 'text-cyan-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Coastal</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.coastalEnvironment?.inCoastalArea && constraints.coastalEnvironment.zones?.length ? 'text-cyan-800' : 'text-gray-400'}`}>
                {constraints?.coastalEnvironment?.inCoastalArea && constraints.coastalEnvironment.zones?.length
                  ? `${constraints.coastalEnvironment.zones.length} zone${constraints.coastalEnvironment.zones.length > 1 ? 's' : ''}`
                  : 'No'}
              </span>
            </div>
          </div>

          {/* Flood detail */}
          {constraints?.floodProne && (
            <div className="mt-2 bg-amber-50 border border-amber-200 rounded p-2">
              <div className="flex items-start gap-1.5">
                <AlertCircle className="h-3.5 w-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-semibold text-amber-800">
                    {constraints.floodInfo?.blockType || 'Flood Prone Land'}
                    {constraints.floodInfo?.name ? ` — ${constraints.floodInfo.name}` : ''}
                  </span>
                  <p className="text-xs text-amber-700 mt-0.5">
                    {floodBlockTypeAnnotation(constraints.floodInfo?.blockType || '')}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Bushfire detail */}
          {constraints?.bushfireProne && constraints.bushfireCategory && (() => {
            const info = bushfireCategoryAnnotation(constraints.bushfireCategory);
            return (
              <div className="mt-2 bg-orange-50 border border-orange-200 rounded p-2">
                <div className="flex items-start gap-1.5">
                  <AlertCircle className="h-3.5 w-3.5 text-orange-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-orange-800">
                        {constraints.bushfireCategory}
                      </span>
                      {info.cdcBlocked && (
                        <span className="text-xs bg-red-100 text-red-700 border border-red-200 rounded px-1 py-0.5 font-semibold">
                          CDC not available
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-orange-700 mt-0.5">{info.annotation}</p>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* ANEF building acceptability table */}
          {propertyData?.anefData?.inAnefZone && propertyData.anefData.buildingAcceptability?.length > 0 && (
            <div className="mt-2 border border-sky-200 rounded overflow-hidden">
              <div className="bg-sky-50 px-2 py-1.5 flex items-center gap-1.5">
                <Plane className="h-3 w-3 text-sky-600" />
                <span className="text-xs font-semibold text-sky-800">
                  ANEF {propertyData.anefData.anefLevel} — Building Acceptability
                </span>
                {propertyData.anefData.airport?.name && (
                  <span className="text-xs text-sky-600 ml-auto">{propertyData.anefData.airport.name}</span>
                )}
              </div>
              <table className="w-full text-xs">
                <tbody>
                  {propertyData.anefData.buildingAcceptability.map((row: { buildingType: string; displayName: string; status: 'acceptable' | 'conditional' | 'unacceptable' }) => {
                    const cfg = anefStatusConfig(row.status);
                    const Icon = row.status === 'acceptable' ? CheckCircle2 : row.status === 'conditional' ? AlertCircle : XCircle;
                    return (
                      <tr key={row.buildingType} className="border-t border-sky-100">
                        <td className="px-2 py-1 text-gray-700">{row.displayName}</td>
                        <td className="px-2 py-1 text-right">
                          <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium ${cfg.badgeClass}`}>
                            <Icon className={`h-3 w-3 ${cfg.iconColor}`} />
                            {cfg.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="bg-sky-50 px-2 py-1 border-t border-sky-100">
                <p className="text-xs text-sky-600">AS 2021-2015 · SEPP (Transport Infrastructure) 2021</p>
              </div>
            </div>
          )}

          <div className="mt-2 pt-2 border-t border-blue-100">
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
