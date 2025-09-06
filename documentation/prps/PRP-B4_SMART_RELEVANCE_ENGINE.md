# PRP-B4: Smart Relevance Engine

## Status: PENDING  
**Created:** 2025-08-30  
**Previous:** PRP-B3 Rule-to-Action Transformer  
**Next:** PRP-B5 Development Application Assistant

## Objective
Implement intelligent relevance scoring and filtering to ensure users see the most important provisions for their specific property and development intent, not just the first 15 results found.

## Problem Statement
Current system returns first 15 provisions found, regardless of relevance:
- ❌ Height query returns "Signs and Advertising" provisions (irrelevant)
- ❌ R2 residential query returns "Industrial Development" rules (wrong zone)
- ✅ Height query returns "Building Height", "Setbacks", "Solar Access" (highly relevant)

## Solution: Smart Relevance Engine

### Phase 1: Multi-Dimensional Relevance Scoring
**File:** `services/relevance_engine.py`
```python
class RelevanceEngine:
    def __init__(self):
        self.scoring_weights = {
            "query_match": 0.30,      # How well provision matches query intent
            "property_match": 0.25,   # How relevant to property characteristics  
            "zone_match": 0.20,       # Zone-specific relevance
            "development_match": 0.15, # Development type relevance
            "practical_impact": 0.10   # Real-world impact on user
        }
    
    def score_provisions(self, provisions: List[PlanningRule], 
                        property_data: PropertyIntelligence,
                        query_context: QueryContext) -> List[ScoredProvision]:
        """Score provisions across multiple relevance dimensions"""
        
        scored_provisions = []
        
        for provision in provisions:
            scores = {
                "query_match": self._score_query_match(provision, query_context),
                "property_match": self._score_property_match(provision, property_data),
                "zone_match": self._score_zone_match(provision, property_data.zone),
                "development_match": self._score_development_match(provision, query_context.development_intent),
                "practical_impact": self._score_practical_impact(provision, property_data)
            }
            
            # Calculate weighted total score
            total_score = sum(
                scores[dimension] * self.scoring_weights[dimension] 
                for dimension in scores
            )
            
            scored_provisions.append(ScoredProvision(
                provision=provision,
                total_score=total_score,
                dimension_scores=scores,
                relevance_explanation=self._explain_relevance(provision, scores, property_data)
            ))
        
        # Sort by total score, highest first
        return sorted(scored_provisions, key=lambda x: x.total_score, reverse=True)
    
    def _score_query_match(self, provision: PlanningRule, query_context: QueryContext) -> float:
        """Score how well provision matches query intent (0-1)"""
        query_type = query_context.query_type.lower()
        provision_type = provision.type.lower()
        provision_text = provision.text.lower()
        
        # Direct type matches get highest score
        if query_type == provision_type:
            return 1.0
            
        # Semantic matches for related concepts
        query_semantic_map = {
            "height": ["height_limit", "building_height", "storey", "floor"],
            "setback": ["setback", "boundary", "side_yard", "front_yard", "rear_yard"],
            "parking": ["parking", "car_space", "vehicle", "garage", "driveway"],
            "heritage": ["heritage", "conservation", "historic", "character"]
        }
        
        if query_type in query_semantic_map:
            semantic_terms = query_semantic_map[query_type]
            matches = sum(1 for term in semantic_terms if term in provision_text)
            return min(matches * 0.3, 1.0)  # Max 1.0, partial credit for matches
            
        return 0.1  # Minimum score for all provisions
    
    def _score_property_match(self, provision: PlanningRule, property_data: PropertyIntelligence) -> float:
        """Score relevance to property characteristics (0-1)"""
        score = 0.0
        
        # Zone-specific provisions get higher score
        if property_data.zone and property_data.zone.lower() in provision.text.lower():
            score += 0.4
        
        # LGA-specific provisions (already filtered but good to boost)
        if property_data.lga_name and property_data.lga_name.lower() in provision.source.lower():
            score += 0.3
            
        # Property size relevance
        if "lot size" in provision.text.lower():
            if property_data.lot_area and property_data.lot_area > 600:  # Large lot
                score += 0.2
            elif property_data.lot_area and property_data.lot_area < 300:  # Small lot
                score += 0.1
                
        # Heritage relevance
        if property_data.heritage_status and "heritage" in provision.text.lower():
            score += 0.5
            
        return min(score, 1.0)
    
    def _score_development_match(self, provision: PlanningRule, development_intent: str) -> float:
        """Score relevance to development intent (0-1)"""
        if not development_intent:
            return 0.5  # Neutral score if no intent specified
            
        intent_provision_map = {
            "single_dwelling": ["dwelling", "house", "residential", "setback", "height"],
            "extension": ["addition", "extension", "alteration", "existing", "heritage"],
            "swimming_pool": ["pool", "outdoor", "recreation", "setback", "drainage"],
            "secondary_dwelling": ["granny flat", "secondary", "ancillary", "separate"],
            "subdivision": ["subdivision", "lot", "boundary", "access", "infrastructure"]
        }
        
        if development_intent in intent_provision_map:
            relevant_terms = intent_provision_map[development_intent]
            matches = sum(1 for term in relevant_terms if term in provision.text.lower())
            return min(matches * 0.2, 1.0)
            
        return 0.3  # Default score for unknown intents
```

