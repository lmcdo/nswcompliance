#!/usr/bin/env python3
"""
Update LocalProvisionsCard to show PDF page images for site-specific clauses
"""

# Read the file
with open('../frontend-nextjs/components/compliance/LocalProvisionsCard.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Update the expanded section to show PDF images for site-specific clauses
old_expanded_section = '''                  {isExpanded && (
                    <div className="mt-3 p-3 bg-white rounded-md border border-amber-200">
                      {isLoading ? (
                        <p className="text-sm text-muted-foreground">Loading provision text...</p>
                      ) : detail ? (
                        <div className="space-y-2">
                          <h5 className="font-semibold text-sm text-amber-900">
                            {detail.clauseTitle}
                          </h5>
                          <div className="text-sm text-gray-700 whitespace-pre-wrap">
                            {detail.provisionText}
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">Provision text not available</p>
                      )}
                    </div>
                  )}'''

new_expanded_section = '''                  {isExpanded && (
                    <div className="mt-3 p-3 bg-white rounded-md border border-amber-200">
                      {isLoading ? (
                        <p className="text-sm text-muted-foreground">Loading provision text...</p>
                      ) : provision.mapType === 'Site-Specific' && provision.clauseNumber ? (
                        <div className="space-y-2">
                          <h5 className="font-semibold text-sm text-amber-900">
                            {provision.title}
                          </h5>
                          <p className="text-sm text-gray-700 mb-2">
                            View the full site-specific provision from Inner West LEP 2022:
                          </p>
                          <img 
                            src={`/pdf-pages/iwlep_site_specific_clause_${provision.clauseNumber.replace('.', '_')}_page_${provision.pageNumber}.png`}
                            alt={`Clause ${provision.clauseNumber} - Page ${provision.pageNumber}`}
                            className="w-full border border-amber-200 rounded"
                          />
                        </div>
                      ) : detail ? (
                        <div className="space-y-2">
                          <h5 className="font-semibold text-sm text-amber-900">
                            {detail.clauseTitle}
                          </h5>
                          <div className="text-sm text-gray-700 whitespace-pre-wrap">
                            {detail.provisionText}
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">Provision text not available</p>
                      )}
                    </div>
                  )}'''

if old_expanded_section in content:
    content = content.replace(old_expanded_section, new_expanded_section)
    print("[OK] Updated expanded section to show PDF images for site-specific clauses")
else:
    print("[SKIP] Expanded section already updated or not found")

# Update the badge to show provision type
old_badge_text = "            {localProvisions.length} {localProvisions.length === 1 ? 'overlay' : 'overlays'}"
new_badge_text = "            {localProvisions.length} {localProvisions.length === 1 ? 'provision' : 'provisions'}"

content = content.replace(old_badge_text, new_badge_text)
print("[OK] Updated badge text to 'provision(s)'")

# Update the footer note to mention site-specific clauses
old_note = '''          <p className="text-xs text-blue-800">
            <strong>Note:</strong> Local Provisions are Part 6 additional local provisions that may impose specific requirements for special areas. Common overlays include Special Entertainment Precincts, Heritage Conservation Areas, and Site-Specific Development Controls.
          </p>'''

new_note = '''          <p className="text-xs text-blue-800">
            <strong>Note:</strong> Local Provisions are Part 6 additional local provisions that may impose specific requirements. This includes Schedule 7 overlays (Special Entertainment Precincts, Heritage Conservation Areas) and site-specific provisions that apply to particular addresses.
          </p>'''

content = content.replace(old_note, new_note)
print("[OK] Updated footer note to mention site-specific clauses")

# Write the updated file
with open('../frontend-nextjs/components/compliance/LocalProvisionsCard.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("[DONE] LocalProvisionsCard update complete")
