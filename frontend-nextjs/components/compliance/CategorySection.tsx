'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PdfPageButton } from './PdfPageButton';

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

interface CategorySectionProps {
  category: string;
  requirements: GeneralRequirement[];
  defaultExpanded?: boolean;
  onViewPdf?: (url: string) => void;
}

// Category icons
const CategoryIcon: React.FC<{ category: string }> = ({ category }) => {
  const iconMap: Record<string, string> = {
    setback_front: '📏',
    setback_side: '📐',
    setback_rear: '📊',
    parking: '🅿️',
    landscaping: '🌳',
    building_height: '📈',
    building_form: '🏛️',
    character: '🎨',
    privacy: '👁️',
    solar_access: '☀️',
    open_space: '🌿',
    deep_soil: '🌱',
    fencing: '🚧',
    heritage_character: '🏛️',
    site_building_envelope: '📐',
    amenity_privacy: '👁️',
    environmental_sustainability: '🌱',
    documentation: '📄',
    other: '📋'
  };

  return <span className="mr-2">{iconMap[category] || '📋'}</span>;
};

// Format category names with proper capitalization
const formatCategoryName = (category: string): string => {
  const formatted = category.replace(/_/g, ' ');

  // Special cases that need specific capitalization
  const specialCases: Record<string, string> = {
    'da requirements': 'DA Requirements',
    'basix': 'BASIX',
    'sepp': 'SEPP',
    'lep': 'LEP',
    'dcp': 'DCP',
    'hca': 'HCA',
  };

  // Check if the full string matches a special case
  const lowerFormatted = formatted.toLowerCase();
  if (specialCases[lowerFormatted]) {
    return specialCases[lowerFormatted];
  }

  // Title case for each word
  return formatted
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

// Individual requirement item component (no PDF button - shown at group level)
const RequirementItem: React.FC<{
  requirement: GeneralRequirement;
  onViewPdf?: (url: string) => void;
}> = ({ requirement, onViewPdf }) => {
  const [expanded, setExpanded] = useState(false);
  const [showVerbatim, setShowVerbatim] = useState(false);

  const isCharacterProvision = requirement.confidence === 'character';

  // Source color based on confidence
  const sourceColor = isCharacterProvision
    ? 'border-l-purple-400'
    : requirement.confidence === 'high'
    ? 'border-l-green-500'
    : 'border-l-yellow-500';

  return (
    <>
      {isCharacterProvision ? (
        // Character provision (descriptive, not prescriptive)
        <div className="border-l-4 border-l-purple-400 bg-purple-50 p-3 mb-2 rounded">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-gray-600">
              {formatCategoryName(requirement.category)}
            </span>
            <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-300">
              Character Provision
            </Badge>
          </div>
          <p className="text-sm text-gray-800">{requirement.requirement_text}</p>
          <p className="text-xs text-gray-600 mt-2 italic">
            ℹ️ This describes typical character, not minimum requirements
          </p>
        </div>
      ) : (
        // Prescriptive requirement (high/low confidence)
        <div
          className={`border-l-4 ${sourceColor} p-3 mb-2 rounded cursor-pointer hover:shadow-sm transition-shadow`}
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium text-gray-600">
                  {formatCategoryName(requirement.category)}
                </span>
                {requirement.has_conditionals && (
                  <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700 border-yellow-300">
                    Conditional
                  </Badge>
                )}
                {requirement.section_type === 'performance_criteria' && (
                  <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-300">
                    Alternative Compliance
                  </Badge>
                )}
              </div>
              <p className="text-sm text-gray-800">{requirement.requirement_text}</p>
              {requirement.section_type === 'performance_criteria' && (
                <p className="text-xs text-blue-700 mt-1 italic">
                  💡 This is a performance-based alternative to the prescriptive controls above
                </p>
              )}

              {/* Verbatim Text Toggle - page number removed since group shows it */}
              {requirement.verbatim_source_text && requirement.verbatim_source_text !== requirement.requirement_text && (
                <div className="mt-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowVerbatim(!showVerbatim);
                    }}
                    className="text-xs text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-1"
                  >
                    {showVerbatim ? '▲ Hide' : '▼ View'} verbatim text
                  </button>
                  {showVerbatim && (
                    <div className="mt-2 p-3 bg-gray-100 border border-gray-300 rounded-lg">
                      <div className="text-xs font-medium text-gray-700 mb-1">📄 Exact text from PDF:</div>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                        {requirement.verbatim_source_text}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {expanded && requirement.has_conditionals && requirement.conditional_text && (
                <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
                  <strong>Condition:</strong> {requirement.conditional_text}
                </div>
              )}
            </div>
            <div className="ml-2 p-1.5 rounded-full hover:bg-gray-200 transition-colors">
              {expanded ? <ChevronDown className="w-5 h-5 text-gray-600" /> : <ChevronRight className="w-5 h-5 text-gray-600" />}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

// Group requirements by subcategory
interface SubcategoryGroup {
  subcategory: string | null;
  requirements: GeneralRequirement[];
  pdfPage?: number;
  pdfPageImageUrl?: string;
}

const groupBySubcategory = (requirements: GeneralRequirement[]): SubcategoryGroup[] => {
  const groups = new Map<string, SubcategoryGroup>();

  requirements.forEach(req => {
    const key = `${req.subcategory || 'NO_SUBCATEGORY'}_${req.pdf_page || 'NO_PAGE'}`;

    if (!groups.has(key)) {
      groups.set(key, {
        subcategory: req.subcategory || null,
        requirements: [],
        pdfPage: req.pdf_page,
        pdfPageImageUrl: req.pdf_page_image_url
      });
    }

    groups.get(key)!.requirements.push(req);
  });

  return Array.from(groups.values());
};

// Subcategory group component with single PDF button at bottom
const SubcategoryGroupComponent: React.FC<{
  group: SubcategoryGroup;
  onViewPdf?: (url: string) => void;
}> = ({ group, onViewPdf }) => {
  const [showingPdf, setShowingPdf] = useState(false);
  const hasPdfAccess = group.pdfPageImageUrl;

  return (
    <>
      <div className="mb-4">
        {/* Subcategory header if exists */}
        {group.subcategory && (
          <h5 className="font-medium text-gray-700 text-sm mb-2">{group.subcategory}</h5>
        )}

        {/* Requirements in this subcategory */}
        <div className="space-y-2">
          {group.requirements.map(req => (
            <RequirementItem
              key={req.id}
              requirement={req}
              onViewPdf={onViewPdf}
            />
          ))}
        </div>

        {/* Single PDF button for the group */}
        {hasPdfAccess && group.pdfPage && (
          <PdfPageButton
            pageNumber={group.pdfPage}
            pdfUrl={group.pdfPageImageUrl!}
            onClick={() => setShowingPdf(true)}
            variant="inline"
            className="mt-2"
          />
        )}
      </div>

      {/* PDF Viewer Modal */}
      {showingPdf && hasPdfAccess && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
          onClick={() => setShowingPdf(false)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-auto relative"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-white border-b p-4 flex items-center justify-between">
              <h3 className="font-semibold">{group.pdfPage ? `DCP Page ${group.pdfPage}` : 'DCP Source Document'}</h3>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowingPdf(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="p-4">
              <img
                src={group.pdfPageImageUrl}
                alt={group.pdfPage ? `PDF Page ${group.pdfPage}` : 'DCP Source Document'}
                className="w-full h-auto"
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
};

/**
 * CategorySection: Displays a category of requirements within a Part
 *
 * Features:
 * - Collapsible category header with chevron
 * - Category icon
 * - Requirement count
 * - Groups requirements by subcategory
 * - Single PDF button per subcategory group
 */
const CategorySection: React.FC<CategorySectionProps> = ({
  category,
  requirements,
  defaultExpanded = false,
  onViewPdf
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const subcategoryGroups = groupBySubcategory(requirements);

  return (
    <div className="border rounded-lg overflow-hidden">
      <div
        className="bg-gray-50 p-3 cursor-pointer hover:bg-gray-100 transition-colors flex items-center gap-2"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown className="w-4 h-4 text-gray-600 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-600 flex-shrink-0" />}
        <CategoryIcon category={category} />
        <div className="flex-1">
          <h4 className="font-semibold text-gray-900 text-sm">
            {formatCategoryName(category)}
          </h4>
          <p className="text-xs text-gray-600">
            {requirements.length} requirement{requirements.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {expanded && (
        <div className="p-3 bg-white">
          {subcategoryGroups.map((group, idx) => (
            <SubcategoryGroupComponent
              key={`${group.subcategory || 'none'}_${group.pdfPage || 'none'}_${idx}`}
              group={group}
              onViewPdf={onViewPdf}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default CategorySection;