### Phase 2: Intelligent Filtering Pipeline
**File:** `services/smart_filter.py`
```python
class SmartFilter:
    def __init__(self, relevance_engine: RelevanceEngine):
        self.relevance_engine = relevance_engine
    
    def filter_and_rank_provisions(self, 
                                 provisions: List[PlanningRule],
                                 property_data: PropertyIntelligence,
                                 query_context: QueryContext,
                                 max_results: int = 15) -> FilteredResults:
        """Apply intelligent filtering and ranking"""
        
        # Step 1: Score all provisions
        scored_provisions = self.relevance_engine.score_provisions(
            provisions, property_data, query_context
        )
        
        # Step 2: Apply minimum relevance threshold  
        min_threshold = 0.3  # Only show provisions with decent relevance
        relevant_provisions = [p for p in scored_provisions if p.total_score >= min_threshold]
        
        # Step 3: Ensure category diversity (don't show 15 height rules)
        diverse_provisions = self._ensure_category_diversity(relevant_provisions)
        
        # Step 4: Apply result limit
        top_provisions = diverse_provisions[:max_results]
        
        # Step 5: Group by relevance tiers
        tiered_results = self._group_by_relevance_tiers(top_provisions)
        
        return FilteredResults(
            provisions=top_provisions,
            tiered_results=tiered_results,
            total_considered=len(provisions),
            total_relevant=len(relevant_provisions),
            filtering_explanation=self._generate_filtering_explanation(
                query_context, property_data, top_provisions
            )
        )
    
    def _ensure_category_diversity(self, scored_provisions: List[ScoredProvision]) -> List[ScoredProvision]:
        """Ensure diverse provision types, not all the same category"""
        diverse_results = []
        category_counts = {}
        max_per_category = 5  # Maximum provisions per type
        
        for provision in scored_provisions:
            category = provision.provision.type
            current_count = category_counts.get(category, 0)
            
            if current_count < max_per_category:
                diverse_results.append(provision)
                category_counts[category] = current_count + 1
            
            # Stop if we have enough total results
            if len(diverse_results) >= 20:  # Allow some buffer above final limit
                break
                
        return diverse_results
    
    def _group_by_relevance_tiers(self, provisions: List[ScoredProvision]) -> Dict[str, List[ScoredProvision]]:
        """Group provisions into relevance tiers for display"""
        tiers = {
            "HIGHLY_RELEVANT": [],     # Score 0.8+
            "RELEVANT": [],            # Score 0.6-0.79
            "SOMEWHAT_RELEVANT": []    # Score 0.3-0.59
        }
        
        for provision in provisions:
            if provision.total_score >= 0.8:
                tiers["HIGHLY_RELEVANT"].append(provision)
            elif provision.total_score >= 0.6:
                tiers["RELEVANT"].append(provision)
            else:
                tiers["SOMEWHAT_RELEVANT"].append(provision)
                
        return tiers
```

