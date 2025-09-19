# PRP-K7: Zone-Aware Development Type System with Progressive Disclosure

## Executive Summary
Implement a comprehensive zone-aware system that displays ALL applicable development types and their specific requirements, replacing the current flawed single-provision aggregation with a progressive disclosure UX that educates users about permitted developments while enabling informed compliance decisions.

## Problem Statement
- System currently shows only ONE development type (RFB) when multiple are permitted
- Missing Multi Dwelling Housing provisions (C11) were found but not displayed
- Aggregation logic incorrectly collapses multiple provisions into one
- Users cannot compare requirements across different development types
- No indication of what development types are actually permitted in each zone

## Solution Architecture

### Phase 1: Data Completeness (Backend)
1. **Import ALL missing zone provisions**
2. **Map development types to zones**
3. **Establish entity relationships**
4. **Remove aggregation logic**

### Phase 2: Progressive Disclosure (Frontend)
1. **Zone determination** → Show permitted development types
2. **Type selection** → Filter displayed requirements
3. **Comparison view** → Side-by-side requirements

### Phase 3: Verification & Testing
1. **Automated data completeness checks**
2. **Zone coverage validation**
3. **Development type mapping verification**

## Technical Implementation

### 1. Data Import Pipeline

#### 1.1 Find and Import All Zone Provisions
```python
# find_and_import_all_zones.py
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class ZoneProvisionImporter:
    """Import all zone-specific provisions from extracted JSON files"""
    
    def __init__(self, db_path: str = 'nsw_planning.db'):
        self.db_path = db_path
        self.zones = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B4', 'B6', 'IN1', 'IN2', 'E2', 'E3', 'RE1', 'RE2']
        self.development_types = {
            'R1': ['dwelling_house', 'dual_occupancy', 'secondary_dwelling'],
            'R2': ['dwelling_house', 'dual_occupancy', 'multi_dwelling_housing', 'residential_flat_building', 'secondary_dwelling'],
            'R3': ['dwelling_house', 'multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing'],
            'R4': ['residential_flat_building', 'shop_top_housing', 'mixed_use'],
            'B1': ['shop_top_housing', 'commercial_premises', 'office_premises'],
            'B2': ['shop_top_housing', 'commercial_premises', 'office_premises', 'mixed_use'],
            'B4': ['mixed_use', 'commercial_premises', 'shop_top_housing'],
            'B6': ['enterprise_corridor', 'business_premises', 'office_premises'],
            'IN1': ['light_industries', 'warehouse', 'industrial_retail'],
            'IN2': ['light_industries', 'warehouse', 'industrial'],
            'E2': ['environmental_conservation'],
            'E3': ['environmental_management'],
            'RE1': ['public_recreation'],
            'RE2': ['private_recreation']
        }
        self.imported_count = 0
        self.skipped_count = 0
        
    def find_json_sources(self) -> List[Path]:
        """Find all JSON files containing zone provisions"""
        json_files = []
        search_dirs = [
            'output',
            'validated_outputs', 
            'langextract_verified_output',
            'autoschemakg_output_comprehensive',
            'rag_storage'
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for root, dirs, files in os.walk(search_dir):
                    for file in files:
                        if file.endswith('.json'):
                            json_files.append(Path(root) / file)
        
        return json_files
    
    def extract_zone_provisions(self, json_path: Path) -> List[Dict]:
        """Extract zone-specific provisions from JSON file"""
        provisions = []
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle different JSON structures
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Try common keys
                items = data.get('provisions', data.get('items', data.get('content', [])))
                if not isinstance(items, list):
                    items = [data]
            else:
                return []
                
            for item in items:
                # Extract text content
                text = None
                if isinstance(item, str):
                    text = item
                elif isinstance(item, dict):
                    text = item.get('provision_text', item.get('text', item.get('content', '')))
                
                if not text:
                    continue
                    
                # Check if it's a zone-related provision
                for zone in self.zones:
                    if f' {zone} ' in text or f'zone {zone}' in text.lower():
                        # Extract development type if mentioned
                        dev_type = self.identify_development_type(text)
                        
                        # Extract setback values
                        setbacks = self.extract_setback_values(text)
                        
                        if setbacks:
                            provision = {
                                'zone': zone,
                                'development_type': dev_type,
                                'text': text,
                                'setbacks': setbacks,
                                'source_file': str(json_path),
                                'document_id': self.extract_document_id(json_path, item)
                            }
                            provisions.append(provision)
                            
        except Exception as e:
            print(f"Error processing {json_path}: {e}")
            
        return provisions
    
    def identify_development_type(self, text: str) -> str:
        """Identify development type from provision text"""
        text_lower = text.lower()
        
        type_mappings = {
            'multi dwelling housing': 'multi_dwelling_housing',
            'multi-dwelling housing': 'multi_dwelling_housing',
            'residential flat building': 'residential_flat_building',
            'dwelling house': 'dwelling_house',
            'dual occupancy': 'dual_occupancy',
            'shop top housing': 'shop_top_housing',
            'mixed use': 'mixed_use',
            'commercial premises': 'commercial_premises',
            'office premises': 'office_premises',
            'light industries': 'light_industries',
            'warehouse': 'warehouse',
            'secondary dwelling': 'secondary_dwelling'
        }
        
        for key, value in type_mappings.items():
            if key in text_lower:
                return value
                
        return 'general'
    
    def extract_setback_values(self, text: str) -> Dict[str, float]:
        """Extract numeric setback values from text"""
        import re
        
        setbacks = {}
        
        # Pattern to find setback values
        patterns = [
            (r'front.*?(\d+(?:\.\d+)?)\s*(?:metres?|m)', 'front'),
            (r'side.*?(\d+(?:\.\d+)?)\s*(?:metres?|m)', 'side'),
            (r'rear.*?(\d+(?:\.\d+)?)\s*(?:metres?|m)', 'rear'),
            (r'(\d+(?:\.\d+)?)\s*(?:metres?|m).*?front', 'front'),
            (r'(\d+(?:\.\d+)?)\s*(?:metres?|m).*?side', 'side'),
            (r'(\d+(?:\.\d+)?)\s*(?:metres?|m).*?rear', 'rear'),
        ]
        
        for pattern, boundary_type in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if 0.5 <= value <= 50:  # Reasonable setback range
                    setbacks[boundary_type] = value
                    
        return setbacks
    
    def extract_document_id(self, json_path: Path, item: Dict) -> str:
        """Extract document ID from path or item"""
        if isinstance(item, dict) and 'document_id' in item:
            return item['document_id']
            
        # Try to extract from file path
        path_str = str(json_path)
        if 'Marrickville' in path_str:
            return 'Marrickville_DCP_2011'
        elif 'Ashfield' in path_str:
            return 'Ashfield_DCP_2016'
        elif 'Leichhardt' in path_str:
            return 'Leichhardt_DCP_2013'
        elif 'LEP' in path_str:
            return 'Inner_West_LEP_2022'
        elif 'SEPP' in path_str:
            return 'SEPP_Housing_2021'
            
        return 'Unknown_Source'
    
    def import_to_database(self, provisions: List[Dict]) -> Tuple[int, int]:
        """Import provisions to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        imported = 0
        skipped = 0
        
        for prov in provisions:
            # Check if already exists
            existing = cursor.execute('''
                SELECT COUNT(*) FROM regulatory_provisions
                WHERE zone = ? AND development_type = ? 
                AND provision_text LIKE ?
            ''', (prov['zone'], prov['development_type'], f"%{prov['text'][:50]}%")).fetchone()[0]
            
            if existing > 0:
                skipped += 1
                continue
                
            try:
                # Insert main provision
                cursor.execute('''
                    INSERT INTO regulatory_provisions (
                        provision_type, zone, development_type,
                        provision_text, document_id, section_header,
                        domain_classification, prp_k1_enhanced,
                        classification_confidence, cross_contamination_checked,
                        created_at
                    ) VALUES (
                        'control', ?, ?, ?, ?, 'Building setbacks',
                        'RESIDENTIAL_BUILDINGS', 1, 0.9, 1, ?
                    )
                ''', (
                    prov['zone'],
                    prov['development_type'],
                    prov['text'],
                    prov['document_id'],
                    datetime.now().isoformat()
                ))
                
                provision_id = cursor.lastrowid
                
                # Insert quantitative standards
                for boundary_type, value in prov['setbacks'].items():
                    cursor.execute('''
                        INSERT INTO quantitative_standards (
                            provision_id, numeric_value, unit,
                            context, confidence_score
                        ) VALUES (?, ?, 'm', ?, 0.9)
                    ''', (provision_id, value, f'setback_{boundary_type}'))
                
                imported += 1
                
            except sqlite3.IntegrityError as e:
                print(f"Skipped duplicate: {e}")
                skipped += 1
                
        conn.commit()
        conn.close()
        
        return imported, skipped
    
    def run_import(self) -> Dict:
        """Run the complete import process"""
        print("=" * 60)
        print("PRP-K7: Zone Provision Import Pipeline")
        print("=" * 60)
        
        # Find JSON sources
        json_files = self.find_json_sources()
        print(f"Found {len(json_files)} JSON files to process")
        
        # Extract provisions
        all_provisions = []
        for json_file in json_files:
            provisions = self.extract_zone_provisions(json_file)
            if provisions:
                all_provisions.extend(provisions)
                print(f"  ✓ Extracted {len(provisions)} provisions from {json_file.name}")
        
        print(f"\nTotal provisions extracted: {len(all_provisions)}")
        
        # Import to database
        imported, skipped = self.import_to_database(all_provisions)
        
        print(f"\nImport complete:")
        print(f"  ✓ Imported: {imported}")
        print(f"  ⊘ Skipped: {skipped}")
        
        return {
            'files_processed': len(json_files),
            'provisions_found': len(all_provisions),
            'imported': imported,
            'skipped': skipped
        }
```

