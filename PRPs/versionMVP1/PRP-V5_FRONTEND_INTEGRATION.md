# PRP-V5: Frontend Version Integration

## Objective
Add version awareness to the Next.js frontend with minimal UI changes and clear version indicators.

## Prerequisites
- PRP-V1 through V4 completed
- Frontend running (Next.js)
- API version endpoints available

## Implementation

### Step 1: Version Display Components

#### File: frontend-nextjs/components/version/VersionBadge.tsx
```typescript
import React from 'react';

interface VersionBadgeProps {
  versionNumber: string;
  status: 'CURRENT' | 'PREVIOUS' | 'ARCHIVED';
  effectiveDate: string;
  className?: string;
}

export const VersionBadge: React.FC<VersionBadgeProps> = ({
  versionNumber,
  status,
  effectiveDate,
  className = ""
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'CURRENT':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'PREVIOUS':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'ARCHIVED':
        return 'bg-gray-100 text-gray-600 border-gray-300';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-md border ${getStatusColor()} ${className}`}>
      <span className="text-xs font-semibold">{versionNumber}</span>
      <span className="text-xs">Effective: {new Date(effectiveDate).toLocaleDateString()}</span>
      {status !== 'CURRENT' && (
        <span className="text-xs italic">({status.toLowerCase()})</span>
      )}
    </div>
  );
};
```

#### File: frontend-nextjs/components/version/VersionSelector.tsx
```typescript
import React, { useState, useEffect } from 'react';

interface VersionOption {
  value: string;
  label: string;
  date?: string;
}

interface VersionSelectorProps {
  onVersionChange: (version: string, date?: string) => void;
  includeDate?: boolean;
  currentVersion?: string;
}

export const VersionSelector: React.FC<VersionSelectorProps> = ({
  onVersionChange,
  includeDate = false,
  currentVersion = 'current'
}) => {
  const [selectedVersion, setSelectedVersion] = useState(currentVersion);
  const [selectedDate, setSelectedDate] = useState<string>('');

  const versionOptions: VersionOption[] = [
    { value: 'current', label: 'Current Version' },
    { value: 'previous', label: 'Previous Version' },
    { value: 'date', label: 'As at Date...' }
  ];

  const handleVersionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const version = e.target.value;
    setSelectedVersion(version);

    if (version !== 'date') {
      onVersionChange(version);
    }
  };

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const date = e.target.value;
    setSelectedDate(date);
    onVersionChange('date', date);
  };

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
      <label className="text-sm font-medium text-gray-700">Version:</label>
      <select
        value={selectedVersion}
        onChange={handleVersionChange}
        className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
      >
        {versionOptions.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      {selectedVersion === 'date' && (
        <>
          <label className="text-sm font-medium text-gray-700">Date:</label>
          <input
            type="date"
            value={selectedDate}
            onChange={handleDateChange}
            max={new Date().toISOString().split('T')[0]}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          />
        </>
      )}

      {selectedVersion !== 'current' && (
        <div className="ml-auto px-3 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-md">
          ⚠️ Viewing historical version
        </div>
      )}
    </div>
  );
};
```

### Step 2: API Integration Hooks

#### File: frontend-nextjs/hooks/useVersion.ts
```typescript
import { useState, useEffect } from 'react';
import { API_BASE_URL } from '@/config';

interface VersionInfo {
  current: DocumentVersion | null;
  previous: DocumentVersion | null;
}

interface DocumentVersion {
  id: number;
  document_type: string;
  document_identifier: string;
  version_number: string;
  version_status: string;
  effective_date: string;
  superseded_date?: string;
  change_summary?: string;
}

export const useVersion = (documentType: string, documentIdentifier: string) => {
  const [versionInfo, setVersionInfo] = useState<VersionInfo>({ current: null, previous: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVersionInfo = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `${API_BASE_URL}/api/versions/${documentType}/${documentIdentifier}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch version info');
        }

        const data = await response.json();
        setVersionInfo(data.versions);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    if (documentType && documentIdentifier) {
      fetchVersionInfo();
    }
  }, [documentType, documentIdentifier]);

  return { versionInfo, loading, error };
};

export const useVersionedProvisions = (
  documentId?: string,
  version: string = 'current',
  asAtDate?: string
) => {
  const [provisions, setProvisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProvisions = async () => {
      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        if (documentId) params.append('document_id', documentId);
        params.append('version', version);
        if (asAtDate) params.append('as_at_date', asAtDate);
        params.append('include_version_info', 'true');

        const response = await fetch(
          `${API_BASE_URL}/api/provisions?${params.toString()}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch provisions');
        }

        const data = await response.json();
        setProvisions(data.provisions);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchProvisions();
  }, [documentId, version, asAtDate]);

  return { provisions, loading, error };
};
```

### Step 3: Update Existing Components

#### Modify: frontend-nextjs/app/authoritative/page.tsx
```typescript
// Add to imports
import { VersionSelector } from '@/components/version/VersionSelector';
import { VersionBadge } from '@/components/version/VersionBadge';
import { useVersionedProvisions } from '@/hooks/useVersion';

