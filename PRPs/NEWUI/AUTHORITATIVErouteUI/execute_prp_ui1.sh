#!/bin/bash
# PRP-UI1 Execution Script: Feature Flag System Implementation
# Week 1 - Days 1-7

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
    log "Checking prerequisites for PRP-UI1..."

    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/package.json" ]] && [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
        error "Not in project root or frontend directory not found"
        exit 1
    fi

    # Check Node.js and npm
    if ! command -v node &> /dev/null; then
        error "Node.js not found. Please install Node.js"
        exit 1
    fi

    if ! command -v npm &> /dev/null; then
        error "npm not found. Please install npm"
        exit 1
    fi

    # Check TypeScript
    if ! command -v npx &> /dev/null; then
        error "npx not found"
        exit 1
    fi

    success "Prerequisites check passed"
}

# Create directory structure
create_directories() {
    log "Creating directory structure for feature flags..."

    directories=(
        "$FRONTEND_DIR/lib"
        "$FRONTEND_DIR/components/providers"
        "$FRONTEND_DIR/components/debug"
        "$FRONTEND_DIR/config"
        "$FRONTEND_DIR/__tests__/lib"
        "$FRONTEND_DIR/__tests__/components"
    )

    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log "Created directory: $dir"
        else
            log "Directory already exists: $dir"
        fi
    done

    success "Directory structure created"
}

# Install required dependencies
install_dependencies() {
    log "Installing required dependencies..."

    cd "$FRONTEND_DIR"

    # Check if package.json exists
    if [[ ! -f "package.json" ]]; then
        error "package.json not found in frontend directory"
        exit 1
    fi

    # Install dependencies if not already present
    dependencies=(
        "react@^18.0.0"
        "next@^14.0.0"
        "@types/react@^18.0.0"
        "@types/node@^20.0.0"
        "typescript@^5.0.0"
    )

    dev_dependencies=(
        "@testing-library/react@^13.0.0"
        "@testing-library/jest-dom@^5.0.0"
        "jest@^29.0.0"
        "@types/jest@^29.0.0"
        "jest-environment-jsdom@^29.0.0"
    )

    # Install production dependencies
    for dep in "${dependencies[@]}"; do
        if ! npm list "${dep%@*}" &> /dev/null; then
            log "Installing $dep"
            npm install "$dep"
        else
            log "Dependency already installed: ${dep%@*}"
        fi
    done

    # Install dev dependencies
    for dep in "${dev_dependencies[@]}"; do
        if ! npm list "${dep%@*}" &> /dev/null; then
            log "Installing dev dependency $dep"
            npm install --save-dev "$dep"
        else
            log "Dev dependency already installed: ${dep%@*}"
        fi
    done

    success "Dependencies installed"
}

# Create feature flag types and interfaces
create_feature_flag_types() {
    log "Creating feature flag types and interfaces..."

    cat > "$FRONTEND_DIR/lib/feature-flags.ts" << 'EOF'
// Feature flag types and interfaces for UI migration
export interface FeatureFlags {
  authoritativeRouteMigration: boolean;
  newDevelopmentSelector: boolean;
  newComplianceStatus: boolean;
  newComplianceChecklist: boolean;
  unifiedStateManagement: boolean;
  legacyRouteFallback: boolean;
}

export interface FeatureFlagConfig {
  environment: 'development' | 'staging' | 'production';
  userId?: string;
  rolloutPercentage: number;
  overrides?: Partial<FeatureFlags>;
}

export interface FeatureFlagUpdate {
  key: keyof FeatureFlags;
  value: boolean;
  timestamp: Date;
  source: 'user' | 'system' | 'config';
}

export const DEFAULT_FEATURE_FLAGS: FeatureFlags = {
  authoritativeRouteMigration: false,
  newDevelopmentSelector: false,
  newComplianceStatus: false,
  newComplianceChecklist: false,
  unifiedStateManagement: false,
  legacyRouteFallback: true,
};

export const FEATURE_FLAG_STORAGE_KEY = 'compliance-engine-feature-flags';
EOF

    success "Feature flag types created"
}

