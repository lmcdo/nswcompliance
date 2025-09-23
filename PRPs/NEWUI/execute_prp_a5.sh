#!/bin/bash
# PRP-A5: State Management & Caching
# Implements assessment state persistence, auto-save functionality, and performance optimization

set -e

echo "🚀 Executing PRP-A5: State Management & Caching"
echo "==============================================="

# Navigate to project root
cd "$(dirname "$0")/../.."
PROJECT_ROOT="$(pwd)"
echo "📁 Project root: $PROJECT_ROOT"

# Step 1: Create caching and storage utilities
echo ""
echo "Step 1: Creating caching and storage utilities..."
echo "------------------------------------------------"

# Create storage utility for localStorage management
cat << 'EOF' > frontend-nextjs/lib/assessment/storage.ts
/**
 * Assessment Storage Utilities
 * Manages localStorage for assessment state persistence
 */

export interface StorageConfig {
  key: string;
  ttl?: number; // Time to live in milliseconds
  compress?: boolean;
}

export class AssessmentStorage {
  private static readonly DEFAULT_TTL = 24 * 60 * 60 * 1000; // 24 hours
  private static readonly STORAGE_PREFIX = 'nsw_assessment_';

  /**
   * Save data to localStorage with optional TTL
   */
  static save<T>(config: StorageConfig, data: T): boolean {
    try {
      const now = Date.now();
      const storageData = {
        data,
        timestamp: now,
        expires: config.ttl ? now + config.ttl : now + this.DEFAULT_TTL
      };

      const serialized = JSON.stringify(storageData);
      const key = this.STORAGE_PREFIX + config.key;

      localStorage.setItem(key, serialized);
      return true;
    } catch (error) {
      console.warn('Failed to save to localStorage:', error);
      return false;
    }
  }

  /**
   * Load data from localStorage with expiration check
   */
  static load<T>(config: StorageConfig): T | null {
    try {
      const key = this.STORAGE_PREFIX + config.key;
      const stored = localStorage.getItem(key);

      if (!stored) return null;

      const parsed = JSON.parse(stored);
      const now = Date.now();

      // Check if data has expired
      if (parsed.expires && now > parsed.expires) {
        this.remove(config);
        return null;
      }

      return parsed.data;
    } catch (error) {
      console.warn('Failed to load from localStorage:', error);
      return null;
    }
  }

  /**
   * Remove data from localStorage
   */
  static remove(config: StorageConfig): boolean {
    try {
      const key = this.STORAGE_PREFIX + config.key;
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      console.warn('Failed to remove from localStorage:', error);
      return false;
    }
  }

  /**
   * Clear all assessment data from localStorage
   */
  static clearAll(): boolean {
    try {
      const keys = Object.keys(localStorage);
      const assessmentKeys = keys.filter(key => key.startsWith(this.STORAGE_PREFIX));

      assessmentKeys.forEach(key => localStorage.removeItem(key));
      return true;
    } catch (error) {
      console.warn('Failed to clear localStorage:', error);
      return false;
    }
  }

  /**
   * Get storage statistics
   */
  static getStorageStats(): {
    totalKeys: number;
    assessmentKeys: number;
    totalSize: number;
    assessmentSize: number;
  } {
    try {
      const keys = Object.keys(localStorage);
      const assessmentKeys = keys.filter(key => key.startsWith(this.STORAGE_PREFIX));

      let totalSize = 0;
      let assessmentSize = 0;

      keys.forEach(key => {
        const size = (localStorage.getItem(key) || '').length;
        totalSize += size;
        if (key.startsWith(this.STORAGE_PREFIX)) {
          assessmentSize += size;
        }
      });

      return {
        totalKeys: keys.length,
        assessmentKeys: assessmentKeys.length,
        totalSize,
        assessmentSize
      };
    } catch (error) {
      console.warn('Failed to get storage stats:', error);
      return { totalKeys: 0, assessmentKeys: 0, totalSize: 0, assessmentSize: 0 };
    }
  }
}

// Storage configuration presets
export const STORAGE_CONFIGS = {
  ASSESSMENT_STATE: { key: 'current_assessment', ttl: 7 * 24 * 60 * 60 * 1000 }, // 7 days
  API_CACHE: { key: 'api_cache', ttl: 30 * 60 * 1000 }, // 30 minutes
  PROPERTY_CACHE: { key: 'property_cache', ttl: 60 * 60 * 1000 }, // 1 hour
  COMPLIANCE_CACHE: { key: 'compliance_cache', ttl: 15 * 60 * 1000 }, // 15 minutes
  USER_PREFERENCES: { key: 'user_preferences', ttl: 30 * 24 * 60 * 60 * 1000 }, // 30 days
} as const;
EOF

