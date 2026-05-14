'use client';

/**
 * BROWSE PAGE - /browse
 *
 * Professional DCP navigation via Table of Contents
 * - Left panel: Hierarchical TOC tree
 * - Right panel: Provisions for selected section
 */

import React, { useState } from 'react';
import { ChevronRight, Home, Search, FileText, Book } from 'lucide-react';
import { DCPSelector } from '@/components/browse/DCPSelector';
import { TOCTree } from '@/components/browse/TOCTree';
import { ProvisionDisplay } from '@/components/browse/ProvisionDisplay';
import Link from 'next/link';

export default function BrowsePage() {
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<{
    sectionNumber: string;
    sectionTitle: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-[1800px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Browse DCP by Section
              </h1>
              <p className="text-gray-600 mt-1">
                Navigate Development Control Plans using their table of contents
              </p>
            </div>

            {/* Navigation Links */}
            <div className="flex items-center gap-4">
              <Link
                href="/assessment"
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Home size={16} />
                Assessment
              </Link>
              <Link
                href="/assessment/search"
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Search size={16} />
                Search
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Breadcrumb */}
      {selectedDocument && (
        <div className="bg-white border-b px-6 py-3">
          <div className="max-w-[1800px] mx-auto">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Book size={14} />
              <ChevronRight size={14} />
              <span className="font-medium text-gray-900">
                {selectedDocument.replace(/_/g, ' ').replace(/__/g, ' - ')}
              </span>
              {selectedSection && (
                <>
                  <ChevronRight size={14} />
                  <span className="text-blue-600">
                    {selectedSection.sectionNumber} {selectedSection.sectionTitle}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-[1800px] mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Panel - TOC Navigation */}
          <div className="lg:col-span-4">
            <div className="bg-white border rounded-lg shadow-sm sticky top-6">
              {/* Document Selector */}
              <div className="p-4 border-b">
                <DCPSelector
                  onDocumentSelect={setSelectedDocument}
                  selectedDocument={selectedDocument}
                />
              </div>

              {/* TOC Tree */}
              {selectedDocument ? (
                <TOCTree
                  documentId={selectedDocument}
                  onSectionSelect={setSelectedSection}
                  selectedSection={selectedSection}
                />
              ) : (
                <div className="p-12 text-center">
                  <FileText size={48} className="mx-auto text-gray-300 mb-4" />
                  <h3 className="text-lg font-medium text-gray-500 mb-2">
                    Select a DCP Document
                  </h3>
                  <p className="text-sm text-gray-600">
                    Choose a document from the dropdown above to view its table of contents
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Provision Display */}
          <div className="lg:col-span-8">
            {selectedDocument && selectedSection ? (
              <ProvisionDisplay
                documentId={selectedDocument}
                sectionNumber={selectedSection.sectionNumber}
                sectionTitle={selectedSection.sectionTitle}
              />
            ) : (
              <div className="bg-white border rounded-lg shadow-sm p-12 text-center">
                <div className="max-w-md mx-auto">
                  <div className="bg-blue-50 rounded-full w-20 h-20 mx-auto mb-4 flex items-center justify-center">
                    <FileText size={36} className="text-blue-500" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-700 mb-2">
                    No Section Selected
                  </h3>
                  <p className="text-sm text-gray-600 mb-6">
                    Select a document and click on a section in the table of contents to view its provisions
                  </p>

                  {/* Quick Help */}
                  <div className="text-left bg-gray-50 rounded-lg p-4 text-sm">
                    <h4 className="font-medium text-gray-700 mb-2">How to use Browse:</h4>
                    <ol className="space-y-1 text-gray-600">
                      <li>1. Select a DCP document from the dropdown</li>
                      <li>2. Browse the table of contents on the left</li>
                      <li>3. Click on a section to view its provisions</li>
                      <li>4. Use filters to find specific content</li>
                    </ol>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-50 border border-red-200 rounded-lg p-4 max-w-md shadow-lg">
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <h4 className="font-medium text-red-800">Error</h4>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-600"
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
