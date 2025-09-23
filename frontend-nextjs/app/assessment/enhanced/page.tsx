'use client';

import React from 'react';
import { useAssessment } from '@/hooks/assessment/useAssessment';
import { PropertySearch } from '@/components/property/PropertySearch';
import PropertyCard from '@/components/assessment/core/PropertyCard';
import ComplianceChecklist from '@/components/assessment/core/ComplianceChecklist';
import {
 PropertyLoading,
 ComplianceLoading,
 ErrorDisplay,
 ValidationErrors
} from '@/components/assessment/core/LoadingStates';
import {
 ValidatedAddressInput,
 ValidatedDevelopmentSelector,
 ValidatedDateInput,
 AssessmentSubmitButton
} from '@/components/assessment/core/ValidatedForm';

export default function EnhancedAssessmentPage() {
 const [state, actions] = useAssessment();

 const handleAddressSubmit = () => {
 // Property loading will be handled by PropertyCard component
 // This demonstrates real-time data binding
 };

 return (
 <div className="min-h-screen bg-gray-50">
 {/* Header */}
 <div className="bg-white shadow-sm border-b">
 <div className="max-w-7xl mx-auto px-4 py-4">
 <h1 className="text-2xl font-bold text-gray-900">
 Enhanced Planning Assessment
 </h1>
 <p className="text-gray-600 mt-1">
 Real-time data binding with comprehensive form validation
 </p>
 </div>
 </div>

 {/* Main Content */}
 <div className="max-w-7xl mx-auto px-4 py-6">
 <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
 {/* Left Panel - Property & Form Controls */}
 <div className="lg:col-span-1 space-y-6">
 {/* Address Input */}
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Property Address</h3>
 <ValidatedAddressInput
 value={state.address}
 onChange={actions.setAddress}
 onSubmit={handleAddressSubmit}
 error={state.propertyError}
 placeholder="Enter NSW property address..."
 />
 </div>

 {/* Property Information */}
 {state.address && !state.property && !state.propertyError && (
 <PropertyLoading address={state.address} />
 )}

 {state.property && (
 <PropertyCard
 address={state.address}
 onPropertyLoaded={actions.setProperty}
 />
 )}

 {/* Development Type Selection */}
 {state.property && (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Development Details</h3>
 <div className="space-y-4">
 <ValidatedDevelopmentSelector
 value={state.developmentType}
 onChange={actions.setDevelopmentType}
 error={state.developmentTypeError}
 />

 <ValidatedDateInput
 value={state.assessmentDate}
 onChange={actions.setAssessmentDate}
 label="Assessment Date"
 max={new Date().toISOString().split('T')[0]}
 />
 </div>
 </div>
 )}

 {/* Form Validation */}
 {state.validationErrors.length > 0 && (
 <ValidationErrors errors={state.validationErrors} />
 )}

 {/* Assessment Action */}
 {state.property && state.developmentType && (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Run Assessment</h3>
 <AssessmentSubmitButton
 onClick={actions.runAssessment}
 loading={state.complianceLoading}
 formValid={state.formValid}
 >
 {state.complianceLoading
 ? 'Running Assessment...'
 : 'Generate Compliance Report'
 }
 </AssessmentSubmitButton>

 {state.lastAssessmentRun && (
 <p className="text-xs text-gray-500 mt-2 text-center">
 Last run: {new Date(state.lastAssessmentRun).toLocaleString()}
 </p>
 )}
 </div>
 )}
 </div>

 {/* Right Panel - Results */}
 <div className="lg:col-span-3 space-y-6">
 {/* Loading State */}
 {state.complianceLoading && state.property && (
 <ComplianceLoading
 developmentType={state.developmentType as string}
 zone={state.property.zone}
 />
 )}

 {/* Error State */}
 {state.complianceError && (
 <ErrorDisplay
 error={state.complianceError}
 onRetry={actions.runAssessment}
 />
 )}

 {/* Results */}
 {state.showResults && state.complianceData && (
 <>
 {/* Assessment Summary */}
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Assessment Summary</h3>
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
 <div className="bg-green-50 border border-green-200 rounded-lg p-4">
 <div className="text-green-800 font-medium">Compliant</div>
 <div className="text-2xl font-bold text-green-900">
 {state.complianceData.summary?.compliant || 0}
 </div>
 </div>
 <div className="bg-red-50 border border-red-200 rounded-lg p-4">
 <div className="text-red-800 font-medium">Non-Compliant</div>
 <div className="text-2xl font-bold text-red-900">
 {state.complianceData.summary?.non_compliant || 0}
 </div>
 </div>
 <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
 <div className="text-yellow-800 font-medium">Requires Review</div>
 <div className="text-2xl font-bold text-yellow-900">
 {state.complianceData.summary?.requires_assessment || 0}
 </div>
 </div>
 <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
 <div className="text-blue-800 font-medium">Total Items</div>
 <div className="text-2xl font-bold text-blue-900">
 {state.complianceData.summary?.total_items || 0}
 </div>
 </div>
 </div>
 </div>

 {/* Detailed Results */}
 <ComplianceChecklist
 items={state.complianceData.compliance_items?.map((item: any, index: number) => ({
 id: index.toString(),
 provision: item.provision,
 clause: item.clause,
 status: item.status,
 details: item.details
 })) || []}
 />

 {/* Actions */}
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Actions</h3>
 <div className="flex gap-3">
 <button
 onClick={actions.runAssessment}
 className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
 >
 Re-run Assessment
 </button>
 <button
 onClick={actions.clearAssessment}
 className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
 >
 Clear Results
 </button>
 <button
 onClick={actions.resetForm}
 className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
 >
 Reset Form
 </button>
 </div>
 </div>
 </>
 )}

 {/* Empty State */}
 {!state.showResults && !state.complianceLoading && !state.complianceError && (
 <div className="bg-white border rounded-lg p-12 shadow-sm text-center">
 <div className="text-gray-500">
 <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
 <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
 </svg>
 </div>
 <h3 className="text-lg font-medium mb-2">Ready for Assessment</h3>
 <p>Complete the form on the left to generate a comprehensive compliance report</p>
 </div>
 </div>
 )}
 </div>
 </div>
 </div>
 </div>
 );
}
