'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LocalProvision } from '@/lib/nsw-planning-portal';

interface LocalProvisionsCardProps {
  localProvisions: LocalProvision[];
}

interface ProvisionDetail {
  clauseNumber: string;
  clauseTitle: string;
  provisionText: string;
  pageNumber: number;
}

export function LocalProvisionsCard({ localProvisions }: LocalProvisionsCardProps) {
  const [expandedProvisions, setExpandedProvisions] = useState<Set<string>>(new Set());
  const [provisionDetails, setProvisionDetails] = useState<Record<string, ProvisionDetail>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const toggleProvision = async (provisionKey: string, clauseNumber: string | undefined) => {
    if (!clauseNumber) return;

    const isExpanded = expandedProvisions.has(provisionKey);

    if (isExpanded) {
      const newExpanded = new Set(expandedProvisions);
      newExpanded.delete(provisionKey);
      setExpandedProvisions(newExpanded);
    } else {
      const newExpanded = new Set(expandedProvisions);
      newExpanded.add(provisionKey);
      setExpandedProvisions(newExpanded);

      if (!provisionDetails[provisionKey]) {
        setLoading({ ...loading, [provisionKey]: true });

        try {
          const response = await fetch(`/api/lep/provisions?clause=${encodeURIComponent(clauseNumber)}`);
          if (response.ok) {
            const data = await response.json();
            setProvisionDetails({
              ...provisionDetails,
              [provisionKey]: data
            });
          }
        } catch (error) {
          console.error('Error fetching provision:', error);
        } finally {
          setLoading({ ...loading, [provisionKey]: false });
        }
      }
    }
  };

  return (
    <Card className="border-amber-200">
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <span>Local Provisions (LEP Part 6)</span>
          <Badge className="bg-amber-100 text-amber-800">
            {localProvisions.length} {localProvisions.length === 1 ? 'provision' : 'provisions'}
          </Badge>
        </CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          Additional local provisions from the Local Environmental Plan
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {localProvisions.map((provision) => {
          const uniqueKey = `${provision.title}-${provision.epiName || ''}-${provision.class || ''}`.replace(/\s+/g, '-');
          const isExpanded = expandedProvisions.has(uniqueKey);
          const detail = provisionDetails[uniqueKey];
          const isLoading = loading[uniqueKey];

          const clauseUrl = provision.legislationUrl && provision.clauseNumber
            ? `${provision.legislationUrl}#cl-${provision.clauseNumber.replace('.', '-')}`
            : provision.legislationUrl;

          return (
            <div key={uniqueKey} className="border-l-4 border-amber-500 pl-4 py-2 bg-amber-50/50 rounded-r-md">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-sm text-amber-900">
                      {provision.title}
                    </h4>
                    {provision.clauseNumber && (
                      <button
                        onClick={() => toggleProvision(uniqueKey, provision.clauseNumber)}
                        className="text-amber-700 hover:text-amber-900 transition-colors"
                        aria-label={isExpanded ? 'Collapse provision' : 'Expand provision'}
                      >
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </button>
                    )}
                  </div>
                  {provision.description && (
                    <p className="text-sm text-muted-foreground mt-1">
                      {provision.description}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2 mt-2">
                    {provision.clauseNumber && (
                      <Badge variant="outline" className="text-xs bg-amber-100 text-amber-900 border-amber-300">
                        Clause {provision.clauseNumber}
                      </Badge>
                    )}
                    {detail?.pageNumber && (
                      <Badge variant="outline" className="text-xs bg-white">
                        Page {detail.pageNumber}
                      </Badge>
                    )}
                    {provision.class && (
                      <Badge variant="outline" className="text-xs">
                        {provision.class}
                      </Badge>
                    )}
                    {provision.epiName && (
                      <Badge variant="outline" className="text-xs bg-white">
                        {provision.epiName}
                      </Badge>
                    )}
                  </div>

                  {isExpanded && (
                    <div className="mt-3 p-3 bg-white rounded-md border border-amber-200">
                      {isLoading ? (
                        <p className="text-sm text-muted-foreground">Loading provision text...</p>
                      ) : provision.mapType === 'Site-Specific' && provision.clauseNumber ? (
                        <div className="space-y-2">
                          <h5 className="font-semibold text-sm text-amber-900">
                            {provision.title}
                          </h5>
                          <p className="text-sm text-gray-700 mb-2">
                            View the full site-specific provision from Inner West LEP 2022:
                          </p>
                          <img 
                            src={`/pdf-pages/iwlep_site_specific_clause_${provision.clauseNumber.replace('.', '_')}_page_${provision.pageNumber}.png`}
                            alt={`Clause ${provision.clauseNumber} - Page ${provision.pageNumber}`}
                            className="w-full border border-amber-200 rounded"
                          />
                        </div>
                      ) : detail ? (
                        <div className="space-y-2">
                          <h5 className="font-semibold text-sm text-amber-900">
                            {detail.clauseTitle}
                          </h5>
                          <div className="text-sm text-gray-700 whitespace-pre-wrap">
                            {detail.provisionText}
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">Provision text not available</p>
                      )}
                    </div>
                  )}
                </div>
                {clauseUrl && (
                  <Button
                    variant="ghost"
                    size="sm"
                    asChild
                    className="shrink-0"
                  >
                    <a
                      href={clauseUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-amber-700 hover:text-amber-900"
                    >
                      <ExternalLink className="h-3 w-3" />
                      <span className="text-xs">View LEP</span>
                    </a>
                  </Button>
                )}
              </div>
            </div>
          );
        })}

        <div className="mt-4 p-3 bg-blue-50 rounded-md border border-blue-200">
          <p className="text-xs text-blue-800">
            <strong>Note:</strong> Local Provisions are Part 6 additional local provisions that may impose specific requirements. This includes Schedule 7 overlays (Special Entertainment Precincts, Heritage Conservation Areas) and site-specific provisions that apply to particular addresses.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
