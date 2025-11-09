'use client';

/**
 * PdfPageButton Component
 * Standardized PDF page view button across all provision types (SEPP, LEP, DCP)
 *
 * Design Principles:
 * - Consistent styling: Neutral gray (not pink/purple/white)
 * - Consistent position: Right-aligned below verbatim text
 * - Clear hierarchy: Secondary action (doesn't compete with requirement text)
 */

import { FileText } from 'lucide-react';

interface PdfPageButtonProps {
  pageNumber?: number;
  pdfUrl: string;
  onClick: () => void;
  variant?: 'inline' | 'footer';
  className?: string;
}

export function PdfPageButton({
  pageNumber,
  pdfUrl,
  onClick,
  variant = 'inline',
  className = ''
}: PdfPageButtonProps) {
  // Inline variant: Small, neutral, right-aligned button below verbatim text
  if (variant === 'inline') {
    return (
      <div className={`flex justify-end mt-2 ${className}`}>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs rounded-md transition-colors flex items-center gap-1.5 border border-slate-300"
        >
          <FileText className="h-3 w-3" />
          <span>View PDF page {pageNumber || ''}</span>
        </button>
      </div>
    );
  }

  // Footer variant: Slightly larger, for page group footers
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={`px-3 py-1.5 bg-slate-600 hover:bg-slate-700 text-white text-xs rounded transition-colors flex items-center gap-1.5 ${className}`}
    >
      <FileText className="h-3 w-3" />
      <span>View PDF page {pageNumber || ''}</span>
    </button>
  );
}

/**
 * PdfPageFooter Component
 * Footer section for PDF page groups (used in categorized requirements)
 */
interface PdfPageFooterProps {
  pageNumber: number;
  requirementCount: number;
  pdfUrl: string;
  onViewPdf: () => void;
  accentColor?: 'purple' | 'blue' | 'slate';
}

export function PdfPageFooter({
  pageNumber,
  requirementCount,
  pdfUrl,
  onViewPdf,
  accentColor = 'slate'
}: PdfPageFooterProps) {
  const colorClasses = {
    purple: {
      bg: 'bg-purple-50',
      border: 'border-purple-200',
      text: 'text-purple-800'
    },
    blue: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      text: 'text-blue-800'
    },
    slate: {
      bg: 'bg-slate-50',
      border: 'border-slate-200',
      text: 'text-slate-800'
    }
  };

  const colors = colorClasses[accentColor];

  return (
    <div className={`px-3 py-2 ${colors.bg} border-t ${colors.border} flex items-center justify-between`}>
      <div className={`text-xs ${colors.text}`}>
        <span className="font-semibold">
          {requirementCount === 1 ? '1 requirement' : `${requirementCount} requirements`}
        </span>
        {' '}from page {pageNumber}
      </div>
      <PdfPageButton
        pageNumber={pageNumber}
        pdfUrl={pdfUrl}
        onClick={onViewPdf}
        variant="footer"
      />
    </div>
  );
}