# Create feature flag service
create_feature_flag_service() {
    log "Creating feature flag service..."

    cat > "$FRONTEND_DIR/lib/feature-flag-service.ts" << 'EOF'
import { FeatureFlags, FeatureFlagConfig, DEFAULT_FEATURE_FLAGS, FEATURE_FLAG_STORAGE_KEY } from './feature-flags';

export class FeatureFlagService {
  private static instance: FeatureFlagService;
  private flags: FeatureFlags;
  private config: FeatureFlagConfig;
  private listeners: Map<keyof FeatureFlags, Set<(value: boolean) => void>> = new Map();

  private constructor() {
    this.flags = { ...DEFAULT_FEATURE_FLAGS };
    this.config = {
      environment: (process.env.NODE_ENV as any) || 'development',
      rolloutPercentage: 0,
    };
    this.loadFromStorage();
    this.loadFromEnvironment();
  }

  static getInstance(): FeatureFlagService {
    if (!FeatureFlagService.instance) {
      FeatureFlagService.instance = new FeatureFlagService();
    }
    return FeatureFlagService.instance;
  }

  async loadFlags(): Promise<FeatureFlags> {
    this.loadFromStorage();
    this.loadFromEnvironment();
    return { ...this.flags };
  }

  updateFlag(key: keyof FeatureFlags, value: boolean): void {
    const oldValue = this.flags[key];
    this.flags[key] = value;

    this.saveToStorage();
    this.notifyListeners(key, value);

    console.log(`Feature flag updated: ${key} = ${value}`);
  }

  isEnabled(key: keyof FeatureFlags): boolean {
    return this.flags[key] || false;
  }

  getAllFlags(): FeatureFlags {
    return { ...this.flags };
  }

  subscribe(key: keyof FeatureFlags, callback: (value: boolean) => void): () => void {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, new Set());
    }
    this.listeners.get(key)!.add(callback);

    // Return unsubscribe function
    return () => {
      this.listeners.get(key)?.delete(callback);
    };
  }

  reset(): void {
    this.flags = { ...DEFAULT_FEATURE_FLAGS };
    this.saveToStorage();

    // Notify all listeners
    for (const [key, value] of Object.entries(this.flags)) {
      this.notifyListeners(key as keyof FeatureFlags, value);
    }
  }

  private loadFromStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem(FEATURE_FLAG_STORAGE_KEY);
      if (stored) {
        const parsedFlags = JSON.parse(stored);
        this.flags = { ...DEFAULT_FEATURE_FLAGS, ...parsedFlags };
      }
    } catch (error) {
      console.warn('Failed to load feature flags from storage:', error);
    }
  }

  private saveToStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      localStorage.setItem(FEATURE_FLAG_STORAGE_KEY, JSON.stringify(this.flags));
    } catch (error) {
      console.warn('Failed to save feature flags to storage:', error);
    }
  }

  private loadFromEnvironment(): void {
    // Environment variable overrides
    const envOverrides: Partial<FeatureFlags> = {};

    if (process.env.NEXT_PUBLIC_FF_AUTHORITATIVE_MIGRATION === 'true') {
      envOverrides.authoritativeRouteMigration = true;
    }
    if (process.env.NEXT_PUBLIC_FF_NEW_DEVELOPMENT_SELECTOR === 'true') {
      envOverrides.newDevelopmentSelector = true;
    }
    if (process.env.NEXT_PUBLIC_FF_NEW_COMPLIANCE_STATUS === 'true') {
      envOverrides.newComplianceStatus = true;
    }
    if (process.env.NEXT_PUBLIC_FF_NEW_COMPLIANCE_CHECKLIST === 'true') {
      envOverrides.newComplianceChecklist = true;
    }

    this.flags = { ...this.flags, ...envOverrides };
  }

  private notifyListeners(key: keyof FeatureFlags, value: boolean): void {
    const listeners = this.listeners.get(key);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(value);
        } catch (error) {
          console.error(`Error in feature flag listener for ${key}:`, error);
        }
      });
    }
  }
}

export const featureFlagService = FeatureFlagService.getInstance();
EOF

    success "Feature flag service created"
}