// Update component to include version selection
export default function AuthoritativePage() {
  const [selectedVersion, setSelectedVersion] = useState('current');
  const [asAtDate, setAsAtDate] = useState<string | undefined>();

  const { provisions, loading, error } = useVersionedProvisions(
    undefined, // document_id
    selectedVersion === 'date' ? undefined : selectedVersion,
    asAtDate
  );

  const handleVersionChange = (version: string, date?: string) => {
    if (version === 'date' && date) {
      setAsAtDate(date);
      setSelectedVersion('date');
    } else {
      setSelectedVersion(version);
      setAsAtDate(undefined);
    }
  };

  return (
    <div>
      {/* Add version selector to top of page */}
      <div className="mb-6">
        <VersionSelector
          onVersionChange={handleVersionChange}
          currentVersion={selectedVersion}
        />
      </div>

      {/* Show version context if not current */}
      {selectedVersion !== 'current' && (
        <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-sm text-amber-800">
            <strong>Note:</strong> You are viewing {
              selectedVersion === 'date'
                ? `provisions as at ${asAtDate}`
                : `the ${selectedVersion} version`
            }. These may not reflect current requirements.
          </p>
        </div>
      )}

      {/* Existing provisions display with version badges */}
      {provisions.map(provision => (
        <div key={provision.id} className="provision-card">
          {/* Add version badge to each provision */}
          {provision.version_info && (
            <VersionBadge
              versionNumber={provision.version_info.version_number}
              status={provision.version_info.version_status}
              effectiveDate={provision.version_info.effective_date}
              className="mb-2"
            />
          )}
          {/* Rest of provision display */}
        </div>
      ))}
    </div>
  );
}
```

### Step 4: Version Comparison View

#### File: frontend-nextjs/components/version/VersionComparison.tsx
```typescript
import React from 'react';
import { diffWords } from 'diff';

interface VersionComparisonProps {
  currentProvision: any;
  previousProvision: any;
}

export const VersionComparison: React.FC<VersionComparisonProps> = ({
  currentProvision,
  previousProvision
}) => {
  if (!previousProvision) {
    return (
      <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
        <p className="text-sm text-green-800">New provision (no previous version)</p>
      </div>
    );
  }

  const diff = diffWords(
    previousProvision.provision_text || '',
    currentProvision.provision_text || ''
  );

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Version Comparison</h3>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Previous Version ({previousProvision.version_number})
          </h4>
          <div className="p-3 bg-gray-50 border border-gray-200 rounded">
            <p className="text-sm">{previousProvision.provision_text}</p>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Current Version ({currentProvision.version_number})
          </h4>
          <div className="p-3 bg-gray-50 border border-gray-200 rounded">
            <p className="text-sm">
              {diff.map((part, index) => (
                <span
                  key={index}
                  className={
                    part.added ? 'bg-green-200' :
                    part.removed ? 'bg-red-200 line-through' : ''
                  }
                >
                  {part.value}
                </span>
              ))}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
```

## Testing Checklist

### Component Testing
- [ ] VersionBadge displays correctly
- [ ] VersionSelector changes trigger API calls
- [ ] Date picker limits to past dates only
- [ ] Warning shows for historical versions
- [ ] Version comparison highlights differences

### Integration Testing
- [ ] API calls include version parameters
- [ ] Provisions update when version changes
- [ ] Loading states display correctly
- [ ] Error handling works
- [ ] Performance acceptable

### User Experience
- [ ] Version indicators clear and visible
- [ ] Historical view warning prominent
- [ ] Version switching smooth
- [ ] No layout shifts
- [ ] Mobile responsive

## Success Criteria

1. ✅ Version indicators visible on all provisions
2. ✅ Version switching works without page reload
3. ✅ Historical date selection functional
4. ✅ Clear warnings for non-current versions
5. ✅ No regression in existing functionality

## Next Steps

1. Run `verify_v5_frontend.py` to test components
2. Proceed to PRP-V6_VALIDATION_SUITE.md
3. Conduct user acceptance testing