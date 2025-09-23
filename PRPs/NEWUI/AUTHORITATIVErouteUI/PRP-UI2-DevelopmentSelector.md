# PRP-UI2: DevelopmentSelector Component Migration

> **Priority**: High
> **Estimated Time**: 7-10 days
> **Dependencies**: PRP-UI1 (Feature Flags)
> **Risk Level**: Medium
> **Week**: 2

## Overview

Migrate the DevelopmentSelector component from the authoritative route to the main page with unified state management, enhanced functionality, and seamless integration. This component is critical for development type selection and compliance workflow initialization.

## Technical Specifications

### 1. Component Architecture

```typescript
// components/development/DevelopmentSelector.tsx
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
```

### 2. State Management Integration

#### A. Development Context
```typescript
// contexts/DevelopmentContext.tsx
export interface DevelopmentContextState {
  selectedDevelopment: DevelopmentType | null;
  availableDevelopments: DevelopmentType[];
  isLoading: boolean;
  error: string | null;
  filters: {
    category?: string;
    zoning?: string;
    searchTerm?: string;
  };
}

export interface DevelopmentContextActions {
  setSelectedDevelopment: (development: DevelopmentType | null) => void;
  loadDevelopmentTypes: (propertyId?: string) => Promise<void>;
  updateFilters: (filters: Partial<DevelopmentContextState['filters']>) => void;
  clearSelection: () => void;
  validateDevelopment: (development: DevelopmentType, property: any) => ValidationResult;
}
```

#### B. Redux Integration
```typescript
// store/slices/developmentSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const fetchDevelopmentTypes = createAsyncThunk(
  'development/fetchTypes',
  async (params: { propertyId?: string; zoning?: string }) => {
    const response = await fetch(`/api/development-types?${new URLSearchParams(params)}`);
    return response.json();
  }
);

const developmentSlice = createSlice({
  name: 'development',
  initialState: {
    types: [],
    selected: null,
    loading: false,
    error: null,
    filters: {}
  },
  reducers: {
    setSelectedDevelopment: (state, action) => {
      state.selected = action.payload;
    },
    updateFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearSelection: (state) => {
      state.selected = null;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDevelopmentTypes.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchDevelopmentTypes.fulfilled, (state, action) => {
        state.loading = false;
        state.types = action.payload;
      })
      .addCase(fetchDevelopmentTypes.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to load development types';
      });
  }
});
```

### 3. Enhanced Component Implementation

```typescript
// components/development/EnhancedDevelopmentSelector.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';
import { useDevelopmentContext } from '@/contexts/DevelopmentContext';
import { cn } from '@/lib/utils';

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
    validateDevelopment
  } = useDevelopmentContext();

  const [searchTerm, setSearchTerm] = useState('');
  const [showValidationErrors, setShowValidationErrors] = useState(false);

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

  const handleDevelopmentSelect = (development: DevelopmentType) => {
    const validation = validateDevelopment(development, { zoning, lotSize });

    if (validation.isValid) {
      onDevelopmentChange(development);
      setShowValidationErrors(false);
    } else {
      setShowValidationErrors(true);
      // Still allow selection but show warnings
      onDevelopmentChange(development);
    }
  };

  return (
    <div className={cn(
      "development-selector",
      variant === 'compact' && "compact",
      variant === 'detailed' && "detailed"
    )}>
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
            <option value="residential">Residential</option>
            <option value="commercial">Commercial</option>
            <option value="industrial">Industrial</option>
            <option value="mixed">Mixed Use</option>
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
```

### 4. Development Card Component

