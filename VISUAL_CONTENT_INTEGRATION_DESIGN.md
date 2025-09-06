# VISUAL CONTENT INTEGRATION DESIGN - IMAGE DISPLAY SYSTEM

## **DISCOVERY SUMMARY**

### **Available Visual Content in Database:**
- **2,525 visual content references** in regulatory_refs table
- **Image files**: 1,658 entries with actual file paths (`images/hash.jpg`)
- **Figures**: 333 entries (Figure 9.11, Figure 26.1, etc.)
- **Diagrams**: 203 entries (Shadow diagrams, building diagrams)
- **AutoSchemaKG traces**: 1,338 processed visual elements
- **Page-linked visuals**: Visual content with specific page numbers

### **Key Insight:**
Visual content exists as **file paths in regulatory_refs** with pattern:
```
Image: images/[hash].jpg | Page: [number] | Context: [description]
```

---

## **VISUAL CONTENT INTEGRATION STRATEGY**

### **Where Images Are Most Helpful:**

1. **Setback Illustrations**: Diagrams showing front/side/rear setback measurements
2. **Zoning Maps**: Visual context for property location and zoning boundaries  
3. **Heritage Examples**: Photos showing compliant/non-compliant development
4. **Building Envelopes**: 3D diagrams showing maximum building form
5. **Shadow Diagrams**: Visual impact analysis for neighboring properties
6. **Precinct Character**: Photos showing desired neighborhood character
7. **Technical Details**: Construction drawings and specification diagrams

### **Image Display Hierarchy:**
```
Priority 1 (Always Show): Setback diagrams, building envelope illustrations
Priority 2 (Context-Dependent): Zoning maps, heritage examples  
Priority 3 (Enhancement): Character photos, technical drawings
```

---

## **TECHNICAL IMPLEMENTATION**

### **1. Visual Content API Enhancement**

