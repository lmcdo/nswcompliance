'use client';

/**
 * CrossReferenceLink Component
 *
 * Displays a clickable cross-reference with navigation support.
 * Handles different document types (DCP, LEP, SEPP) with appropriate
 * navigation behavior.
 *
 * Navigation behaviors:
 * - Same DCP section: Scroll to provision, highlight for 2 seconds
 * - Different DCP section: Open in side panel (preserve current context)
 * - LEP clause reference: Navigate to LEP tab, scroll to clause
 * - SEPP clause reference: Navigate to SEPP tab, scroll to clause
 * - Unresolved reference: Tooltip shows reference text, no navigation
 */

import { useState } from 'react';
import { Link2, ExternalLink, AlertCircle, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { CrossReference } from '@/hooks/useCrossReferences';

export type DocumentType = 'dcp' | 'lep' | 'sepp' | null;

export interface CrossReferenceLinkProps {
  reference: CrossReference;
  /** Current document type for context */
  currentDocType?: DocumentType;
  /** Current provision ID for same-document detection */
  currentProvisionId?: number;
  /** Callback when navigation is triggered */
  onNavigate?: (provisionId: number, docType: DocumentType) => void;
  /** Callback for scrolling to provision (same document) */
  onScrollTo?: (provisionId: number) => void;
  /** Size variant */
  size?: 'sm' | 'md';
}

/**
 * Infer document type from reference type or text
 */
function inferDocumentType(reference: CrossReference): DocumentType {
  const refType = reference.referenceType?.toLowerCase() || '';
  const refText = reference.referenceText?.toLowerCase() || '';
  const refNumber = reference.referenceNumber?.toLowerCase() || '';

  // Check for LEP patterns
  if (
    refType.includes('lep') ||
    refText.includes('local environmental plan') ||
    refNumber.includes('lep')
  ) {
    return 'lep';
  }

  // Check for SEPP patterns
  if (
    refType.includes('sepp') ||
    refText.includes('state environmental planning policy') ||
    refNumber.includes('sepp')
  ) {
    return 'sepp';
  }

  // Check for DCP patterns
  if (
    refType.includes('dcp') ||
    refType.includes('part') ||
    refType.includes('section') ||
    refText.includes('development control plan')
  ) {
    return 'dcp';
  }

  // Default to DCP if it's resolved (has a target)
  if (reference.targetProvisionId) {
    return 'dcp';
  }

  return null;
}

/**
 * Format the reference for display
 */
function formatReferenceLabel(reference: CrossReference): string {
  // Use reference number if available
  if (reference.referenceNumber) {
    return reference.referenceNumber;
  }

  // Fall back to reference text (truncated)
  if (reference.referenceText) {
    const text = reference.referenceText;
    return text.length > 30 ? text.substring(0, 27) + '...' : text;
  }

  return 'Reference';
}

/**
 * Get tooltip content based on resolution status
 */
function getTooltipContent(reference: CrossReference, targetDocType: DocumentType): string {
  if (reference.resolutionStatus === 'resolved' && reference.targetText) {
    const truncated = reference.targetText.length > 150
      ? reference.targetText.substring(0, 147) + '...'
      : reference.targetText;
    return truncated;
  }

  if (reference.resolutionStatus === 'unresolved') {
    return `Reference: ${reference.referenceText || reference.referenceNumber}\n(Could not resolve target)`;
  }

  return reference.referenceText || 'Cross-reference';
}

export function CrossReferenceLink({
  reference,
  currentDocType = 'dcp',
  currentProvisionId,
  onNavigate,
  onScrollTo,
  size = 'sm',
}: CrossReferenceLinkProps) {
  const [isHovered, setIsHovered] = useState(false);

  const isResolved = reference.resolutionStatus === 'resolved' && reference.targetProvisionId;
  const targetDocType = inferDocumentType(reference);
  const isSameDocument = targetDocType === currentDocType;
  const label = formatReferenceLabel(reference);
  const tooltipContent = getTooltipContent(reference, targetDocType);

  const handleClick = () => {
    if (!isResolved || !reference.targetProvisionId) {
      return; // No navigation for unresolved references
    }

    if (isSameDocument && onScrollTo) {
      // Same document: scroll to and highlight
      onScrollTo(reference.targetProvisionId);
    } else if (onNavigate) {
      // Different document: navigate with tab switch
      onNavigate(reference.targetProvisionId, targetDocType);
    }
  };

  const sizeClasses = size === 'sm'
    ? 'text-xs px-1.5 py-0.5 gap-0.5'
    : 'text-sm px-2 py-1 gap-1';

  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-4 h-4';

  // Style based on resolution status and mandatory flag
  const getVariantClasses = () => {
    if (!isResolved) {
      return 'bg-gray-100 text-gray-500 border-gray-200 cursor-default';
    }

    if (reference.isMandatory) {
      return 'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100 cursor-pointer';
    }

    return 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 cursor-pointer';
  };

  // Get icon based on status
  const getIcon = () => {
    if (!isResolved) {
      return <AlertCircle className={`${iconSize} text-gray-400`} />;
    }

    if (isSameDocument) {
      return <ChevronRight className={`${iconSize}`} />;
    }

    return <ExternalLink className={`${iconSize}`} />;
  };

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={`
              inline-flex items-center rounded border font-medium
              transition-colors duration-150
              ${sizeClasses}
              ${getVariantClasses()}
            `}
            onClick={handleClick}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            disabled={!isResolved}
          >
            <Link2 className={`${iconSize} flex-shrink-0`} />
            <span className="truncate max-w-[120px]">{label}</span>
            {isResolved && getIcon()}
            {reference.isMandatory && isResolved && (
              <span className="text-[10px] font-bold ml-0.5">!</span>
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          className="max-w-xs text-xs"
          sideOffset={5}
        >
          <div className="space-y-1">
            <div className="font-medium">
              {reference.referenceNumber || reference.referenceType}
              {reference.isMandatory && ' (Mandatory)'}
            </div>
            <div className="text-gray-600 whitespace-pre-line">
              {tooltipContent}
            </div>
            {isResolved && (
              <div className="text-gray-400 text-[10px] mt-1">
                Click to {isSameDocument ? 'scroll to' : 'navigate to'} reference
              </div>
            )}
            {!isResolved && (
              <div className="text-amber-600 text-[10px] mt-1">
                Reference could not be resolved
              </div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * Component to display a list of cross-references
 */
export interface CrossReferenceListProps {
  references: CrossReference[];
  currentDocType?: DocumentType;
  currentProvisionId?: number;
  onNavigate?: (provisionId: number, docType: DocumentType) => void;
  onScrollTo?: (provisionId: number) => void;
  /** Maximum references to show before "show more" */
  maxVisible?: number;
}

export function CrossReferenceList({
  references,
  currentDocType,
  currentProvisionId,
  onNavigate,
  onScrollTo,
  maxVisible = 5,
}: CrossReferenceListProps) {
  const [showAll, setShowAll] = useState(false);

  if (!references || references.length === 0) {
    return null;
  }

  // Sort: mandatory first, then resolved, then by reference number
  const sortedRefs = [...references].sort((a, b) => {
    if (a.isMandatory !== b.isMandatory) return a.isMandatory ? -1 : 1;
    if (a.resolutionStatus !== b.resolutionStatus) {
      return a.resolutionStatus === 'resolved' ? -1 : 1;
    }
    return (a.referenceNumber || '').localeCompare(b.referenceNumber || '');
  });

  const visibleRefs = showAll ? sortedRefs : sortedRefs.slice(0, maxVisible);
  const hiddenCount = sortedRefs.length - maxVisible;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-gray-500 mr-1">
        <Link2 className="w-3 h-3 inline mr-0.5" />
        References:
      </span>
      {visibleRefs.map((ref) => (
        <CrossReferenceLink
          key={ref.id}
          reference={ref}
          currentDocType={currentDocType}
          currentProvisionId={currentProvisionId}
          onNavigate={onNavigate}
          onScrollTo={onScrollTo}
          size="sm"
        />
      ))}
      {!showAll && hiddenCount > 0 && (
        <button
          type="button"
          className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
          onClick={() => setShowAll(true)}
        >
          +{hiddenCount} more
        </button>
      )}
      {showAll && hiddenCount > 0 && (
        <button
          type="button"
          className="text-xs text-gray-500 hover:text-gray-700 hover:underline"
          onClick={() => setShowAll(false)}
        >
          show less
        </button>
      )}
    </div>
  );
}

export default CrossReferenceLink;