# Create safeguards
create_safeguards() {
    log "Creating feature flag safeguards..."

    cat > "$FRONTEND_DIR/lib/feature-flag-safeguards.ts" << 'EOF'
import React from 'react';
import { FeatureFlags } from './feature-flags';

export interface FeatureFlagSafeguardOptions {
  errorBoundary?: boolean;
  performanceMonitoring?: boolean;
  loadingFallback?: React.ComponentType;
  errorFallback?: React.ComponentType<{ error: Error }>;
}

export const withFeatureFlagSafeguard = <T extends object>(
  flagKey: keyof FeatureFlags,
  newComponent: React.ComponentType<T>,
  fallbackComponent: React.ComponentType<T>,
  options: FeatureFlagSafeguardOptions = {}
) => {
  return (props: T) => {
    const [isEnabled, setIsEnabled] = React.useState(false);
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState<Error | null>(null);

    React.useEffect(() => {
      try {
        // Dynamic import to avoid circular dependencies
        import('./feature-flag-service').then(({ featureFlagService }) => {
          const enabled = featureFlagService.isEnabled(flagKey);
          setIsEnabled(enabled);
          setIsLoading(false);

          // Subscribe to flag changes
          const unsubscribe = featureFlagService.subscribe(flagKey, setIsEnabled);
          return unsubscribe;
        });
      } catch (err) {
        setError(err as Error);
        setIsLoading(false);
      }
    }, []);

    // Performance monitoring
    React.useEffect(() => {
      if (options.performanceMonitoring && isEnabled) {
        const startTime = performance.now();
        return () => {
          const endTime = performance.now();
          console.log(`Feature flag component ${flagKey} render time: ${endTime - startTime}ms`);
        };
      }
    }, [isEnabled]);

    if (isLoading && options.loadingFallback) {
      return React.createElement(options.loadingFallback);
    }

    if (error && options.errorFallback) {
      return React.createElement(options.errorFallback, { error });
    }

    try {
      return isEnabled ?
        React.createElement(newComponent, props) :
        React.createElement(fallbackComponent, props);
    } catch (componentError) {
      console.error(`Feature flag component error for ${flagKey}:`, componentError);

      if (options.errorFallback) {
        return React.createElement(options.errorFallback, { error: componentError as Error });
      }

      // Always fallback to legacy component on error
      return React.createElement(fallbackComponent, props);
    }
  };
};

export const useFeatureFlagSafeguard = (flagKey: keyof FeatureFlags) => {
  const [isEnabled, setIsEnabled] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    import('./feature-flag-service').then(({ featureFlagService }) => {
      setIsEnabled(featureFlagService.isEnabled(flagKey));
      setIsLoading(false);

      const unsubscribe = featureFlagService.subscribe(flagKey, setIsEnabled);
      return unsubscribe;
    });
  }, [flagKey]);

  return { isEnabled, isLoading };
};
EOF

    success "Feature flag safeguards created"
}

# Create React provider
create_react_provider() {
    log "Creating React feature flag provider..."

    cat > "$FRONTEND_DIR/components/providers/FeatureFlagProvider.tsx" << 'EOF'
'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { FeatureFlags, FeatureFlagUpdate } from '@/lib/feature-flags';
import { featureFlagService } from '@/lib/feature-flag-service';

interface FeatureFlagContextType {
  flags: FeatureFlags;
  updateFlag: (key: keyof FeatureFlags, value: boolean) => void;
  isLoading: boolean;
  error: string | null;
  resetFlags: () => void;
}

const FeatureFlagContext = createContext<FeatureFlagContextType>({
  flags: {} as FeatureFlags,
  updateFlag: () => {},
  isLoading: true,
  error: null,
  resetFlags: () => {},
});

export const useFeatureFlags = () => {
  const context = useContext(FeatureFlagContext);
  if (!context) {
    throw new Error('useFeatureFlags must be used within a FeatureFlagProvider');
  }
  return context;
};

interface FeatureFlagProviderProps {
  children: ReactNode;
}

export const FeatureFlagProvider: React.FC<FeatureFlagProviderProps> = ({ children }) => {
  const [flags, setFlags] = useState<FeatureFlags>({} as FeatureFlags);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadFlags = async () => {
      try {
        setIsLoading(true);
        const loadedFlags = await featureFlagService.loadFlags();
        setFlags(loadedFlags);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load feature flags');
        console.error('Failed to load feature flags:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadFlags();

    // Subscribe to flag changes
    const unsubscribers: (() => void)[] = [];

    Object.keys(flags).forEach(key => {
      const unsubscribe = featureFlagService.subscribe(
        key as keyof FeatureFlags,
        (value) => {
          setFlags(prev => ({ ...prev, [key]: value }));
        }
      );
      unsubscribers.push(unsubscribe);
    });

    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe());
    };
  }, []);

  const updateFlag = (key: keyof FeatureFlags, value: boolean) => {
    try {
      featureFlagService.updateFlag(key, value);
      // State will be updated via subscription
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update feature flag');
      console.error('Failed to update feature flag:', err);
    }
  };

  const resetFlags = () => {
    try {
      featureFlagService.reset();
      // State will be updated via subscription
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset feature flags');
      console.error('Failed to reset feature flags:', err);
    }
  };

  return (
    <FeatureFlagContext.Provider
      value={{
        flags,
        updateFlag,
        isLoading,
        error,
        resetFlags,
      }}
    >
      {children}
    </FeatureFlagContext.Provider>
  );
};
EOF

    success "React feature flag provider created"
}

