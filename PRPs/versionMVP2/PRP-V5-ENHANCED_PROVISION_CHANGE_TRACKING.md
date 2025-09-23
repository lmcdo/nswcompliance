# PRP-V5-Enhanced: Provision Change Tracking

## Objective
Enhance the VersionManager service to automatically detect and track provision-level changes when new document versions are created, providing granular change metadata for planner workflows.

## Prerequisites
- PRP-V4-Enhanced completed (baseline versions and change tracking table exist)
- VersionManager service operational
- provision_changes table created and populated with baseline data

## Technical Specification

### Enhancement 1: Change Detection Algorithm
```python
def detect_provision_changes(old_provisions: List[Dict], new_provisions: List[Dict]) -> List[Dict]:
    """
    Detect changes between two sets of provisions
    Returns list of change records with metadata
    """
    changes = []

    # Create lookup maps
    old_map = {p['ref_number']: p for p in old_provisions}
    new_map = {p['ref_number']: p for p in new_provisions}

    # Detect modifications and deletions
    for ref_number, old_provision in old_map.items():
        if ref_number in new_map:
            new_provision = new_map[ref_number]
            if old_provision['provision_text'] != new_provision['provision_text']:
                changes.append({
                    'ref_number': ref_number,
                    'change_type': 'MODIFIED',
                    'old_content': old_provision['provision_text'],
                    'new_content': new_provision['provision_text'],
                    'change_summary': generate_change_summary(old_provision, new_provision)
                })
        else:
            changes.append({
                'ref_number': ref_number,
                'change_type': 'DELETED',
                'old_content': old_provision['provision_text'],
                'new_content': None,
                'change_summary': f"Provision {ref_number} deleted"
            })

    # Detect new provisions
    for ref_number, new_provision in new_map.items():
        if ref_number not in old_map:
            changes.append({
                'ref_number': ref_number,
                'change_type': 'NEW',
                'old_content': None,
                'new_content': new_provision['provision_text'],
                'change_summary': f"New provision {ref_number} added"
            })

    return changes
```

### Enhancement 2: Change Summary Generation
```python
def generate_change_summary(old_provision: Dict, new_provision: Dict) -> str:
    """Generate human-readable change summary"""

    # Extract key regulatory elements
    old_text = old_provision['provision_text'].lower()
    new_text = new_provision['provision_text'].lower()

    # Check for common planning changes
    height_change = extract_height_change(old_text, new_text)
    if height_change:
        return height_change

    setback_change = extract_setback_change(old_text, new_text)
    if setback_change:
        return setback_change

    # Generic text change summary
    if len(new_text) > len(old_text) * 1.2:
        return "Provision significantly expanded"
    elif len(new_text) < len(old_text) * 0.8:
        return "Provision significantly shortened"
    else:
        return "Provision text modified"

def extract_height_change(old_text: str, new_text: str) -> Optional[str]:
    """Extract height limit changes"""
    import re

    old_height = re.search(r'(\d+(?:\.\d+)?)\s*m(?:etres?)?.*height', old_text)
    new_height = re.search(r'(\d+(?:\.\d+)?)\s*m(?:etres?)?.*height', new_text)

    if old_height and new_height:
        old_val = float(old_height.group(1))
        new_val = float(new_height.group(1))
        if old_val != new_val:
            return f"Height limit changed from {old_val}m to {new_val}m"

    return None
```

### Enhancement 3: Enhanced VersionManager Methods
```python
class VersionManager:
    def create_new_version_with_change_tracking(self,
                                              document_type: DocumentType,
                                              document_identifier: str,
                                              version_number: str,
                                              effective_date: date,
                                              new_provisions: List[Dict],
                                              document_url: Optional[str] = None,
                                              change_summary: Optional[str] = None,
                                              created_by: str = "system") -> Tuple[DocumentVersion, List[Dict]]:
        """Create new version with automatic change detection"""

        # Get current provisions for comparison
        current_version = self.get_current_version(document_type, document_identifier)
        if current_version:
            old_provisions = self.get_provisions_for_version(current_version.id)
        else:
            old_provisions = []

        # Detect changes
        changes = detect_provision_changes(old_provisions, new_provisions)

        # Create new document version (existing logic)
        new_version = self.create_new_version(
            document_type, document_identifier, version_number,
            effective_date, document_url, change_summary, created_by
        )

        # Record provision changes
        self.record_provision_changes(new_version.id, changes, effective_date, created_by)

        return new_version, changes

    def record_provision_changes(self,
                               document_version_id: int,
                               changes: List[Dict],
                               effective_date: date,
                               created_by: str):
        """Record provision changes in tracking table"""

        with self.conn.cursor() as cursor:
            for change in changes:
                cursor.execute("""
                    INSERT INTO versions.provision_changes (
                        document_version_id,
                        provision_id,
                        change_type,
                        old_content,
                        new_content,
                        change_summary,
                        change_metadata,
                        effective_date,
                        created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    document_version_id,
                    change.get('provision_id'),
                    change['change_type'],
                    change.get('old_content'),
                    change.get('new_content'),
                    change['change_summary'],
                    json.dumps(change.get('metadata', {})),
                    effective_date,
                    created_by
                ))

            self.conn.commit()
```

