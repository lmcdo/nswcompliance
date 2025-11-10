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

import React, { useState } from 'react';
import { FileText, Book } from 'lucide-react';
import DARequirementsSection from './DARequirementsSection';
import PartSection from './PartSection';

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
  part_name?: string | null;
  part_number?: string | null;
  objective?: string | null;
  user_category?: string | null;
  section_type?: string | null;
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
}

/**
 * PartBasedDCPSection: Main component for Phase 1 Part-based display
 */
const PartBasedDCPSection: React.FC<PartBasedDCPSectionProps> = ({
  generalData,
  daRequirements,
  formerCouncil = 'INNER WEST',
  zone,
  developmentType
}) => {
  const byPart = generalData.by_part || {};
  const hasDaRequirements = daRequirements && daRequirements.count > 0;
  const hasParts = Object.keys(byPart).length > 0;

  // Sort parts by part_number
  const sortedParts = Object.entries(byPart).sort(([, a], [, b]) => {
    const aNum = a.part_number || 'ZZ'; // Sort null to end
    const bNum = b.part_number || 'ZZ';
    return aNum.localeCompare(bNum);
  });

  return (
    <div className="space-y-6">
      {/* DA Requirements Section (if any) */}
      {hasDaRequirements && (
        <DARequirementsSection
          requirements={daRequirements.requirements}
          defaultExpanded={true}
          zone={zone}
          developmentType={developmentType}
          formerCouncil={formerCouncil}
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
