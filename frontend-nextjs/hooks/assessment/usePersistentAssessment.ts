'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { assessmentAPI } from '@/lib/assessment/api-client';
import { PropertyData, DevelopmentType, VersionInfo } from '@/lib/assessment/types';
import { AssessmentStorage, STORAGE_CONFIGS } from '@/lib/assessment/storage';
import { cachedFetch } from '@/lib/assessment/cache';

export interface PersistentAssessmentState {
 // Core assessment data
 address: string;
 property: PropertyData | null;
 developmentType: DevelopmentType | '';
 assessmentDate: string;
 selectedVersion: VersionInfo | null;
 useHistoricalVersion: boolean;

 // UI state
 propertyLoading: boolean;
 propertyError: string | null;
 complianceLoading: boolean;
 complianceError: string | null;
 complianceData: any | null;

 // Form validation
 formValid: boolean;
 validationErrors: string[];

 // Persistence state
 autoSaveEnabled: boolean;
 lastSaved: string | null;
 isDirty: boolean;
 showResults: boolean;
}

export interface PersistentAssessmentActions {
 // Core actions
 setAddress: (address: string) => void;
 setProperty: (property: PropertyData | null) => void;
 setDevelopmentType: (type: DevelopmentType | '') => void;
 setAssessmentDate: (date: string) => void;
 setSelectedVersion: (version: VersionInfo | null) => void;
 setUseHistoricalVersion: (use: boolean) => void;

 // Assessment actions
 runAssessment: () => Promise<void>;
 clearAssessment: () => void;
 resetForm: () => void;

 // Persistence actions
 saveState: () => void;
 loadState: () => void;
 toggleAutoSave: () => void;
 clearSavedState: () => void;
}

const initialState: PersistentAssessmentState = {
 address: '',
 property: null,
 developmentType: '',
 assessmentDate: new Date().toISOString().split('T')[0],
 selectedVersion: null,
 useHistoricalVersion: false,
 propertyLoading: false,
 propertyError: null,
 complianceLoading: false,
 complianceError: null,
 complianceData: null,
 formValid: false,
 validationErrors: [],
 autoSaveEnabled: true,
 lastSaved: null,
 isDirty: false,
 showResults: false
};

export function usePersistentAssessment() {
 const [state, setState] = useState<PersistentAssessmentState>(initialState);
 const autoSaveTimeoutRef = useRef<NodeJS.Timeout>();
 const lastStateRef = useRef<string>('');

 // Auto-save functionality
 useEffect(() => {
 if (!state.autoSaveEnabled || !state.isDirty) return;

 // Clear existing timeout
 if (autoSaveTimeoutRef.current) {
 clearTimeout(autoSaveTimeoutRef.current);
 }

 // Set new timeout for auto-save
 autoSaveTimeoutRef.current = setTimeout(() => {
 saveState();
 }, 2000); // Auto-save after 2 seconds of inactivity

 return () => {
 if (autoSaveTimeoutRef.current) {
 clearTimeout(autoSaveTimeoutRef.current);
 }
 };
 }, [state.isDirty, state.autoSaveEnabled]);

 // Load saved state on mount
 useEffect(() => {
 loadState();
 }, []);

 // Track state changes for dirty detection
 useEffect(() => {
 const currentStateString = JSON.stringify({
 address: state.address,
 property: state.property,
 developmentType: state.developmentType,
 assessmentDate: state.assessmentDate,
 selectedVersion: state.selectedVersion,
 useHistoricalVersion: state.useHistoricalVersion
 });

 const isDirty = currentStateString !== lastStateRef.current && lastStateRef.current !== '';

 if (isDirty !== state.isDirty) {
 setState(prev => ({ ...prev, isDirty }));
 }

 lastStateRef.current = currentStateString;
 }, [state.address, state.property, state.developmentType, state.assessmentDate, state.selectedVersion, state.useHistoricalVersion]);

 // Form validation
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
 const endpoint = '/api/assessment';
 const params = {
 action: 'getCompliance',
 propertyId: state.property.propId,
 zone: state.property.zone,
 developmentType: state.developmentType,
 assessmentDate: state.assessmentDate
 };

 // Use cached fetch for better performance
 const result = await cachedFetch(endpoint, {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify(params)
 }, params, { ttl: 15 * 60 * 1000 }); // 15 minute cache

 setState(prev => ({
 ...prev,
 complianceData: result.data,
 complianceLoading: false,
 showResults: true
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
 showResults: false
 }));
 }, []);

 const resetForm = useCallback(() => {
 setState(initialState);
 lastStateRef.current = '';
 }, []);

 const saveState = useCallback(() => {
 const stateToSave = {
 address: state.address,
 property: state.property,
 developmentType: state.developmentType,
 assessmentDate: state.assessmentDate,
 selectedVersion: state.selectedVersion,
 useHistoricalVersion: state.useHistoricalVersion,
 complianceData: state.complianceData,
 showResults: state.showResults
 };

 const saved = AssessmentStorage.save(STORAGE_CONFIGS.ASSESSMENT_STATE, stateToSave);

 if (saved) {
 setState(prev => ({
 ...prev,
 lastSaved: new Date().toISOString(),
 isDirty: false
 }));
 }
 }, [state]);

 const loadState = useCallback(() => {
 const savedState = AssessmentStorage.load(STORAGE_CONFIGS.ASSESSMENT_STATE);

 if (savedState) {
 setState(prev => ({
 ...prev,
 ...savedState,
 propertyLoading: false,
 complianceLoading: false,
 propertyError: null,
 complianceError: null,
 formValid: false,
 validationErrors: [],
 autoSaveEnabled: prev.autoSaveEnabled,
 lastSaved: new Date().toISOString(),
 isDirty: false
 }));
 }
 }, []);

 const toggleAutoSave = useCallback(() => {
 setState(prev => ({
 ...prev,
 autoSaveEnabled: !prev.autoSaveEnabled
 }));
 }, []);

 const clearSavedState = useCallback(() => {
 AssessmentStorage.remove(STORAGE_CONFIGS.ASSESSMENT_STATE);
 setState(prev => ({
 ...prev,
 lastSaved: null,
 isDirty: false
 }));
 }, []);

 const actions: PersistentAssessmentActions = {
 setAddress,
 setProperty,
 setDevelopmentType,
 setAssessmentDate,
 setSelectedVersion,
 setUseHistoricalVersion,
 runAssessment,
 clearAssessment,
 resetForm,
 saveState,
 loadState,
 toggleAutoSave,
 clearSavedState
 };

 return [state, actions] as const;
}