### 2. Remove Aggregation Logic

#### 2.1 Update API Route to Return All Provisions
```typescript
// app/api/setbacks/calculate/route.ts - UPDATED SECTION
// Replace lines 104-154 with:

// DO NOT AGGREGATE - Return all provisions for all development types
const enhancedSetbacks = setbacksData.map((setback: any) => {
  // Add development type identification
  const devType = identifyDevelopmentType(setback.legal_source, setback.provision_text);
  
  return {
    boundary_type: setback.boundary_type,
    development_type: devType,
    value: setback.required_setback,
    setback_distance: setback.required_setback,
    required_setback: setback.required_setback,
    unit: 'meters',
    confidence: setback.confidence,
    confidence_score: setback.confidence,
    rule_source: setback.legal_source,
    clause_reference: setback.clause_reference,
    legal_source: setback.legal_source,
    authority: getCorrectAuthorityLevel(setback.legal_authority?.secondary_authority || setback.legal_source || 'DCP'),
    precedence: getCorrectAuthorityLevel(setback.legal_authority?.secondary_authority || setback.legal_source || 'DCP') === 'SEPP' ? 1 : 
               getCorrectAuthorityLevel(setback.legal_authority?.secondary_authority || setback.legal_source || 'DCP') === 'LEP' ? 2 : 3,
    provision_id: setback.provision_id,
    legal_authority: setback.legal_authority,
    domain_classification: setback.domain_classification,
    cross_contamination_checked: setback.cross_contamination_checked,
    full_text: setback.contextual_requirements // Include full text, not truncated
  };
});

// Group by development type for organized display
const groupedSetbacks = enhancedSetbacks.reduce((acc: any, setback: any) => {
  const devType = setback.development_type || 'general';
  if (!acc[devType]) {
    acc[devType] = [];
  }
  acc[devType].push(setback);
  return acc;
}, {});

function identifyDevelopmentType(source: string, text?: string): string {
  const combined = `${source} ${text || ''}`.toLowerCase();
  
  if (combined.includes('multi dwelling') || combined.includes('multi-dwelling')) {
    return 'multi_dwelling_housing';
  }
  if (combined.includes('residential flat') || combined.includes('rfb')) {
    return 'residential_flat_building';
  }
  if (combined.includes('dwelling house') || combined.includes('single dwelling')) {
    return 'dwelling_house';
  }
  if (combined.includes('dual occupancy')) {
    return 'dual_occupancy';
  }
  if (combined.includes('shop top') || combined.includes('shoptop')) {
    return 'shop_top_housing';
  }
  
  return 'general';
}
```