### Enhancement 4: Change Query Methods
```python
def get_version_changes(self, document_identifier: str, limit: int = 50) -> List[Dict]:
    """Get change history for a document"""

    with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT
                dv.version_number,
                dv.effective_date,
                pc.change_type,
                pc.change_summary,
                pc.old_content,
                pc.new_content,
                pc.created_at
            FROM versions.provision_changes pc
            JOIN versions.document_versions dv ON pc.document_version_id = dv.id
            WHERE dv.document_identifier = %s
            ORDER BY dv.effective_date DESC, pc.created_at DESC
            LIMIT %s
        """, (document_identifier, limit))

        return [dict(row) for row in cursor.fetchall()]

def get_provision_change_summary(self, document_identifier: str, from_version: str, to_version: str) -> Dict:
    """Get summary of changes between two versions"""

    with self.conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                pc.change_type,
                COUNT(*) as change_count,
                array_agg(pc.change_summary) as summaries
            FROM versions.provision_changes pc
            JOIN versions.document_versions dv ON pc.document_version_id = dv.id
            WHERE dv.document_identifier = %s
              AND dv.version_number BETWEEN %s AND %s
            GROUP BY pc.change_type
        """, (document_identifier, from_version, to_version))

        changes = {}
        for row in cursor.fetchall():
            changes[row[0]] = {
                'count': row[1],
                'summaries': row[2]
            }

        return changes
```

## Implementation Steps

### Step 1: Enhance Change Detection (45 minutes)
1. **Add change detection functions** to VersionManager
2. **Implement change summary generation**
3. **Add provision comparison logic**
4. **Test change detection accuracy**

### Step 2: Update VersionManager Service (30 minutes)
1. **Add change tracking methods**
2. **Enhance version creation workflow**
3. **Add change query methods**
4. **Update service documentation**

### Step 3: Create Change Analysis Tools (30 minutes)
1. **Add change statistics methods**
2. **Create change reporting functions**
3. **Add version comparison utilities**
4. **Implement change visualization data**

### Step 4: Performance Optimization (15 minutes)
1. **Add change tracking indexes**
2. **Optimize change queries**
3. **Test bulk change operations**
4. **Validate performance benchmarks**

## Granular Verification Requirements

### Database Modifications Verification
- [ ] **provision_changes table** - exists with all required columns
- [ ] **change_type constraint** - enforces valid values
- [ ] **foreign key constraints** - properly reference parent tables
- [ ] **indexes** - created for performance
- [ ] **triggers** - none required for this PRP

### Service Layer Verification
- [ ] **detect_provision_changes function** - correctly identifies all change types
- [ ] **generate_change_summary function** - produces readable summaries
- [ ] **create_new_version_with_change_tracking** - integrates change detection
- [ ] **record_provision_changes** - properly stores change records
- [ ] **get_version_changes** - retrieves change history correctly
- [ ] **get_provision_change_summary** - aggregates changes properly

### Data Integrity Verification
- [ ] **Change records created** - for every version creation
- [ ] **Change types accurate** - NEW/MODIFIED/DELETED correctly identified
- [ ] **Content preservation** - old/new content stored correctly
- [ ] **Metadata consistency** - change summaries match actual changes
- [ ] **Performance benchmarks** - change queries <1s response time

### Integration Verification
- [ ] **VersionManager enhanced** - new methods work with existing code
- [ ] **Backward compatibility** - existing functionality unchanged
- [ ] **Error handling** - graceful failure for invalid inputs
- [ ] **Transaction integrity** - changes recorded atomically
- [ ] **Audit trail** - complete tracking of who changed what when

## Deliverables

1. **Enhanced VersionManager service** - with change tracking capabilities
2. **Change detection algorithms** - for automatic change identification
3. **Change analysis tools** - for planner workflows
4. **Performance optimizations** - for production use
5. **Comprehensive verification** - proof of functionality

## Success Criteria
✅ Change detection identifies 95%+ of provision modifications
✅ Change summaries provide meaningful descriptions
✅ Version creation includes automatic change tracking
✅ Change queries respond in <1 second
✅ Integration maintains backward compatibility
✅ All verification checks pass

## Estimated Time
**2.5 hours total**
- Enhancement: 45 minutes
- Service updates: 30 minutes
- Analysis tools: 30 minutes
- Optimization: 15 minutes
- Verification: 20 minutes