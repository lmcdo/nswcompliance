'use client';

import { useState } from 'react';
import { SmartFeedbackTrigger } from './SmartFeedbackTrigger';
import { RequirementFeedback } from './RequirementFeedback';
import { PersistentFeedbackHub } from './PersistentFeedbackHub';
import { Button } from '@/components/ui/button';

export function FeedbackDemo() {
  const [showDemo, setShowDemo] = useState(false);

  if (!showDemo) {
    return (
      <div className="p-4 border border-gray-200 rounded-lg bg-gray-50">
        <h3 className="text-lg font-semibold mb-2">Professional Feedback System Demo</h3>
        <p className="text-sm text-gray-600 mb-4">
          Test the feedback system designed for council certifiers, town planners, and developers.
        </p>
        <Button onClick={() => setShowDemo(true)} variant="outline" size="sm">
          Show Demo
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 border border-gray-200 rounded-lg bg-gray-50">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Feedback System Active</h3>
          <p className="text-sm text-gray-600">
            Interact with the demo scenarios below to see feedback prompts.
          </p>
        </div>
        <Button onClick={() => setShowDemo(false)} variant="ghost" size="sm">
          Hide Demo
        </Button>
      </div>

      {/* Persistent Feedback Hub Demo */}
      <div className="p-3 border border-purple-200 rounded bg-purple-50">
        <h4 className="text-sm font-medium text-purple-900 mb-2">
          🔄 Persistent Feedback Hub
        </h4>
        <p className="text-xs text-purple-700 mb-3">
          Always available feedback hub for continuous user journey
        </p>
        <PersistentFeedbackHub
          propertyAddress="29 Norton Street, Leichhardt NSW 2040"
          propertyId="demo_property_001"
          sections={['setbacks', 'compliance_results', 'zoning', 'parking']}
          onFeedback={(feedback) => console.log('Feedback submitted:', feedback)}
        />
      </div>

      {/* Demo Scenarios */}
      <div className="space-y-4">
        <div className="p-3 border border-orange-200 rounded bg-orange-50">
          <h4 className="text-sm font-medium text-orange-900 mb-2">
            🏠 Address Resolution Demo
          </h4>
          <p className="text-xs text-orange-700 mb-2">
            Property: "29 Norton Street, Leichhardt NSW 2040"
          </p>
          <SmartFeedbackTrigger
            type="address_issue"
            context={{
              propertyAddress: "29 NORTON STREET LEICHHARDT 2040",
              userInput: "29 Norton Street, Leichhardt NSW 2040",
              section: "address_resolution",
              confidence: 0.65
            }}
            delay={2}
          />
        </div>

        <div className="p-3 border border-blue-200 rounded bg-blue-50">
          <h4 className="text-sm font-medium text-blue-900 mb-2">
            📋 Requirement Feedback Demo
          </h4>
          <div className="text-xs text-blue-700 space-y-2">
            <p><strong>DCP Requirement:</strong> "Front setback is 6m from boundary"</p>
            <RequirementFeedback
              requirement={{
                id: "req_demo_001",
                title: "Front Setback",
                text: "Development must maintain a minimum setback of 6m from the front boundary.",
                section: "setbacks"
              }}
              propertyAddress="29 Norton Street, Leichhardt NSW 2040"
              compact={true}
            />
          </div>
        </div>

        <div className="p-3 border border-green-200 rounded bg-green-50">
          <h4 className="text-sm font-medium text-green-900 mb-2">
            ✅ Data Quality Demo
          </h4>
          <p className="text-xs text-green-700 mb-2">
            Compliance results shown - feedback appears after 3 seconds
          </p>
          <SmartFeedbackTrigger
            type="missing_data"
            context={{
              propertyAddress: "29 Norton Street, Leichhardt NSW 2040",
              section: "compliance_results",
              currentValue: { requirementsCount: 15 }
            }}
            delay={3}
          />
        </div>
      </div>

      {/* Instructions */}
      <div className="p-3 border border-gray-200 rounded bg-white">
        <h4 className="text-sm font-medium text-gray-900 mb-2">How to Test Persistent Feedback:</h4>
        <ul className="text-xs text-gray-600 space-y-1">
          <li>• <strong>Persistent Hub:</strong> Notice the blue feedback hub that stays available</li>
          <li>• <strong>Re-appearance:</strong> Dismiss feedback, it returns after 15 seconds</li>
          <li>• <strong>Session Memory:</strong> Your role is remembered throughout</li>
          <li>• <strong>General Suggestions:</strong> Add professional insights not tied to specific requirements</li>
          <li>• <strong>Section Switching:</strong> Click different sections to focus feedback context</li>
          <li>• <strong>Feedback History:</strong> View and clear your session feedback</li>
        </ul>
      </div>

      {/* Professional Workflow Testing */}
      <div className="p-3 border border-indigo-200 rounded bg-indigo-50">
        <h4 className="text-sm font-medium text-indigo-900 mb-2">
          🎯 Professional Workflow Simulation
        </h4>
        <p className="text-xs text-indigo-700 mb-3">
          Simulate how certifiers, planners, and developers use the system:
        </p>
        <div className="grid md:grid-cols-3 gap-2">
          <div className="p-2 border border-gray-200 rounded bg-white">
            <h5 className="text-xs font-medium text-gray-900 mb-1">Certifier Journey:</h5>
            <ol className="text-xs text-gray-600 space-y-1">
              <li>Review property details</li>
              <li>Submit setback issues</li>
              <li>Add compliance observations</li>
              <li>Submit final assessment feedback</li>
            </ol>
          </div>
          <div className="p-2 border border-gray-200 rounded bg-white">
            <h5 className="text-xs font-medium text-gray-900 mb-1">Planner Journey:</h5>
            <ol className="text-xs text-gray-600 space-y-1">
              <li>Identify missing requirements</li>
              <li>Report zoning concerns</li>
              <li>Suggest planning improvements</li>
              <li>Document professional insights</li>
            </ol>
          </div>
          <div className="p-2 border border-gray-200 rounded bg-white">
            <h5 className="text-xs font-medium text-gray-900 mb-1">Developer Journey:</h5>
            <ol className="text-xs text-gray-600 space-y-1">
              <li>Check feasibility constraints</li>
              <li>Flag calculation errors</li>
              <li>Suggest development insights</li>
              <li>Report regulatory insights</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}