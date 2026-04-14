'use client';

/**
 * PartBasedDCPSection - Phase 1 contextual presentation
 * Displays DCP provisions organized by Part structure with DA requirements separated
 *
 * Features:
 * - DA Requirements section (purple theme) at top
 * - Part-level grouping with objectives
 * - Categories nested within Parts
 * - Council-specific color theming
 * - Performance criteria shown inline as "Alternative Compliance"
 */

import React, { useState, useEffect, useMemo } from 'react';
import { FileText, Book, Info } from 'lucide-react';
import DARequirementsSection from './DARequirementsSection';
import PartSection from './PartSection';
import { canSubdivide, isSubdivisionRequirement, hasHeritage, isHeritageRequirement } from '@/lib/requirement-prioritization';

interface GeneralRequirement {
  id: number;
  category: string;
  subcategory?: string;
  requirement_text: string;
  verbatim_source_text?: string;
  value_numeric?: number;
  value_min?: number;
  value_max?: number;
  unit?: string;
  has_conditionals: boolean;
  conditional_text?: string;
  confidence: string;
  pdf_page?: number;
  pdf_page_image_url?: string;
  pdf_path?: string;
  part_name?: string;
  part_number?: string;
  objective?: string | null;
  user_category?: string | null;
  section_type?: string;
  priority_level?: number | null;
}

interface PartData {
  part_number: string | null;
  provision_count: number;
  objectives: string[];
  categories: Record<string, GeneralRequirement[]>;
}

interface PartBasedDCPSectionProps {
  generalData: {
    source: string;
    applicable_to: string;
    count: number;
    requirements_count: number;
    requirements: GeneralRequirement[];
    by_part?: Record<string, PartData>;
  };
  daRequirements?: {
    count: number;
    requirements: GeneralRequirement[];
  };
  formerCouncil?: string;
  zone: string;
  developmentType: string;
  lotArea?: number;  // For subdivision filtering (cadastre area in m²)
  heritage?: any;  // For heritage filtering
}

/**
 * PartBasedDCPSection: Main component for Phase 1 Part-based display
 */
