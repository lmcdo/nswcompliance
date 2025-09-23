#!/bin/bash
# PRP-UI2 Execution Script: DevelopmentSelector Component Migration
# Week 2 - Days 8-14

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend-nextjs"
PRP_DIR="$PROJECT_ROOT/PRPs/NEWUI/AUTHORITATIVErouteUI"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites for PRP-UI2..."

    # Check if PRP-UI1 was completed
    if [[ ! -f "$FRONTEND_DIR/lib/feature-flags.ts" ]]; then
        error "PRP-UI1 not completed. Please run execute_prp_ui1.sh first"
        exit 1
    fi

    # Check Redux Toolkit
    cd "$FRONTEND_DIR"
    if ! npm list @reduxjs/toolkit &> /dev/null; then
        log "Installing Redux Toolkit..."
        npm install @reduxjs/toolkit react-redux
    fi

    success "Prerequisites check passed"
}

# Create directory structure
create_directories() {
    log "Creating directory structure for DevelopmentSelector..."

    directories=(
        "$FRONTEND_DIR/components/development"
        "$FRONTEND_DIR/contexts"
        "$FRONTEND_DIR/store"
        "$FRONTEND_DIR/store/slices"
        "$FRONTEND_DIR/pages/api"
        "$FRONTEND_DIR/__tests__/components/development"
        "$FRONTEND_DIR/__tests__/contexts"
        "$FRONTEND_DIR/__tests__/store"
    )

    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log "Created directory: $dir"
        fi
    done

    success "Directory structure created"
}

# Create development types
create_development_types() {
    log "Creating development type definitions..."

    cat > "$FRONTEND_DIR/components/development/types.ts" << 'EOF'
export interface DevelopmentType {
  id: string;
  code: string;
  name: string;
  description: string;
  category: 'residential' | 'commercial' | 'industrial' | 'mixed';
  complianceRequirements: string[];
  applicableZones: string[];
  minimumLotSize?: number;
  maximumHeight?: number;
  isEnabled: boolean;
}

export interface DevelopmentSelectorProps {
  selectedDevelopment?: DevelopmentType;
  onDevelopmentChange: (development: DevelopmentType | null) => void;
  propertyId?: string;
  zoning?: string;
  lotSize?: number;
  disabled?: boolean;
  variant?: 'default' | 'compact' | 'detailed';
  showDescription?: boolean;
  filterByZoning?: boolean;
}

export interface ValidationResult {
  isValid: boolean;
  warnings: string[];
  errors: string[];
}
EOF

    success "Development types created"
}

# Create Redux slice
create_redux_slice() {
    log "Creating development Redux slice..."

    cat > "$FRONTEND_DIR/store/slices/developmentSlice.ts" << 'EOF'
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { DevelopmentType } from '@/components/development/types';

export interface DevelopmentState {
  types: DevelopmentType[];
  selected: DevelopmentType | null;
  loading: boolean;
  error: string | null;
  filters: {
    category?: string;
    zoning?: string;
    searchTerm?: string;
  };
}

const initialState: DevelopmentState = {
  types: [],
  selected: null,
  loading: false,
  error: null,
  filters: {},
};

export const fetchDevelopmentTypes = createAsyncThunk(
  'development/fetchTypes',
  async (params: { propertyId?: string; zoning?: string }) => {
    const searchParams = new URLSearchParams();
    if (params.propertyId) searchParams.append('propertyId', params.propertyId);
    if (params.zoning) searchParams.append('zoning', params.zoning);

    const response = await fetch(`/api/development-types?${searchParams}`);
    if (!response.ok) {
      throw new Error('Failed to fetch development types');
    }
    return response.json();
  }
);

const developmentSlice = createSlice({
  name: 'development',
  initialState,
  reducers: {
    setSelectedDevelopment: (state, action: PayloadAction<DevelopmentType | null>) => {
      state.selected = action.payload;
    },
    updateFilters: (state, action: PayloadAction<Partial<DevelopmentState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearSelection: (state) => {
      state.selected = null;
    },
    clearError: (state) => {
      state.error = null;
    },
    resetFilters: (state) => {
      state.filters = {};
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDevelopmentTypes.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDevelopmentTypes.fulfilled, (state, action) => {
        state.loading = false;
        state.types = action.payload;
      })
      .addCase(fetchDevelopmentTypes.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to load development types';
      });
  },
});

export const {
  setSelectedDevelopment,
  updateFilters,
  clearSelection,
  clearError,
  resetFilters,
} = developmentSlice.actions;

export default developmentSlice.reducer;
EOF

    success "Redux slice created"
}