#### **Enhanced Assessment Endpoint Extension:**
```python
@app.post("/enhanced-complete-assessment")
async def enhanced_complete_assessment(request: QueryRequest) -> EnhancedAssessmentResponse:
    # ... existing implementation ...
    
    # Phase 4: Visual Content Discovery
    visual_content = await discover_relevant_visual_content(property_data, setback_result, connected)
    
    return EnhancedAssessmentResponse(
        # ... existing fields ...
        visual_content=visual_content,
        visual_metadata=VisualMetadata(
            total_images_available=len(visual_content),
            images_displayed=len([v for v in visual_content if v.priority <= 2]),
            autoschema_processed=len([v for v in visual_content if v.source == "AutoSchemaKG"])
        )
    )

async def discover_relevant_visual_content(property_data, setback_result, connected):
    """Discover and prioritize relevant visual content"""
    
    conn = sqlite3.connect('nsw_planning.db')
    cur = conn.cursor()
    
    visual_content = []
    
    # Priority 1: Setback-related visuals
    setback_visuals = cur.execute("""
        SELECT ref_context, page_number, document_id, ref_type
        FROM regulatory_refs 
        WHERE (ref_context LIKE '%setback%' OR ref_context LIKE '%building envelope%')
          AND (ref_context LIKE '%.jpg%' OR ref_context LIKE '%Figure%' OR ref_context LIKE '%diagram%')
          AND document_id LIKE ? 
        ORDER BY page_number
    """, (f'%{property_data.former_council_area}%',)).fetchall()
    
    for context, page, doc, ref_type in setback_visuals:
        visual_content.append(VisualElement(
            visual_type="setback_diagram",
            file_path=extract_image_path(context),
            description=extract_description(context),
            page_number=page,
            document_name=doc,
            priority=1,
            relevance_score=0.95,
            source="AutoSchemaKG",
            related_requirement="setbacks"
        ))
    
    # Priority 2: Zone and context visuals
    zone_visuals = cur.execute("""
        SELECT ref_context, page_number, document_id  
        FROM regulatory_refs
        WHERE (ref_context LIKE ? OR ref_context LIKE '%zoning%' OR ref_context LIKE '%precinct%')
          AND (ref_context LIKE '%.jpg%' OR ref_context LIKE '%Figure%')
        ORDER BY page_number
        LIMIT 5
    """, (f'%{property_data.zone}%',)).fetchall()
    
    for context, page, doc in zone_visuals:
        visual_content.append(VisualElement(
            visual_type="zoning_context", 
            file_path=extract_image_path(context),
            description=extract_description(context),
            page_number=page,
            document_name=doc,
            priority=2,
            relevance_score=0.8,
            source="LangExtract",
            related_requirement="zoning"
        ))
    
    # Priority 3: Connected requirement visuals
    for requirement in connected.get("immediate_actions", []):
        req_visuals = cur.execute("""
            SELECT ref_context, page_number, document_id
            FROM regulatory_refs 
            WHERE ref_context LIKE ?
              AND (ref_context LIKE '%.jpg%' OR ref_context LIKE '%Figure%')
            LIMIT 2
        """, (f'%{requirement.get("type", "")}%',)).fetchall()
        
        for context, page, doc in req_visuals:
            visual_content.append(VisualElement(
                visual_type="requirement_illustration",
                file_path=extract_image_path(context),
                description=extract_description(context), 
                page_number=page,
                document_name=doc,
                priority=3,
                relevance_score=0.7,
                source="Connected Requirements",
                related_requirement=requirement.get("type", "general")
            ))
    
    conn.close()
    
    # Sort by priority and relevance
    visual_content.sort(key=lambda x: (x.priority, -x.relevance_score))
    
    return visual_content

def extract_image_path(context_text):
    """Extract image file path from regulatory_refs context"""
    import re
    
    # Pattern: "Image: images/hash.jpg" or "images/hash.jpg"
    image_match = re.search(r'images/[a-f0-9]+\.jpg', context_text)
    if image_match:
        return image_match.group(0)
    
    # Pattern: "Figure X.X" - would need mapping to actual files
    figure_match = re.search(r'Figure\s+[\d\.]+', context_text)  
    if figure_match:
        return f"figures/{figure_match.group(0).replace(' ', '_').lower()}.png"
    
    return None

def extract_description(context_text):
    """Extract meaningful description from context"""
    # Remove file path and extract description
    clean_text = re.sub(r'Image:\s*images/[a-f0-9]+\.jpg\s*\|\s*Page:\s*\d+\s*\|\s*', '', context_text)
    return clean_text[:200] + "..." if len(clean_text) > 200 else clean_text
```

#### **Visual Element Data Model:**
```python
class VisualElement(BaseModel):
    visual_type: str                    # "setback_diagram", "zoning_context", "heritage_example"
    file_path: str                      # "images/hash.jpg" or "figures/figure_9_11.png"
    description: str                    # Human-readable description
    page_number: Optional[int]          # Page in source document
    document_name: str                  # Source document
    priority: int                       # 1=Critical, 2=Important, 3=Helpful
    relevance_score: float              # 0.0-1.0 relevance to current query
    source: str                         # "AutoSchemaKG", "LangExtract", "Connected Requirements"
    related_requirement: str            # "setbacks", "heritage", "zoning", etc.
    width: Optional[int] = None         # Image dimensions if available
    height: Optional[int] = None
    
class VisualMetadata(BaseModel):
    total_images_available: int
    images_displayed: int
    autoschema_processed: int
    processing_time_ms: int
    cache_hit_rate: float
```

### **2. Image Serving Infrastructure**

#### **Static File Serving Setup:**
```python
# Add to FastAPI app
from fastapi.staticfiles import StaticFiles

# Mount static files directory for images
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/figures", StaticFiles(directory="figures"), name="figures") 
app.mount("/diagrams", StaticFiles(directory="diagrams"), name="diagrams")

# Image proxy endpoint for security and caching
@app.get("/visual-content/{image_path:path}")
async def serve_visual_content(image_path: str):
    """Secure image serving with access control and caching"""
    
    # Validate image path
    if not is_valid_image_path(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Check if image exists in database
    conn = sqlite3.connect('nsw_planning.db')
    cur = conn.cursor()
    
    image_exists = cur.execute("""
        SELECT 1 FROM regulatory_refs 
        WHERE ref_context LIKE ?
    """, (f'%{image_path}%',)).fetchone()
    
    conn.close()
    
    if not image_exists:
        raise HTTPException(status_code=404, detail="Image not authorized")
    
    # Serve image with proper headers
    full_path = Path("images") / image_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(
        full_path,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
            "X-Content-Source": "AutoSchemaKG"
        }
    )

def is_valid_image_path(path: str) -> bool:
    """Validate image path for security"""
    # Only allow specific patterns
    return bool(re.match(r'^[a-f0-9]+\.(jpg|png|gif)$', path)) and len(path) < 100
```