### 3. Progressive Disclosure UI

#### 3.1 Development Type Selector Component
```typescript
// components/compliance/DevelopmentTypeSelector.tsx
'use client';

import { useState, useEffect } from 'react';
import { Check, Info, Building, Home, Users, Store } from 'lucide-react';

interface DevelopmentType {
  id: string;
  name: string;
  description: string;
  icon: any;
  permitted: boolean;
}

interface DevelopmentTypeSelectorProps {
  zone: string;
  onSelectionChange: (selected: string[]) => void;
}

const ZONE_DEVELOPMENT_TYPES: Record<string, DevelopmentType[]> = {
  'R1': [
    { id: 'dwelling_house', name: 'Dwelling House', description: 'Single residential dwelling', icon: Home, permitted: true },
    { id: 'dual_occupancy', name: 'Dual Occupancy', description: 'Two dwellings on one lot', icon: Users, permitted: true },
  ],
  'R2': [
    { id: 'dwelling_house', name: 'Dwelling House', description: 'Single residential dwelling', icon: Home, permitted: true },
    { id: 'dual_occupancy', name: 'Dual Occupancy', description: 'Two dwellings on one lot', icon: Users, permitted: true },
    { id: 'multi_dwelling_housing', name: 'Multi Dwelling Housing', description: 'Townhouses, villas (3+ dwellings)', icon: Building, permitted: true },
    { id: 'residential_flat_building', name: 'Residential Flat Building', description: 'Apartment building', icon: Building, permitted: true },
  ],
  'R3': [
    { id: 'dwelling_house', name: 'Dwelling House', description: 'Single residential dwelling', icon: Home, permitted: true },
    { id: 'multi_dwelling_housing', name: 'Multi Dwelling Housing', description: 'Townhouses, villas', icon: Building, permitted: true },
    { id: 'residential_flat_building', name: 'Residential Flat Building', description: 'Apartment building', icon: Building, permitted: true },
    { id: 'shop_top_housing', name: 'Shop Top Housing', description: 'Residential above retail', icon: Store, permitted: true },
  ],
  'R4': [
    { id: 'residential_flat_building', name: 'Residential Flat Building', description: 'High density apartments', icon: Building, permitted: true },
    { id: 'shop_top_housing', name: 'Shop Top Housing', description: 'Mixed use development', icon: Store, permitted: true },
  ],
};

export function DevelopmentTypeSelector({ zone, onSelectionChange }: DevelopmentTypeSelectorProps) {
  const developmentTypes = ZONE_DEVELOPMENT_TYPES[zone] || [];
  const [selected, setSelected] = useState<string[]>(developmentTypes.map(dt => dt.id));

  useEffect(() => {
    onSelectionChange(selected);
  }, [selected, onSelectionChange]);

  const toggleSelection = (typeId: string) => {
    setSelected(prev => 
      prev.includes(typeId) 
        ? prev.filter(id => id !== typeId)
        : [...prev, typeId]
    );
  };

  if (developmentTypes.length === 0) {
    return null;
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex items-start gap-2 mb-3">
        <Info className="h-5 w-5 text-blue-600 mt-0.5" />
        <div>
          <h3 className="font-semibold text-gray-900">
            Development Types Permitted in Zone {zone}
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Select the development types you want to see requirements for:
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
        {developmentTypes.map(type => {
          const Icon = type.icon;
          const isSelected = selected.includes(type.id);
          
          return (
            <button
              key={type.id}
              onClick={() => toggleSelection(type.id)}
              className={`
                flex items-start gap-3 p-3 rounded-lg border-2 transition-all
                ${isSelected 
                  ? 'border-blue-500 bg-white shadow-sm' 
                  : 'border-gray-200 bg-gray-50 opacity-60'
                }
              `}
            >
              <div className={`mt-0.5 ${isSelected ? 'text-blue-600' : 'text-gray-400'}`}>
                {isSelected ? (
                  <div className="relative">
                    <Icon className="h-5 w-5" />
                    <Check className="h-3 w-3 absolute -bottom-1 -right-1 text-green-600" />
                  </div>
                ) : (
                  <Icon className="h-5 w-5" />
                )}
              </div>
              <div className="flex-1 text-left">
                <div className="font-medium text-sm text-gray-900">
                  {type.name}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {type.description}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-4 text-xs text-gray-500 flex items-center gap-1">
        <Info className="h-3 w-3" />
        All types are shown by default. Uncheck types not relevant to your project.
      </div>
    </div>
  );
}
```