# Create Redux store
create_redux_store() {
    log "Creating Redux store..."

    cat > "$FRONTEND_DIR/store/index.ts" << 'EOF'
import { configureStore } from '@reduxjs/toolkit';
import developmentReducer from './slices/developmentSlice';

export const store = configureStore({
  reducer: {
    development: developmentReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
EOF

    success "Redux store created"
}

# Create Development Context
create_development_context() {
    log "Creating Development Context..."

    cat > "$FRONTEND_DIR/contexts/DevelopmentContext.tsx" << 'EOF'
'use client';

import React, { createContext, useContext, useEffect, useReducer, ReactNode } from 'react';
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

  const loadDevelopmentTypes = async (propertyId?: string) => {
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
  };

  const setSelectedDevelopment = (development: DevelopmentType | null) => {
    dispatch({ type: 'SET_SELECTED', payload: development });
  };

  const updateFilters = (filters: Partial<DevelopmentContextState['filters']>) => {
    dispatch({ type: 'SET_FILTERS', payload: filters });
  };

  const clearSelection = () => {
    dispatch({ type: 'CLEAR_SELECTION' });
  };

  const validateDevelopment = (
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
  };

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
EOF

    success "Development Context created"
}

# Create DevelopmentCard component
create_development_card() {
    log "Creating DevelopmentCard component..."

    cat > "$FRONTEND_DIR/components/development/DevelopmentCard.tsx" << 'EOF'
import React from 'react';
import { DevelopmentType, ValidationResult } from './types';

interface DevelopmentCardProps {
  development: DevelopmentType;
  isSelected: boolean;
  onSelect: () => void;
  showDescription: boolean;
  disabled: boolean;
  validation: ValidationResult | null;
}

export const DevelopmentCard: React.FC<DevelopmentCardProps> = ({
  development,
  isSelected,
  onSelect,
  showDescription,
  disabled,
  validation
}) => {
  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'residential': return 'bg-green-100 text-green-800';
      case 'commercial': return 'bg-blue-100 text-blue-800';
      case 'industrial': return 'bg-purple-100 text-purple-800';
      case 'mixed': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const cardClasses = [
    'p-4 border rounded-md cursor-pointer transition-all',
    isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300',
    disabled && 'opacity-50 cursor-not-allowed',
    validation && !validation.isValid && 'border-yellow-400 bg-yellow-50'
  ].filter(Boolean).join(' ');

  return (
    <div
      className={cardClasses}
      onClick={disabled ? undefined : onSelect}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="font-medium text-gray-900">{development.name}</h3>
          <p className="text-sm text-gray-500 mt-1">{development.code}</p>
          {showDescription && (
            <p className="text-sm text-gray-600 mt-2">{development.description}</p>
          )}
        </div>
        <div className="ml-2">
          <span className={`px-2 py-1 text-xs rounded-full ${getCategoryColor(development.category)}`}>
            {development.category}
          </span>
        </div>
      </div>

      {/* Compliance Requirements */}
      <div className="mt-3">
        <div className="flex flex-wrap gap-1">
          {development.complianceRequirements.slice(0, 3).map((req, i) => (
            <span key={i} className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
              {req}
            </span>
          ))}
          {development.complianceRequirements.length > 3 && (
            <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
              +{development.complianceRequirements.length - 3} more
            </span>
          )}
        </div>
      </div>

      {/* Validation Indicator */}
      {validation && (
        <div className="mt-2 flex items-center">
          {validation.isValid ? (
            <div className="flex items-center text-green-600">
              <span className="w-4 h-4 mr-1">✓</span>
              <span className="text-xs">Compatible</span>
            </div>
          ) : (
            <div className="flex items-center text-yellow-600">
              <span className="w-4 h-4 mr-1">⚠</span>
              <span className="text-xs">{validation.warnings.length} warning(s)</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
EOF

    success "DevelopmentCard component created"
}

# Create Enhanced DevelopmentSelector
create_enhanced_selector() {
    log "Creating Enhanced DevelopmentSelector component..."

    cat > "$FRONTEND_DIR/components/development/EnhancedDevelopmentSelector.tsx" << 'EOF'
'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';
import { useDevelopmentContext } from '@/contexts/DevelopmentContext';
import { DevelopmentCard } from './DevelopmentCard';
import { DevelopmentSelectorProps, DevelopmentType } from './types';

export const EnhancedDevelopmentSelector: React.FC<DevelopmentSelectorProps> = ({
  selectedDevelopment,
  onDevelopmentChange,
  propertyId,
  zoning,
  lotSize,
  disabled = false,
  variant = 'default',
  showDescription = true,
  filterByZoning = true,
}) => {
  const { flags } = useFeatureFlags();
  const {
    availableDevelopments,
    isLoading,
    error,
    filters,
    updateFilters,
    validateDevelopment,
    loadDevelopmentTypes
  } = useDevelopmentContext();

  const [searchTerm, setSearchTerm] = useState('');
  const [showValidationErrors, setShowValidationErrors] = useState(false);

  // Load development types on mount
  useEffect(() => {
    loadDevelopmentTypes(propertyId);
  }, [propertyId, loadDevelopmentTypes]);

  // Filter developments based on property constraints
  const filteredDevelopments = useMemo(() => {
    let filtered = availableDevelopments;

    if (filterByZoning && zoning) {
      filtered = filtered.filter(dev =>
        dev.applicableZones.includes(zoning) || dev.applicableZones.includes('*')
      );
    }

    if (lotSize && lotSize > 0) {
      filtered = filtered.filter(dev =>
        !dev.minimumLotSize || lotSize >= dev.minimumLotSize
      );
    }

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(dev =>
        dev.name.toLowerCase().includes(term) ||
        dev.code.toLowerCase().includes(term) ||
        dev.description.toLowerCase().includes(term)
      );
    }

    if (filters.category) {
      filtered = filtered.filter(dev => dev.category === filters.category);
    }

    return filtered.filter(dev => dev.isEnabled);
  }, [availableDevelopments, filterByZoning, zoning, lotSize, searchTerm, filters]);

  // Validation for selected development
  const validationResult = useMemo(() => {
    if (!selectedDevelopment) return null;
    return validateDevelopment(selectedDevelopment, { zoning, lotSize });
  }, [selectedDevelopment, zoning, lotSize, validateDevelopment]);

  const handleDevelopmentSelect = useCallback((development: DevelopmentType) => {
    const validation = validateDevelopment(development, { zoning, lotSize });

    if (validation.isValid) {
      onDevelopmentChange(development);
      setShowValidationErrors(false);
    } else {
      setShowValidationErrors(true);
      // Still allow selection but show warnings
      onDevelopmentChange(development);
    }
  }, [validateDevelopment, zoning, lotSize, onDevelopmentChange]);

  const getUniqueCategories = () => {
    const categories = availableDevelopments.map(dev => dev.category);
    return [...new Set(categories)];
  };

  if (variant === 'compact') {
    return (
      <div className="development-selector-compact">
        <select
          value={selectedDevelopment?.id || ''}
          onChange={(e) => {
            const development = availableDevelopments.find(d => d.id === e.target.value);
            onDevelopmentChange(development || null);
          }}
          disabled={disabled || isLoading}
          className="w-full px-3 py-2 border rounded-md"
        >
          <option value="">Select development type...</option>
          {filteredDevelopments.map((dev) => (
            <option key={dev.id} value={dev.id}>
              {dev.name} ({dev.code})
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className={`development-selector ${variant === 'detailed' ? 'detailed' : ''}`}>
      {/* Search and Filter Controls */}
      <div className="flex flex-col space-y-4 mb-4">
        <div className="flex items-center space-x-2">
          <input
            type="text"
            placeholder="Search development types..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 px-3 py-2 border rounded-md"
            disabled={disabled || isLoading}
          />
          <select
            value={filters.category || ''}
            onChange={(e) => updateFilters({ category: e.target.value || undefined })}
            className="px-3 py-2 border rounded-md"
            disabled={disabled || isLoading}
          >
            <option value="">All Categories</option>
            {getUniqueCategories().map((category) => (
              <option key={category} value={category}>
                {category.charAt(0).toUpperCase() + category.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Development Type Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 animate-pulse rounded-md" />
          ))}
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-600">Error loading development types: {error}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDevelopments.map((development) => (
            <DevelopmentCard
              key={development.id}
              development={development}
              isSelected={selectedDevelopment?.id === development.id}
              onSelect={() => handleDevelopmentSelect(development)}
              showDescription={showDescription}
              disabled={disabled}
              validation={selectedDevelopment?.id === development.id ? validationResult : null}
            />
          ))}
        </div>
      )}

      {/* Validation Messages */}
      {showValidationErrors && validationResult && !validationResult.isValid && (
        <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
          <h4 className="font-medium text-yellow-800">Development Compatibility Warnings:</h4>
          <ul className="mt-2 list-disc list-inside text-yellow-700">
            {validationResult.warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* No Results Message */}
      {!isLoading && !error && filteredDevelopments.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">No development types match your criteria.</p>
          <button
            onClick={() => {
              setSearchTerm('');
              updateFilters({ category: undefined });
            }}
            className="mt-2 text-blue-600 hover:text-blue-800"
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  );
};
EOF

    success "Enhanced DevelopmentSelector component created"
}

# Create main DevelopmentSelector with feature flag integration
create_main_selector() {
    log "Creating main DevelopmentSelector with feature flag integration..."

    cat > "$FRONTEND_DIR/components/development/DevelopmentSelector.tsx" << 'EOF'
'use client';

import React from 'react';
import { withFeatureFlagSafeguard } from '@/lib/feature-flag-safeguards';
import { EnhancedDevelopmentSelector } from './EnhancedDevelopmentSelector';
import { DevelopmentSelectorProps } from './types';

// Legacy component placeholder
const LegacyDevelopmentSelector: React.FC<DevelopmentSelectorProps> = (props) => {
  return (
    <div className="p-4 border border-gray-300 rounded-md bg-gray-50">
      <p className="text-gray-600">Legacy Development Selector</p>
      <p className="text-sm text-gray-500">Feature flag disabled - using legacy component</p>
    </div>
  );
};

// Feature flag wrapped component
export const DevelopmentSelector = withFeatureFlagSafeguard(
  'newDevelopmentSelector',
  EnhancedDevelopmentSelector,
  LegacyDevelopmentSelector,
  {
    errorBoundary: true,
    performanceMonitoring: true,
  }
);

export default DevelopmentSelector;
EOF

    success "Main DevelopmentSelector component created"
}

# Create API endpoint
create_api_endpoint() {
    log "Creating development types API endpoint..."

    cat > "$FRONTEND_DIR/pages/api/development-types.ts" << 'EOF'
import { NextApiRequest, NextApiResponse } from 'next';
import { DevelopmentType } from '@/components/development/types';

// Mock development types data
const mockDevelopmentTypes: DevelopmentType[] = [
  {
    id: '1',
    code: 'RFB',
    name: 'Residential Flat Building',
    description: 'A building containing multiple dwellings, but not a boarding house',
    category: 'residential',
    complianceRequirements: ['Building Height', 'Floor Space Ratio', 'Setbacks', 'Parking'],
    applicableZones: ['R3', 'R4', 'B1', 'B4'],
    minimumLotSize: 600,
    maximumHeight: 24,
    isEnabled: true,
  },
  {
    id: '2',
    code: 'SFD',
    name: 'Single Family Dwelling',
    description: 'A detached house for occupation by a single family',
    category: 'residential',
    complianceRequirements: ['Building Height', 'Setbacks', 'Site Coverage'],
    applicableZones: ['R1', 'R2', 'R3'],
    minimumLotSize: 450,
    maximumHeight: 9,
    isEnabled: true,
  },
  {
    id: '3',
    code: 'CP',
    name: 'Commercial Premises',
    description: 'Building or place used for commercial purposes',
    category: 'commercial',
    complianceRequirements: ['Floor Space Ratio', 'Parking', 'Access'],
    applicableZones: ['B1', 'B2', 'B3', 'B4'],
    isEnabled: true,
  },
  {
    id: '4',
    code: 'TH',
    name: 'Townhouse',
    description: 'One of a group of attached dwellings, each on its own lot',
    category: 'residential',
    complianceRequirements: ['Building Height', 'Setbacks', 'Private Open Space'],
    applicableZones: ['R2', 'R3'],
    minimumLotSize: 300,
    maximumHeight: 12,
    isEnabled: true,
  },
  {
    id: '5',
    code: 'MU',
    name: 'Mixed Use Development',
    description: 'Building containing both residential and commercial uses',
    category: 'mixed',
    complianceRequirements: ['Floor Space Ratio', 'Building Height', 'Parking', 'Acoustic Privacy'],
    applicableZones: ['B1', 'B2', 'B4'],
    minimumLotSize: 800,
    isEnabled: true,
  },
];

async function getDevelopmentTypes(params: {
  propertyId?: string;
  zoning?: string;
  category?: string;
}): Promise<DevelopmentType[]> {
  // In a real implementation, this would query a database
  let filtered = [...mockDevelopmentTypes];

  // Filter by zoning if provided
  if (params.zoning) {
    filtered = filtered.filter(dev =>
      dev.applicableZones.includes(params.zoning!) || dev.applicableZones.includes('*')
    );
  }

  // Filter by category if provided
  if (params.category) {
    filtered = filtered.filter(dev => dev.category === params.category);
  }

  return filtered;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { propertyId, zoning, category } = req.query;

    const developmentTypes = await getDevelopmentTypes({
      propertyId: propertyId as string,
      zoning: zoning as string,
      category: category as string,
    });

    res.status(200).json(developmentTypes);
  } catch (error) {
    console.error('Development types API error:', error);
    res.status(500).json({ error: 'Failed to load development types' });
  }
}
EOF

    success "API endpoint created"
}

# Create unit tests
create_unit_tests() {
    log "Creating unit tests..."

    # DevelopmentSelector tests
    cat > "$FRONTEND_DIR/__tests__/components/development/DevelopmentSelector.test.tsx" << 'EOF'
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { FeatureFlagProvider } from '@/components/providers/FeatureFlagProvider';
import { DevelopmentProvider } from '@/contexts/DevelopmentContext';
import { EnhancedDevelopmentSelector } from '@/components/development/EnhancedDevelopmentSelector';
import developmentReducer from '@/store/slices/developmentSlice';

// Mock fetch
global.fetch = jest.fn();

const mockDevelopmentTypes = [
  {
    id: '1',
    code: 'RFB',
    name: 'Residential Flat Building',
    description: 'A building containing multiple dwellings',
    category: 'residential' as const,
    complianceRequirements: ['Building Height', 'Floor Space Ratio'],
    applicableZones: ['R3', 'R4'],
    minimumLotSize: 600,
    isEnabled: true,
  },
  {
    id: '2',
    code: 'SFD',
    name: 'Single Family Dwelling',
    description: 'A detached house',
    category: 'residential' as const,
    complianceRequirements: ['Building Height', 'Setbacks'],
    applicableZones: ['R1', 'R2'],
    minimumLotSize: 450,
    isEnabled: true,
  },
];

const createTestStore = () => {
  return configureStore({
    reducer: {
      development: developmentReducer,
    },
  });
};

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const store = createTestStore();

  return (
    <Provider store={store}>
      <FeatureFlagProvider>
        <DevelopmentProvider>
          {children}
        </DevelopmentProvider>
      </FeatureFlagProvider>
    </Provider>
  );
};

const defaultProps = {
  onDevelopmentChange: jest.fn(),
  propertyId: 'test-property',
};

describe('EnhancedDevelopmentSelector', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDevelopmentTypes),
    });
  });

  test('renders development types', async () => {
    render(
      <TestWrapper>
        <EnhancedDevelopmentSelector {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Residential Flat Building')).toBeInTheDocument();
      expect(screen.getByText('Single Family Dwelling')).toBeInTheDocument();
    });
  });

  test('filters by search term', async () => {
    render(
      <TestWrapper>
        <EnhancedDevelopmentSelector {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Residential Flat Building')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText('Search development types...'), {
      target: { value: 'single' }
    });

    await waitFor(() => {
      expect(screen.getByText('Single Family Dwelling')).toBeInTheDocument();
      expect(screen.queryByText('Residential Flat Building')).not.toBeInTheDocument();
    });
  });

  test('calls onDevelopmentChange when selection is made', async () => {
    const onDevelopmentChange = jest.fn();

    render(
      <TestWrapper>
        <EnhancedDevelopmentSelector {...defaultProps} onDevelopmentChange={onDevelopmentChange} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Residential Flat Building')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Residential Flat Building'));

    expect(onDevelopmentChange).toHaveBeenCalledWith(mockDevelopmentTypes[0]);
  });

  test('validates property constraints', async () => {
    render(
      <TestWrapper>
        <EnhancedDevelopmentSelector
          {...defaultProps}
          zoning="R1"
          lotSize={300}
        />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Residential Flat Building')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Residential Flat Building'));

    await waitFor(() => {
      expect(screen.getByText('Development Compatibility Warnings:')).toBeInTheDocument();
    });
  });
});
EOF

    # Context tests
    cat > "$FRONTEND_DIR/__tests__/contexts/DevelopmentContext.test.tsx" << 'EOF'
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DevelopmentProvider, useDevelopmentContext } from '@/contexts/DevelopmentContext';

global.fetch = jest.fn();

const TestComponent: React.FC = () => {
  const {
    availableDevelopments,
    selectedDevelopment,
    isLoading,
    loadDevelopmentTypes,
    setSelectedDevelopment,
  } = useDevelopmentContext();

  return (
    <div>
      <div data-testid="loading">{isLoading ? 'Loading' : 'Loaded'}</div>
      <div data-testid="count">{availableDevelopments.length}</div>
      <div data-testid="selected">
        {selectedDevelopment ? selectedDevelopment.name : 'None'}
      </div>
      <button onClick={() => loadDevelopmentTypes()}>Load</button>
      <button onClick={() => setSelectedDevelopment(availableDevelopments[0])}>
        Select First
      </button>
    </div>
  );
};

const mockDevelopmentTypes = [
  {
    id: '1',
    code: 'RFB',
    name: 'Residential Flat Building',
    description: 'Test description',
    category: 'residential' as const,
    complianceRequirements: [],
    applicableZones: [],
    isEnabled: true,
  },
];

describe('DevelopmentContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDevelopmentTypes),
    });
  });

  test('provides development context', () => {
    render(
      <DevelopmentProvider>
        <TestComponent />
      </DevelopmentProvider>
    );

    expect(screen.getByTestId('loading')).toHaveTextContent('Loaded');
    expect(screen.getByTestId('count')).toHaveTextContent('0');
    expect(screen.getByTestId('selected')).toHaveTextContent('None');
  });

  test('loads development types', async () => {
    render(
      <DevelopmentProvider>
        <TestComponent />
      </DevelopmentProvider>
    );

    fireEvent.click(screen.getByText('Load'));

    await waitFor(() => {
      expect(screen.getByTestId('count')).toHaveTextContent('1');
    });
  });

  test('sets selected development', async () => {
    render(
      <DevelopmentProvider>
        <TestComponent />
      </DevelopmentProvider>
    );

    fireEvent.click(screen.getByText('Load'));

    await waitFor(() => {
      expect(screen.getByTestId('count')).toHaveTextContent('1');
    });

    fireEvent.click(screen.getByText('Select First'));

    expect(screen.getByTestId('selected')).toHaveTextContent('Residential Flat Building');
  });
});
EOF

    success "Unit tests created"
}

