'use client';

/**
 * Structured SEPP Requirements Component
 * Displays manually curated, actionable compliance requirements
 * 100% reliable - no AI interpretation
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface RequirementItem {
  [key: string]: string;
}

interface RequirementCategory {
  name: string;
  reference: string;
  requirements: RequirementItem[];
}

interface RequirementData {
  title: string;
  description?: string;
  categories: RequirementCategory[];
}

interface StructuredRequirement {
  id: number;
  seppId: string;
  seppName: string;
  schedule: string;
  scheduleName: string;
  section: string | null;
  sectionName: string | null;
  developmentTypeCategory: string;
  requirementData: RequirementData;
  sourceProvisionId: number | null;
}

interface StructuredSeppRequirementsProps {
  requirements: StructuredRequirement[];
  onViewFullText?: (provisionId: number) => void;
  compact?: boolean;
}

export function StructuredSeppRequirements({
  requirements,
  onViewFullText,
  compact = false
}: StructuredSeppRequirementsProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [showFullLegalText, setShowFullLegalText] = useState(false);

  if (requirements.length === 0) {
    return null;
  }

  // Toggle category expansion
  const toggleCategory = (categoryKey: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(categoryKey)) {
        next.delete(categoryKey);
      } else {
        next.add(categoryKey);
      }
      return next;
    });
  };

  // Render a single requirement item as bullet point
  const renderRequirementItem = (item: RequirementItem, index: number) => {
    // Each item is a key-value pair (e.g. { "fixture": "Toilets", "standard": "max 4L/flush" })
    const entries = Object.entries(item);

    if (entries.length === 1) {
      // Single property - simple bullet
      const [key, value] = entries[0];
      return (
        <li key={index} className="flex items-start gap-2 text-sm">
          <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
          <span>{value}</span>
        </li>
      );
    } else {
      // Multiple properties - format as "key: value"
      return (
        <li key={index} className="flex items-start gap-2 text-sm">
          <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
          <div>
            {entries.map(([key, value], i) => (
              <div key={i}>
                {i > 0 && <span className="mx-2 text-gray-400">|</span>}
                <span className="font-medium">{key}:</span>{' '}
                <span>{value}</span>
              </div>
            ))}
          </div>
        </li>
      );
    }
  };

  return (
    <div className="space-y-4">
      {requirements.map((req, reqIndex) => {
        const { requirementData, seppName, schedule, scheduleName, sourceProvisionId } = req;

        return (
          <Card key={reqIndex} className="border-purple-200 bg-purple-50/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold text-purple-900">
                {requirementData.title}
              </CardTitle>
              {requirementData.description && (
                <p className="text-xs text-gray-700 mt-1">
                  {requirementData.description}
                </p>
              )}
              <div className="text-xs text-gray-600 mt-1">
                {seppName} - Schedule {schedule}: {scheduleName}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Requirement Categories */}
              {requirementData.categories.map((category, catIndex) => {
                const categoryKey = `${reqIndex}-${catIndex}`;
                const isExpanded = expandedCategories.has(categoryKey);

                return (
                  <div key={catIndex} className="border-l-2 border-purple-300 pl-3">
                    {/* Category Header (Collapsible) */}
                    <button
                      onClick={() => toggleCategory(categoryKey)}
                      className="flex items-center gap-2 w-full text-left hover:bg-purple-100 rounded px-2 py-1 transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-purple-600" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-purple-600" />
                      )}
                      <div className="flex-1">
                        <div className="font-medium text-sm text-gray-900">
                          {category.name}
                        </div>
                        <div className="text-xs text-gray-500">
                          {category.reference}
                        </div>
                      </div>
                      <div className="text-xs text-purple-700 bg-purple-100 px-2 py-0.5 rounded">
                        {category.requirements.length} {category.requirements.length === 1 ? 'requirement' : 'requirements'}
                      </div>
                    </button>

                    {/* Category Requirements (Collapsible) */}
                    {isExpanded && (
                      <ul className="mt-2 space-y-2 ml-6">
                        {category.requirements.map((item, itemIndex) =>
                          renderRequirementItem(item, itemIndex)
                        )}
                      </ul>
                    )}
                  </div>
                );
              })}

              {/* View Full Legal Text Link */}
              {sourceProvisionId && onViewFullText && (
                <div className="pt-3 border-t border-purple-200">
                  <button
                    onClick={() => onViewFullText(sourceProvisionId)}
                    className="text-sm text-purple-700 hover:text-purple-900 hover:underline flex items-center gap-1"
                  >
                    <span>View full legal text</span>
                    <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              )}

              {/* How to Use This Section */}
              {!compact && (
                <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs">
                  <div className="font-semibold text-blue-900 mb-1">
                    💡 How to Use This Section
                  </div>
                  <ul className="space-y-1 text-blue-800">
                    <li>• Click category headers to expand/collapse requirements</li>
                    <li>• Each ✓ represents a specific compliance requirement</li>
                    <li>• All requirements must be met for SEPP compliance</li>
                    <li>• Click "View full legal text" for exact legislative wording</li>
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
