'use client';

import React, { createContext, useContext, useCallback, useEffect, useReducer, ReactNode } from 'react';
import { DevelopmentType, ValidationResult } from '@/components/development/types';

interface DevelopmentContextState {
 availableDevelopments: DevelopmentType[];
 selectedDevelopment: DevelopmentType | null;
 isLoading: boolean;
 error: string | null;
 filters: {
 category?: string;
 zoning?: string;
 searchTerm?: string;
 };
}

interface DevelopmentContextActions {
 setSelectedDevelopment: (development: DevelopmentType | null) => void;
 loadDevelopmentTypes: (propertyId?: string) => Promise<void>;
 updateFilters: (filters: Partial<DevelopmentContextState['filters']>) => void;
 clearSelection: () => void;
 validateDevelopment: (development: DevelopmentType, property: any) => ValidationResult;
}

type DevelopmentAction =
 | { type: 'SET_LOADING'; payload: boolean }
 | { type: 'SET_ERROR'; payload: string | null }
 | { type: 'SET_DEVELOPMENTS'; payload: DevelopmentType[] }
 | { type: 'SET_SELECTED'; payload: DevelopmentType | null }
 | { type: 'SET_FILTERS'; payload: Partial<DevelopmentContextState['filters']> }
 | { type: 'CLEAR_SELECTION' };

const initialState: DevelopmentContextState = {
 availableDevelopments: [],
 selectedDevelopment: null,
 isLoading: false,
 error: null,
 filters: {},
};

const developmentReducer = (
 state: DevelopmentContextState,
 action: DevelopmentAction
): DevelopmentContextState => {
 switch (action.type) {
 case 'SET_LOADING':
 return { ...state, isLoading: action.payload };
 case 'SET_ERROR':
 return { ...state, error: action.payload, isLoading: false };
 case 'SET_DEVELOPMENTS':
 return { ...state, availableDevelopments: action.payload, isLoading: false };
 case 'SET_SELECTED':
 return { ...state, selectedDevelopment: action.payload };
 case 'SET_FILTERS':
 return { ...state, filters: { ...state.filters, ...action.payload } };
 case 'CLEAR_SELECTION':
 return { ...state, selectedDevelopment: null };
 default:
 return state;
 }
};

const DevelopmentContext = createContext<
 (DevelopmentContextState & DevelopmentContextActions) | null
>(null);

export const useDevelopmentContext = () => {
 const context = useContext(DevelopmentContext);
 if (!context) {
 throw new Error('useDevelopmentContext must be used within a DevelopmentProvider');
 }
 return context;
};

interface DevelopmentProviderProps {
 children: ReactNode;
}

export const DevelopmentProvider: React.FC<DevelopmentProviderProps> = ({ children }) => {
 const [state, dispatch] = useReducer(developmentReducer, initialState);

 const loadDevelopmentTypes = useCallback(async (propertyId?: string) => {
 try {
 dispatch({ type: 'SET_LOADING', payload: true });

 const params = new URLSearchParams();
 if (propertyId) params.append('propertyId', propertyId);

 const response = await fetch(`/api/development-types?${params}`);
 if (!response.ok) {
 throw new Error('Failed to load development types');
 }

 const developments = await response.json();
 dispatch({ type: 'SET_DEVELOPMENTS', payload: developments });
 } catch (error) {
 dispatch({
 type: 'SET_ERROR',
 payload: error instanceof Error ? error.message : 'Unknown error',
 });
 }
 }, [dispatch]);

 const setSelectedDevelopment = useCallback((development: DevelopmentType | null) => {
 dispatch({ type: 'SET_SELECTED', payload: development });
 }, [dispatch]);

 const updateFilters = useCallback((filters: Partial<DevelopmentContextState['filters']>) => {
 dispatch({ type: 'SET_FILTERS', payload: filters });
 }, [dispatch]);

 const clearSelection = useCallback(() => {
 dispatch({ type: 'CLEAR_SELECTION' });
 }, [dispatch]);

 const validateDevelopment = useCallback((
 development: DevelopmentType,
 property: any
 ): ValidationResult => {
 const warnings: string[] = [];
 const errors: string[] = [];

 // Zone compatibility check
 if (property?.zoning && development.applicableZones.length > 0) {
 if (
 !development.applicableZones.includes(property.zoning) &&
 !development.applicableZones.includes('*')
 ) {
 warnings.push(`Development may not be permitted in ${property.zoning} zone`);
 }
 }

 // Lot size check
 if (development.minimumLotSize && property?.lotSize) {
 if (property.lotSize < development.minimumLotSize) {
 errors.push(
 `Lot size (${property.lotSize}m²) is below minimum requirement (${development.minimumLotSize}m²)`
 );
 }
 }

 return {
 isValid: errors.length === 0,
 warnings,
 errors,
 };
 }, []);

 const contextValue = {
 ...state,
 setSelectedDevelopment,
 loadDevelopmentTypes,
 updateFilters,
 clearSelection,
 validateDevelopment,
 };

 return (
 <DevelopmentContext.Provider value={contextValue}>
 {children}
 </DevelopmentContext.Provider>
 );
};