# Create component index
create_component_index() {
    log "Creating component index file..."

    cat > "$FRONTEND_DIR/components/development/index.ts" << 'EOF'
export { DevelopmentSelector as default } from './DevelopmentSelector';
export { EnhancedDevelopmentSelector } from './EnhancedDevelopmentSelector';
export { DevelopmentCard } from './DevelopmentCard';
export type { DevelopmentType, DevelopmentSelectorProps, ValidationResult } from './types';
EOF

    success "Component index created"
}

# Run verification
run_verification() {
    log "Running PRP-UI2 verification..."

    cd "$PRP_DIR"
    python verify_ui_migration.py --project-root "$PROJECT_ROOT" ui2 --detailed

    if [[ $? -eq 0 ]]; then
        success "PRP-UI2 verification passed"
    else
        error "PRP-UI2 verification failed"
        exit 1
    fi
}

# Main execution
main() {
    log "Starting PRP-UI2 execution: DevelopmentSelector Component Migration"
    log "Project root: $PROJECT_ROOT"
    log "Frontend directory: $FRONTEND_DIR"

    check_prerequisites
    create_directories
    create_development_types
    create_redux_slice
    create_redux_store
    create_development_context
    create_development_card
    create_enhanced_selector
    create_main_selector
    create_api_endpoint
    create_unit_tests
    create_component_index
    run_verification

    success "PRP-UI2 execution completed successfully!"
    log "DevelopmentSelector migration is ready"
    log "Next steps:"
    log "  1. Enable 'newDevelopmentSelector' feature flag"
    log "  2. Test component functionality in development"
    log "  3. Verify integration with property selection"
    log "  4. Proceed with PRP-UI3: ComplianceStatus migration"
}

# Execute main function
main "$@"