'use client';

/**
 * State Level Controls Component
 * Displays SEPP, LEP, and ADG requirements in a unified view
 * Separated from DCP (council-level) provisions
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, Scale, Building2, Car } from 'lucide-react';
import { AuthorityColors } from '@/lib/design-tokens';
import { StructuredSeppRequirements } from './StructuredSeppRequirements';
import { LandUseZoningCard } from './LandUseZoningCard';
import { MinimumLotSizeCard } from './MinimumLotSizeCard';
import { ADGBuildingSeparationTable } from './ADGBuildingSeparationTable';
import TODParkingCalculator from '@/components/tod/TODParkingCalculator';

interface StateLevelControlsProps {
  propertyData: any;
  developmentType: string;
  buildingHeight?: number;
}

const APARTMENT_DEV_TYPES = [
  'multi_dwelling_housing',
  'residential_flat_building',
  'shop_top_housing',
  'boarding_house',
  'mixed_use'
];

export function StateLevelControls({
  propertyData,
  developmentType,
  buildingHeight
}: StateLevelControlsProps) {
  const [structuredRequirements, setStructuredRequirements] = useState<any[]>([]);
  const [loadingSepp, setLoadingSepp] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({
    sepp: false,
    lep: false,
    adg: false,
    tod: true // TOD collapsed by default
  });

  const isApartmentDevelopment = APARTMENT_DEV_TYPES.includes(developmentType);

  // Toggle section collapse
  const toggleSection = (section: string) => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Load structured SEPP requirements
  const loadStructuredRequirements = useCallback(async () => {
    if (!developmentType) return;

    setLoadingSepp(true);
    try {
      const response = await fetch('/api/sepp/structured-requirements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          seppId: 'sustainable_buildings_2022',
          developmentType: developmentType
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data.hasStructuredRequirements) {
          setStructuredRequirements(data.data.requirements);
        } else {
          setStructuredRequirements([]);
        }
      }
    } catch (error) {
      console.error('[StateLevelControls] Failed to fetch SEPP requirements:', error);
      setStructuredRequirements([]);
    } finally {
      setLoadingSepp(false);
    }
  }, [developmentType]);

  useEffect(() => {
    loadStructuredRequirements();
  }, [loadStructuredRequirements]);

  // Extract zone and lot size data from propertyData
  const zone = propertyData?.constraints?.zone;
  const zoneDescription = propertyData?.constraints?.zoneDescription;
  const lga = propertyData?.constraints?.lga || 'Inner West';

  // Get land zoning layer data
  const landZoningLayer = propertyData?.planningLayers?.find(
    (layer: any) => layer.layerName === 'Land Zoning Map'
  );
  const zoneResult = landZoningLayer?.results?.[0];

  // Get lot size layer data
  const lotSizeLayer = propertyData?.planningLayers?.find(
    (layer: any) => layer.layerName === 'Lot Size Map' || layer.layerName === 'Minimum Lot Size'
  );
  const lotSizeResult = lotSizeLayer?.results?.[0];
  const minimumLotSize = lotSizeResult?.['Minimum Lot Size'] || lotSizeResult?.['Lot Size'];

  if (!propertyData) {
    return (
      <div className="bg-white border rounded-lg p-8 text-center text-gray-500">
        Select a property to view State-level controls
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* SEPP Section */}
      <Card className={`${AuthorityColors.SEPP.border.replace('500', '200')} ${AuthorityColors.SEPP.bg}/30`}>
        <CardHeader
          className={`cursor-pointer ${AuthorityColors.SEPP.hover.replace('100', '100/50')} transition-colors`}
          onClick={() => toggleSection('sepp')}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {collapsedSections.sepp ? (
                <ChevronRight className={`h-5 w-5 ${AuthorityColors.SEPP.text.replace('700', '600')}`} />
              ) : (
                <ChevronDown className={`h-5 w-5 ${AuthorityColors.SEPP.text.replace('700', '600')}`} />
              )}
              <Scale className={`h-5 w-5 ${AuthorityColors.SEPP.text.replace('700', '600')}`} />
              <CardTitle className={`text-lg ${AuthorityColors.SEPP.text.replace('700', '900')}`}>SEPP Requirements</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={`${AuthorityColors.SEPP.bg.replace('50', '100')} ${AuthorityColors.SEPP.text.replace('700', '800')}`}>State Policy</Badge>
            </div>
          </div>
          <p className={`text-sm ${AuthorityColors.SEPP.text} mt-1 ml-7`}>
            State Environmental Planning Policies - Mandatory requirements
          </p>
        </CardHeader>
        {!collapsedSections.sepp && (
          <CardContent className="pt-0">
            {loadingSepp ? (
              <div className="animate-pulse space-y-2">
                <div className={`h-4 ${AuthorityColors.SEPP.bg.replace('50', '200')} rounded w-3/4`}></div>
                <div className={`h-4 ${AuthorityColors.SEPP.bg.replace('50', '200')} rounded w-1/2`}></div>
              </div>
            ) : structuredRequirements.length > 0 ? (
              <StructuredSeppRequirements
                requirements={structuredRequirements}
                compact
              />
            ) : (
              <p className="text-sm text-gray-500 italic">
                No structured SEPP requirements for this development type
              </p>
            )}
          </CardContent>
        )}
      </Card>

      {/* LEP Section */}
      <Card className={`${AuthorityColors.LEP.border.replace('500', '200')} ${AuthorityColors.LEP.bg}/30`}>
        <CardHeader
          className={`cursor-pointer ${AuthorityColors.LEP.hover.replace('100', '100/50')} transition-colors`}
          onClick={() => toggleSection('lep')}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {collapsedSections.lep ? (
                <ChevronRight className={`h-5 w-5 ${AuthorityColors.LEP.text.replace('700', '600')}`} />
              ) : (
                <ChevronDown className={`h-5 w-5 ${AuthorityColors.LEP.text.replace('700', '600')}`} />
              )}
              <Building2 className={`h-5 w-5 ${AuthorityColors.LEP.text.replace('700', '600')}`} />
              <CardTitle className={`text-lg ${AuthorityColors.LEP.text.replace('700', '900')}`}>LEP Controls</CardTitle>
            </div>
            <Badge className={`${AuthorityColors.LEP.bg.replace('50', '100')} ${AuthorityColors.LEP.text.replace('700', '800')}`}>Local Environmental Plan</Badge>
          </div>
          <p className={`text-sm ${AuthorityColors.LEP.text} mt-1 ml-7`}>
            Zoning, land use permissibility, and lot size requirements
          </p>
        </CardHeader>
        {!collapsedSections.lep && (
          <CardContent className="pt-0 space-y-4">
            {/* Land Use Zoning */}
            {zone && (
              <LandUseZoningCard
                zone={zone}
                zoneDescription={zoneDescription}
                lga={lga}
                legislationUrl={zoneResult?.['legislationUrl']}
                epiName={zoneResult?.['EPI Name']}
                amendment={zoneResult?.['Amendment']}
                legislativeClause={zoneResult?.['Legislative Clause']}
              />
            )}

            {/* Minimum Lot Size */}
            {minimumLotSize && (
              <MinimumLotSizeCard
                minimumSize={parseFloat(minimumLotSize)}
                unit={lotSizeResult?.['Units'] || 'm²'}
                epiName={lotSizeResult?.['EPI Name']}
                amendment={lotSizeResult?.['Amendment']}
                legislativeClause={lotSizeResult?.['Legislative Clause'] || 'Clause 4.1'}
              />
            )}

            {!zone && !minimumLotSize && (
              <p className="text-sm text-gray-500 italic">
                No LEP data available for this property
              </p>
            )}
          </CardContent>
        )}
      </Card>

      {/* ADG Section - Only for apartment developments */}
      {isApartmentDevelopment && buildingHeight && buildingHeight > 0 && (
        <Card className="border-pink-200 bg-pink-50/30">
          <CardHeader
            className="cursor-pointer hover:bg-pink-100/50 transition-colors"
            onClick={() => toggleSection('adg')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {collapsedSections.adg ? (
                  <ChevronRight className="h-5 w-5 text-pink-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-pink-600" />
                )}
                <Building2 className="h-5 w-5 text-pink-600" />
                <CardTitle className="text-lg text-pink-900">ADG Building Separation</CardTitle>
              </div>
              <Badge className="bg-pink-100 text-pink-800">SEPP (Housing) 2021</Badge>
            </div>
            <p className="text-sm text-pink-700 mt-1 ml-7">
              Apartment Design Guide - Statutory setback standards
            </p>
          </CardHeader>
          {!collapsedSections.adg && (
            <CardContent className="pt-0">
              <ADGBuildingSeparationTable
                buildingHeight={buildingHeight}
                developmentType={developmentType}
              />
            </CardContent>
          )}
        </Card>
      )}

      {/* TOD Parking Section - Only for apartment developments */}
      {isApartmentDevelopment && (
        <Card className="border-emerald-200 bg-emerald-50/30">
          <CardHeader
            className="cursor-pointer hover:bg-emerald-100/50 transition-colors"
            onClick={() => toggleSection('tod')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {collapsedSections.tod ? (
                  <ChevronRight className="h-5 w-5 text-emerald-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-emerald-600" />
                )}
                <Car className="h-5 w-5 text-emerald-600" />
                <CardTitle className="text-lg text-emerald-900">TOD Parking Calculator</CardTitle>
              </div>
              <Badge className="bg-emerald-100 text-emerald-800">Transit Oriented</Badge>
            </div>
            <p className="text-sm text-emerald-700 mt-1 ml-7">
              Calculate parking reductions based on transport proximity
            </p>
          </CardHeader>
          {!collapsedSections.tod && (
            <CardContent className="pt-0">
              <TODParkingCalculator
                developmentType={developmentType}
                zoneCode={zone}
                lga={lga}
              />
            </CardContent>
          )}
        </Card>
      )}

      {/* Info for non-apartment developments */}
      {!isApartmentDevelopment && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600">
          <p>
            <strong>Note:</strong> ADG Building Separation and TOD Parking Calculator are only
            applicable to multi-dwelling housing, residential flat buildings, and similar apartment
            developments.
          </p>
        </div>
      )}
    </div>
  );
}
