'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Shield, ExternalLink, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface HeritageProvisionsCardProps {
  heritage: boolean;
  heritageType?: string;
  heritageItemName?: string;
  heritageItemNumber?: string;
  heritageLegislativeClause?: string;
  heritageSignificance?: string;
  heritageLegislationUrl?: string;
}

interface ProvisionDetail {
  clauseNumber: string;
  clauseTitle: string;
  provisionText: string;
  pageNumber: number;
}

export function HeritageProvisionsCard({
  heritage,
  heritageType,
  heritageItemName,
  heritageItemNumber,
  heritageLegislativeClause,
  heritageSignificance,
  heritageLegislationUrl
}: HeritageProvisionsCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [provisionDetail, setProvisionDetail] = useState<ProvisionDetail | null>(null);
  const [loading, setLoading] = useState(false);

  if (!heritage) return null;

  // Determine if this is a Heritage Conservation Area or specific heritage item
  const isHCA = heritageType?.toLowerCase().includes('conservation area');
  const isStateHeritage = heritageSignificance?.toLowerCase() === 'state';

  // Extract clause number from legislative clause string (e.g., "Clause 6.20" -> "6.20")
  const clauseNumber = heritageLegislativeClause?.match(/\d+\.\d+/)?.[0];

  const toggleProvision = async () => {
    if (isExpanded) {
      setIsExpanded(false);
    } else {
      setIsExpanded(true);

      if (!provisionDetail && clauseNumber) {
        setLoading(true);

        try {
          const response = await fetch('/api/lep/provisions?clause=' + encodeURIComponent(clauseNumber));
          if (response.ok) {
            const data = await response.json();
            setProvisionDetail(data);
          }
        } catch (error) {
          console.error('Error fetching heritage provision:', error);
        } finally {
          setLoading(false);
        }
      }
    }
  };

  // Link to base LEP document - NSW legislation site doesn't support reliable clause anchors
  const clauseUrl = heritageLegislationUrl;

  const cardColor = isHCA ? 'border-blue-300' : isStateHeritage ? 'border-red-300' : 'border-blue-300';
  const bgColor = isHCA ? 'bg-blue-50/50' : isStateHeritage ? 'bg-red-50/50' : 'bg-blue-50/50';

  return (
    <Card className={'border-blue-300 bg-blue-50/50'}>
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-700" />
            <span className="text-blue-900">
              {isHCA ? 'Heritage Conservation Area' : 'Heritage Listed Property'}
            </span>
          </div>
          <Badge className={isStateHeritage ? 'bg-red-100 text-red-800 border-red-300 font-semibold' : 'bg-blue-100 text-blue-800 font-semibold'}>
            {heritageSignificance || 'Heritage'} Significance
          </Badge>
        </CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          {isHCA 
            ? 'Area-wide heritage controls under the Local Environmental Plan'
            : 'Specific heritage item protections under the Local Environmental Plan'
          }
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="border-l-4 border-blue-500 pl-4 py-2 bg-blue-50/50 rounded-r-md">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-sm text-blue-900">
                  {heritageItemName || (isHCA ? 'Heritage Conservation Area' : 'Heritage Item')}
                </h4>
                {clauseNumber && (
                  <button
                    onClick={toggleProvision}
                    className="text-blue-700 hover:text-blue-900 transition-colors"
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

              <div className="flex flex-wrap gap-2 mt-2">
                {heritageLegislativeClause && (
                  <Badge variant="outline" className="text-xs bg-blue-100 text-blue-900 border-blue-300">
                    {heritageLegislativeClause}
                  </Badge>
                )}
                {provisionDetail?.pageNumber && (
                  <Badge variant="outline" className="text-xs bg-white">
                    Page {provisionDetail.pageNumber}
                  </Badge>
                )}
                {heritageItemNumber && (
                  <Badge variant="outline" className="text-xs bg-white">
                    Item {heritageItemNumber}
                  </Badge>
                )}
                {heritageType && (
                  <Badge variant="outline" className="text-xs">
                    {heritageType}
                  </Badge>
                )}
              </div>

              {isExpanded && (
                <div className="mt-3 p-3 bg-white rounded-md border border-blue-200">
                  {loading ? (
                    <p className="text-sm text-muted-foreground">Loading provision text...</p>
                  ) : clauseNumber === '5.10' ? (
                    <div className="space-y-3">
                      <h5 className="font-semibold text-sm text-blue-900">
                        Clause 5.10 Heritage conservation
                      </h5>
                      <div className="text-sm text-gray-700 space-y-2">
                        <p>
                          This clause requires development consent for work that could affect the heritage significance of:
                        </p>
                        <ul className="list-disc ml-5 space-y-1">
                          <li>Heritage items listed in Schedule 5</li>
                          <li>Heritage conservation areas shown on the Heritage Map</li>
                          <li>Archaeological sites</li>
                          <li>Aboriginal objects or places of heritage significance</li>
                        </ul>
                        <p className="mt-2">
                          Before granting consent, the consent authority must consider the effect on heritage significance and may require a heritage management document.
                        </p>
                      </div>
                      <a
                        href="https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0399#sec.5.10"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-blue-700 hover:text-blue-900 hover:underline"
                      >
                        <ExternalLink className="h-3 w-3" />
                        View full clause on NSW Legislation
                      </a>
                    </div>
                  ) : provisionDetail && provisionDetail.provisionText && provisionDetail.provisionText.length > 100 ? (
                    <div className="space-y-2">
                      <h5 className="font-semibold text-sm text-blue-900">
                        {provisionDetail.clauseTitle}
                      </h5>
                      <div className="text-sm text-gray-700 whitespace-pre-wrap">
                        {provisionDetail.provisionText}
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
                  className="flex items-center gap-1 text-blue-700 hover:text-blue-900"
                >
                  <ExternalLink className="h-3 w-3" />
                  <span className="text-xs">View LEP</span>
                </a>
              </Button>
            )}
          </div>
        </div>

        <div className="mt-4 p-3 bg-amber-50 rounded-md border border-amber-200 flex gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900">
            <strong>Note:</strong> Development {isHCA ? 'within this Heritage Conservation Area' : 'on this heritage-listed property'} requires
            heritage impact assessment and may require additional consent pathways.
          </div>
        </div>

        {/* Link to DCP heritage controls */}
        {isHCA && (
          <a
            href="#dcp-hca-section"
            className="mt-3 flex items-center gap-2 text-sm text-blue-700 hover:text-blue-900 hover:underline transition-colors"
            onClick={(e) => {
              e.preventDefault();
              const element = document.getElementById('dcp-hca-section');
              if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }}
          >
            <span>79 DCP heritage controls apply</span>
            <span className="text-blue-500">→ View in DCP section</span>
          </a>
        )}
      </CardContent>
    </Card>
  );
}
