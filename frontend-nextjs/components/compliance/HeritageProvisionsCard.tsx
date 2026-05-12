'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Shield, ExternalLink, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SemanticColors } from '@/lib/design-tokens';

interface HeritageProvisionsCardProps {
  heritage: boolean;
  heritageType?: string;
  heritageItemName?: string;
  heritageItemNumber?: string;
  heritageLegislativeClause?: string;
  heritageSignificance?: string;
  heritageLegislationUrl?: string;
  formerCouncil?: string;
  lga?: string;
}

/** Council-specific DCP heritage chapter references */
const COUNCIL_DCP_INFO: Record<string, { year: string; chapter: string; hcaNote: string }> = {
  Ashfield: {
    year: '2016',
    chapter: 'Chapter E1',
    hcaNote: 'Area Character Statements describe the character of individual Heritage Conservation Areas within the Ashfield DCP.'
  },
  Leichhardt: {
    year: '2013',
    chapter: 'Part C, Section 1',
    hcaNote: 'Heritage controls apply generally to all Heritage Conservation Areas in Leichhardt — there are no HCA-specific controls in the Leichhardt DCP.'
  },
  Marrickville: {
    year: '2011',
    chapter: 'Section 8',
    hcaNote: 'Individual Heritage Conservation Areas may have specific controls and a Statement of Significance in the Marrickville DCP.'
  }
};

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
  heritageLegislationUrl,
  formerCouncil,
  lga
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

  const cardColor = isHCA ? 'border-amber-300' : isStateHeritage ? 'border-red-300' : 'border-amber-300';
  const bgColor = isHCA ? 'bg-amber-50/50' : isStateHeritage ? 'bg-red-50/50' : 'bg-amber-50/50';

  return (
    <Card className={'border-amber-300 bg-amber-50/50'}>
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-amber-700" />
            <span className="text-amber-900">
              {isHCA ? 'Heritage Conservation Area' : 'Heritage Listed Property'}
            </span>
          </div>
          <Badge className={isStateHeritage ? 'bg-red-100 text-red-800 border-red-300 font-semibold' : 'bg-amber-100 text-amber-800 font-semibold'}>
            {heritageSignificance || 'Heritage'} Significance
          </Badge>
        </CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          {isHCA
            ? `Heritage Conservation Area identified under the ${lga || 'local'} LEP. DCP heritage controls are in ${COUNCIL_DCP_INFO[formerCouncil || '']?.chapter || 'the heritage chapter'} of the ${formerCouncil || lga || ''} DCP ${COUNCIL_DCP_INFO[formerCouncil || '']?.year || ''}.`
            : `Heritage-listed property identified under the ${lga || 'local'} LEP. General heritage controls apply from ${COUNCIL_DCP_INFO[formerCouncil || '']?.chapter || 'the heritage chapter'} of the ${formerCouncil || lga || ''} DCP ${COUNCIL_DCP_INFO[formerCouncil || '']?.year || ''}.`
          }
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="border-l-4 border-amber-500 pl-4 py-2 bg-amber-50/50 rounded-r-md">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-sm text-amber-900">
                  {heritageItemName || (isHCA ? 'Heritage Conservation Area' : 'Heritage Item')}
                </h4>
                {clauseNumber && (
                  <button
                    onClick={toggleProvision}
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

              <div className="flex flex-wrap gap-2 mt-2">
                {heritageLegislativeClause && (
                  <Badge variant="outline" className="text-xs bg-amber-100 text-amber-900 border-amber-300">
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
                <div className="mt-3 p-3 bg-white rounded-md border border-amber-200">
                  {loading ? (
                    <p className="text-sm text-muted-foreground">Loading provision text...</p>
                  ) : clauseNumber === '5.10' ? (
                    <div className="space-y-3">
                      <h5 className="font-semibold text-sm text-amber-900">
                        Clause 5.10 Heritage conservation — Inner West LEP 2022
                      </h5>
                      {/* Note about generic vs specific */}
                      <div className="text-xs text-gray-600 bg-gray-50 rounded px-2 py-1.5 border border-gray-200">
                        <strong>LEP clause:</strong> Clause 5.10 applies to all heritage items and HCAs across the Inner West.
                        For design controls specific to this property, see the <strong>DCP tab → Heritage</strong>.
                        {formerCouncil && COUNCIL_DCP_INFO[formerCouncil] && (
                          <span className="block mt-1">{COUNCIL_DCP_INFO[formerCouncil].hcaNote}</span>
                        )}
                      </div>
                      {/* Full PDF page image of clause 5.10 */}
                      <div className="border border-amber-200 rounded-lg overflow-hidden">
                        <img
                          src="https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/iwlep_clause_5_10_page_50.png"
                          alt="Inner West LEP 2022 Clause 5.10 Heritage conservation - Page 50"
                          className="w-full"
                        />
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <a
                          href="https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457#sec.5.10"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-amber-700 hover:text-amber-900 hover:underline"
                        >
                          <ExternalLink className="h-3 w-3" />
                          View full clause on NSW Legislation
                        </a>
                        <span className="text-gray-400">|</span>
                        <span className="text-xs text-gray-500">
                          Page 50 of Inner West LEP 2022
                        </span>
                      </div>
                    </div>
                  ) : provisionDetail && provisionDetail.provisionText && provisionDetail.provisionText.length > 100 ? (
                    <div className="space-y-2">
                      <h5 className="font-semibold text-sm text-amber-900">
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
                  className="flex items-center gap-1 text-amber-700 hover:text-amber-900"
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

        {/* Note about DCP heritage controls */}
        {isHCA && formerCouncil && (
          <p className="mt-3 text-sm text-amber-700 bg-amber-50 rounded px-3 py-2">
            Heritage controls for this area are in {COUNCIL_DCP_INFO[formerCouncil]?.chapter || 'the heritage chapter'} of the {formerCouncil} DCP {COUNCIL_DCP_INFO[formerCouncil]?.year || ''} — see DCP tab.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
