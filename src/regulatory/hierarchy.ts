/**
 * NSW Planning Regulatory Hierarchy
 * Authoritative mapping of planning instrument precedence and applicability
 */

export enum RegulatoryLevel {
  COMMONWEALTH = 1,    // Commonwealth legislation
  STATE_ACT = 2,       // Environmental Planning & Assessment Act
  SEPP = 3,           // State Environmental Planning Policies
  REP = 4,            // Regional Environmental Plans (legacy)
  LEP = 5,            // Local Environmental Plans
  DCP = 6,            // Development Control Plans
  POLICY = 7          // Council policies/guidelines
}

export enum DevelopmentType {
  RESIDENTIAL_LOW = "residential_low",
  RESIDENTIAL_MEDIUM = "residential_medium", 
  RESIDENTIAL_HIGH = "residential_high",
  COMMERCIAL = "commercial",
  INDUSTRIAL = "industrial",
  MIXED_USE = "mixed_use",
  INFRASTRUCTURE = "infrastructure",
  RECREATIONAL = "recreational",
  INSTITUTIONAL = "institutional"
}

export interface RegulatoryDocument {
  id: string;
  name: string;
  level: RegulatoryLevel;
  jurisdiction: "STATE" | "REGIONAL" | "LOCAL";
  authority: string;
  effective_date: string;
  applies_to: {
    lgas?: string[];
    zones: string[];
    development_types: DevelopmentType[];
    land_uses?: string[];
  };
  file_path?: string;
  sections: DocumentSection[];
}

export interface DocumentSection {
  id: string;
  title: string;
  applies_to: {
    zones?: string[];
    development_types?: DevelopmentType[];
    conditions?: string[];
  };
  rule_types: string[];
  precedence_notes?: string;
}

/**
 * NSW Planning Regulatory Hierarchy Manager
 * Determines which documents apply to specific development scenarios
 */
export class RegulatoryHierarchy {
  private documents: Map<string, RegulatoryDocument> = new Map();
  
  constructor() {
    this.loadRegulatoryFramework();
  }

  /**
   * Load the complete NSW regulatory framework
   */
  private loadRegulatoryFramework() {
    // Load SEPP documents
    this.registerSEPPs();
    
    // Load LEP documents by LGA
    this.registerLEPs();
    
    // Load DCP documents by LGA
    this.registerDCPs();
  }

  /**
   * Register State Environmental Planning Policies
   */
  private registerSEPPs() {
    // SEPP (Planning Systems) 2021 - Universal
    this.documents.set("SEPP_PLANNING_SYSTEMS_2021", {
      id: "SEPP_PLANNING_SYSTEMS_2021",
      name: "State Environmental Planning Policy (Planning Systems) 2021",
      level: RegulatoryLevel.SEPP,
      jurisdiction: "STATE",
      authority: "NSW Department of Planning and Environment",
      effective_date: "2021-12-01",
      applies_to: {
        lgas: [], // Applies to ALL LGAs
        zones: ["R1", "R2", "R3", "R4", "R5", "RU1", "RU2", "RU3", "RU4", "RU5", "RU6", "E1", "E2", "E3", "E4", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "IN1", "IN2", "IN3", "IN4", "SP1", "SP2", "SP3", "RE1", "RE2", "W1", "W2", "W3"],
        development_types: [
          DevelopmentType.RESIDENTIAL_LOW,
          DevelopmentType.RESIDENTIAL_MEDIUM,
          DevelopmentType.RESIDENTIAL_HIGH,
          DevelopmentType.COMMERCIAL,
          DevelopmentType.MIXED_USE
        ]
      },
      sections: [
        {
          id: "PART_4_SUBDIVISION",
          title: "Part 4 - Subdivision",
          applies_to: {
            zones: ["R1", "R2", "R3", "R4", "R5"],
            development_types: [DevelopmentType.RESIDENTIAL_LOW, DevelopmentType.RESIDENTIAL_MEDIUM]
          },
          rule_types: ["subdivision", "lot_size", "frontage"]
        }
      ]
    });

    // SEPP (Housing) 2021
    this.documents.set("SEPP_HOUSING_2021", {
      id: "SEPP_HOUSING_2021", 
      name: "State Environmental Planning Policy (Housing) 2021",
      level: RegulatoryLevel.SEPP,
      jurisdiction: "STATE",
      authority: "NSW Department of Planning and Environment", 
      effective_date: "2021-12-01",
      applies_to: {
        zones: ["R1", "R2", "R3", "R4", "R5"],
        development_types: [
          DevelopmentType.RESIDENTIAL_LOW,
          DevelopmentType.RESIDENTIAL_MEDIUM,
          DevelopmentType.RESIDENTIAL_HIGH
        ]
      },
      sections: [
        {
          id: "CHAPTER_2_HOUSING_DIVERSITY",
          title: "Chapter 2 - Housing Diversity",
          applies_to: {
            zones: ["R2", "R3", "R4"],
            development_types: [DevelopmentType.RESIDENTIAL_MEDIUM]
          },
          rule_types: ["dwelling_density", "building_height", "setbacks"]
        }
      ]
    });

    // SEPP (Resilience and Hazards) 2021
    this.documents.set("SEPP_RESILIENCE_HAZARDS_2021", {
      id: "SEPP_RESILIENCE_HAZARDS_2021",
      name: "State Environmental Planning Policy (Resilience and Hazards) 2021", 
      level: RegulatoryLevel.SEPP,
      jurisdiction: "STATE",
      authority: "NSW Department of Planning and Environment",
      effective_date: "2021-12-01",
      applies_to: {
        zones: ["R1", "R2", "R3", "R4", "R5", "RU1", "RU2", "E1", "E2", "E3"],
        development_types: Object.values(DevelopmentType)
      },
      sections: [
        {
          id: "CHAPTER_4_CONTAMINATED_LAND",
          title: "Chapter 4 - Remediation of Contaminated Land",
          applies_to: {},
          rule_types: ["contamination", "remediation"]
        }
      ]
    });
  }