#### 3.2 Enhanced Setback Display Component
```typescript
// components/analysis/GroupedSetbackDisplay.tsx
'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Building, Home, Users, FileText } from 'lucide-react';
import { DevelopmentTypeSelector } from '@/components/compliance/DevelopmentTypeSelector';
import { ReferencedLegislationAccordion } from '@/components/compliance/ReferencedLegislationAccordion';

interface GroupedSetbackDisplayProps {
  zone: string;
  groupedSetbacks: Record<string, any[]>;
}

const DEV_TYPE_NAMES: Record<string, string> = {
  'dwelling_house': 'Single Dwelling House',
  'dual_occupancy': 'Dual Occupancy',
  'multi_dwelling_housing': 'Multi Dwelling Housing',
  'residential_flat_building': 'Residential Flat Buildings',
  'shop_top_housing': 'Shop Top Housing',
  'general': 'General Requirements'
};

const DEV_TYPE_ICONS: Record<string, any> = {
  'dwelling_house': Home,
  'dual_occupancy': Users,
  'multi_dwelling_housing': Building,
  'residential_flat_building': Building,
  'shop_top_housing': Building,
  'general': FileText
};

export function GroupedSetbackDisplay({ zone, groupedSetbacks }: GroupedSetbackDisplayProps) {
  const [selectedTypes, setSelectedTypes] = useState<string[]>(Object.keys(groupedSetbacks));
  const [expandedTypes, setExpandedTypes] = useState<string[]>(Object.keys(groupedSetbacks));

  const toggleExpanded = (type: string) => {
    setExpandedTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  return (
    <div className="space-y-6">
      {/* Development Type Selector */}
      <DevelopmentTypeSelector 
        zone={zone}
        onSelectionChange={setSelectedTypes}
      />

      {/* Grouped Setback Display */}
      <div className="space-y-4">
        {Object.entries(groupedSetbacks)
          .filter(([devType]) => selectedTypes.includes(devType))
          .map(([devType, setbacks]) => {
            const Icon = DEV_TYPE_ICONS[devType] || FileText;
            const isExpanded = expandedTypes.includes(devType);
            
            // Group setbacks by boundary type
            const byBoundary = setbacks.reduce((acc: any, s: any) => {
              if (!acc[s.boundary_type]) acc[s.boundary_type] = [];
              acc[s.boundary_type].push(s);
              return acc;
            }, {});

            return (
              <div key={devType} className="border border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleExpanded(devType)}
                  className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-5 w-5 text-gray-600" />
                    <h3 className="font-semibold text-gray-900">
                      {DEV_TYPE_NAMES[devType] || devType}
                    </h3>
                    <span className="text-sm text-gray-500">
                      ({setbacks.length} provisions)
                    </span>
                  </div>
                  {isExpanded ? <ChevronUp /> : <ChevronDown />}
                </button>

                {isExpanded && (
                  <div className="p-4 space-y-3">
                    {/* Summary of setbacks */}
                    <div className="grid grid-cols-3 gap-4 mb-4">
                      {['front', 'side', 'rear'].map(boundary => {
                        const boundarySetbacks = byBoundary[boundary] || [];
                        const values = boundarySetbacks.map((s: any) => s.value);
                        const min = Math.min(...values);
                        const max = Math.max(...values);
                        
                        return (
                          <div key={boundary} className="bg-white border border-gray-200 rounded p-3">
                            <div className="text-xs text-gray-500 uppercase mb-1">
                              {boundary} Setback
                            </div>
                            <div className="font-bold text-lg text-gray-900">
                              {values.length > 0 ? (
                                min === max ? `${min}m` : `${min}-${max}m`
                              ) : (
                                <span className="text-gray-400">N/A</span>
                              )}
                            </div>
                            {values.length > 1 && (
                              <div className="text-xs text-gray-500 mt-1">
                                {values.length} variations
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Detailed provisions */}
                    <div className="space-y-2">
                      {setbacks.map((setback: any, idx: number) => (
                        <div key={idx} className="bg-gray-50 rounded p-3 text-sm">
                          <div className="flex justify-between items-start mb-2">
                            <div>
                              <span className="font-medium capitalize">{setback.boundary_type}</span>
                              <span className="ml-2 text-gray-600">{setback.value}m</span>
                            </div>
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                              {setback.authority}
                            </span>
                          </div>
                          <div className="text-xs text-gray-600">
                            {setback.clause_reference}
                          </div>
                          {setback.full_text && (
                            <div className="mt-2 text-xs text-gray-500 italic">
                              {setback.full_text}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Referenced Legislation */}
                    <ReferencedLegislationAccordion 
                      setbacks={setbacks}
                    />
                  </div>
                )}
              </div>
            );
          })}
      </div>

      {/* Comparison Table (optional enhancement) */}
      {selectedTypes.length > 1 && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="font-semibold mb-3">Quick Comparison</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">Development Type</th>
                <th className="text-center">Front</th>
                <th className="text-center">Side</th>
                <th className="text-center">Rear</th>
              </tr>
            </thead>
            <tbody>
              {selectedTypes.map(devType => {
                const setbacks = groupedSetbacks[devType] || [];
                const front = setbacks.find((s: any) => s.boundary_type === 'front');
                const side = setbacks.find((s: any) => s.boundary_type === 'side');
                const rear = setbacks.find((s: any) => s.boundary_type === 'rear');
                
                return (
                  <tr key={devType} className="border-b">
                    <td className="py-2">{DEV_TYPE_NAMES[devType]}</td>
                    <td className="text-center">{front?.value || '-'}m</td>
                    <td className="text-center">{side?.value || '-'}m</td>
                    <td className="text-center">{rear?.value || '-'}m</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

### 4. Verification & Testing Suite

#### 4.1 Automated Verification Script
```python
# verify_prp_k7_implementation.py
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any