### Phase 3: Enhanced Query Processing
**File:** Enhanced `api_server.py` integration
```python
class QueryContext:
    def __init__(self, query_request: QueryRequest):
        self.query_type = query_request.query_type
        self.address = query_request.address
        self.context = query_request.context
        self.development_intent = self._infer_development_intent(query_request)
        self.specific_keywords = self._extract_keywords(query_request)
    
    def _infer_development_intent(self, request: QueryRequest) -> str:
        """Infer what user wants to build from query"""
        context = (request.context or "").lower()
        query_type = request.query_type.lower()
        
        intent_keywords = {
            "extension": ["extension", "addition", "extend", "add on"],
            "swimming_pool": ["pool", "spa", "swimming"],
            "secondary_dwelling": ["granny flat", "studio", "secondary"],
            "subdivision": ["subdivide", "split", "separate lot"]
        }
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in context for keyword in keywords):
                return intent
                
        return "single_dwelling"  # Default assumption

@app.post("/query-smart")
async def query_with_smart_relevance(request: QueryRequest):
    # Get base query results (without smart filtering)
    base_results = await query_planning_rules_raw(request)  # Returns all results
    
    # Get property intelligence
    property_data = await get_property_dashboard(request.address)
    
    # Create query context
    query_context = QueryContext(request)
    
    # Apply smart relevance filtering
    relevance_engine = RelevanceEngine()
    smart_filter = SmartFilter(relevance_engine)
    
    filtered_results = smart_filter.filter_and_rank_provisions(
        base_results['results'],
        property_data, 
        query_context,
        max_results=15
    )
    
    return SmartQueryResponse(
        success=True,
        filtered_results=filtered_results,
        query_context=query_context,
        property_context=property_data,
        relevance_explanation=filtered_results.filtering_explanation
    )
```

## Frontend Integration

### Relevance Indicators
```javascript
function displaySmartResults(smartResponse) {
    const container = document.getElementById('smart-results');
    
    container.innerHTML = `
        <div class="smart-results">
            <div class="results-summary">
                <h4>🎯 SMART RESULTS FOR YOUR QUERY</h4>
                <p>Showing ${smartResponse.filtered_results.provisions.length} most relevant provisions 
                   (from ${smartResponse.filtered_results.total_considered} considered)</p>
                <div class="filtering-explanation">${smartResponse.relevance_explanation}</div>
            </div>
            
            ${Object.entries(smartResponse.filtered_results.tiered_results).map(([tier, provisions]) => 
                provisions.length > 0 ? `
                    <div class="relevance-tier ${tier.toLowerCase()}">
                        <h5>${formatTierName(tier)} (${provisions.length} provisions)</h5>
                        ${provisions.map(scoredProvision => displayScoredProvision(scoredProvision)).join('')}
                    </div>
                ` : ''
            ).join('')}
        </div>
    `;
}

function displayScoredProvision(scoredProvision) {
    const provision = scoredProvision.provision;
    const score = Math.round(scoredProvision.total_score * 100);
    
    return `
        <div class="scored-provision" data-score="${score}">
            <div class="provision-header">
                <span class="provision-title">${provision.title}</span>
                <span class="relevance-score">${score}% relevant</span>
            </div>
            <div class="provision-text">${provision.text}</div>
            <div class="relevance-explanation">${scoredProvision.relevance_explanation}</div>
            <div class="provision-source">${provision.source}</div>
        </div>
    `;
}
```

## Success Criteria
1. ✅ Most relevant provisions appear first, not just first found
2. ✅ Category diversity (height + setbacks + parking, not 15 height rules)
3. ✅ Property-specific relevance (R2 provisions for R2 properties)
4. ✅ Query intent matching (height queries return height-related provisions)
5. ✅ Relevance scores and explanations for transparency

## Test Cases
**Primary Test:** Height query for R2 residential property  
- Query: "height limits"
- Expected Top Results:
  1. Building Height provisions (query match)
  2. Setback requirements (connects to height)
  3. Solar access rules (connects to height)
  4. Zone-specific R2 provisions (property match)
- NOT: Industrial development, advertising signs, child care centers

**Relevance Test:** Swimming pool query  
- Should prioritize: setbacks, drainage, utilities, access
- Should deprioritize: heritage conservation, commercial signage

## Dependencies
- Enhanced provision parsing with better type classification
- Property intelligence data from PRP-B1
- Query context analysis and development intent inference

## Implementation Timeline
**Week 1:** Multi-dimensional scoring engine
**Week 2:** Smart filtering and diversity logic
**Week 3:** Enhanced query processing integration
**Week 4:** Frontend relevance indicators and explanations

## Notes
This PRP ensures users see the RIGHT 15 provisions, not just the first 15 found - dramatically improving the value of every query response.