  /**
   * Register Local Environmental Plans by LGA
   */
  private registerLEPs() {
    // Inner West LEP 2022
    this.documents.set("INNER_WEST_LEP_2022", {
      id: "INNER_WEST_LEP_2022",
      name: "Inner West Local Environmental Plan 2022",
      level: RegulatoryLevel.LEP,
      jurisdiction: "LOCAL",
      authority: "Inner West Council",
      effective_date: "2022-03-01",
      applies_to: {
        lgas: ["Inner West"],
        zones: ["R1", "R2", "R3", "R4", "B1", "B2", "B4", "IN1", "IN2", "RE1", "RE2", "E2", "SP2"],
        development_types: Object.values(DevelopmentType)
      },
      file_path: "docs/leps/INNERWEST/Inner-West-LEP-2022.pdf",
      sections: [
        {
          id: "PART_4_PRINCIPAL_DEVELOPMENT_STANDARDS", 
          title: "Part 4 - Principal Development Standards",
          applies_to: {},
          rule_types: ["height_of_buildings", "floor_space_ratio", "minimum_subdivision_lot_size"]
        },
        {
          id: "PART_6_ADDITIONAL_LOCAL_PROVISIONS",
          title: "Part 6 - Additional Local Provisions", 
          applies_to: {},
          rule_types: ["heritage", "design_excellence", "affordable_housing"]
        }
      ]
    });

    // City of Sydney LEP 2012
    this.documents.set("SYDNEY_LEP_2012", {
      id: "SYDNEY_LEP_2012",
      name: "Sydney Local Environmental Plan 2012",
      level: RegulatoryLevel.LEP,
      jurisdiction: "LOCAL", 
      authority: "City of Sydney",
      effective_date: "2012-12-14",
      applies_to: {
        lgas: ["Sydney"],
        zones: ["R1", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "IN1", "W1", "RE1", "SP2"],
        development_types: Object.values(DevelopmentType)
      },
      file_path: "docs/leps/SYDNEY/Sydney-LEP-2012.pdf",
      sections: [
        {
          id: "PART_4_PRINCIPAL_DEVELOPMENT_STANDARDS",
          title: "Part 4 - Principal Development Standards",
          applies_to: {},
          rule_types: ["height_of_buildings", "floor_space_ratio", "minimum_subdivision_lot_size"]
        }
      ]
    });
  }