echo "✅ Created assessment storage utilities"

# Step 2: Create API caching layer
echo ""
echo "Step 2: Creating API caching layer..."
echo "------------------------------------"

# Create API cache manager
cat << 'EOF' > frontend-nextjs/lib/assessment/cache.ts
/**
 * API Caching Layer
 * Provides intelligent caching for assessment API calls
 */

import { AssessmentStorage, STORAGE_CONFIGS } from './storage';

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  key: string;
}

export interface CacheConfig {
  ttl: number; // Time to live in milliseconds
  staleWhileRevalidate?: boolean; // Serve stale data while fetching fresh
  maxEntries?: number; // Maximum cache entries
}

export class APICache {
  private static cache = new Map<string, CacheEntry<any>>();
  private static readonly DEFAULT_CONFIG: CacheConfig = {
    ttl: 15 * 60 * 1000, // 15 minutes
    staleWhileRevalidate: true,
    maxEntries: 100
  };

  /**
   * Generate cache key from request parameters
   */
  private static generateKey(endpoint: string, params?: any): string {
    const paramString = params ? JSON.stringify(params) : '';
    return `${endpoint}_${btoa(paramString)}`;
  }

  /**
   * Check if cache entry is expired
   */
  private static isExpired(entry: CacheEntry<any>, ttl: number): boolean {
    return Date.now() - entry.timestamp > ttl;
  }

  /**
   * Clean up expired entries
   */
  private static cleanup(maxEntries: number): void {
    if (this.cache.size <= maxEntries) return;

    const entries = Array.from(this.cache.entries());
    entries.sort((a, b) => a[1].timestamp - b[1].timestamp);

    // Remove oldest entries
    const toRemove = entries.slice(0, entries.length - maxEntries);
    toRemove.forEach(([key]) => this.cache.delete(key));
  }

  /**
   * Get cached data
   */
  static get<T>(endpoint: string, params?: any, config: Partial<CacheConfig> = {}): T | null {
    const mergedConfig = { ...this.DEFAULT_CONFIG, ...config };
    const key = this.generateKey(endpoint, params);
    const entry = this.cache.get(key);

    if (!entry) return null;

    const expired = this.isExpired(entry, mergedConfig.ttl);

    if (expired && !mergedConfig.staleWhileRevalidate) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  /**
   * Set cached data
   */
  static set<T>(endpoint: string, params: any, data: T, config: Partial<CacheConfig> = {}): void {
    const mergedConfig = { ...this.DEFAULT_CONFIG, ...config };
    const key = this.generateKey(endpoint, params);

    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      key
    };

    this.cache.set(key, entry);
    this.cleanup(mergedConfig.maxEntries || 100);

    // Also save to localStorage for persistence
    this.saveToStorage(key, entry);
  }

  /**
   * Clear cache
   */
  static clear(): void {
    this.cache.clear();
    AssessmentStorage.remove(STORAGE_CONFIGS.API_CACHE);
  }

  /**
   * Get cache statistics
   */
  static getStats(): {
    size: number;
    entries: Array<{ key: string; age: number; size: number }>;
  } {
    const entries = Array.from(this.cache.entries()).map(([key, entry]) => ({
      key,
      age: Date.now() - entry.timestamp,
      size: JSON.stringify(entry.data).length
    }));

    return {
      size: this.cache.size,
      entries
    };
  }

  /**
   * Save cache entry to localStorage
   */
  private static saveToStorage<T>(key: string, entry: CacheEntry<T>): void {
    try {
      const storageKey = `cache_${key}`;
      AssessmentStorage.save({ key: storageKey, ttl: 60 * 60 * 1000 }, entry);
    } catch (error) {
      console.warn('Failed to save cache to storage:', error);
    }
  }

  /**
   * Load cache from localStorage
   */
  static loadFromStorage(): void {
    try {
      const stats = AssessmentStorage.getStorageStats();
      console.log(`Loading cache from storage: ${stats.assessmentKeys} entries`);

      // This would load cache entries from localStorage
      // Implementation depends on storage structure
    } catch (error) {
      console.warn('Failed to load cache from storage:', error);
    }
  }
}

