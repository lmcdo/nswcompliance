'use client';

/**
 * Structured SEPP Requirements Component
 * Displays manually curated, actionable compliance requirements
 * 100% reliable - no AI interpretation
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle2, FileImage } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { getPdfImageUrl } from '@/lib/pdf-image-url';
import { AuthorityColors, SemanticColors } from '@/lib/design-tokens';

/**
 * Fix common UTF-8 encoding artifacts (mojibake)
 */
function sanitizeText(text: string | undefined | null): string {
  if (!text) return '';
  return text
    // Em-dash
    .replace(/â€"/g, '—')
    .replace(/â€"}/g, '—')
    // Quotes
    .replace(/â€˜/g, "'")
    .replace(/â€™/g, "'")
    .replace(/â€œ/g, '"')
    .replace(/â€\u009D/g, '"')
    // Symbols
    .replace(/â˜…/g, '★')  // star
    .replace(/Â²/g, '²')   // superscript 2
    .replace(/Â°/g, '°')   // degree
    .replace(/Â·/g, '·')   // middle dot
    .replace(/â€¢/g, '•')  // bullet
    .replace(/â€¦/g, '…')  // ellipsis
    // Accented chars
    .replace(/Ã©/g, 'é')
    .replace(/Ã¨/g, 'è')
    // Currency/special
    .replace(/Â£/g, '£')
    .replace(/â‚¬/g, '€')
    .trim();
}

interface RequirementItem {
  [key: string]: string | boolean | object | undefined;
  legal_text?: string;
  legal_citation?: string;
  resource?: {
    label: string;
    url: string;
  };
}

interface RequirementCategory {
  name: string;
  reference: string;
  requirements: RequirementItem[];
  legal_citation?: string;
}

interface RequirementData {
  title: string;
  description?: string;
  categories: RequirementCategory[];
  pdf_references?: Array<{page: number; section: string; description: string; url: string}>;
  feasibility_note?: {
    heading: string;
    content: string;
    resources: Array<{
      label: string;
      url: string;
      description: string;
    }>;
  };
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
  pdfPageImageUrl: string | null;
  pdfPage: number | null;
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
  // Auto-expand first category by default for better visibility
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['0-0']) // Auto-expand first category
  );
  const [expandedFeasibility, setExpandedFeasibility] = useState<Set<string>>(new Set());
  const [showFullLegalText, setShowFullLegalText] = useState(false);
  const [viewingPdfImage, setViewingPdfImage] = useState<string | null>(null);

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
  const renderRequirementItem = (item: RequirementItem, index: number, categoryLegalCitation?: string) => {
    // Extract special fields separately
    const { legal_text, legal_citation, resource, ...displayProps } = item;
    const entries = Object.entries(displayProps);

    return (
      <li key={index} className="flex items-start gap-2 text-sm mb-3">
        <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          {/* Display properties */}
          {entries.length === 1 ? (
            <span>{sanitizeText(entries[0][1]?.toString())}</span>
          ) : (
            <div>
              {entries.map(([key, value], i) => (
                <div key={i} className="inline">
                  {i > 0 && <span className="mx-2 text-gray-400">|</span>}
                  <span className="font-medium">{sanitizeText(key)}:</span>{' '}
                  <span>{sanitizeText(value?.toString())}</span>
                </div>
              ))}
            </div>
          )}

          {/* Show legal text if available */}
          {legal_text && (
            <div className="mt-1 text-xs text-gray-600 italic bg-gray-50 border-l-2 border-gray-300 pl-2 py-1">
              "{sanitizeText(legal_text)}"
            </div>
          )}

          {/* Show inline resource link if available */}
          {resource && (
            <div className="mt-1">
              <a
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:text-blue-800 underline inline-flex items-center gap-1"
              >
                🔗 {resource.label}
              </a>
            </div>
          )}

          {/* Show citation (item-specific or category-level) */}
          {(legal_citation || categoryLegalCitation) && (
            <div className="mt-1 text-xs text-purple-700">
              📎 {sanitizeText(legal_citation || categoryLegalCitation)}
            </div>
          )}
        </div>
      </li>
    );
  };

  return (
    <div className="space-y-4">
      {requirements.map((req, reqIndex) => {
        const { requirementData, seppName, schedule, scheduleName, sourceProvisionId, pdfPageImageUrl, pdfPage } = req;

        // Skip requirements with invalid data structure
        if (!requirementData || !requirementData.categories || !Array.isArray(requirementData.categories)) {
          console.warn('[StructuredSeppRequirements] Skipping requirement with invalid data:', req.id || reqIndex);
          return null;
        }

        return (
          <Card key={reqIndex} className="border-purple-200 bg-purple-50/30">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-base font-semibold text-purple-900">
                  {sanitizeText(requirementData?.title)}
                </CardTitle>
                {/* PDF Page Links */}
                {pdfPageImageUrl && (
                  <button
                    onClick={() => setViewingPdfImage(getPdfImageUrl(pdfPageImageUrl))}
                    className="p-1 rounded hover:bg-purple-100 transition-colors flex-shrink-0"
                    title={`View PDF page ${pdfPage || ''}`}
                  >
                    <FileImage className="w-5 h-5 text-purple-500 hover:text-purple-700" />
                  </button>
                )}
                {/* Multiple PDF references (for contamination, etc.) */}
                {requirementData?.pdf_references && requirementData.pdf_references.length > 0 && (
                  <div className="flex gap-1">
                    {requirementData.pdf_references.map((ref: any, refIndex: number) => (
                      <button
                        key={refIndex}
                        onClick={() => setViewingPdfImage(ref.url)}
                        className="p-1 rounded hover:bg-purple-100 transition-colors flex-shrink-0"
                        title={ref.description}
                      >
                        <FileImage className="w-4 h-4 text-purple-500 hover:text-purple-700" />
                        <span className="sr-only">p{ref.page}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {requirementData?.description && (
                <p className="text-xs text-gray-700 mt-1">
                  {sanitizeText(requirementData?.description)}
                </p>
              )}
              <div className="text-xs text-gray-600 mt-1">
                {seppName} - Schedule {schedule}: {scheduleName}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Requirement Categories */}
              {requirementData?.categories?.map((category, catIndex) => {
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
                          {sanitizeText(category.name)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {sanitizeText(category.reference)}
                        </div>
                      </div>
                      <div className="text-xs text-purple-700 bg-purple-100 px-2 py-0.5 rounded">
                        {category.requirements.length} {category.requirements.length === 1 ? 'requirement' : 'requirements'}
                      </div>
                    </button>

                    {/* Category Requirements (Collapsible) */}
                    {isExpanded && (
                      <div>
                        {/* Show category legal citation */}
                        {category.legal_citation && (
                          <div className="mt-2 ml-6 text-xs text-purple-700 bg-purple-100 border border-purple-200 rounded px-2 py-1">
                            📎 {sanitizeText(category.legal_citation)}
                          </div>
                        )}
                        <ul className="mt-2 space-y-2 ml-6">
                          {category.requirements.map((item, itemIndex) =>
                            renderRequirementItem(item, itemIndex, category.legal_citation)
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}


              {/* Feasibility Note - Collapsible, Unobtrusive */}
              {requirementData?.feasibility_note && (
                <div className="mt-4 border-t border-gray-200 pt-3">
                  <button
                    onClick={() => {
                      const key = `feasibility-${reqIndex}`;
                      setExpandedFeasibility(prev => {
                        const next = new Set(prev);
                        if (next.has(key)) {
                          next.delete(key);
                        } else {
                          next.add(key);
                        }
                        return next;
                      });
                    }}
                    className="flex items-center gap-2 text-xs text-gray-600 hover:text-gray-800 transition-colors"
                  >
                    {expandedFeasibility.has(`feasibility-${reqIndex}`) ? (
                      <ChevronDown className="w-3 h-3" />
                    ) : (
                      <ChevronRight className="w-3 h-3" />
                    )}
                    <span className="font-medium">{requirementData.feasibility_note.heading}</span>
                  </button>
                  
                  {expandedFeasibility.has(`feasibility-${reqIndex}`) && (
                    <div className="mt-2 ml-5 text-xs text-gray-700 space-y-2">
                      <p className="leading-relaxed">{requirementData.feasibility_note.content}</p>
                      <div className="space-y-1 pt-1">
                        {requirementData.feasibility_note.resources.map((resource, idx) => (
                          <div key={idx}>
                            <a
                              href={resource.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:text-blue-800 underline inline-flex items-center gap-1"
                              title={resource.description}
                            >
                              🔗 {resource.label}
                            </a>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* How to Use This Section */}
              {!compact && (
                <div className="mt-4 bg-purple-100 border border-purple-200 rounded-lg p-3 text-xs">
                  <div className="font-semibold text-purple-900 mb-1">
                    💡 How to Use This Section
                  </div>
                  <ul className="space-y-1 text-purple-800">
                    <li>• Click category headers to expand/collapse requirements</li>
                    <li>• Each ✓ represents a specific compliance requirement</li>
                    <li>• All requirements must be met for SEPP compliance</li>
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}

      {/* PDF Image Modal */}
      <PdfImageModal
        isOpen={!!viewingPdfImage}
        imageUrl={viewingPdfImage}
        onClose={() => setViewingPdfImage(null)}
        title="SEPP Requirement"
      />
    </div>
  );
}