const PartBasedDCPSection: React.FC<PartBasedDCPSectionProps> = ({
  generalData,
  daRequirements,
  formerCouncil = 'INNER WEST',
  zone,
  developmentType,
  lotArea,
  heritage
}) => {
  // Subdivision filter state
  const [showSubdivisionOverride, setShowSubdivisionOverride] = useState(false);
  const propertyCanSubdivide = canSubdivide(lotArea);

  // Heritage filter state
  const [showHeritageOverride, setShowHeritageOverride] = useState(false);
  const propertyHasHeritage = hasHeritage(heritage);

  // Count subdivision requirements
  const subdivisionCount = useMemo(() => {
    return generalData.requirements.filter(isSubdivisionRequirement).length;
  }, [generalData.requirements]);

  // Count heritage requirements
  const heritageCount = useMemo(() => {
    return generalData.requirements.filter(isHeritageRequirement).length;
  }, [generalData.requirements]);

  const subdivisionFiltered = !propertyCanSubdivide && !showSubdivisionOverride && subdivisionCount > 0;
  const heritageFiltered = !propertyHasHeritage && !showHeritageOverride && heritageCount > 0;

  // Debug logging
  useEffect(() => {
    console.log('[PartBased Smart Filters] Debug:', {
      lotArea,
      propertyCanSubdivide,
      heritage: propertyHasHeritage,
      totalRequirements: generalData.requirements.length,
      subdivisionCount,
      heritageCount
    });
  }, [lotArea, propertyCanSubdivide, propertyHasHeritage, generalData.requirements, subdivisionCount, heritageCount]);

  // Apply smart filters to requirements
  const filteredRequirements = useMemo(() => {
    let filtered = generalData.requirements;

    // Apply subdivision filter
    if (!showSubdivisionOverride && !propertyCanSubdivide) {
      filtered = filtered.filter(req => !isSubdivisionRequirement(req));
      console.log('[PartBased Smart Filters] Filtered out subdivision requirements:', {
        removed: subdivisionCount
      });
    }

    // Apply heritage filter
    if (!showHeritageOverride && !propertyHasHeritage) {
      const beforeHeritage = filtered.length;
      filtered = filtered.filter(req => !isHeritageRequirement(req));
      console.log('[PartBased Smart Filters] Filtered out heritage requirements:', {
        removed: beforeHeritage - filtered.length
      });
    }

    console.log('[PartBased Smart Filters] Final filtered count:', {
      before: generalData.requirements.length,
      after: filtered.length,
      totalRemoved: generalData.requirements.length - filtered.length
    });

    return filtered;
  }, [generalData.requirements, showSubdivisionOverride, propertyCanSubdivide, showHeritageOverride, propertyHasHeritage, subdivisionCount]);

  // Rebuild by_part structure with filtered requirements
  const filteredByPart = useMemo(() => {
    const byPart = generalData.by_part || {};
    const newByPart: Record<string, PartData> = {};

    for (const [partKey, partData] of Object.entries(byPart)) {
      const newCategories: Record<string, GeneralRequirement[]> = {};

      for (const [catKey, catReqs] of Object.entries(partData.categories)) {
        const filteredCatReqs = catReqs.filter(req =>
          filteredRequirements.some(fr => fr.id === req.id)
        );
        if (filteredCatReqs.length > 0) {
          newCategories[catKey] = filteredCatReqs;
        }
      }

      if (Object.keys(newCategories).length > 0) {
        newByPart[partKey] = {
          ...partData,
          categories: newCategories,
          provision_count: Object.values(newCategories).flat().length
        };
      }
    }

    return newByPart;
  }, [generalData.by_part, filteredRequirements]);

  const hasDaRequirements = daRequirements && daRequirements.count > 0;
  const hasParts = Object.keys(filteredByPart).length > 0;

  // Sort parts by part_number
  const sortedParts = Object.entries(filteredByPart).sort(([, a], [, b]) => {
    const aNum = a.part_number || 'ZZ'; // Sort null to end
    const bNum = b.part_number || 'ZZ';
    return aNum.localeCompare(bNum);
  });

  return (
    <div className="space-y-6">
      {/* Smart Filter Summary */}
      {(subdivisionFiltered || heritageFiltered) && (
        <div className="bg-blue-50 border-l-4 border-blue-500 p-3 text-sm">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-700 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-medium text-blue-900 mb-1">
                Smart Filter Active: {subdivisionFiltered && heritageFiltered ? `${subdivisionCount + heritageCount} requirements hidden` : subdivisionFiltered ? `${subdivisionCount} subdivision ${subdivisionCount === 1 ? 'requirement' : 'requirements'} hidden` : `${heritageCount} heritage ${heritageCount === 1 ? 'requirement' : 'requirements'} hidden`}
              </p>
              <div className="space-y-2">
                {subdivisionFiltered && (
                  <div className="flex items-center justify-between">
                    <p className="text-blue-800 text-xs">
                      • Subdivision: Property is {lotArea ? `${Math.round(lotArea)}m²` : 'unknown size'} - too small to subdivide (450m² minimum)
                    </p>
                    <button
                      onClick={() => setShowSubdivisionOverride(true)}
                      className="ml-2 text-xs text-blue-700 hover:text-blue-900 underline whitespace-nowrap"
                    >
                      Show anyway
                    </button>
                  </div>
                )}
                {heritageFiltered && (
                  <div className="flex items-center justify-between">
                    <p className="text-blue-800 text-xs">
                      • Heritage: Property not in Heritage Conservation Area
                    </p>
                    <button
                      onClick={() => setShowHeritageOverride(true)}
                      className="ml-2 text-xs text-blue-700 hover:text-blue-900 underline whitespace-nowrap"
                    >
                      Show anyway
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DA Requirements Section (if any) */}
      {hasDaRequirements && (
        <DARequirementsSection
          requirements={daRequirements.requirements as any[]}
          defaultExpanded={true}
          zone={zone}
          developmentType={developmentType}
          formerCouncil={formerCouncil}
          lotArea={lotArea}
          heritage={heritage}
          showSubdivisionOverride={showSubdivisionOverride}
          showHeritageOverride={showHeritageOverride}
        />
      )}

      {/* Design & Development Controls */}
      {hasParts ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Book className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold text-gray-900">
              Design & Development Controls
            </h3>
          </div>

          {sortedParts.map(([partName, partData]) => (
            <PartSection
              key={partName}
              partName={partName}
              partData={partData}
              formerCouncil={formerCouncil}
              defaultExpanded={false}
            />
          ))}
        </div>
      ) : (
        /* Fallback: No Part structure */
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            ⚠️ No Part-level structure available for this council. Showing requirements by category instead.
          </p>
        </div>
      )}

      {/* Empty State */}
      {!hasParts && !hasDaRequirements && (
        <div className="text-center py-12 text-gray-500">
          <FileText className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p>No DCP requirements found for this zone and development type</p>
        </div>
      )}
    </div>
  );
};

export default PartBasedDCPSection;