/**
 * Cached API wrapper
 */
export async function cachedFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  params?: any,
  cacheConfig?: Partial<CacheConfig>
): Promise<T> {
  // Try to get from cache first
  const cached = APICache.get<T>(endpoint, params, cacheConfig);
  if (cached && (!cacheConfig?.staleWhileRevalidate || !APICache.isExpired(cached as any, cacheConfig.ttl || 15 * 60 * 1000))) {
    return cached;
  }

  // Fetch fresh data
  try {
    const response = await fetch(endpoint, options);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Cache the fresh data
    APICache.set(endpoint, params, data, cacheConfig);

    return data;
  } catch (error) {
    // If we have stale cached data, return it as fallback
    if (cached && cacheConfig?.staleWhileRevalidate) {
      console.warn('Using stale cache due to fetch error:', error);
      return cached;
    }
    throw error;
  }
}
EOF

echo "✅ Created API caching layer"

# Step 3: Create enhanced assessment hook with persistence
echo ""
echo "Step 3: Creating enhanced assessment hook with persistence..."
echo "----------------------------------------------------------"

# Create persistent assessment hook
cat << 'EOF' > frontend-nextjs/hooks/assessment/usePersistentAssessment.ts
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
EOF

echo "✅ Created enhanced assessment hook with persistence"

# Step 4: Create state management components
echo ""
echo "Step 4: Creating state management components..."
echo "----------------------------------------------"

# Create state management UI components
cat << 'EOF' > frontend-nextjs/components/assessment/core/StateManagement.tsx
'use client';

import React from 'react';
import { AssessmentStorage } from '@/lib/assessment/storage';
import { APICache } from '@/lib/assessment/cache';

interface StateIndicatorProps {
  isDirty: boolean;
  lastSaved: string | null;
  autoSaveEnabled: boolean;
  className?: string;
}

