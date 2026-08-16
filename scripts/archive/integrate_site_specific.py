#!/usr/bin/env python3
"""
Integrate site-specific Part 6 matching into property-data.ts
"""

# Read the file
with open('../frontend-nextjs/lib/property-data.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add import at the top after existing imports
import_line = "import { getSiteSpecificClauses, getSiteSpecificProvisionDetails } from './site-specific-part6-mapping';"
if import_line not in content:
    # Add after the inner-west-mapping import
    content = content.replace(
        "import { determineFormerCouncilArea as determineFormerCouncilAreaUtil } from './inner-west-mapping';",
        "import { determineFormerCouncilArea as determineFormerCouncilAreaUtil } from './inner-west-mapping';\nimport { getSiteSpecificClauses, getSiteSpecificProvisionDetails } from './site-specific-part6-mapping';"
    )
    print("[OK] Added import statement")
else:
    print("[SKIP] Import already exists")

# 2. Add site-specific matching logic after former council mapping (before SEPP routing)
matching_code = '''
    // Match site-specific Part 6 LEP clauses (based on address/Lot-DP)
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
    }
'''

# Find the insertion point (right before "// Route applicable SEPPs")
if matching_code.strip() not in content:
    content = content.replace(
        "    // Route applicable SEPPs",
        matching_code + "\n    // Route applicable SEPPs"
    )
    print("[OK] Added site-specific matching logic")
else:
    print("[SKIP] Matching logic already exists")

# Write the updated file
with open('../frontend-nextjs/lib/property-data.ts', 'w', encoding='utf-8') as f:
    f.write(content)

print("[DONE] Integration complete")
