'use client';

import React, { useState } from 'react';
import { usePersistentAssessment } from '@/hooks/assessment/usePersistentAssessment';
import { PropertySearch } from '@/components/property/PropertySearch';
import PropertyCard from '@/components/assessment/core/PropertyCard';
import ProvisionSearch from '@/components/assessment/core/ProvisionSearch';
import EnhancedComplianceChecklist from '@/components/assessment/core/EnhancedComplianceChecklist';
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

export default function ProfessionalComplianceAssessmentPage() {
 const [state, actions] = usePersistentAssessment();
 const [showProvisionSearch, setShowProvisionSearch] = useState(false);
 const [enhancedResults, setEnhancedResults] = useState<any>(null);
 const [enhancedLoading, setEnhancedLoading] = useState(false);

 const handleAddressSubmit = () => {
 // Property loading handled by PropertyCard
 };

 const runEnhancedAssessment = async () => {
 if (!state.formValid || !state.property) return;

 setEnhancedLoading(true);
 try {
 const response = await fetch('/api/compliance/enhanced', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 propertyId: state.property.propId,
 zone: state.property.zone,
 developmentType: state.developmentType,
 assessmentDate: state.assessmentDate,
 includeRecommendations: true,
 includeCitations: true,
 detailedAnalysis: true
 })
 });

 if (response.ok) {
 const data = await response.json();
 setEnhancedResults(data.data);
 }
 } catch (error) {
 console.error('Enhanced assessment failed:', error);
 } finally {
 setEnhancedLoading(false);
 }
 };

 return (
 <div className="min-h-screen bg-gray-50">
 {/* Header */}
 <div className="bg-white shadow-sm border-b">
 <div className="max-w-7xl mx-auto px-4 py-4">
 <div className="flex items-center justify-between">
 <div>
 <h1 className="text-2xl font-bold text-gray-900">
 Professional Compliance Assessment
 </h1>
 <p className="text-gray-600 mt-1">
 Advanced compliance analysis with provision search, citations, and recommendations
 </p>
 </div>

 {/* Professional Badge */}
 <div className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm font-medium">
 Professional
 </div>
 </div>
 </div>
 </div>

 {/* Main Content */}
 <div className="max-w-7xl mx-auto px-4 py-6">
 <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
 {/* Left Panel - Property & Controls */}
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

 {/* State Management */}
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

 {/* Assessment Actions */}
 {state.property && state.developmentType && (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Professional Analysis</h3>
 <div className="space-y-3">
 <AssessmentSubmitButton
 onClick={runEnhancedAssessment}
 loading={enhancedLoading}
 formValid={state.formValid}
 >
 {enhancedLoading
 ? 'Running Enhanced Analysis...'
 : 'Generate Professional Report'
 }
 </AssessmentSubmitButton>

 <button
 onClick={() => setShowProvisionSearch(!showProvisionSearch)}
 className="w-full px-4 py-2 border border-purple-300 text-purple-700 rounded-md hover:bg-purple-50 transition-colors"
 >
 {showProvisionSearch ? 'Hide' : 'Show'} Provision Search
 </button>
 </div>
 </div>
 )}
 </div>

 {/* Right Panel - Results & Tools */}
 <div className="lg:col-span-3 space-y-6">
 {/* Provision Search */}
 {showProvisionSearch && (
 <ProvisionSearch
 onProvisionSelect={(provision) => {
 console.log('Selected provision:', provision);
 }}
 initialFilters={{
 zones: state.property ? [state.property.zone] : undefined,
 status: ['current']
 }}
 />
 )}

 {/* Loading State */}
 {enhancedLoading && state.property && (
 <ComplianceLoading
 developmentType={state.developmentType as string}
 zone={state.property.zone}
 />
 )}

 {/* Enhanced Results */}
 {enhancedResults && (
 <EnhancedComplianceChecklist
 checks={enhancedResults.checks || []}
 citations={enhancedResults.citations || []}
 recommendations={enhancedResults.recommendations || []}
 nextSteps={enhancedResults.next_steps || []}
 analysisMetadata={enhancedResults.analysis_metadata}
 />
 )}

 {/* Empty State */}
 {!enhancedResults && !enhancedLoading && (
 <div className="bg-white border rounded-lg p-12 shadow-sm text-center">
 <div className="text-gray-500">
 <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
 <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
 </svg>
 </div>
 <h3 className="text-lg font-medium mb-2">Professional Assessment Ready</h3>
 <p>Complete the form to generate a comprehensive compliance analysis with citations and recommendations</p>
 {state.lastSaved && (
 <p className="text-sm text-purple-600 mt-2">
 Previous session restored with auto-save
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