### **3. Frontend Image Display Components**

#### **Enhanced Display Function with Images:**
```javascript
function displayEnhancedCompleteAssessment(data) {
    const resultsDiv = document.getElementById('results');
    
    let html = `
        <!-- Existing enhanced assessment content -->
        ${renderEnhancedHeader(data)}
        ${renderSetbacksWithVisuals(data)}
        ${renderConnectedRequirementsWithVisuals(data)}
        ${renderPageCitationsWithVisuals(data)}
        
        <!-- Visual Content Gallery -->
        ${data.visual_content.length > 0 ? renderVisualContentGallery(data.visual_content) : ''}
    `;
    
    resultsDiv.innerHTML = html;
    
    // Initialize image interactions
    initializeImageGallery();
    initializeImageLazyLoading();
}

function renderSetbacksWithVisuals(data) {
    const setbacks = data.setback_calculations;
    const visuals = data.visual_content.filter(v => v.related_requirement === 'setbacks');
    
    return `
        <div class="enhanced-setbacks-section">
            <div class="section-header">
                <h3>📐 Database-Driven Setbacks</h3>
                ${visuals.length > 0 ? `<div class="visual-indicator">${visuals.length} diagrams available</div>` : ''}
            </div>
            
            <!-- Setback Cards with Inline Images -->
            <div class="setbacks-grid">
                ${formatSetbackCard('Front', setbacks.front_setback, visuals.find(v => v.visual_type.includes('front')))}
                ${formatSetbackCard('Side', setbacks.side_setback, visuals.find(v => v.visual_type.includes('side')))}
                ${formatSetbackCard('Rear', setbacks.rear_setback, visuals.find(v => v.visual_type.includes('rear')))}
            </div>
            
            <!-- Setback Diagrams Section -->
            ${visuals.filter(v => v.priority === 1).length > 0 ? `
                <div class="setback-diagrams">
                    <h4>📋 Regulatory Diagrams</h4>
                    <div class="diagram-grid">
                        ${visuals.filter(v => v.priority === 1).map(visual => 
                            renderInlineImage(visual, 'setback-diagram')
                        ).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

function formatSetbackCard(type, setback, visual) {
    return `
        <div class="setback-card ${type.toLowerCase()} ${visual ? 'has-visual' : ''}">
            <div class="setback-header">
                <h4>${type} Setback</h4>
                <div class="confidence-indicator confidence-${setback.confidence_score >= 0.9 ? 'high' : 'medium'}">
                    ${Math.round(setback.confidence_score * 100)}%
                </div>
            </div>
            
            <div class="setback-content">
                <div class="setback-value">${setback.distance}</div>
                <div class="setback-source">
                    📋 ${setback.source_document}
                    ${setback.page_number ? ` • Page ${setback.page_number}` : ''}
                </div>
                
                <!-- Inline Visual Preview -->
                ${visual ? `
                    <div class="inline-visual-preview">
                        <img src="/visual-content/${visual.file_path}" 
                             alt="${visual.description}"
                             class="setback-diagram-thumbnail"
                             onclick="openImageModal('${visual.file_path}', '${visual.description}', '${visual.document_name}', ${visual.page_number})"
                             loading="lazy" />
                        <div class="visual-caption">
                            <small>📊 ${visual.description.substring(0, 50)}...</small>
                        </div>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

function renderVisualContentGallery(visuals) {
    return `
        <div class="visual-content-section">
            <div class="section-header">
                <h3>🖼️ Regulatory Visual Content</h3>
                <div class="visual-count">${visuals.length} images • ${visuals.filter(v => v.priority <= 2).length} priority</div>
            </div>
            
            <!-- Priority Images (Always Visible) -->
            <div class="priority-visuals">
                <h4>🎯 Priority Visual Guidance</h4>
                <div class="visual-grid priority">
                    ${visuals.filter(v => v.priority === 1).map(visual => 
                        renderVisualCard(visual, 'priority')
                    ).join('')}
                </div>
            </div>
            
            <!-- Context Images (Expandable) -->
            ${visuals.filter(v => v.priority === 2).length > 0 ? `
                <div class="context-visuals">
                    <details class="visual-section-toggle">
                        <summary>📍 Additional Context Images (${visuals.filter(v => v.priority === 2).length})</summary>
                        <div class="visual-grid context">
                            ${visuals.filter(v => v.priority === 2).map(visual => 
                                renderVisualCard(visual, 'context')
                            ).join('')}
                        </div>
                    </details>
                </div>
            ` : ''}
            
            <!-- Enhancement Images (Collapsible) -->
            ${visuals.filter(v => v.priority === 3).length > 0 ? `
                <div class="enhancement-visuals">
                    <details class="visual-section-toggle">
                        <summary>✨ Additional Reference Images (${visuals.filter(v => v.priority === 3).length})</summary>
                        <div class="visual-grid enhancement">
                            ${visuals.filter(v => v.priority === 3).map(visual => 
                                renderVisualCard(visual, 'enhancement')
                            ).join('')}
                        </div>
                    </details>
                </div>
            ` : ''}
        </div>
    `;
}

function renderVisualCard(visual, category) {
    return `
        <div class="visual-card ${category}" data-visual-type="${visual.visual_type}">
            <div class="visual-image-container">
                <img src="/visual-content/${visual.file_path}" 
                     alt="${visual.description}"
                     class="visual-image"
                     onclick="openImageModal('${visual.file_path}', '${visual.description}', '${visual.document_name}', ${visual.page_number})"
                     loading="lazy"
                     onerror="this.src='/static/placeholder-image.png'; this.onerror=null;" />
                
                <div class="visual-overlay">
                    <div class="visual-type-badge">${visual.visual_type.replace('_', ' ')}</div>
                    <div class="visual-priority priority-${visual.priority}">Priority ${visual.priority}</div>
                </div>
            </div>
            
            <div class="visual-card-content">
                <div class="visual-title">${visual.description.substring(0, 60)}...</div>
                <div class="visual-metadata">
                    <div class="visual-source">
                        📋 ${visual.document_name.split('___')[0]}
                        ${visual.page_number ? ` • Page ${visual.page_number}` : ''}
                    </div>
                    <div class="visual-relevance">
                        <span class="relevance-score">${Math.round(visual.relevance_score * 100)}% relevant</span>
                        <span class="visual-source-badge">${visual.source}</span>
                    </div>
                </div>
                
                <div class="visual-actions">
                    <button class="view-full-btn" onclick="openImageModal('${visual.file_path}', '${visual.description}', '${visual.document_name}', ${visual.page_number})">
                        🔍 View Full Size
                    </button>
                    <button class="cite-btn" onclick="copyImageCitation('${visual.document_name}', ${visual.page_number}, '${visual.description}')">
                        📋 Cite
                    </button>
                </div>
            </div>
        </div>
    `;
}

function renderInlineImage(visual, className) {
    return `
        <div class="inline-image ${className}">
            <img src="/visual-content/${visual.file_path}" 
                 alt="${visual.description}"
                 onclick="openImageModal('${visual.file_path}', '${visual.description}', '${visual.document_name}', ${visual.page_number})"
                 loading="lazy" />
            <div class="inline-caption">
                <strong>${visual.visual_type.replace('_', ' ')}</strong>
                <br>
                <small>${visual.description}</small>
            </div>
        </div>
    `;
}

// Image Modal and Interaction Functions
function openImageModal(imagePath, description, documentName, pageNumber) {
    const modal = document.createElement('div');
    modal.className = 'image-modal';
    modal.innerHTML = `
        <div class="image-modal-content">
            <div class="image-modal-header">
                <h3>${description}</h3>
                <button class="close-modal" onclick="closeImageModal()">&times;</button>
            </div>
            
            <div class="image-modal-body">
                <img src="/visual-content/${imagePath}" alt="${description}" class="modal-image" />
            </div>
            
            <div class="image-modal-footer">
                <div class="image-citation">
                    <strong>Source:</strong> ${documentName}${pageNumber ? `, Page ${pageNumber}` : ''}
                </div>
                <div class="image-actions">
                    <button onclick="downloadImage('${imagePath}', '${description}')">💾 Download</button>
                    <button onclick="copyImageCitation('${documentName}', ${pageNumber}, '${description}')">📋 Copy Citation</button>
                </div>
            </div>
        </div>
        <div class="image-modal-backdrop" onclick="closeImageModal()"></div>
    `;
    
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
}

function closeImageModal() {
    const modal = document.querySelector('.image-modal');
    if (modal) {
        document.body.removeChild(modal);
        document.body.style.overflow = '';
    }
}

function copyImageCitation(documentName, pageNumber, description) {
    const citation = `${description} (${documentName}${pageNumber ? `, Page ${pageNumber}` : ''})`;
    navigator.clipboard.writeText(citation);
    
    // Show toast notification
    showToast(`Citation copied: ${citation.substring(0, 50)}...`);
}

function downloadImage(imagePath, description) {
    const link = document.createElement('a');
    link.href = `/visual-content/${imagePath}`;
    link.download = `${description.replace(/[^a-zA-Z0-9]/g, '_')}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function initializeImageLazyLoading() {
    // Implement intersection observer for lazy loading
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });
    
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}
```

### **4. Enhanced CSS for Visual Content**

```css
/* Visual Content Sections */
.visual-content-section {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
}

