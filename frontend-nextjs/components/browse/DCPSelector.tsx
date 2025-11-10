'use client';

/**
 * DCP Selector Component
 * Dropdown to select which DCP document to browse
 * Fetches all available DCP documents from API
 */

import React, { useState, useEffect } from 'react';
import { ChevronDown, Loader2, BookOpen, AlertCircle } from 'lucide-react';

interface Document {
  documentId: string;
  label: string;
  hasTOC: boolean;
  provisionCount: number;
  partNumber: string | null;
}

interface DCPSelectorProps {
  onDocumentSelect: (documentId: string) => void;
  selectedDocument: string | null;
}

export function DCPSelector({ onDocumentSelect, selectedDocument }: DCPSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [grouped, setGrouped] = useState<Record<string, Document[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await fetch('/api/browse/documents');
      const data = await response.json();

      if (data.success) {
        setDocuments(data.data.documents);
        setGrouped(data.data.grouped);
      } else {
        setError(data.error || 'Failed to load documents');
      }
    } catch (err) {
      setError('Network error: Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  };

  const selectedDoc = documents.find(doc => doc.documentId === selectedDocument);

  if (loading) {
    return (
      <div className="relative">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select DCP Document
        </label>
        <div className="w-full flex items-center justify-center px-4 py-2.5 bg-gray-50 border border-gray-300 rounded-lg">
          <Loader2 size={16} className="text-gray-400 animate-spin mr-2" />
          <span className="text-sm text-gray-500">Loading documents...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="relative">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select DCP Document
        </label>
        <div className="w-full px-4 py-2.5 bg-red-50 border border-red-300 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-red-600">
            <AlertCircle size={16} />
            {error}
          </div>
          <button
            onClick={fetchDocuments}
            className="text-xs text-red-700 hover:text-red-900 underline mt-2"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Select DCP Document
      </label>

      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={documents.length === 0}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-white border border-gray-300 rounded-lg hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span className={selectedDoc ? 'text-gray-900 text-sm' : 'text-gray-500 text-sm'}>
          {selectedDoc ? selectedDoc.label : 'Choose a document...'}
        </span>
        <div className="flex items-center gap-2">
          {selectedDoc && !selectedDoc.hasTOC && (
            <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded">
              No TOC
            </span>
          )}
          <ChevronDown
            size={16}
            className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute z-20 mt-2 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-y-auto">
            {/* Grouped by Part */}
            {Object.entries(grouped).map(([partName, docs]) => (
              <div key={partName} className="border-b last:border-b-0">
                {/* DCP Header */}
                <div className="bg-gradient-to-r from-blue-50 to-gray-50 px-4 py-3 border-b sticky top-0 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <BookOpen size={16} className="text-blue-600" />
                      <span className="text-sm font-bold text-gray-800">
                        {partName}
                      </span>
                    </div>
                    <span className="text-xs font-medium text-gray-600 bg-white px-2 py-1 rounded">
                      {docs.length} {docs.length === 1 ? 'section' : 'sections'}
                    </span>
                  </div>
                </div>

                {/* Documents in DCP */}
                <div className="bg-white">
                  {docs.map((doc) => (
                    <button
                      key={doc.documentId}
                      onClick={() => {
                        onDocumentSelect(doc.documentId);
                        setIsOpen(false);
                      }}
                      className={`w-full text-left px-4 py-3 hover:bg-blue-50 transition-all border-b last:border-b-0 ${
                        selectedDocument === doc.documentId
                          ? 'bg-blue-100 border-l-4 border-l-blue-600'
                          : 'border-l-4 border-l-transparent'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <span className={`text-sm block truncate ${
                            selectedDocument === doc.documentId
                              ? 'font-semibold text-blue-800'
                              : 'text-gray-800'
                          }`}>
                            {doc.label}
                          </span>
                          {!doc.hasTOC && (
                            <span className="text-xs text-amber-600 mt-1 inline-block">
                              ⚠️ No table of contents
                            </span>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-1 flex-shrink-0">
                          <span className="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                            {doc.provisionCount} provisions
                          </span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}

            {/* Footer Stats */}
            <div className="border-t p-3 bg-gray-50 sticky bottom-0">
              <p className="text-xs text-gray-600">
                {documents.length} total documents • {documents.filter(d => d.hasTOC).length} with TOC
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