# Create debug panel
create_debug_panel() {
    log "Creating feature flag debug panel..."

    cat > "$FRONTEND_DIR/components/debug/FeatureFlagDebugPanel.tsx" << 'EOF'
'use client';

import React, { useState } from 'react';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';

export const FeatureFlagDebugPanel: React.FC = () => {
  const { flags, updateFlag, isLoading, error, resetFlags } = useFeatureFlags();
  const [isOpen, setIsOpen] = useState(false);

  if (process.env.NODE_ENV !== 'development') {
    return null;
  }

  if (isLoading) {
    return (
      <div className="fixed bottom-4 left-4 bg-gray-800 text-white p-2 rounded text-sm">
        Loading feature flags...
      </div>
    );
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-4 left-4 bg-blue-600 text-white p-2 rounded shadow-lg hover:bg-blue-700 z-50"
        title="Feature Flag Debug Panel"
      >
        🚩 FF
      </button>

      {isOpen && (
        <div className="fixed bottom-16 left-4 bg-white border border-gray-300 rounded-lg shadow-xl p-4 max-w-sm z-50">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-gray-900">Feature Flags</h3>
            <div className="flex space-x-2">
              <button
                onClick={resetFlags}
                className="text-xs bg-gray-500 text-white px-2 py-1 rounded hover:bg-gray-600"
                title="Reset all flags"
              >
                Reset
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-2 max-h-80 overflow-y-auto">
            {Object.entries(flags).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <label className="text-sm text-gray-700 flex-1 cursor-pointer">
                  {key.replace(/([A-Z])/g, ' $1').trim()}
                </label>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={value}
                    onChange={(e) => updateFlag(key as keyof typeof flags, e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
            ))}
          </div>

          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="text-xs text-gray-500">
              Environment: {process.env.NODE_ENV}
            </div>
          </div>
        </div>
      )}
    </>
  );
};
EOF

    success "Feature flag debug panel created"
}

# Create configuration files
create_config_files() {
    log "Creating configuration files..."

    # Development config
    cat > "$FRONTEND_DIR/config/feature-flags.development.json" << 'EOF'
{
  "authoritativeRouteMigration": true,
  "newDevelopmentSelector": false,
  "newComplianceStatus": false,
  "newComplianceChecklist": false,
  "unifiedStateManagement": false,
  "legacyRouteFallback": true
}
EOF

    # Staging config
    cat > "$FRONTEND_DIR/config/feature-flags.staging.json" << 'EOF'
{
  "authoritativeRouteMigration": false,
  "newDevelopmentSelector": false,
  "newComplianceStatus": false,
  "newComplianceChecklist": false,
  "unifiedStateManagement": false,
  "legacyRouteFallback": true
}
EOF

    # Production config
    cat > "$FRONTEND_DIR/config/feature-flags.production.json" << 'EOF'
{
  "authoritativeRouteMigration": false,
  "newDevelopmentSelector": false,
  "newComplianceStatus": false,
  "newComplianceChecklist": false,
  "unifiedStateManagement": false,
  "legacyRouteFallback": true
}
EOF

    success "Configuration files created"
}

