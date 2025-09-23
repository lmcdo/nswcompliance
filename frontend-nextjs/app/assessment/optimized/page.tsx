'use client';

import React from 'react';
import { usePersistentAssessment } from '@/hooks/assessment/usePersistentAssessment';
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
import { StateManagementPanel } from '@/components/assessment/core/StateManagement';

export default function OptimizedAssessmentPage() {
 const [state, actions] = usePersistentAssessment();

 const handleAddressSubmit = () => {
 // Property loading will be handled by PropertyCard component
 };

 return (
 <div className="min-h-screen bg-gray-50">
 {/* Header */}
 <div className="bg-white shadow-sm border-b">
 <div className="max-w-7xl mx-auto px-4 py-4">
 <div className="flex items-center justify-between">
 <div>
 <h1 className="text-2xl font-bold text-gray-900">
 Optimized Assessment
 </h1>
 <p className="text-gray-600 mt-1">
 Enhanced with state persistence, auto-save, and intelligent caching
 </p>
 </div>

 {/* Performance Badge */}
 <div className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
 Optimized
 </div>
 </div>
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

 {/* State Management Panel */}
 <StateManagementPanel
 isDirty={state.isDirty}
 lastSaved={state.lastSaved}
 autoSaveEnabled={state.autoSaveEnabled}
 onToggleAutoSave={actions.toggleAutoSave}
 onSave={actions.saveState}
 onClear={actions.clearSavedState}
 />

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
 <div className="flex items-center justify-between mb-4">
 <h3 className="text-lg font-semibold">Assessment Summary</h3>
 <div className="text-sm text-green-600 bg-green-50 px-2 py-1 rounded">
 Cached Result
 </div>
 </div>
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
 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
 </svg>
 </div>
 <h3 className="text-lg font-medium mb-2">Ready for Optimized Assessment</h3>
 <p>Complete the form to generate a fast, cached compliance report</p>
 {state.lastSaved && (
 <p className="text-sm text-blue-600 mt-2">
 Previous session restored automatically
 </p>
 )}
 </div>
 </div>
 )}
 </div>
 </div>
 </div>
 </div>
 );
}