```typescript
// components/development/DevelopmentCard.tsx
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
  return (
    <div
      className={cn(
        "p-4 border rounded-md cursor-pointer transition-all",
        isSelected ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-gray-300",
        disabled && "opacity-50 cursor-not-allowed",
        validation && !validation.isValid && "border-yellow-400 bg-yellow-50"
      )}
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
          <span className={cn(
            "px-2 py-1 text-xs rounded-full",
            development.category === 'residential' && "bg-green-100 text-green-800",
            development.category === 'commercial' && "bg-blue-100 text-blue-800",
            development.category === 'industrial' && "bg-purple-100 text-purple-800",
            development.category === 'mixed' && "bg-orange-100 text-orange-800"
          )}>
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
              <CheckCircle className="w-4 h-4 mr-1" />
              <span className="text-xs">Compatible</span>
            </div>
          ) : (
            <div className="flex items-center text-yellow-600">
              <AlertTriangle className="w-4 h-4 mr-1" />
              <span className="text-xs">{validation.warnings.length} warning(s)</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

## Implementation Steps

### Phase 1: Context and State Setup (Day 1-3)
1. **Create DevelopmentContext**
   - State management interface
   - Action definitions
   - Provider implementation

2. **Redux Integration**
   - Development slice creation
   - Async thunks for API calls
   - Middleware setup

3. **API Endpoint Creation**
   - `/api/development-types` endpoint
   - Property-specific filtering
   - Caching implementation

### Phase 2: Component Development (Day 4-6)
1. **Core Component Implementation**
   - EnhancedDevelopmentSelector
   - DevelopmentCard component
   - Search and filter functionality

2. **Validation Logic**
   - Property compatibility checking
   - Zoning constraint validation
   - User feedback implementation

3. **Responsive Design**
   - Mobile-first approach
   - Grid layout optimization
   - Accessibility features

### Phase 3: Integration and Testing (Day 7-10)
1. **Feature Flag Integration**
   - Conditional rendering logic
   - Fallback to legacy component
   - Gradual rollout preparation

2. **State Synchronization**
   - Property selection integration
   - Compliance workflow triggering
   - Cross-component communication

3. **Comprehensive Testing**
   - Unit tests for all components
   - Integration tests with property data
   - E2E user workflow testing

## Risk Mitigation

### Critical Risks
1. **State Inconsistency Between Routes**
   - **Mitigation**: Centralized state management
   - **Monitoring**: State change logging
   - **Fallback**: Legacy route preservation

2. **Performance Impact on Large Datasets**
   - **Mitigation**: Virtual scrolling and pagination
   - **Caching**: Client-side development type caching
   - **Optimization**: Lazy loading of descriptions

3. **User Experience Regression**
   - **Mitigation**: A/B testing with feature flags
   - **Monitoring**: User interaction analytics
   - **Rollback**: Instant flag toggle to legacy

### Implementation Safeguards
```typescript
// lib/development-safeguards.ts
export const withDevelopmentSafeguard = (Component: React.ComponentType) => {
  return (props: any) => {
    const { flags } = useFeatureFlags();

    try {
      if (flags.newDevelopmentSelector) {
        return <Component {...props} />;
      }
      return <LegacyDevelopmentSelector {...props} />;
    } catch (error) {
      console.error('DevelopmentSelector error:', error);
      return <LegacyDevelopmentSelector {...props} />;
    }
  };
};
```

## Verification Criteria

### Automated Tests
1. **Unit Tests** (>95% coverage)
   - Component rendering with various props
   - State management functions
   - Validation logic accuracy

2. **Integration Tests**
   - Context provider functionality
   - API integration
   - State synchronization

3. **E2E Tests**
   - Development type selection flow
   - Filter and search functionality
   - Property compatibility validation

### Manual Verification Checklist
- [ ] All development types load correctly
- [ ] Search functionality works accurately
- [ ] Category filters operate properly
- [ ] Property constraints are enforced
- [ ] Validation messages display appropriately
- [ ] Mobile responsive design functions
- [ ] Accessibility standards met (WCAG 2.1 AA)
- [ ] Performance meets benchmarks (<200ms selection)

## Success Metrics

### Technical Metrics
- **Component Load Time**: <200ms
- **Search Response Time**: <100ms
- **Memory Usage**: <5MB additional
- **Bundle Size Impact**: <10KB

### User Experience Metrics
- **Selection Accuracy**: >98%
- **User Task Completion**: >95%
- **Error Rate**: <1%
- **User Satisfaction**: >4.5/5

## API Integration

### Development Types Endpoint
```typescript
// pages/api/development-types.ts
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const { propertyId, zoning, category } = req.query;

  try {
    const developmentTypes = await getDevelopmentTypes({
      propertyId: propertyId as string,
      zoning: zoning as string,
      category: category as string,
    });

    // Apply property-specific filtering
    const filtered = await filterByPropertyConstraints(
      developmentTypes,
      propertyId as string
    );

    res.status(200).json(filtered);
  } catch (error) {
    console.error('Development types API error:', error);
    res.status(500).json({ error: 'Failed to load development types' });
  }
}
```

## Testing Requirements

### Unit Tests
```typescript
// __tests__/components/development/DevelopmentSelector.test.tsx
describe('EnhancedDevelopmentSelector', () => {
  test('renders all development types', async () => {
    render(<EnhancedDevelopmentSelector {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('Residential Flat Building')).toBeInTheDocument();
    });
  });

  test('filters by search term', async () => {
    render(<EnhancedDevelopmentSelector {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText('Search development types...'), {
      target: { value: 'residential' }
    });

    await waitFor(() => {
      expect(screen.getByText('Residential Flat Building')).toBeInTheDocument();
      expect(screen.queryByText('Commercial Premises')).not.toBeInTheDocument();
    });
  });

  test('validates property compatibility', async () => {
    const props = {
      ...defaultProps,
      zoning: 'R1',
      lotSize: 300
    };

    render(<EnhancedDevelopmentSelector {...props} />);
    fireEvent.click(screen.getByText('High Density Residential'));

    await waitFor(() => {
      expect(screen.getByText('Development Compatibility Warnings:')).toBeInTheDocument();
    });
  });
});
```

## Next Steps

Upon completion of PRP-UI2:
1. **Prepare for PRP-UI3**: ComplianceStatus migration
2. **Monitor Performance**: Track component usage analytics
3. **Gather Feedback**: Collect user experience data
4. **Optimize**: Performance improvements based on usage patterns

## Dependencies & Prerequisites

### Required Packages
```json
{
  "dependencies": {
    "@reduxjs/toolkit": "^1.9.0",
    "react-redux": "^8.0.0",
    "lucide-react": "^0.263.0"
  }
}
```

### File Structure
```
components/
├── development/
│   ├── DevelopmentSelector.tsx
│   ├── EnhancedDevelopmentSelector.tsx
│   ├── DevelopmentCard.tsx
│   └── index.ts
├── providers/
│   └── DevelopmentProvider.tsx
└── legacy/
    └── LegacyDevelopmentSelector.tsx

contexts/
└── DevelopmentContext.tsx

store/
└── slices/
    └── developmentSlice.ts

pages/api/
└── development-types.ts
```

This PRP ensures a robust, performant, and user-friendly development type selection experience while maintaining backward compatibility and enabling smooth migration.