.visual-count {
    background: #f3e8ff;
    color: #7c3aed;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
}

/* Visual Grid Layouts */
.visual-grid {
    display: grid;
    gap: 16px;
    margin-top: 16px;
}

.visual-grid.priority {
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}

.visual-grid.context {
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
}

.visual-grid.enhancement {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

/* Visual Cards */
.visual-card {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
    background: white;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.visual-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.visual-card.priority { border-left: 4px solid #dc2626; }
.visual-card.context { border-left: 4px solid #f59e0b; }
.visual-card.enhancement { border-left: 4px solid #10b981; }

.visual-image-container {
    position: relative;
    width: 100%;
    height: 200px;
    overflow: hidden;
}

.visual-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    cursor: pointer;
    transition: transform 0.3s ease;
}

.visual-image:hover {
    transform: scale(1.05);
}

.visual-overlay {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    gap: 4px;
    flex-direction: column;
    align-items: flex-end;
}

.visual-type-badge {
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 10px;
    text-transform: capitalize;
}

.visual-priority {
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 9px;
    font-weight: bold;
}

.priority-1 { background: #fee2e2; color: #dc2626; }
.priority-2 { background: #fef3c7; color: #f59e0b; }
.priority-3 { background: #dcfce7; color: #16a34a; }

.visual-card-content {
    padding: 12px;
}

.visual-title {
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 8px;
    font-size: 14px;
    line-height: 1.3;
}

.visual-metadata {
    margin-bottom: 12px;
}

.visual-source {
    font-size: 11px;
    color: #6b7280;
    margin-bottom: 4px;
}

.visual-relevance {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.relevance-score {
    font-size: 10px;
    color: #10b981;
    font-weight: 600;
}

.visual-source-badge {
    background: #f3f4f6;
    color: #374151;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 9px;
}

.visual-actions {
    display: flex;
    gap: 8px;
}

.view-full-btn, .cite-btn {
    flex: 1;
    padding: 6px 12px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    background: white;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.2s;
}

.view-full-btn:hover {
    background: #3b82f6;
    color: white;
    border-color: #3b82f6;
}

.cite-btn:hover {
    background: #10b981;
    color: white;
    border-color: #10b981;
}

/* Inline Visual Previews in Setback Cards */
.setback-card.has-visual {
    border-left-width: 6px;
}

.inline-visual-preview {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #f0f0f0;
}

.setback-diagram-thumbnail {
    width: 100%;
    max-height: 120px;
    object-fit: cover;
    border-radius: 4px;
    cursor: pointer;
    transition: opacity 0.2s;
}

.setback-diagram-thumbnail:hover {
    opacity: 0.8;
}

.visual-caption {
    margin-top: 4px;
    text-align: center;
}

/* Inline Images */
.inline-image {
    margin: 12px 0;
    text-align: center;
}

.inline-image img {
    max-width: 100%;
    max-height: 200px;
    border-radius: 4px;
    cursor: pointer;
    border: 1px solid #e5e7eb;
}

.inline-caption {
    margin-top: 8px;
    font-size: 12px;
    color: #6b7280;
}

/* Section Toggles */
.visual-section-toggle summary {
    cursor: pointer;
    padding: 8px 0;
    font-weight: 500;
    color: #374151;
    user-select: none;
}

.visual-section-toggle summary:hover {
    color: #1f2937;
}

/* Image Modal */
.image-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
}

.image-modal-backdrop {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
}

.image-modal-content {
    position: relative;
    background: white;
    border-radius: 8px;
    max-width: 90vw;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
}

.image-modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;
}

.image-modal-header h3 {
    margin: 0;
    font-size: 16px;
    color: #1f2937;
}

.close-modal {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    padding: 0;
    color: #6b7280;
}

.close-modal:hover {
    color: #374151;
}

.image-modal-body {
    flex: 1;
    padding: 16px;
    text-align: center;
    overflow: auto;
}

.modal-image {
    max-width: 100%;
    max-height: calc(90vh - 200px);
    border-radius: 4px;
}

.image-modal-footer {
    padding: 16px;
    border-top: 1px solid #e5e7eb;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.image-citation {
    font-size: 12px;
    color: #6b7280;
}

.image-actions {
    display: flex;
    gap: 8px;
}

.image-actions button {
    padding: 8px 16px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    background: white;
    cursor: pointer;
    font-size: 12px;
}

.image-actions button:hover {
    background: #f9fafb;
}

/* Toast Notifications */
.toast {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #1f2937;
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    z-index: 10001;
    transform: translateY(100px);
    opacity: 0;
    transition: all 0.3s ease;
    max-width: 300px;
    font-size: 12px;
}

.toast.show {
    transform: translateY(0);
    opacity: 1;
}

/* Responsive Design */
@media (max-width: 768px) {
    .visual-grid {
        grid-template-columns: 1fr;
    }
    
    .visual-image-container {
        height: 150px;
    }
    
    .image-modal-content {
        margin: 20px;
        max-width: calc(100vw - 40px);
        max-height: calc(100vh - 40px);
    }
    
    .modal-image {
        max-height: calc(100vh - 160px);
    }
}

/* Loading States */
.visual-image[loading="lazy"] {
    background: #f3f4f6;
    min-height: 100px;
}

.visual-image.error {
    background: #fef2f2;
    color: #dc2626;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
}

/* Visual Indicators */
.visual-indicator {
    background: #ecfdf5;
    color: #059669;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
}
```

---

## **INTEGRATION WITH ENHANCED ASSESSMENT**

### **Updated PRP Integration:**
The visual content system integrates seamlessly with the existing PRP-FRONTEND_UNIFIED_ENHANCEMENT.md:

1. **API Enhancement**: Extends `/enhanced-complete-assessment` endpoint
2. **Frontend Display**: Adds visual content to `displayEnhancedCompleteAssessment()`
3. **User Experience**: Progressive disclosure (Priority 1 → 2 → 3 images)
4. **Performance**: Lazy loading, caching, and optimized serving
5. **Professional**: Citations, downloads, and council-ready references

### **Implementation Priority:**
- **Phase 1**: Priority 1 images (setback diagrams) - immediately helpful
- **Phase 2**: Priority 2 images (context visuals) - valuable enhancement  
- **Phase 3**: Priority 3 images (reference content) - comprehensive coverage

This system transforms the assessment from text-only to a rich, visual regulatory guidance experience while maintaining professional compliance standards!