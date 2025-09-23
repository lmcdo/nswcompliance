'use client';

import { useState, useCallback, useEffect } from 'react';
import { assessmentAPI } from '@/lib/assessment/api-client';
import { PropertyData, DevelopmentType, VersionInfo } from '@/lib/assessment/types';

export interface AssessmentState {
 // Property data
 address: string;
 property: PropertyData | null;
 propertyLoading: boolean;
 propertyError: string | null;

 // Development type
 developmentType: DevelopmentType | '';
 developmentTypeError: string | null;

 // Version management
 assessmentDate: string;
 selectedVersion: VersionInfo | null;
 useHistoricalVersion: boolean;

 // Compliance data
 complianceData: any | null;
 complianceLoading: boolean;
 complianceError: string | null;

 // Form validation
 formValid: boolean;
 validationErrors: string[];

 // UI state
 showResults: boolean;
 lastAssessmentRun: string | null;
}

export interface AssessmentActions {
 setAddress: (address: string) => void;
 setProperty: (property: PropertyData | null) => void;
 setDevelopmentType: (type: DevelopmentType | '') => void;
 setAssessmentDate: (date: string) => void;
 setSelectedVersion: (version: VersionInfo | null) => void;
 setUseHistoricalVersion: (use: boolean) => void;
 runAssessment: () => Promise<void>;
 clearAssessment: () => void;
 resetForm: () => void;
}

const initialState: AssessmentState = {
 address: '',
 property: null,
 propertyLoading: false,
 propertyError: null,
 developmentType: '',
 developmentTypeError: null,
 assessmentDate: new Date().toISOString().split('T')[0],
 selectedVersion: null,
 useHistoricalVersion: false,
 complianceData: null,
 complianceLoading: false,
 complianceError: null,
 formValid: false,
 validationErrors: [],
 showResults: false,
 lastAssessmentRun: null
};

export function useAssessment() {
 const [state, setState] = useState<AssessmentState>(initialState);

 // Validate form whenever dependencies change
 useEffect(() => {
 validateForm();
 }, [state.property, state.developmentType, state.assessmentDate]);

 const validateForm = useCallback(() => {
 const errors: string[] = [];

 if (!state.property) {
 errors.push('Property address is required');
 }

 if (!state.developmentType) {
 errors.push('Development type is required');
 }

 if (!state.assessmentDate) {
 errors.push('Assessment date is required');
 }

 const isValid = errors.length === 0;

 setState(prev => ({
 ...prev,
 formValid: isValid,
 validationErrors: errors
 }));
 }, [state.property, state.developmentType, state.assessmentDate]);

 const setAddress = useCallback((address: string) => {
 setState(prev => ({
 ...prev,
 address,
 property: null,
 propertyError: null,
 showResults: false,
 complianceData: null
 }));
 }, []);

 const setProperty = useCallback((property: PropertyData | null) => {
 setState(prev => ({
 ...prev,
 property,
 propertyError: property ? null : 'Failed to load property data'
 }));
 }, []);

 const setDevelopmentType = useCallback((developmentType: DevelopmentType | '') => {
 setState(prev => ({
 ...prev,
 developmentType,
 developmentTypeError: null,
 showResults: false,
 complianceData: null
 }));
 }, []);

 const setAssessmentDate = useCallback((assessmentDate: string) => {
 setState(prev => ({
 ...prev,
 assessmentDate,
 showResults: false,
 complianceData: null
 }));
 }, []);

 const setSelectedVersion = useCallback((selectedVersion: VersionInfo | null) => {
 setState(prev => ({
 ...prev,
 selectedVersion,
 showResults: false,
 complianceData: null
 }));
 }, []);

 const setUseHistoricalVersion = useCallback((useHistoricalVersion: boolean) => {
 setState(prev => ({
 ...prev,
 useHistoricalVersion,
 showResults: false,
 complianceData: null
 }));
 }, []);

 const runAssessment = useCallback(async () => {
 if (!state.formValid || !state.property) return;

 setState(prev => ({
 ...prev,
 complianceLoading: true,
 complianceError: null,
 showResults: false
 }));

 try {
 const result = await assessmentAPI.getCompliance({
 propertyId: state.property.propId,
 zone: state.property.zone,
 developmentType: state.developmentType as DevelopmentType,
 assessmentDate: state.assessmentDate
 });

 setState(prev => ({
 ...prev,
 complianceData: result,
 complianceLoading: false,
 showResults: true,
 lastAssessmentRun: new Date().toISOString()
 }));
 } catch (error) {
 setState(prev => ({
 ...prev,
 complianceError: error instanceof Error ? error.message : 'Assessment failed',
 complianceLoading: false,
 showResults: false
 }));
 }
 }, [state.formValid, state.property, state.developmentType, state.assessmentDate]);

 const clearAssessment = useCallback(() => {
 setState(prev => ({
 ...prev,
 complianceData: null,
 complianceError: null,
 showResults: false,
 lastAssessmentRun: null
 }));
 }, []);

 const resetForm = useCallback(() => {
 setState(initialState);
 }, []);

 const actions: AssessmentActions = {
 setAddress,
 setProperty,
 setDevelopmentType,
 setAssessmentDate,
 setSelectedVersion,
 setUseHistoricalVersion,
 runAssessment,
 clearAssessment,
 resetForm
 };

 return [state, actions] as const;
}