  /**
   * Register Development Control Plans by LGA
   */
  private registerDCPs() {
    // Inner West DCP - Ashfield
    this.documents.set("ASHFIELD_DCP_2016", {
      id: "ASHFIELD_DCP_2016", 
      name: "Inner West Development Control Plan - Ashfield 2016",
      level: RegulatoryLevel.DCP,
      jurisdiction: "LOCAL",
      authority: "Inner West Council (formerly Ashfield Council)",
      effective_date: "2016-01-01",
      applies_to: {
        lgas: ["Inner West"],
        zones: ["R1", "R2", "R3", "R4"],
        development_types: [
          DevelopmentType.RESIDENTIAL_LOW,
          DevelopmentType.RESIDENTIAL_MEDIUM
        ]
      },
      file_path: "docs/dcps/INNERWEST/",
      sections: [
        {
          id: "CHAPTER_E2_HABERFIELD",
          title: "Chapter E2 - Haberfield Neighbourhood",
          applies_to: {
            zones: ["R2"],
            conditions: ["heritage_conservation_area"]
          },
          rule_types: ["setbacks", "building_envelope", "heritage_controls"]
        }
      ]
    });

    // Inner West DCP - Leichhardt  
    this.documents.set("LEICHHARDT_DCP_2013", {
      id: "LEICHHARDT_DCP_2013",
      name: "Inner West Development Control Plan - Leichhardt 2013", 
      level: RegulatoryLevel.DCP,
      jurisdiction: "LOCAL",
      authority: "Inner West Council (formerly Leichhardt Council)",
      effective_date: "2013-01-01", 
      applies_to: {
        lgas: ["Inner West"],
        zones: ["R1", "R2", "R3", "R4", "B1", "B2"],
        development_types: [
          DevelopmentType.RESIDENTIAL_LOW,
          DevelopmentType.RESIDENTIAL_MEDIUM,
          DevelopmentType.COMMERCIAL
        ]
      },
      file_path: "docs/dcps/INNERWEST/",
      sections: [
        {
          id: "PART_G_RESIDENTIAL_CONTROLS",
          title: "Part G - Residential Controls",
          applies_to: {
            zones: ["R1", "R2", "R3", "R4"]
          },
          rule_types: ["setbacks", "building_height", "site_coverage", "landscaping"]
        }
      ]
    });
  }

  /**
   * Get applicable regulatory documents for a specific development scenario
   */
  public getApplicableDocuments(
    lga: string,
    zone: string, 
    developmentType: DevelopmentType,
    landUse?: string
  ): RegulatoryDocument[] {
    
    const applicableDocuments: RegulatoryDocument[] = [];
    
    for (const doc of this.documents.values()) {
      // Check LGA applicability (empty means applies to all)
      if (doc.applies_to.lgas && doc.applies_to.lgas.length > 0) {
        if (!doc.applies_to.lgas.includes(lga)) {
          continue;
        }
      }
      
      // Check zone applicability
      if (!doc.applies_to.zones.includes(zone)) {
        continue;
      }
      
      // Check development type applicability
      if (!doc.applies_to.development_types.includes(developmentType)) {
        continue;
      }
      
      // Check land use if specified
      if (landUse && doc.applies_to.land_uses && !doc.applies_to.land_uses.includes(landUse)) {
        continue;
      }
      
      applicableDocuments.push(doc);
    }
    
    // Sort by regulatory hierarchy (lower number = higher priority)
    return applicableDocuments.sort((a, b) => a.level - b.level);
  }

  /**
   * Get document sections applicable to specific criteria
   */
  public getApplicableSections(
    documentId: string,
    zone: string,
    developmentType: DevelopmentType,
    ruleType: string
  ): DocumentSection[] {
    
    const document = this.documents.get(documentId);
    if (!document) return [];
    
    return document.sections.filter(section => {
      // Check if section applies to this zone
      if (section.applies_to.zones && !section.applies_to.zones.includes(zone)) {
        return false;
      }
      
      // Check if section applies to this development type
      if (section.applies_to.development_types && !section.applies_to.development_types.includes(developmentType)) {
        return false;
      }
      
      // Check if section covers the required rule type
      if (!section.rule_types.includes(ruleType)) {
        return false;
      }
      
      return true;
    });
  }

  /**
   * Get regulatory precedence order for conflicting rules
   */
  public getDocumentPrecedence(): RegulatoryLevel[] {
    return [
      RegulatoryLevel.COMMONWEALTH,
      RegulatoryLevel.STATE_ACT, 
      RegulatoryLevel.SEPP,
      RegulatoryLevel.REP,
      RegulatoryLevel.LEP,
      RegulatoryLevel.DCP,
      RegulatoryLevel.POLICY
    ];
  }
}