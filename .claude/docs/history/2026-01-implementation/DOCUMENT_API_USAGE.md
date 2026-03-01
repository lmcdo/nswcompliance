# Full Document API - Usage Guide

## Overview

The `/api/documents/[id]` endpoint provides complete DCP/LEP/SEPP document text including embedded images, figures, and tables. This solves the truncation issue where provisions were cut off at 300-500 characters.

## Endpoint

```
GET /api/documents/[id]
```

## Use Cases

1. **View Complete DCP Chapter** - When provision text is truncated, fetch full chapter
2. **Access Images/Figures** - Get markdown-formatted text with image references
3. **Full Context** - See provision in context of entire document
4. **Complex Setbacks** - View complete setback rules with all conditions and exceptions

## Response Format

```typescript
{
  success: true,
  data: {
    id: string;                    // e.g., "Marrickville_DCP_2011___2_10_Parking"
    pdfName: string;               // e.g., "Marrickville DCP 2011 - 2 10 Parking.pdf"
    documentType: string;          // "DCP", "LEP", or "SEPP"
    documentArea: string | null;   // Former council area
    charCount: number;             // Total characters
    wordCount: number;             // Total words
    fullText: string;              // Complete markdown-formatted text with images
    extractionTimestamp: string;   // When document was extracted
    metadata: {
      imageCount: number;          // Number of images in document
      sectionCount: number;        // Number of sections (headers)
      hasVisualElements: boolean;  // Whether visual_elements_real has entries
    };
  },
  meta: {
    responseTimeMs: number;
    source: "documents_table";
    textLength: number;
  }
}
```

## Example Usage

### Frontend (React/TypeScript)

```typescript
// In LegalTextPanel or provision detail component
const fetchFullDocument = async (documentId: string) => {
  const response = await fetch(`/api/documents/${documentId}`);
  const data = await response.json();

  if (data.success) {
    const doc = data.data;

    // Display full text with images
    return (
      <div className="document-viewer">
        <h2>{doc.pdfName}</h2>
        <p>{doc.charCount.toLocaleString()} chars | {doc.wordCount.toLocaleString()} words</p>

        {/* Render markdown with images */}
        <ReactMarkdown>
          {doc.fullText}
        </ReactMarkdown>

        {doc.metadata.imageCount > 0 && (
          <div className="notice">
            📊 This document contains {doc.metadata.imageCount} figures/diagrams
          </div>
        )}
      </div>
    );
  }
};
```

### Button to View Full Document

```typescript
<Button onClick={() => fetchFullDocument(provision.document_id)}>
  View Complete Chapter (55,172 chars)
</Button>
```

### Extract Specific Section

```typescript
// Get full document
const response = await fetch(`/api/documents/${documentId}`);
const { data } = await response.json();

// Extract section 2.10.1 from full text
const section = extractSection(data.fullText, '2.10.1');

function extractSection(fullText: string, sectionRef: string): string {
  // Find section heading
  const regex = new RegExp(`## ${sectionRef}[^#]*`, 's');
  const match = fullText.match(regex);
  return match ? match[0] : '';
}
```

## Real Example

**Document ID:** `Marrickville_DCP_2011___2_10_Parking`

**What You Get:**
- **55,172 characters** of full text
- **7,326 words**
- Multiple **embedded images** as markdown: `![](images/6417552a08d069a7bf8a6375318434235ffa5c510509b589a95efdf789558968.jpg)`
- Complete sections from 2.10 through 2.10.16
- All parking tables, diagrams, and appendices

**Before (Truncated Provision):**
```
"To balance the need to meet car parking demand on-site to avoid excessive
spillover on to streets, with the need to constrain parking to maintain the
area's compact urban form and promote sustainable transport. To balance the
need to provide service/delivery areas on-site to avoid excessive use of
streets for this purpose, with the need to constrain those areas to maintain
the area's compact urban form and promote sustainable transport. To improve
the integration of land use and transport by app"
```

**After (Full Document Available):**
```
Complete 55,172 character document including:
- Full objectives text
- All parking rate tables
- Design control diagrams
- Bicycle parking provisions
- Appendix with parking area maps
- All embedded images
```

## Integration with Existing UI

### ComplianceDashboardV2

```typescript
// When user clicks provision card
const handleViewProvision = async (provision: ZoneProvision) => {
  // Show truncated text in panel
  setSelectedProvision({
    constraint: provisionToConstraint(provision),
    provisions: [...]
  });

  // Add button to view full document
  <Button onClick={() => viewFullDocument(provision.documentId)}>
    📄 View Complete {provision.documentId.includes('DCP') ? 'DCP' : 'LEP'} Chapter
  </Button>
};
```

### Handling Complex Setbacks

```typescript
<SetbackCard>
  <Value>1.2m rear setback</Value>

  {provision.hasConditions && (
    <>
      <Badge>⚠️ Conditions apply</Badge>
      <Button onClick={() => viewFullDocument(provision.documentId)}>
        View full setback rules with diagrams
      </Button>
    </>
  )}
</SetbackCard>
```

## Performance Notes

- **Response time:** ~50-100ms for typical DCP chapter
- **Caching:** Consider caching full documents client-side
- **Size:** Largest documents ~460KB (Heritage chapters)
- **Images:** Markdown references only, actual images served separately

## Testing

```bash
# Start Next.js dev server
cd frontend-nextjs
npm run dev

# Run test script
python test_document_api.py
```

## Error Handling

```typescript
try {
  const response = await fetch(`/api/documents/${documentId}`);
  const data = await response.json();

  if (!data.success) {
    console.error('API Error:', data.error);
    // Show fallback: "Document not available"
  }
} catch (error) {
  console.error('Network error:', error);
  // Show error message to user
}
```

## What Was Fixed

1. ❌ **Before:** Provisions truncated to 300 chars in API
2. ✅ **Now:** Zone-applicability API returns 2000 chars
3. ✅ **New:** Full document endpoint returns complete text (50k+ chars)
4. ✅ **Images:** Full text includes markdown image references
5. ✅ **Metadata:** Know image count, section count before fetching

## Next Steps

1. Update LegalTextPanel to add "View Full Document" button
2. Add markdown renderer to display images inline
3. Implement section extraction for targeted viewing
4. Add visual element linking (provision → specific figure)