class PRPk7Verifier:
    """Automated verification for PRP-K7 implementation"""
    
    def __init__(self, db_path: str = 'nsw_planning.db'):
        self.db_path = db_path
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'summary': {}
        }
        
    def verify_data_completeness(self) -> Dict:
        """Verify all zones have appropriate provisions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        zones = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B4', 'B6', 'IN1', 'IN2']
        zone_coverage = {}
        
        for zone in zones:
            # Count provisions per zone
            provisions = cursor.execute('''
                SELECT COUNT(DISTINCT id) as count,
                       COUNT(DISTINCT development_type) as dev_types
                FROM regulatory_provisions
                WHERE zone = ?
            ''', (zone,)).fetchone()
            
            # Get development types
            dev_types = cursor.execute('''
                SELECT DISTINCT development_type
                FROM regulatory_provisions
                WHERE zone = ?
                AND development_type IS NOT NULL
            ''', (zone,)).fetchall()
            
            zone_coverage[zone] = {
                'provision_count': provisions[0],
                'development_type_count': provisions[1],
                'development_types': [dt[0] for dt in dev_types]
            }
        
        conn.close()
        
        # Check minimum requirements
        passed = all([
            zone_coverage.get('R2', {}).get('development_type_count', 0) >= 4,
            zone_coverage.get('R3', {}).get('development_type_count', 0) >= 3,
            zone_coverage.get('R4', {}).get('development_type_count', 0) >= 2
        ])
        
        return {
            'test': 'data_completeness',
            'passed': passed,
            'zone_coverage': zone_coverage
        }
    
    def verify_development_types(self) -> Dict:
        """Verify development types are properly mapped"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check C11 and C12 provisions exist
        c11_check = cursor.execute('''
            SELECT COUNT(*) FROM regulatory_provisions
            WHERE ref_number LIKE 'C11%'
            AND section_header = '4.2.4.3 Building setbacks'
        ''').fetchone()[0]
        
        c12_check = cursor.execute('''
            SELECT COUNT(*) FROM regulatory_provisions
            WHERE ref_number LIKE 'C12%'
            AND section_header = '4.2.4.3 Building setbacks'
        ''').fetchone()[0]
        
        # Check development type assignments
        dev_type_counts = cursor.execute('''
            SELECT development_type, COUNT(*) as count
            FROM regulatory_provisions
            WHERE development_type IS NOT NULL
            GROUP BY development_type
        ''').fetchall()
        
        conn.close()
        
        return {
            'test': 'development_types',
            'passed': c11_check >= 3 and c12_check >= 2,
            'c11_provisions': c11_check,
            'c12_provisions': c12_check,
            'development_type_distribution': dict(dev_type_counts)
        }
    
    def verify_quantitative_standards(self) -> Dict:
        """Verify quantitative standards are linked"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check linkage between provisions and quantitative standards
        linked_standards = cursor.execute('''
            SELECT 
                rp.zone,
                rp.development_type,
                qs.context,
                qs.numeric_value,
                qs.unit
            FROM regulatory_provisions rp
            JOIN quantitative_standards qs ON rp.id = qs.provision_id
            WHERE rp.zone IN ('R2', 'R3', 'R4')
            AND qs.context LIKE 'setback%'
            ORDER BY rp.zone, rp.development_type, qs.context
        ''').fetchall()
        
        # Group by zone and development type
        standards_by_zone = {}
        for zone, dev_type, context, value, unit in linked_standards:
            if zone not in standards_by_zone:
                standards_by_zone[zone] = {}
            if dev_type not in standards_by_zone[zone]:
                standards_by_zone[zone][dev_type] = []
            standards_by_zone[zone][dev_type].append({
                'context': context,
                'value': value,
                'unit': unit
            })
        
        conn.close()
        
        # Check R2 has both multi dwelling and RFB standards
        r2_check = (
            'multi_dwelling_housing' in standards_by_zone.get('R2', {}) and
            'residential_flat_building' in standards_by_zone.get('R2', {})
        )
        
        return {
            'test': 'quantitative_standards',
            'passed': r2_check and len(linked_standards) > 10,
            'total_standards': len(linked_standards),
            'standards_by_zone': standards_by_zone
        }
    
    def verify_no_aggregation(self) -> Dict:
        """Verify multiple provisions are returned (no aggregation)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for multiple provisions per boundary type in R2
        r2_provisions = cursor.execute('''
            SELECT 
                qs.context,
                COUNT(DISTINCT rp.development_type) as dev_type_count,
                GROUP_CONCAT(DISTINCT rp.development_type) as dev_types
            FROM regulatory_provisions rp
            JOIN quantitative_standards qs ON rp.id = qs.provision_id
            WHERE rp.zone = 'R2'
            AND qs.context IN ('setback_front', 'setback_side', 'setback_rear')
            GROUP BY qs.context
        ''').fetchall()
        
        conn.close()
        
        # Should have multiple development types per boundary
        multiple_types = all([count >= 2 for _, count, _ in r2_provisions])
        
        return {
            'test': 'no_aggregation',
            'passed': multiple_types,
            'r2_boundary_provisions': [
                {
                    'boundary': context.replace('setback_', ''),
                    'dev_type_count': count,
                    'dev_types': types.split(',') if types else []
                }
                for context, count, types in r2_provisions
            ]
        }
    
    def verify_full_text_availability(self) -> Dict:
        """Verify full provision text is available (not truncated)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check provision text lengths
        text_lengths = cursor.execute('''
            SELECT 
                MIN(LENGTH(provision_text)) as min_length,
                AVG(LENGTH(provision_text)) as avg_length,
                MAX(LENGTH(provision_text)) as max_length,
                COUNT(CASE WHEN LENGTH(provision_text) > 200 THEN 1 END) as long_texts
            FROM regulatory_provisions
            WHERE provision_text IS NOT NULL
            AND zone IN ('R2', 'R3', 'R4')
        ''').fetchone()
        
        conn.close()
        
        return {
            'test': 'full_text_availability',
            'passed': text_lengths[3] > 10,  # At least 10 provisions with >200 chars
            'min_text_length': text_lengths[0],
            'avg_text_length': round(text_lengths[1], 2),
            'max_text_length': text_lengths[2],
            'provisions_with_long_text': text_lengths[3]
        }
    
    def run_all_tests(self) -> Dict:
        """Run all verification tests"""
        print("=" * 60)
        print("PRP-K7 Implementation Verification")
        print("=" * 60)
        
        tests = [
            self.verify_data_completeness(),
            self.verify_development_types(),
            self.verify_quantitative_standards(),
            self.verify_no_aggregation(),
            self.verify_full_text_availability()
        ]
        
        for test in tests:
            test_name = test['test']
            passed = test['passed']
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"\n{test_name}: {status}")
            
            # Show key details
            if test_name == 'data_completeness':
                for zone, data in test['zone_coverage'].items():
                    if data['provision_count'] > 0:
                        print(f"  {zone}: {data['provision_count']} provisions, {data['development_type_count']} dev types")
            elif test_name == 'development_types':
                print(f"  C11 provisions: {test['c11_provisions']}")
                print(f"  C12 provisions: {test['c12_provisions']}")
            elif test_name == 'quantitative_standards':
                print(f"  Total linked standards: {test['total_standards']}")
            elif test_name == 'no_aggregation':
                for boundary_data in test['r2_boundary_provisions']:
                    print(f"  {boundary_data['boundary']}: {boundary_data['dev_type_count']} development types")
            elif test_name == 'full_text_availability':
                print(f"  Avg text length: {test['avg_text_length']} chars")
                print(f"  Long texts (>200 chars): {test['provisions_with_long_text']}")
        
        # Summary
        total_tests = len(tests)
        passed_tests = sum(1 for t in tests if t['passed'])
        
        print("\n" + "=" * 60)
        print(f"SUMMARY: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("✓ PRP-K7 Implementation COMPLETE AND VERIFIED")
        else:
            print("✗ PRP-K7 Implementation INCOMPLETE - Review failed tests")
        
        # Save results
        self.results['tests'] = {t['test']: t for t in tests}
        self.results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': round(passed_tests / total_tests * 100, 2)
        }
        
        with open('PRP_K7_VERIFICATION_REPORT.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed report saved to PRP_K7_VERIFICATION_REPORT.json")
        
        return self.results

if __name__ == "__main__":
    # Run import pipeline
    importer = ZoneProvisionImporter()
    import_results = importer.run_import()
    
    # Run verification
    verifier = PRPk7Verifier()
    verification_results = verifier.run_all_tests()
```

### 5. Implementation Checklist

```markdown
## PRP-K7 Implementation Checklist

### Phase 1: Data Import
- [ ] Run `find_and_import_all_zones.py` to import missing provisions
- [ ] Verify C11 Multi Dwelling Housing provisions present
- [ ] Verify C12 Residential Flat Building provisions present
- [ ] Verify all zones have appropriate coverage

### Phase 2: API Updates
- [ ] Remove aggregation logic from `/api/setbacks/calculate/route.ts`
- [ ] Implement development type identification
- [ ] Return grouped setbacks by development type
- [ ] Include full provision text (not truncated)

### Phase 3: Frontend Components
- [ ] Create `DevelopmentTypeSelector.tsx` component
- [ ] Create `GroupedSetbackDisplay.tsx` component
- [ ] Update `PreciseSetbackCalculator.tsx` to use new components
- [ ] Integrate with `ReferencedLegislationAccordion.tsx`

### Phase 4: Verification
- [ ] Run `verify_prp_k7_implementation.py`
- [ ] All 5 tests must pass:
  - [ ] Data completeness
  - [ ] Development types mapped
  - [ ] Quantitative standards linked
  - [ ] No aggregation (multiple provisions shown)
  - [ ] Full text available
- [ ] Review `PRP_K7_VERIFICATION_REPORT.json`

### Phase 5: User Testing
- [ ] Test with R2 zone address (should show 4 development types)
- [ ] Test with R3 zone address (should show 3-4 development types)
- [ ] Test with R4 zone address (should show 2 development types)
- [ ] Verify checkbox filtering works
- [ ] Verify comparison table displays correctly
- [ ] Verify Referenced Legislation shows full text
```

## Success Criteria

1. **Data Complete**: All zones have provisions for permitted development types
2. **No Aggregation**: Multiple provisions shown per boundary type
3. **Progressive Disclosure**: Users can select relevant development types
4. **Full Text**: Complete provision text available in accordion
5. **Verified**: Automated tests confirm implementation complete

## Testing Commands

```bash
# Import missing provisions
python find_and_import_all_zones.py

# Verify implementation
python verify_prp_k7_implementation.py

# Check specific zone coverage
python -c "from verify_prp_k7_implementation import PRPk7Verifier; v = PRPk7Verifier(); print(v.verify_data_completeness())"

# Test API endpoint
curl -X POST http://localhost:3008/api/setbacks/calculate \
  -H "Content-Type: application/json" \
  -d '{"property_id": 1962876, "property_zone": "R2"}'
```

## Expected Outcomes

After successful implementation:

1. **R2 Zone Query Returns**:
   - Multi Dwelling Housing: 6m front, 4m side, 4m rear
   - Residential Flat Buildings: 9m front, 3-4.5m side/rear
   - Dual Occupancy provisions (if available)
   - Single Dwelling provisions (if available)

2. **UI Shows**:
   - Checkbox selector for each permitted development type
   - Grouped display of requirements
   - Full provision text in accordion
   - Comparison table for easy reference

3. **Verification Report Shows**:
   - 100% test pass rate
   - All zones have coverage
   - No aggregation occurring
   - Full text preserved

## Risk Mitigation

- **Missing Data**: Import pipeline searches multiple JSON sources
- **Performance**: Frontend filtering avoids repeated API calls
- **User Confusion**: Progressive disclosure with sensible defaults
- **Data Quality**: Verification suite ensures completeness

---

**Status**: Ready for Implementation
**Priority**: Critical - Fixes fundamental data display issues
**Dependencies**: Requires database write access, API deployment capability
**Estimated Time**: 4-6 hours for complete implementation and verification