#!/usr/bin/env node
/**
 * Build Unified Cache - Optimizes unified extraction for fast API responses
 * Converts the complete semantic extraction into indexed, queryable format
 */

const fs = require('fs');
const path = require('path');

class UnifiedCacheBuilder {
  constructor() {
    this.inputPath = path.join(process.cwd(), 'public', 'regulatory-data', 'unified');
    this.outputPath = path.join(process.cwd(), 'public', 'regulatory-data', 'cache');
    
    // Ensure output directory exists
    if (!fs.existsSync(this.outputPath)) {
      fs.mkdirSync(this.outputPath, { recursive: true });
    }
  }
  
  buildCache() {
    console.log('Building unified cache for fast API responses...');
    
    // Load unified extraction
    const unifiedPath = path.join(this.inputPath, 'unified_extraction.json');
    if (!fs.existsSync(unifiedPath)) {
      console.error('Unified extraction not found. Run npm run process-unified first.');
      process.exit(1);
    }
    
    const unifiedData = JSON.parse(fs.readFileSync(unifiedPath, 'utf8'));
    
    // Build indexed caches
    const caches = {
      // 1. Rule Index - Fast rule lookup by ID
      ruleIndex: this.buildRuleIndex(unifiedData),
      
      // 2. Area Index - Fast lookup by council area
      areaIndex: this.buildAreaIndex(unifiedData),
      
      // 3. Query Index - Pre-computed answers for common queries
      queryIndex: this.buildQueryIndex(unifiedData),
      
      // 4. Visual Index - Fast access to diagrams/tables
      visualIndex: this.buildVisualIndex(unifiedData),
      
      // 5. Triple Index - Knowledge graph relationships
      tripleIndex: this.buildTripleIndex(unifiedData),
      
      // 6. Compliance Index - Pre-computed compliance rules
      complianceIndex: this.buildComplianceIndex(unifiedData)
    };
    
    // Save each cache
    for (const [name, cache] of Object.entries(caches)) {
      const cachePath = path.join(this.outputPath, `${name}.json`);
      fs.writeFileSync(cachePath, JSON.stringify(cache, null, 2));
      console.log(`  ✓ Built ${name} with ${Object.keys(cache).length} entries`);
    }
    
    // Build master index
    const masterIndex = this.buildMasterIndex(caches);
    fs.writeFileSync(
      path.join(this.outputPath, 'master_index.json'),
      JSON.stringify(masterIndex, null, 2)
    );
    
    console.log('✓ Cache building complete!');
    console.log(`  Output: ${this.outputPath}`);
  }
  
  buildRuleIndex(data) {
    const index = {};
    
    // Index all enhanced rules by ID
    for (const [area, areaData] of Object.entries(data)) {
      if (areaData && areaData.enhanced_rules) {
        for (const rule of areaData.enhanced_rules) {
          index[rule.rule_id] = {
            ...rule,
            area: area,
            quick_access: {
              text: rule.rule_text,
              type: rule.rule_type,
              tier: rule.rule_classification?.tier || 3,
              measurements: rule.measurements
            }
          };
        }
      }
    }
    
    return index;
  }
  
  buildAreaIndex(data) {
    const index = {};
    
    // Group all data by council area
    for (const [area, areaData] of Object.entries(data)) {
      if (area === 'LEP' || area === 'SEPPs') continue;
      
      index[area] = {
        rules: areaData?.enhanced_rules || [],
        documents: areaData?.document_path || '',
        setbacks: this.extractSetbackSummary(areaData),
        statistics: {
          total_rules: areaData?.enhanced_rules?.length || 0,
          mandatory_rules: areaData?.enhanced_rules?.filter(r => r.rule_classification?.tier === 1).length || 0,
          source_groundings: areaData?.source_groundings?.length || 0,
          knowledge_triples: areaData?.knowledge_triples?.length || 0
        }
      };
    }
    
    return index;
  }
  
  buildQueryIndex(data) {
    const index = {};
    
    // Pre-compute common queries
    const commonQueries = [
      {
        query: "can_build_duplex",
        question: "Can I build a duplex on this property?",
        extractor: (data) => this.extractDuplexRequirements(data)
      },
      {
        query: "minimum_setbacks",
        question: "What are the minimum setback requirements?",
        extractor: (data) => this.extractMinimumSetbacks(data)
      },
      {
        query: "height_restrictions",
        question: "What are the height restrictions?",
        extractor: (data) => this.extractHeightRestrictions(data)
      },
      {
        query: "heritage_requirements",
        question: "What are the heritage requirements?",
        extractor: (data) => this.extractHeritageRequirements(data)
      }
    ];
    
    for (const {query, question, extractor} of commonQueries) {
      index[query] = {
        question,
        answers: {}
      };
      
      for (const [area, areaData] of Object.entries(data)) {
        if (areaData && areaData.enhanced_rules) {
          index[query].answers[area] = extractor(areaData);
        }
      }
    }
    
    return index;
  }
  
  buildVisualIndex(data) {
    const index = {};
    
    // Index all visual elements for quick access
    for (const [area, areaData] of Object.entries(data)) {
      if (areaData && areaData.multimodal_context) {
        const visuals = areaData.multimodal_context;
        
        if (visuals.tables || visuals.visual_elements || visuals.zoning_maps) {
          index[area] = {
            tables: visuals.tables || [],
            diagrams: visuals.visual_elements || {},
            maps: visuals.zoning_maps || {},
            setback_visuals: visuals.setback_visuals || ''
          };
        }
      }
    }
    
    return index;
  }
  
