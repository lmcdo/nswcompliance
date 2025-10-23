'use client';

/**
 * Week 3: Categorized Requirements Display Component
 * Shows LLM-categorized precinct requirements grouped by category
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, ExternalLink, CheckCircle, AlertTriangle } from 'lucide-react';

interface CategorizedRequirement {
  id: number;
  category: string;
  subcategory?: string;
  requirement_text: string;
  value_numeric?: number;
  value_min?: number;
  value_max?: number;
  unit?: string;
  confidence: 'high' | 'medium' | 'low';
  has_conditionals: boolean;
  conditional_text?: string;
  validated: boolean;
  source_provision_ids: number[];
  source_document_ids: string[];
}

interface CategoryGroup {
  category: string;
  display_name: string;
  requirements: CategorizedRequirement[];
  total_count: number;
  high_confidence_count: number;
  validated_count: number;
}

interface CategorizedRequirementsCardProps {
  categories: CategoryGroup[];
  precinctName?: string;
  onViewSource?: (provisionIds: number[], documentIds: string[]) => void;
  className?: string;
}

export function CategorizedRequirementsCard({
  categories,
  precinctName,
  onViewSource,
  className = ''
}: CategorizedRequirementsCardProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(categories.slice(0, 3).map(c => c.category)) // Expand first 3 by default
  );

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const getConfidenceBadge = (confidence: 'high' | 'medium' | 'low') => {
    const variants = {
      high: 'default',
      medium: 'secondary',
      low: 'outline'
    };

    const colors = {
      high: 'bg-green-100 text-green-800 border-green-200',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      low: 'bg-gray-100 text-gray-800 border-gray-200'
    };

    return (
      <Badge className={`text-xs ${colors[confidence]}`}>
        {confidence.toUpperCase()}
      </Badge>
    );
  };

  const formatValue = (req: CategorizedRequirement) => {
    if (req.value_min && req.value_max) {
      return `${req.value_min}-${req.value_max} ${req.unit || ''}`;
    } else if (req.value_numeric) {
      return `${req.value_numeric} ${req.unit || ''}`;
    }
    return null;
  };

  if (!categories || categories.length === 0) {
    return null;
  }

  const totalRequirements = categories.reduce((sum, cat) => sum + cat.total_count, 0);
  const totalHighConfidence = categories.reduce((sum, cat) => sum + cat.high_confidence_count, 0);
  const highConfidencePercent = Math.round((totalHighConfidence / totalRequirements) * 100);

  return (
    <Card className={`${className} border-purple-200 bg-purple-50/30`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <span className="text-purple-700">📍 Precinct Requirements</span>
            </CardTitle>
            {precinctName && (
              <p className="text-sm text-gray-600 mt-1">{precinctName}</p>
            )}
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-gray-700">
              {totalRequirements} Requirements
            </div>
            <div className="text-xs text-gray-500">
              {highConfidencePercent}% High Confidence
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {categories.map(category => {
          const isExpanded = expandedCategories.has(category.category);
          const confidencePercent = Math.round(
            (category.high_confidence_count / category.total_count) * 100
          );

          return (
            <div key={category.category} className="border border-purple-100 rounded-lg overflow-hidden bg-white">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category.category)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-purple-50/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-purple-600" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-purple-600" />
                  )}
                  <div className="text-left">
                    <div className="font-medium text-gray-900">
                      {category.display_name}
                    </div>
                    <div className="text-xs text-gray-500">
                      {category.total_count} requirement{category.total_count !== 1 ? 's' : ''}
                      {' · '}
                      {confidencePercent}% high confidence
                    </div>
                  </div>
                </div>
                {category.validated_count > 0 && (
                  <Badge className="bg-blue-100 text-blue-800 text-xs">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    {category.validated_count} Validated
                  </Badge>
                )}
              </button>

              {/* Category Requirements */}
              {isExpanded && (
                <div className="border-t border-purple-100 divide-y divide-purple-50">
                  {category.requirements.map((req, idx) => (
                    <div key={req.id} className="px-4 py-3 hover:bg-purple-50/30 transition-colors">
                      {/* Requirement Header */}
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex-1">
                          <p className="text-sm text-gray-900 leading-relaxed">
                            {req.requirement_text}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {getConfidenceBadge(req.confidence)}
                          {req.validated && (
                            <Badge className="bg-blue-100 text-blue-800 text-xs">
                              <CheckCircle className="w-3 h-3" />
                            </Badge>
                          )}
                        </div>
                      </div>

                      {/* Value Display */}
                      {formatValue(req) && (
                        <div className="mb-2 inline-block">
                          <Badge className="bg-purple-100 text-purple-800 text-sm font-mono">
                            {formatValue(req)}
                          </Badge>
                        </div>
                      )}

                      {/* Conditional Warning */}
                      {req.has_conditionals && (
                        <div className="flex items-start gap-2 mb-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
                          <AlertTriangle className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="font-medium text-yellow-900">Contains Conditions</div>
                            {req.conditional_text && (
                              <div className="text-yellow-700 mt-1">{req.conditional_text}</div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Source Link */}
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <div>
                          Source: {req.source_provision_ids.length} provision{req.source_provision_ids.length !== 1 ? 's' : ''}
                        </div>
                        {onViewSource && (
                          <button
                            onClick={() => onViewSource(req.source_provision_ids, req.source_document_ids)}
                            className="flex items-center gap-1 text-purple-600 hover:text-purple-700 hover:underline"
                          >
                            View Source
                            <ExternalLink className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {/* Help Text */}
        <div className="mt-4 p-3 bg-purple-50 border border-purple-100 rounded-lg text-xs text-gray-600">
          <div className="font-medium text-gray-900 mb-1">About these requirements</div>
          <p>
            These requirements are specific to the {precinctName || 'precinct'} and supplement the base DCP requirements.
            They have been extracted and categorized using AI. High confidence requirements have been validated for accuracy.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
