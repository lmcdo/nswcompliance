import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LandUseZoningCard } from './LandUseZoningCard';
import { ConstraintArithmeticCard } from './ConstraintArithmeticCard';
import { LocalProvisionsCard } from './LocalProvisionsCard';
import { HeritageProvisionsCard } from './HeritageProvisionsCard';
import { NotApplicableCard } from './NotApplicableCard';
import { ServicingTile } from './ServicingTile';
import { PlanningConstraints, PlanningLayer } from '@/lib/nsw-planning-portal';
import { AuthorityColors } from '@/lib/design-tokens';
import { Building2, Ruler, AlertTriangle, Droplets, Flame, FlaskConical, ExternalLink, Plane, TreePine, Waves, MapPin, CheckCircle2, AlertCircle, XCircle, Anchor, BookOpen, LandPlot, FileText, Info } from 'lucide-react';
import { calculateGFA, anefStatusConfig, bushfireCategoryAnnotation } from '@/lib/see/propertyUtils';

interface StrataInfo {
  isStrata: boolean;
  source: string | null;
  strataUnit: string | null;
}

interface LepControlsProps {
  propertyData?: any; // Keep for now - full PropertyData type would require extensive refactoring
  planningLayers: PlanningLayer[];
  constraints: PlanningConstraints;
  formerCouncil?: string;
  lotArea?: number;
  strataInfo?: StrataInfo;
  developmentType?: string;
  /** Lot coordinates — feed the Sydney Water servicing lookup. */
  lat?: number | null;
  lng?: number | null;
}

