'use client';

import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { getPdfImageUrl } from '@/lib/pdf-image-url';

interface PdfImageModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string | null | undefined;
  pageNumber?: number;
  title?: string;
}

/**
 * Shared PDF image viewer modal component.
 * Mobile-responsive: slides up from bottom on mobile, centered on desktop.
 * Accessible: supports Escape key, focus management, and screen readers.
 *
 * Usage:
 * ```tsx
 * const [viewingPdf, setViewingPdf] = useState<string | null>(null);
 *
 * <PdfImageModal
 *   isOpen={!!viewingPdf}
 *   onClose={() => setViewingPdf(null)}
 *   imageUrl={viewingPdf}
 *   pageNumber={5}
 *   title="DCP Source Document"
 * />
 * ```
 */
export function PdfImageModal({
  isOpen,
  onClose,
  imageUrl,
  pageNumber,
  title,
}: PdfImageModalProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Handle Escape key to close
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    // Focus the close button when modal opens
    closeButtonRef.current?.focus();

    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !imageUrl) return null;

  const displayTitle = title || (pageNumber ? `DCP Page ${pageNumber}` : 'DCP Source Page');
  const isDirectPdf = imageUrl.includes('#page=');
  const resolvedUrl = isDirectPdf ? null : getPdfImageUrl(imageUrl);

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-end md:items-center justify-center md:p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="pdf-modal-title"
    >
      <div
        className={`bg-white rounded-t-xl md:rounded-lg shadow-xl w-full md:max-w-4xl relative ${isDirectPdf ? 'max-h-[95vh]' : 'max-h-[95vh] md:max-h-[90vh] overflow-auto'}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-4 py-3 flex items-center justify-between z-10">
          <h3 id="pdf-modal-title" className="text-base md:text-lg font-semibold text-gray-900">
            {displayTitle}
          </h3>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors p-2 -mr-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-full hover:bg-gray-100"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* PDF content — iframe for direct PDFs, img for page screenshots */}
        <div className="p-2 md:p-4">
          {isDirectPdf ? (
            <iframe
              src={imageUrl}
              title={displayTitle}
              className="w-full border-0"
              style={{ height: '80vh' }}
            />
          ) : resolvedUrl ? (
            <img
              src={resolvedUrl}
              alt={displayTitle}
              className="w-full h-auto"
            />
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-500">
              Unable to load PDF image
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