  buildTripleIndex(data) {
    const index = {
      subjects: {},
      predicates: {},
      objects: {},
      full_triples: []
    };
    
    // Index knowledge triples for graph queries
    for (const [area, areaData] of Object.entries(data)) {
      if (areaData && areaData.knowledge_triples) {
        for (const triple of areaData.knowledge_triples) {
          const [subject, predicate, object] = triple;
          
          // Index by subject
          if (!index.subjects[subject]) index.subjects[subject] = [];
          index.subjects[subject].push({predicate, object, area});
          
          // Index by predicate
          if (!index.predicates[predicate]) index.predicates[predicate] = [];
          index.predicates[predicate].push({subject, object, area});
          
          // Index by object
          if (!index.objects[object]) index.objects[object] = [];
          index.objects[object].push({subject, predicate, area});
          
          // Store full triple
          index.full_triples.push({subject, predicate, object, area});
        }
      }
    }
    
    return index;
  }
  
  buildComplianceIndex(data) {
    const index = {};
    
    // Build compliance rules by type and area
    const ruleTypes = ['front_setback', 'side_setback', 'rear_setback', 'height', 'fsr'];
    
    for (const type of ruleTypes) {
      index[type] = {};
      
      for (const [area, areaData] of Object.entries(data)) {
        if (areaData && areaData.enhanced_rules) {
          const relevantRules = areaData.enhanced_rules.filter(r => 
            r.rule_type === type || r.rule_text?.toLowerCase().includes(type.replace('_', ' '))
          );
          
          if (relevantRules.length > 0) {
            index[type][area] = relevantRules.map(rule => ({
              id: rule.rule_id,
              text: rule.rule_text,
              measurements: rule.measurements,
              tier: rule.rule_classification?.tier,
              source: rule.source_grounding?.source_location
            }));
          }
        }
      }
    }
    
    return index;
  }
  
  buildMasterIndex(caches) {
    return {
      created_at: new Date().toISOString(),
      version: '1.0.0',
      indices: Object.keys(caches),
      statistics: {
        total_rules: Object.keys(caches.ruleIndex).length,
        total_areas: Object.keys(caches.areaIndex).length,
        total_queries: Object.keys(caches.queryIndex).length,
        total_triples: caches.tripleIndex.full_triples.length,
        total_visual_areas: Object.keys(caches.visualIndex).length
      },
      quick_access: {
        areas: Object.keys(caches.areaIndex),
        rule_types: Object.keys(caches.complianceIndex),
        query_types: Object.keys(caches.queryIndex)
      }
    };
  }
  
  // Helper methods for extraction
  extractSetbackSummary(areaData) {
    if (!areaData || !areaData.enhanced_rules) return {};
    
    const summary = {
      front: null,
      side: null,
      rear: null
    };
    
    for (const rule of areaData.enhanced_rules) {
      if (rule.rule_type === 'front_setback' && rule.measurements?.[0]) {
        summary.front = rule.measurements[0].value;
      } else if (rule.rule_type === 'side_setback' && rule.measurements?.[0]) {
        summary.side = rule.measurements[0].value;
      } else if (rule.rule_type === 'rear_setback' && rule.measurements?.[0]) {
        summary.rear = rule.measurements[0].value;
      }
    }
    
    return summary;
  }
  
  extractDuplexRequirements(areaData) {
    const requirements = [];
    
    if (areaData.enhanced_rules) {
      for (const rule of areaData.enhanced_rules) {
        if (rule.rule_text?.toLowerCase().includes('duplex') ||
            rule.rule_text?.toLowerCase().includes('dual occupancy') ||
            rule.rule_text?.toLowerCase().includes('semi-detached')) {
          requirements.push({
            rule: rule.rule_text,
            source: rule.source_grounding?.source_location,
            tier: rule.rule_classification?.tier
          });
        }
      }
    }
    
    return requirements;
  }
  
  extractMinimumSetbacks(areaData) {
    const setbacks = {};
    
    if (areaData.enhanced_rules) {
      for (const rule of areaData.enhanced_rules) {
        if (rule.rule_type?.includes('setback') && rule.measurements?.[0]) {
          const type = rule.rule_type.replace('_setback', '');
          if (!setbacks[type] || rule.measurements[0].value < setbacks[type].value) {
            setbacks[type] = {
              value: rule.measurements[0].value,
              unit: rule.measurements[0].unit || 'metres',
              source: rule.source_grounding?.source_location
            };
          }
        }
      }
    }
    
    return setbacks;
  }
  
  extractHeightRestrictions(areaData) {
    const restrictions = [];
    
    if (areaData.enhanced_rules) {
      for (const rule of areaData.enhanced_rules) {
        if (rule.rule_text?.toLowerCase().includes('height') ||
            rule.rule_type === 'height') {
          restrictions.push({
            rule: rule.rule_text,
            measurements: rule.measurements,
            source: rule.source_grounding?.source_location
          });
        }
      }
    }
    
    return restrictions;
  }
  
  extractHeritageRequirements(areaData) {
    const requirements = [];
    
    if (areaData.enhanced_rules) {
      for (const rule of areaData.enhanced_rules) {
        if (rule.rule_text?.toLowerCase().includes('heritage')) {
          requirements.push({
            rule: rule.rule_text,
            tier: rule.rule_classification?.tier,
            source: rule.source_grounding?.source_location
          });
        }
      }
    }
    
    return requirements;
  }
}

// Run the cache builder
const builder = new UnifiedCacheBuilder();
builder.buildCache();