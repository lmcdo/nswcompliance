import React, { useState, useEffect } from 'react';

interface CompleteProvision {
  id: number;
  reference: string;
  excerptText: string;
  fullClauseText: string | null;
  legalPrecedence: number;
  instrumentType: string;
  documentTitle: string;
  documentId: string;
  charCount?: number;
}

interface CompleteProvisionViewerProps {
  provisionId: number;
  className?: string;
}

export default function CompleteProvisionViewer({
  provisionId,
  className = ''
}: CompleteProvisionViewerProps) {
  const [provision, setProvision] = useState<CompleteProvision | null>(null);
  const [showFullText, setShowFullText] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProvision = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`/api/provisions/${provisionId}/complete`);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        setProvision(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch provision');
        console.error('Error fetching complete provision:', err);
      } finally {
        setLoading(false);
      }
    };

    if (provisionId) {
      fetchProvision();
    }
  }, [provisionId]);

  if (loading) {
    return (
      <div className={`provision-viewer loading ${className}`}>
        <div className="loading-spinner">Loading provision...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`provision-viewer error ${className}`}>
        <div className="error-message">
          <h4>Error Loading Provision</h4>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!provision) {
    return (
      <div className={`provision-viewer not-found ${className}`}>
        <div className="not-found-message">
          <h4>Provision Not Found</h4>
          <p>Provision ID {provisionId} could not be found.</p>
        </div>
      </div>
    );
  }

  const getPrecedenceColor = (precedence: number) => {
    switch (precedence) {
      case 1: return 'text-red-600 bg-red-50'; // SEPP - highest
      case 2: return 'text-orange-600 bg-orange-50';
      case 3: return 'text-blue-600 bg-blue-50'; // LEP
      case 4: return 'text-green-600 bg-green-50'; // DCP - lowest
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const formatLegalText = (text: string) => {
    // Preserve paragraph structure and legal formatting
    return text
      .split('\n')
      .map((line, index) => {
        // Handle subsections and bullet points
        const trimmed = line.trim();
        if (trimmed.match(/^\([a-z]\)/)) {
          return <div key={index} className="ml-4 mt-2">{trimmed}</div>;
        } else if (trimmed.match(/^\([ivx]+\)/)) {
          return <div key={index} className="ml-8 mt-1">{trimmed}</div>;
        } else if (trimmed.match(/^\(\d+\)/)) {
          return <div key={index} className="mt-3 font-medium">{trimmed}</div>;
        } else if (trimmed) {
          return <div key={index} className="mt-2">{trimmed}</div>;
        }
        return <div key={index} className="h-2"></div>;
      });
  };

  return (
    <div className={`provision-viewer ${className}`}>
      {/* Header */}
      <div className="provision-header bg-white border border-gray-200 rounded-t-lg p-4">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {provision.instrumentType} - Clause {provision.reference}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              {provision.documentTitle}
            </p>
          </div>
          <div className={`px-3 py-1 rounded-full text-xs font-medium ${getPrecedenceColor(provision.legalPrecedence)}`}>
            Legal Precedence: {provision.legalPrecedence}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="provision-content bg-white border-l border-r border-gray-200 p-4">
        {!showFullText ? (
          <>
            <div className="excerpt-text">
              <p className="text-gray-700 leading-relaxed">
                {provision.excerptText}
              </p>
              {provision.excerptText.endsWith('...') || provision.excerptText.length >= 450 && (
                <p className="text-sm text-gray-500 mt-2 italic">
                  Text may be truncated...
                </p>
              )}
            </div>

            <button
              onClick={() => setShowFullText(true)}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              disabled={!provision.fullClauseText}
            >
              {provision.fullClauseText ? 'View Complete Legal Text' : 'Complete text not available'}
            </button>
          </>
        ) : (
          <>
            <div className="full-legal-text">
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="font-mono text-sm leading-relaxed">
                  {provision.fullClauseText ?
                    formatLegalText(provision.fullClauseText) :
                    <p className="text-gray-500 italic">Complete legal text not available</p>
                  }
                </div>
              </div>

              {provision.fullClauseText && (
                <div className="mt-2 text-xs text-gray-500">
                  Source: {provision.documentId} • {provision.charCount?.toLocaleString()} total characters in document
                </div>
              )}
            </div>

            <button
              onClick={() => setShowFullText(false)}
              className="mt-4 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
            >
              Show Summary
            </button>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="provision-footer bg-gray-50 border border-gray-200 rounded-b-lg px-4 py-2">
        <div className="flex justify-between items-center text-xs text-gray-600">
          <span>Provision ID: {provision.id}</span>
          <span>Database: nsw_planning_corrected</span>
        </div>
      </div>
    </div>
  );
}