export function LepControls({
  propertyData,
  planningLayers,
  constraints,
  formerCouncil,
  lotArea,
  strataInfo,
  developmentType,
  lat,
  lng,
}: LepControlsProps) {
  // Extract layer metadata for child cards
  const landZoningLayer = planningLayers?.find(
    (layer) => layer.layerName === 'Land Zoning Map'
  );
  const zoneResult = landZoningLayer?.results?.[0];

  // Use the actual LEP/EPI instrument name returned by the Planning Portal
  // (e.g. "Sydney Local Environmental Plan 2012"). Never fabricate a year:
  // fall back to the council name without a year when no EPI Name is available.
  const lepName = zoneResult?.['EPI Name']
    || (constraints?.lga ? `${constraints.lga} Local Environmental Plan` : 'Local Environmental Plan');

  return (
    <div className="space-y-6">
      {/* Data currency indicator */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
        <span className="font-medium text-gray-700">{lepName}</span>
        <span>·</span>
        <span>Sourced live — NSW Planning Portal</span>
      </div>

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
          zoneDescription={constraints.zoneDescription ?? undefined}
          lga={constraints.lga ?? undefined}
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

          {/* Strata notice — FSR/GFA and subdivision figures apply to the parent lot */}
          {strataInfo?.isStrata && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 flex items-start gap-2">
              <Info className="h-4 w-4 text-orange-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-orange-800">
                <span className="font-semibold">Strata unit — </span>
                Height, FSR, and lot area figures above apply to the parent lot, not the individual unit. GFA capacity shown is the whole-lot entitlement. Subdivision of a strata lot requires owners corporation resolution — Torrens-title subdivision is not applicable.
              </p>
            </div>
          )}

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

      {/* Constraint Arithmetic — development yield estimate */}
      {lotArea && lotArea > 0 && (constraints?.maxHeight || constraints?.maxFsr) && (
        <ConstraintArithmeticCard
          lotArea={lotArea}
          devType={developmentType || 'dwelling_house'}
          zone={constraints?.zone ?? undefined}
          formerCouncil={formerCouncil}
          lga={constraints?.lga ?? undefined}
          maxHeight={constraints?.maxHeight}
          maxFsr={constraints?.maxFsr}
          frontage={propertyData?.lotDimensions?.frontage ?? null}
          depth={propertyData?.lotDimensions?.depth ?? null}
        />
      )}

      {/* Environmental Constraints Card */}
      <Card className="border-blue-200 bg-blue-50/30">
        <CardContent className="p-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="h-4 w-4 text-blue-700" />
            <span className="text-sm font-semibold text-blue-900">Environmental Constraints</span>
            <Badge className="bg-blue-100 text-blue-800 text-xs ml-auto">LEP Part 5</Badge>
          </div>

          <div className="grid grid-cols-2 gap-1">
            {/* Flood Mapping — PostGIS spatial overlay */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.dcpFloodMap?.inFloodArea ? 'bg-amber-50 border-amber-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <Droplets className={`h-3 w-3 flex-shrink-0 ${constraints?.dcpFloodMap?.inFloodArea ? 'text-amber-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Flood Mapping</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.dcpFloodMap?.inFloodArea ? 'text-amber-800' : 'text-gray-400'}`}>
                {constraints?.dcpFloodMap?.inFloodArea ? (constraints.dcpFloodMap.classification || 'Yes') : 'No'}
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

            {/* Water/Sewer Servicing — Sydney Water GSP (self-fetches by lat/lng;
                renders nothing when coords or data are unavailable) */}
            <ServicingTile lat={lat} lng={lng} />

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

            {/* Additional Permitted Uses */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.additionalPermittedUses?.hasAPU ? 'bg-violet-50 border-violet-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <BookOpen className={`h-3 w-3 flex-shrink-0 ${constraints?.additionalPermittedUses?.hasAPU ? 'text-violet-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Additional Uses</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.additionalPermittedUses?.hasAPU ? 'text-violet-800' : 'text-gray-400'}`}>
                {constraints?.additionalPermittedUses?.hasAPU
                  ? `Sch ${constraints.additionalPermittedUses.schedules.join(', ')}`
                  : 'No'}
              </span>
            </div>

            {/* Foreshore Building Line */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.foreshoreBuildingLine?.hasLine ? 'bg-teal-50 border-teal-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <Anchor className={`h-3 w-3 flex-shrink-0 ${constraints?.foreshoreBuildingLine?.hasLine ? 'text-teal-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Foreshore Line</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.foreshoreBuildingLine?.hasLine ? 'text-teal-800' : 'text-gray-400'}`}>
                {constraints?.foreshoreBuildingLine?.hasLine ? 'Yes' : 'No'}
              </span>
            </div>

            {/* Land Reservation (Compulsory Acquisition) */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.landReservation?.hasReservation ? 'bg-red-50 border-red-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <LandPlot className={`h-3 w-3 flex-shrink-0 ${constraints?.landReservation?.hasReservation ? 'text-red-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Land Reservation</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.landReservation?.hasReservation ? 'text-red-800' : 'text-gray-400'}`}>
                {constraints?.landReservation?.hasReservation
                  ? (constraints.landReservation.purpose || 'Yes')
                  : 'No'}
              </span>
            </div>

            {/* Riparian Land */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.riparianLand?.inRiparianArea ? 'bg-teal-50 border-teal-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <Waves className={`h-3 w-3 flex-shrink-0 ${constraints?.riparianLand?.inRiparianArea ? 'text-teal-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Riparian Land</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.riparianLand?.inRiparianArea ? 'text-teal-800' : 'text-gray-400'}`}>
                {constraints?.riparianLand?.inRiparianArea ? (constraints.riparianLand.category || 'Yes') : 'No'}
              </span>
            </div>

            {/* Wetlands */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.wetlands?.inWetlandsArea ? 'bg-emerald-50 border-emerald-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <Droplets className={`h-3 w-3 flex-shrink-0 ${constraints?.wetlands?.inWetlandsArea ? 'text-emerald-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Wetlands</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.wetlands?.inWetlandsArea ? 'text-emerald-800' : 'text-gray-400'}`}>
                {constraints?.wetlands?.inWetlandsArea ? 'Yes' : 'No'}
              </span>
            </div>

            {/* Key Site */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.keySite?.isKeySite ? 'bg-yellow-50 border-yellow-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <MapPin className={`h-3 w-3 flex-shrink-0 ${constraints?.keySite?.isKeySite ? 'text-yellow-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Key Site</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.keySite?.isKeySite ? 'text-yellow-800' : 'text-gray-400'}`}>
                {constraints?.keySite?.isKeySite ? (constraints.keySite.clause || 'Yes') : 'No'}
              </span>
            </div>

            {/* Active Street Frontage */}
            <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${
              constraints?.activeStreetFrontage?.required ? 'bg-slate-50 border-slate-200' : 'bg-white border-gray-100'
            }`}>
              <div className="flex items-center gap-1.5 min-w-0">
                <Building2 className={`h-3 w-3 flex-shrink-0 ${constraints?.activeStreetFrontage?.required ? 'text-slate-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-700 truncate">Active Frontage</span>
              </div>
              <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${constraints?.activeStreetFrontage?.required ? 'text-slate-800' : 'text-gray-400'}`}>
                {constraints?.activeStreetFrontage?.required ? 'Required' : 'No'}
              </span>
            </div>

          </div>

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

          {/* X11: Coastal zone names */}
          {constraints?.coastalEnvironment?.inCoastalArea && (constraints.coastalEnvironment.zones?.length ?? 0) > 0 && (
            <div className="mt-2 bg-cyan-50 border border-cyan-200 rounded p-2">
              <div className="flex items-start gap-1.5">
                <Waves className="h-3.5 w-3.5 text-cyan-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-semibold text-cyan-800 block mb-1">
                    Coastal Management Areas (SEPP Resilience and Hazards 2021)
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {constraints.coastalEnvironment.zones!.map((zone: string) => (
                      <span key={zone} className="text-xs bg-cyan-100 text-cyan-800 border border-cyan-200 rounded px-1.5 py-0.5">
                        {zone}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* X12: Contaminated land detail */}
          {constraints?.contaminatedLand?.hasNotifiedSites && constraints.contaminatedLand.nearestSite && (
            <div className="mt-2 bg-red-50 border border-red-200 rounded p-2">
              <div className="flex items-start gap-1.5">
                <AlertCircle className="h-3.5 w-3.5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="w-full">
                  <span className="text-xs font-semibold text-red-800 block">
                    Notified Contaminated Site — {constraints.contaminatedLand.nearestSite.distance}m
                  </span>
                  {constraints.contaminatedLand.nearestSite.address && (
                    <p className="text-xs text-red-700 mt-0.5">
                      {constraints.contaminatedLand.nearestSite.name
                        ? `${constraints.contaminatedLand.nearestSite.name}, `
                        : ''}{constraints.contaminatedLand.nearestSite.address}
                    </p>
                  )}
                  {constraints.contaminatedLand.nearestSite.managementClass && (
                    <p className="text-xs text-red-700 mt-0.5">
                      Management Class: {constraints.contaminatedLand.nearestSite.managementClass}
                      {constraints.contaminatedLand.nearestSite.contaminationType
                        ? ` · ${constraints.contaminatedLand.nearestSite.contaminationType}`
                        : ''}
                    </p>
                  )}
                  <p className="text-xs text-red-600 mt-0.5">Contamination assessment may be required — SEPP (Resilience and Hazards) 2021 Chapter 7.</p>
                </div>
              </div>
            </div>
          )}

          {/* X13: Landslide risk class */}
          {constraints?.landslideRisk?.hasRisk && (
            <div className="mt-2 bg-amber-50 border border-amber-200 rounded p-2">
              <div className="flex items-start gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-semibold text-amber-800">
                    Landslide Risk
                    {(constraints.landslideRisk as any).layClass ? ` — ${(constraints.landslideRisk as any).layClass}` : ''}
                  </span>
                  <p className="text-xs text-amber-700 mt-0.5">
                    Geotechnical assessment required.
                    {(constraints.landslideRisk as any).epiName ? ` · ${(constraints.landslideRisk as any).epiName}` : ''}
                  </p>
                </div>
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
          lga={constraints.lga ?? undefined}
        />
      ) : (
        <NotApplicableCard
          title="Heritage Conservation"
          reason="This property is not in a Heritage Conservation Area and is not listed as a heritage item."
          color="blue"
        />
      )}

      {/* Planning Instruments Card (Land Application Map) */}
      {constraints?.landApplicationInstruments && constraints.landApplicationInstruments.length > 0 && (
        <Card className="border-blue-200 bg-blue-50/30">
          <CardContent className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-blue-700" />
              <span className="text-sm font-semibold text-blue-900">Planning Instruments</span>
              <Badge className="bg-blue-100 text-blue-800 text-xs ml-auto">Land Application Map</Badge>
            </div>
            <p className="text-xs text-blue-700 mb-2">
              All instruments whose maps apply to this property.
            </p>
            <div className="space-y-1">
              {constraints.landApplicationInstruments.map((instr, i) => (
                <div key={i} className="flex items-center justify-between rounded px-2 py-1 bg-white border border-blue-100">
                  <span className="text-xs text-gray-800">{instr.name}</span>
                  <span className="text-xs text-gray-400 ml-2 flex-shrink-0">{instr.type}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
