'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Info } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface CouncilSetbackGuidanceProps {
  formerCouncil: 'Ashfield' | 'Marrickville' | 'Leichhardt';
  zone?: string;
}

const GUIDANCE_DATA = {
  Ashfield: {
    approach: 'Prescriptive Minimums',
    badgeColor: 'bg-blue-100 text-blue-800 border-blue-300',
    description: 'This council uses fixed numeric minimums',
    setbacks: [
      { label: 'Front', value: '6m minimum' },
      { label: 'Side', value: '0.9m or 1/2 building height' },
      { label: 'Rear', value: '1.2m to habitable rooms' }
    ],
    guidance: 'Meet or exceed these minimums',
    source: 'Ashfield DCP 2016 Chapter E2'
  },
  Marrickville: {
    approach: 'Character-Based',
    badgeColor: 'bg-purple-100 text-purple-800 border-purple-300',
    description: 'This council uses contextual guidance',
    setbacks: [
      { label: 'Front', value: '2m-4m (match existing pattern)' },
      { label: 'Side', value: '0.9m typical' },
      { label: 'Rear', value: 'Varies by lot depth' }
    ],
    guidance: 'Survey 3 adjacent properties and match streetscape character',
    source: 'Marrickville DCP 2011 Part 9 (Precincts)'
  },
  Leichhardt: {
    approach: 'Character-Based',
    badgeColor: 'bg-purple-100 text-purple-800 border-purple-300',
    description: 'This council uses contextual guidance',
    setbacks: [
      { label: 'Front', value: '1m-4m (varies by streetscape)' },
      { label: 'Side', value: '1.5m typical' },
      { label: 'Rear', value: 'Must complement context' }
    ],
    guidance: 'Match existing streetscape character and building patterns',
    source: 'Leichhardt DCP 2013 Part C Section 2'
  }
};

export function CouncilSetbackGuidance({ formerCouncil, zone }: CouncilSetbackGuidanceProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const guidance = GUIDANCE_DATA[formerCouncil];

  return (
    <div className="border border-gray-200 rounded-lg bg-gray-50 mb-4">
      {/* Collapsed header - single line */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-100 transition-colors rounded-lg"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-500" />
          )}
          <Info className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">
            {formerCouncil} Setback Approach
          </span>
          <Badge variant="outline" className={`text-xs ${guidance.badgeColor}`}>
            {guidance.approach}
          </Badge>
        </div>
        <span className="text-xs text-gray-500">
          {isExpanded ? 'Hide' : 'Show'} guidance
        </span>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-1 space-y-2">
          <p className="text-xs text-gray-600 italic">
            {guidance.description}
          </p>

          {/* Setback summary - compact 3-column grid */}
          <div className="grid grid-cols-3 gap-2 py-2 border-t border-gray-200">
            {guidance.setbacks.map((setback) => (
              <div key={setback.label} className="text-xs">
                <div className="font-medium text-gray-700">{setback.label}:</div>
                <div className="text-gray-600">{setback.value}</div>
              </div>
            ))}
          </div>

          {/* Guidance */}
          <div className="bg-blue-50 border border-blue-200 rounded px-2 py-2">
            <div className="flex items-start gap-2">
              <span className="text-sm">💡</span>
              <p className="text-xs text-blue-900">{guidance.guidance}</p>
            </div>
          </div>

          {/* Source */}
          <div className="text-xs text-gray-500 pt-1">
            Source: {guidance.source}
          </div>
        </div>
      )}
    </div>
  );
}
