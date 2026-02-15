// Test ContextSection with actual property data structure
import { pdf } from '@react-pdf/renderer';
import { createElement } from 'react';
import React from 'react';
import { Document } from '@react-pdf/renderer';

// Import the actual ContextSection component
const { ContextSection } = await import('./components/pdf/ContextSection.tsx');

// Build property context matching what the UI sends
const propertyContext = {
  address: '12 SHELLEYS LANE, PETERSHAM NSW 2049',
  zone: 'R4 High Density Residential',
  former_council: 'Marrickville',
  heritage_status: {
    in_hca: true,
    hca_name: 'Llewellyn Estate Heritage Conservation Area',
    hca_code: 'C12',
  },
  lot_dimensions: {
    area: 289,
    frontage: 12.2,
    depth: 23.7,
    is_corner: false,
  },
  lep_controls: {
    height: '12m',
    fsr: '1.5:1',
    acid_sulfate_soils: 'Class 5',
  },
  planning_portal_layers: {
    heritage_map: 'C12',
    fsr_map: '1.5:1',
    height_map: '12m',
    acid_sulfate_soils_map: 'Class 5',
    tree_canopy_2019: '20.80',
    tree_canopy_2022: '14.63',
  },
};

console.log('Testing ContextSection with property data...\n');

try {
  const doc = createElement(Document, {},
    createElement(ContextSection, {
      property: propertyContext,
      exportedCount: 163,
      totalCount: 597,
      activeFilters: ['Numeric provisions only']
    })
  );

  await pdf(doc).toBlob();
  console.log('✓ ContextSection works!\n');
  console.log('Issue must be in how ProvisionReport combines all components');
} catch (e) {
  console.log(`✗ ContextSection FAILED: ${e.message}`);
  console.log(`\nThis is the culprit! Error in ContextSection.`);
  console.log(`Stack: ${e.stack}`);
}
