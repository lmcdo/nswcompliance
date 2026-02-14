'use client';

import React from 'react';
import { Home } from 'lucide-react';
import Link from 'next/link';

export default function QuickGuidePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="relative border-b shadow-sm overflow-hidden flex">
        <div className="relative flex-shrink-0 bg-white">
          <svg className="h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
            <path d="M0 0 L16 0 Q36 14 28 28 Q20 42 36 56 L0 56 Z" fill="#0d9488" />
          </svg>
        </div>
        <a
          href="https://plotdetect.com.au/"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 pr-4 py-3 md:py-4 bg-white hover:opacity-80 transition-opacity"
        >
          <img src="/logo.png" alt="PlotDetect" className="h-8 w-auto" />
          <span className="text-base font-semibold text-gray-900">PlotDetect</span>
        </a>
        <div className="flex-1 bg-teal-50 flex items-center gap-4 px-4 py-3 md:py-4">
          <div className="flex-1">
            <h1 className="text-lg md:text-xl font-semibold tracking-tight text-teal-800">
              Quick Reference
            </h1>
            <p className="text-teal-600 text-xs hidden sm:block">
              Visual workflows for NSW planning compliance
            </p>
          </div>
          <Link
            href="/assessment"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border border-teal-600 bg-teal-600 text-white hover:bg-teal-700 transition-colors"
          >
            <Home className="h-3.5 w-3.5" />
            Back to Assessment
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">

        {/* Overview */}
        <div className="bg-white border rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-3">How PlotDetect Works</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-purple-50 rounded-lg border border-purple-200">
              <div className="text-2xl font-bold text-purple-700 mb-1">SEPP</div>
              <div className="text-xs text-purple-600">State Policies</div>
              <div className="text-xs text-purple-500 mt-2">E&C, BASIX, ADG, Heritage</div>
            </div>
            <div className="text-center p-4 bg-amber-50 rounded-lg border border-amber-200">
              <div className="text-2xl font-bold text-amber-700 mb-1">LEP</div>
              <div className="text-xs text-amber-600">Zone Rules</div>
              <div className="text-xs text-amber-500 mt-2">Height, FSR, Land Use</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="text-2xl font-bold text-green-700 mb-1">DCP</div>
              <div className="text-xs text-green-600">Local Controls</div>
              <div className="text-xs text-green-500 mt-2">Setbacks, Character, Heritage</div>
            </div>
          </div>
          <p className="text-xs text-gray-500 text-center mt-3">All three layers apply — check all tabs</p>
        </div>

        {/* Workflow 1: E&C Compliance */}
        <div className="bg-white border rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <span className="bg-emerald-600 text-white px-2 py-1 rounded text-xs font-bold">WORKFLOW 1</span>
            <h2 className="text-lg font-bold text-gray-900">Complying Development (E&C)</h2>
          </div>
          <div className="bg-gray-50 border rounded-lg p-4">
            <img
              src="/userguidediagramforverify.png"
              alt="E&C Compliance Pathway"
              className="w-full h-auto"
            />
          </div>
          <div className="mt-3 text-xs text-gray-600 space-y-1">
            <p><strong>1.</strong> SEPP Tab → E&C card → Check all standards met</p>
            <p><strong>2.</strong> LEP Tab → Verify use permitted in zone</p>
            <p><strong>3.</strong> DCP Tab → Check local controls apply</p>
          </div>
        </div>

        {/* Workflow 2: Heritage Assessment */}
        <div className="bg-white border rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <span className="bg-purple-600 text-white px-2 py-1 rounded text-xs font-bold">WORKFLOW 2</span>
            <h2 className="text-lg font-bold text-gray-900">Heritage Property Assessment</h2>
          </div>
          <div className="bg-gray-50 border rounded-lg p-4">
            <img
              src="/hierarchyandcompliance.png"
              alt="Heritage Assessment Workflow"
              className="w-full h-auto"
            />
          </div>
          <div className="mt-3 text-xs text-gray-600 space-y-1">
            <p><strong>1.</strong> DCP Tab → Heritage card → Read HCA objectives & general provisions</p>
            <p><strong>2.</strong> DCP Tab → Select work type (Additions, Roof, etc.) → Check specific controls</p>
            <p><strong>3.</strong> SEPP Tab → Check if State Heritage Register item (additional requirements)</p>
            <p><strong>4.</strong> LEP & DCP → Standard controls also apply (setbacks, height, character)</p>
          </div>
        </div>

        {/* Workflow 3: Standard DA */}
        <div className="bg-white border rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <span className="bg-blue-600 text-white px-2 py-1 rounded text-xs font-bold">WORKFLOW 3</span>
            <h2 className="text-lg font-bold text-gray-900">Standard Development Application</h2>
          </div>
          <div className="bg-gray-50 border rounded-lg p-4">
            <img
              src="/DAProcess.png"
              alt="Standard DA Workflow"
              className="w-full h-auto"
            />
          </div>
          <div className="mt-3 text-xs text-gray-600 space-y-1">
            <p><strong>1.</strong> LEP Tab → Verify use permitted, check height/FSR limits</p>
            <p><strong>2.</strong> DCP Tab → Review all design controls (setbacks, landscaping, parking, character)</p>
            <p><strong>3.</strong> SEPP Tab → Check applicable state policies (BASIX, ADG if apartments, TOD provisions)</p>
          </div>
        </div>

        {/* Regulatory Hierarchy */}
        <div className="bg-white border rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">NSW Planning & PlotDetect Navigation</h2>
          <div className="bg-gray-50 border rounded-lg p-4">
            <img
              src="/sepp-lep-dcp-hierarchy-diagram.png"
              alt="NSW Planning Hierarchy and PlotDetect Navigation"
              className="w-full h-auto"
            />
          </div>
          <p className="mt-3 text-xs text-gray-600 text-center">
            State policies override local rules where inconsistent, but all layers apply simultaneously
          </p>
        </div>

        {/* Quick Tips */}
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 mb-6">
          <h3 className="font-bold text-teal-900 mb-2 text-sm">⚡ Quick Tips</h3>
          <ul className="space-y-1 text-xs text-teal-800">
            <li>• Click PDF icons to view original document pages</li>
            <li>• Heritage properties: Check DCP Heritage card first</li>
            <li>• E&C compliance: All three tabs must pass (SEPP + LEP + DCP)</li>
            <li>• Use property summary (left panel) to identify zone and heritage status</li>
          </ul>
        </div>

        {/* Footer */}
        <div className="text-center">
          <p className="text-sm text-gray-600 mb-2">Need more detailed guidance?</p>
          <Link
            href="/user-guide"
            className="inline-flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors text-sm font-medium"
          >
            View Complete User Guide
          </Link>
          <p className="text-xs text-gray-400 mt-4">Quick Reference · PlotDetect · February 2026</p>
        </div>
      </div>
    </div>
  );
}
