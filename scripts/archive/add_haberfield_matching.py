#!/usr/bin/env python3
"""
Add Haberfield (C54) matching for Clause 6.20
"""

# Read the file
with open('../frontend-nextjs/lib/property-data.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the site-specific matching block and add Haberfield check
old_matching = '''    // Match site-specific Part 6 LEP clauses (based on address/Lot-DP)
    try {
      const siteSpecificClauseNumbers = getSiteSpecificClauses(propertyData.address);
      if (siteSpecificClauseNumbers.length > 0) {
        console.log(`[PropertyDataService] Found ${siteSpecificClauseNumbers.length} site-specific Part 6 clause(s): ${siteSpecificClauseNumbers.join(', ')}`);
        
        // Initialize localProvisions array if not exists
        if (!constraints.localProvisions) {
          constraints.localProvisions = [];
        }
        
        // Add each site-specific clause as a LocalProvision
        for (const clauseNumber of siteSpecificClauseNumbers) {
          const details = getSiteSpecificProvisionDetails(clauseNumber);
          if (details) {
            constraints.localProvisions.push({
              title: details.title,
              clauseNumber: clauseNumber,
              pageNumber: details.pageNumber,
              mapType: 'Site-Specific', // Distinguish from Schedule 7 overlays
              legislationUrl: constraints.heritageLegislationUrl, // Use same LEP URL
              epiName: constraints.lga ? `${constraints.lga} Local Environmental Plan 2022` : undefined
            });
          }
        }
      }
    } catch (error) {
      console.log('[PropertyDataService] Site-specific clause matching failed:', error);
    }'''

new_matching = '''    // Match site-specific Part 6 LEP clauses (based on address/Lot-DP)
    try {
      const siteSpecificClauseNumbers = getSiteSpecificClauses(propertyData.address);
      
      // Special case: Haberfield Heritage Conservation Area (C54) -> Clause 6.20
      if (constraints.heritage && constraints.heritageItemNumber === 'C54') {
        if (!siteSpecificClauseNumbers.includes('6.20')) {
          siteSpecificClauseNumbers.push('6.20');
          console.log('[PropertyDataService] Added Clause 6.20 for Haberfield HCA (C54)');
        }
      }
      
      if (siteSpecificClauseNumbers.length > 0) {
        console.log(`[PropertyDataService] Found ${siteSpecificClauseNumbers.length} site-specific Part 6 clause(s): ${siteSpecificClauseNumbers.join(', ')}`);
        
        // Initialize localProvisions array if not exists
        if (!constraints.localProvisions) {
          constraints.localProvisions = [];
        }
        
        // Add each site-specific clause as a LocalProvision
        for (const clauseNumber of siteSpecificClauseNumbers) {
          const details = getSiteSpecificProvisionDetails(clauseNumber);
          if (details) {
            constraints.localProvisions.push({
              title: details.title,
              clauseNumber: clauseNumber,
              pageNumber: details.pageNumber,
              mapType: 'Site-Specific', // Distinguish from Schedule 7 overlays
              legislationUrl: constraints.heritageLegislationUrl, // Use same LEP URL
              epiName: constraints.lga ? `${constraints.lga} Local Environmental Plan 2022` : undefined
            });
          }
        }
      }
    } catch (error) {
      console.log('[PropertyDataService] Site-specific clause matching failed:', error);
    }'''

if old_matching in content:
    content = content.replace(old_matching, new_matching)
    print("[OK] Added Haberfield (C54) matching for Clause 6.20")
else:
    print("[SKIP] Haberfield matching already exists or code structure changed")

# Write the updated file
with open('../frontend-nextjs/lib/property-data.ts', 'w', encoding='utf-8') as f:
    f.write(content)

print("[DONE] Haberfield matching complete")
