'use client';

import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { ComplianceItem } from '@/components/compliance/EnhancedComplianceChecklist';

interface ChecklistContextState {
 items: ComplianceItem[];
 loading: boolean;
 error: string | null;
 selectedProperty: string | null;
 developmentType: string | null;
 zoneCode: string | null;
 progress: {
 total: number;
 compliant: number;
 nonCompliant: number;
 pending: number;
 notApplicable: number;
 };
}

interface ChecklistContextActions {
 loadChecklist: (propertyId: string, developmentType: string, zoneCode?: string) => Promise<void>;
 updateItemStatus: (itemId: string, status: ComplianceItem['status']) => void;
 addEvidence: (itemId: string, evidence: string) => void;
 removeEvidence: (itemId: string, evidenceIndex: number) => void;
 clearChecklist: () => void;
 refreshChecklist: () => Promise<void>;
}

type ChecklistAction =
 | { type: 'SET_LOADING'; payload: boolean }
 | { type: 'SET_ERROR'; payload: string | null }
 | { type: 'SET_ITEMS'; payload: ComplianceItem[] }
 | { type: 'SET_PROPERTY_DATA'; payload: { propertyId: string; developmentType: string; zoneCode?: string } }
 | { type: 'UPDATE_ITEM_STATUS'; payload: { itemId: string; status: ComplianceItem['status'] } }
 | { type: 'ADD_EVIDENCE'; payload: { itemId: string; evidence: string } }
 | { type: 'REMOVE_EVIDENCE'; payload: { itemId: string; evidenceIndex: number } }
 | { type: 'CLEAR_CHECKLIST' };

const initialState: ChecklistContextState = {
 items: [],
 loading: false,
 error: null,
 selectedProperty: null,
 developmentType: null,
 zoneCode: null,
 progress: {
 total: 0,
 compliant: 0,
 nonCompliant: 0,
 pending: 0,
 notApplicable: 0,
 },
};

const calculateProgress = (items: ComplianceItem[]) => {
 return {
 total: items.length,
 compliant: items.filter(item => item.status === 'compliant').length,
 nonCompliant: items.filter(item => item.status === 'non-compliant').length,
 pending: items.filter(item => item.status === 'pending').length,
 notApplicable: items.filter(item => item.status === 'not-applicable').length,
 };
};

const checklistReducer = (
 state: ChecklistContextState,
 action: ChecklistAction
): ChecklistContextState => {
 switch (action.type) {
 case 'SET_LOADING':
 return { ...state, loading: action.payload };

 case 'SET_ERROR':
 return { ...state, error: action.payload, loading: false };

 case 'SET_ITEMS': {
 const items = action.payload;
 return {
 ...state,
 items,
 loading: false,
 error: null,
 progress: calculateProgress(items)
 };
 }

 case 'SET_PROPERTY_DATA':
 return {
 ...state,
 selectedProperty: action.payload.propertyId,
 developmentType: action.payload.developmentType,
 zoneCode: action.payload.zoneCode || null,
 };

 case 'UPDATE_ITEM_STATUS': {
 const updatedItems = state.items.map(item =>
 item.id === action.payload.itemId
 ? { ...item, status: action.payload.status }
 : item
 );
 return {
 ...state,
 items: updatedItems,
 progress: calculateProgress(updatedItems)
 };
 }

 case 'ADD_EVIDENCE': {
 const updatedItems = state.items.map(item =>
 item.id === action.payload.itemId
 ? {
 ...item,
 evidence: [...(item.evidence || []), action.payload.evidence]
 }
 : item
 );
 return { ...state, items: updatedItems };
 }

 case 'REMOVE_EVIDENCE': {
 const updatedItems = state.items.map(item =>
 item.id === action.payload.itemId
 ? {
 ...item,
 evidence: item.evidence?.filter((_, index) => index !== action.payload.evidenceIndex) || []
 }
 : item
 );
 return { ...state, items: updatedItems };
 }

 case 'CLEAR_CHECKLIST':
 return {
 ...initialState,
 };

 default:
 return state;
 }
};

const ChecklistContext = createContext<
 (ChecklistContextState & ChecklistContextActions) | null
>(null);

export const useChecklistContext = () => {
 const context = useContext(ChecklistContext);
 if (!context) {
 throw new Error('useChecklistContext must be used within a ChecklistProvider');
 }
 return context;
};

interface ChecklistProviderProps {
 children: ReactNode;
}

export const ChecklistProvider: React.FC<ChecklistProviderProps> = ({ children }) => {
 const [state, dispatch] = useReducer(checklistReducer, initialState);

 const loadChecklist = async (propertyId: string, developmentType: string, zoneCode?: string) => {
 try {
 dispatch({ type: 'SET_LOADING', payload: true });
 dispatch({
 type: 'SET_PROPERTY_DATA',
 payload: { propertyId, developmentType, zoneCode }
 });

 const params = new URLSearchParams();
 params.append('propertyId', propertyId);
 params.append('developmentType', developmentType);
 if (zoneCode) params.append('zoneCode', zoneCode);

 const response = await fetch(`/api/compliance/checklist?${params}`);
 if (!response.ok) {
 throw new Error(`HTTP ${response.status}: Failed to load checklist`);
 }

 const data = await response.json();
 dispatch({ type: 'SET_ITEMS', payload: data.items || [] });
 } catch (error) {
 const errorMessage = error instanceof Error ? error.message : 'Failed to load checklist';
 dispatch({ type: 'SET_ERROR', payload: errorMessage });
 console.error('Error loading checklist:', error);
 }
 };

 const updateItemStatus = (itemId: string, status: ComplianceItem['status']) => {
 dispatch({ type: 'UPDATE_ITEM_STATUS', payload: { itemId, status } });

 // Optionally sync with backend
 fetch('/api/compliance/checklist', {
 method: 'PATCH',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ itemId, status }),
 }).catch(error => {
 console.error('Failed to sync status update:', error);
 });
 };

 const addEvidence = (itemId: string, evidence: string) => {
 dispatch({ type: 'ADD_EVIDENCE', payload: { itemId, evidence } });
 };

 const removeEvidence = (itemId: string, evidenceIndex: number) => {
 dispatch({ type: 'REMOVE_EVIDENCE', payload: { itemId, evidenceIndex } });
 };

 const clearChecklist = () => {
 dispatch({ type: 'CLEAR_CHECKLIST' });
 };

 const refreshChecklist = async () => {
 if (state.selectedProperty && state.developmentType) {
 await loadChecklist(state.selectedProperty, state.developmentType, state.zoneCode || undefined);
 }
 };

 const contextValue = {
 ...state,
 loadChecklist,
 updateItemStatus,
 addEvidence,
 removeEvidence,
 clearChecklist,
 refreshChecklist,
 };

 return (
 <ChecklistContext.Provider value={contextValue}>
 {children}
 </ChecklistContext.Provider>
 );
};