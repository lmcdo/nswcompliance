'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Book, Target } from 'lucide-react';
import CategorySection from './CategorySection';
import { AuthorityColors, SemanticColors } from '@/lib/design-tokens';

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

interface PartSectionProps {
  partName: string;
  partData: PartData;
  formerCouncil: string;
  defaultExpanded?: boolean;
  onViewPdf?: (url: string) => void;
}

/**
 * DCP authority color theming (teal for all councils)
 */
const getCouncilTheme = (council: string, partName: string) => {
  // All DCP provisions use teal authority color
  return {
    border: 'border-teal-200',
    bg: 'bg-teal-50',
    text: 'text-teal-900',
    icon: 'text-teal-600',
    objective: 'bg-amber-50 border-amber-200 text-amber-900'
  };
};

/**
 * PartSection: Displays a DCP Part with objectives and nested categories
 *
 * Features:
 * - Collapsible Part header with chevron
 * - Council-specific color theming
 * - Objectives shown in yellow box (when present)
 * - Nested CategorySection components
 * - Provision count badge
 */
const PartSection: React.FC<PartSectionProps> = ({
  partName,
  partData,
  formerCouncil,
  defaultExpanded = false,
  onViewPdf
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const theme = getCouncilTheme(formerCouncil, partName);

  const toggleExpanded = () => setExpanded(!expanded);

  // Sort categories by provision count (descending)
  const sortedCategories = Object.entries(partData.categories).sort(
    ([, a], [, b]) => b.length - a.length
  );

  return (
    <div className={`border rounded-lg overflow-hidden ${theme.border}`}>
      {/* Part Header */}
      <button
        onClick={toggleExpanded}
        className={`w-full px-4 py-3 flex items-center justify-between ${theme.bg} hover:opacity-80 transition-opacity`}
      >
        <div className="flex items-center gap-3">
          {/* Chevron Icon (12x12 for consistency) */}
          {expanded ? (
            <ChevronDown className={`w-12 h-12 ${theme.icon} flex-shrink-0`} />
          ) : (
            <ChevronRight className={`w-12 h-12 ${theme.icon} flex-shrink-0`} />
          )}

          {/* Book Icon */}
          <Book className={`w-5 h-5 ${theme.icon}`} />

          {/* Part Name */}
          <div className="flex flex-col items-start">
            <span className={`font-semibold ${theme.text}`}>
              {partData.part_number || 'General'}
            </span>
            <span className={`text-sm ${theme.text}`}>{partName}</span>
          </div>
        </div>

        {/* Provision Count Badge */}
        <div className={`px-3 py-1 rounded-full ${theme.bg} ${theme.text} text-sm font-medium border ${theme.border}`}>
          {partData.provision_count} provisions
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="p-4 bg-white space-y-4">
          {/* Objectives Section (if any) */}
          {partData.objectives.length > 0 && (
            <div className={`border rounded-lg p-4 ${theme.objective}`}>
              <div className="flex items-start gap-2">
                <Target className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-amber-900 mb-2">
                    {partData.objectives.length === 1 ? 'Objective' : 'Objectives'}
                  </h4>
                  <div className="space-y-2">
                    {partData.objectives.map((objective, idx) => (
                      <p key={idx} className="text-sm text-amber-800 leading-relaxed">
                        {objective}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Categories */}
          <div className="space-y-3">
            {sortedCategories.map(([category, requirements]) => (
              <CategorySection
                key={category}
                category={category}
                requirements={requirements}
                defaultExpanded={false}
                onViewPdf={onViewPdf}
              />
            ))}
          </div>

          {/* Empty State */}
          {sortedCategories.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No requirements in this Part
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PartSection;