# Create unit tests
create_unit_tests() {
    log "Creating unit tests..."

    # Feature flags tests
    cat > "$FRONTEND_DIR/__tests__/lib/feature-flags.test.ts" << 'EOF'
import { FeatureFlagService } from '@/lib/feature-flag-service';
import { DEFAULT_FEATURE_FLAGS } from '@/lib/feature-flags';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('FeatureFlagService', () => {
  let service: FeatureFlagService;

  beforeEach(() => {
    jest.clearAllMocks();
    // Reset singleton instance
    (FeatureFlagService as any).instance = undefined;
    service = FeatureFlagService.getInstance();
  });

  test('getInstance returns singleton', () => {
    const service1 = FeatureFlagService.getInstance();
    const service2 = FeatureFlagService.getInstance();
    expect(service1).toBe(service2);
  });

  test('initializes with default flags', () => {
    const flags = service.getAllFlags();
    expect(flags).toEqual(DEFAULT_FEATURE_FLAGS);
  });

  test('updateFlag changes flag value', () => {
    service.updateFlag('authoritativeRouteMigration', true);
    expect(service.isEnabled('authoritativeRouteMigration')).toBe(true);
  });

  test('updateFlag notifies subscribers', () => {
    const callback = jest.fn();
    service.subscribe('authoritativeRouteMigration', callback);

    service.updateFlag('authoritativeRouteMigration', true);
    expect(callback).toHaveBeenCalledWith(true);
  });

  test('reset restores default flags', () => {
    service.updateFlag('authoritativeRouteMigration', true);
    service.reset();

    const flags = service.getAllFlags();
    expect(flags).toEqual(DEFAULT_FEATURE_FLAGS);
  });

  test('subscribe returns unsubscribe function', () => {
    const callback = jest.fn();
    const unsubscribe = service.subscribe('authoritativeRouteMigration', callback);

    service.updateFlag('authoritativeRouteMigration', true);
    expect(callback).toHaveBeenCalledTimes(1);

    unsubscribe();
    service.updateFlag('authoritativeRouteMigration', false);
    expect(callback).toHaveBeenCalledTimes(1); // Should not be called again
  });
});
EOF

    # Provider tests
    cat > "$FRONTEND_DIR/__tests__/components/FeatureFlagProvider.test.tsx" << 'EOF'
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FeatureFlagProvider, useFeatureFlags } from '@/components/providers/FeatureFlagProvider';

// Test component that uses the hook
const TestComponent: React.FC = () => {
  const { flags, updateFlag, isLoading } = useFeatureFlags();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <div data-testid="flag-status">
        {flags.authoritativeRouteMigration ? 'Enabled' : 'Disabled'}
      </div>
      <button
        onClick={() => updateFlag('authoritativeRouteMigration', !flags.authoritativeRouteMigration)}
        data-testid="toggle-flag"
      >
        Toggle
      </button>
    </div>
  );
};

describe('FeatureFlagProvider', () => {
  test('provides feature flag context', async () => {
    render(
      <FeatureFlagProvider>
        <TestComponent />
      </FeatureFlagProvider>
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    expect(screen.getByTestId('flag-status')).toHaveTextContent('Disabled');
  });

  test('updates flag when toggled', async () => {
    render(
      <FeatureFlagProvider>
        <TestComponent />
      </FeatureFlagProvider>
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('toggle-flag'));

    await waitFor(() => {
      expect(screen.getByTestId('flag-status')).toHaveTextContent('Enabled');
    });
  });

  test('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useFeatureFlags must be used within a FeatureFlagProvider');

    consoleSpy.mockRestore();
  });
});
EOF

    success "Unit tests created"
}

# Update package.json scripts
update_package_scripts() {
    log "Updating package.json scripts..."

    cd "$FRONTEND_DIR"

    # Check if jq is available for JSON manipulation
    if command -v jq &> /dev/null; then
        # Add test script if it doesn't exist
        jq '.scripts.test = "jest --watchAll=false"' package.json > package.json.tmp && mv package.json.tmp package.json
        jq '.scripts["test:watch"] = "jest --watch"' package.json > package.json.tmp && mv package.json.tmp package.json
        jq '.scripts["test:coverage"] = "jest --coverage"' package.json > package.json.tmp && mv package.json.tmp package.json
    else
        warning "jq not available. Please manually add test scripts to package.json"
    fi

    success "Package.json scripts updated"
}

# Run verification
run_verification() {
    log "Running PRP-UI1 verification..."

    cd "$PRP_DIR"
    python verify_ui_migration.py --project-root "$PROJECT_ROOT" ui1 --detailed

    if [[ $? -eq 0 ]]; then
        success "PRP-UI1 verification passed"
    else
        error "PRP-UI1 verification failed"
        exit 1
    fi
}

# Main execution
main() {
    log "Starting PRP-UI1 execution: Feature Flag System Implementation"
    log "Project root: $PROJECT_ROOT"
    log "Frontend directory: $FRONTEND_DIR"

    check_prerequisites
    create_directories
    install_dependencies
    create_feature_flag_types
    create_feature_flag_service
    create_safeguards
    create_react_provider
    create_debug_panel
    create_config_files
    create_unit_tests
    update_package_scripts
    run_verification

    success "PRP-UI1 execution completed successfully!"
    log "Feature flag system is ready for use"
    log "Next steps:"
    log "  1. Add FeatureFlagProvider to your app layout"
    log "  2. Use feature flags in components with useFeatureFlags hook"
    log "  3. Test feature flag toggling in development"
    log "  4. Proceed with PRP-UI2: DevelopmentSelector migration"
}

# Execute main function
main "$@"