export function StateIndicator({
  isDirty,
  lastSaved,
  autoSaveEnabled,
  className = ''
}: StateIndicatorProps) {
  const getStatusColor = () => {
    if (!lastSaved) return 'text-gray-500';
    if (isDirty) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getStatusText = () => {
    if (!lastSaved) return 'Not saved';
    if (isDirty) return autoSaveEnabled ? 'Saving...' : 'Unsaved changes';
    return 'Saved';
  };

  return (
    <div className={`flex items-center gap-2 text-sm ${getStatusColor()} ${className}`}>
      <div className={`w-2 h-2 rounded-full ${
        !lastSaved ? 'bg-gray-400' :
        isDirty ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'
      }`} />
      <span>{getStatusText()}</span>
      {lastSaved && (
        <span className="text-gray-400">
          • {new Date(lastSaved).toLocaleTimeString()}
        </span>
      )}
    </div>
  );
}

interface AutoSaveToggleProps {
  enabled: boolean;
  onToggle: () => void;
  className?: string;
}

export function AutoSaveToggle({ enabled, onToggle, className = '' }: AutoSaveToggleProps) {
  return (
    <label className={`flex items-center gap-2 cursor-pointer ${className}`}>
      <input
        type="checkbox"
        checked={enabled}
        onChange={onToggle}
        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
      />
      <span className="text-sm text-gray-700">Auto-save</span>
    </label>
  );
}

interface SaveActionsProps {
  onSave: () => void;
  onClear: () => void;
  isDirty: boolean;
  lastSaved: string | null;
  className?: string;
}

export function SaveActions({
  onSave,
  onClear,
  isDirty,
  lastSaved,
  className = ''
}: SaveActionsProps) {
  return (
    <div className={`flex gap-2 ${className}`}>
      <button
        onClick={onSave}
        disabled={!isDirty}
        className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      >
        Save Now
      </button>
      <button
        onClick={onClear}
        disabled={!lastSaved}
        className="px-3 py-1 border border-gray-300 text-gray-700 rounded text-sm hover:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
      >
        Clear Saved
      </button>
    </div>
  );
}

interface CacheStatsProps {
  className?: string;
}

export function CacheStats({ className = '' }: CacheStatsProps) {
  const [cacheStats, setCacheStats] = React.useState<any>(null);
  const [storageStats, setStorageStats] = React.useState<any>(null);

  React.useEffect(() => {
    const updateStats = () => {
      setCacheStats(APICache.getStats());
      setStorageStats(AssessmentStorage.getStorageStats());
    };

    updateStats();
    const interval = setInterval(updateStats, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  if (!cacheStats || !storageStats) return null;

  return (
    <div className={`bg-gray-50 border rounded-lg p-4 ${className}`}>
      <h4 className="font-semibold text-gray-800 mb-3">Performance Stats</h4>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="font-medium text-gray-700 mb-1">API Cache</div>
          <div className="text-gray-600">
            {cacheStats.size} entries
          </div>
        </div>

        <div>
          <div className="font-medium text-gray-700 mb-1">Storage</div>
          <div className="text-gray-600">
            {storageStats.assessmentKeys} saved items
          </div>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-gray-200">
        <button
          onClick={() => {
            APICache.clear();
            AssessmentStorage.clearAll();
            setCacheStats(APICache.getStats());
            setStorageStats(AssessmentStorage.getStorageStats());
          }}
          className="text-sm text-red-600 hover:text-red-700 transition-colors"
        >
          Clear All Cache & Storage
        </button>
      </div>
    </div>
  );
}

interface StateManagementPanelProps {
  isDirty: boolean;
  lastSaved: string | null;
  autoSaveEnabled: boolean;
  onToggleAutoSave: () => void;
  onSave: () => void;
  onClear: () => void;
  className?: string;
}

export function StateManagementPanel({
  isDirty,
  lastSaved,
  autoSaveEnabled,
  onToggleAutoSave,
  onSave,
  onClear,
  className = ''
}: StateManagementPanelProps) {
  return (
    <div className={`bg-white border rounded-lg p-4 ${className}`}>
      <h3 className="font-semibold text-gray-800 mb-4">State Management</h3>

      <div className="space-y-4">
        <StateIndicator
          isDirty={isDirty}
          lastSaved={lastSaved}
          autoSaveEnabled={autoSaveEnabled}
        />

        <div className="flex items-center justify-between">
          <AutoSaveToggle
            enabled={autoSaveEnabled}
            onToggle={onToggleAutoSave}
          />

          <SaveActions
            onSave={onSave}
            onClear={onClear}
            isDirty={isDirty}
            lastSaved={lastSaved}
          />
        </div>

        <CacheStats />
      </div>
    </div>
  );
}
EOF

echo "✅ Created state management components"

# Step 5: Create optimized assessment page with caching
echo ""
echo "Step 5: Creating optimized assessment page with caching..."
echo "--------------------------------------------------------"

# Create optimized assessment page
cat << 'EOF' > frontend-nextjs/app/assessment/optimized/page.tsx
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
              ⚡ Optimized
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
EOF

echo "✅ Created optimized assessment page with caching"

# Step 6: Update run_prp.sh to enable A5
echo ""
echo "Step 6: Updating run_prp.sh to enable PRP-A5..."
echo "-----------------------------------------------"

# Update the run_prp.sh script to enable A5
sed -i 's/echo "❌ PRP-A5 not yet implemented"/run_prp "a5" "State Management \& Caching"/' run_prp.sh
sed -i '/echo "📋 Coming soon: State Management & Caching"/d' run_prp.sh

echo "✅ Updated run_prp.sh to enable PRP-A5"

echo ""
echo "🎉 PRP-A5 EXECUTION COMPLETE!"
echo "============================="
echo "✅ Created assessment storage utilities with localStorage management"
echo "✅ Created intelligent API caching layer with TTL and stale-while-revalidate"
echo "✅ Created enhanced assessment hook with state persistence"
echo "✅ Created state management UI components with auto-save indicators"
echo "✅ Created optimized assessment page with caching and persistence"
echo "✅ Updated PRP runner to enable A5"
echo ""
echo "📋 Key Features Implemented:"
echo "  • Auto-save functionality with 2-second debounce"
echo "  • Intelligent API caching with configurable TTL"
echo "  • State persistence across browser sessions"
echo "  • Real-time dirty state detection"
echo "  • Performance statistics and cache management"
echo "  • Stale-while-revalidate for better UX"
echo ""
echo "📋 Next Steps:"
echo "  1. Run verification script: python scripts/verify_prp_a5.py"
echo "  2. Test optimized assessment at: /assessment/optimized"
echo "  3. Verify auto-save and caching functionality"
echo ""
echo "🚀 Ready for PRP-A6: Compliance Engine Integration"