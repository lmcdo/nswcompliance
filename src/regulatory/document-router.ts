/**
 * Regulatory Document Router
 * Routes document processing requests based on property characteristics
 * and regulatory hierarchy
 */

import { RegulatoryHierarchy, DevelopmentType, RegulatoryDocument } from './hierarchy';
import path from 'path';
import fs from 'fs';

export interface PropertyContext {
  lga: string;
  zone: string;
  developmentType: DevelopmentType;
  landUse?: string;
  heritage?: boolean;
  environmentallySignificant?: boolean;
  formerCouncilArea?: string; // For amalgamated councils
}

export interface DocumentProcessingPlan {
  documents: ProcessingDocument[];
  processingOrder: string[];
  ruleConflictResolution: ConflictResolution[];
}

export interface ProcessingDocument {
  documentId: string;
  name: string;
  level: number;
  filePaths: string[];
  sectionsToProcess: string[];
  ruleTypes: string[];
  priority: number;
}

export interface ConflictResolution {
  ruleType: string;
  precedenceOrder: string[];
  notes: string;
}

/**
 * LGA Directory Structure Mapping
 */
const LGA_DIRECTORY_MAP = {
  "Inner West": "INNERWEST",
  "Sydney": "SYDNEY", 
  "Randwick": "RANDWICK",
  "Waverley": "WAVERLEY",
  "Woollahra": "WOOLLAHRA",
  "Canada Bay": "CANADABAY",
  "Strathfield": "STRATHFIELD",
  "Burwood": "BURWOOD"
  // Add more as needed
};

/**
 * Former Council Area Mapping (for amalgamated councils)
 */
const FORMER_COUNCIL_MAPPING = {
  "Inner West": {
    suburbs: {
      "Ashfield": "Ashfield",
      "Haberfield": "Ashfield", 
      "Summer Hill": "Ashfield",
      "Leichhardt": "Leichhardt",
      "Annandale": "Leichhardt",
      "Balmain": "Leichhardt",
      "Rozelle": "Leichhardt",
      "Marrickville": "Marrickville",
      "Newtown": "Marrickville",
      "Enmore": "Marrickville",
      "Dulwich Hill": "Marrickville"
    }
  }
};

export class DocumentRouter {
  private hierarchy: RegulatoryHierarchy;
  private docsBasePath: string;

  constructor(docsBasePath: string = "docs") {
    this.hierarchy = new RegulatoryHierarchy();
    this.docsBasePath = docsBasePath;
  }

  /**
   * Create comprehensive document processing plan for a property
   */
  public createProcessingPlan(context: PropertyContext): DocumentProcessingPlan {
    console.log(`Creating processing plan for ${context.lga}, Zone: ${context.zone}, Type: ${context.developmentType}`);
    
    // Get applicable documents from regulatory hierarchy
    const applicableDocuments = this.hierarchy.getApplicableDocuments(
      context.lga,
      context.zone,
      context.developmentType,
      context.landUse
    );

    console.log(`Found ${applicableDocuments.length} applicable regulatory documents`);

    // Convert to processing documents with file paths
    const processingDocuments = this.mapToProcessingDocuments(applicableDocuments, context);
    
    // Determine processing order based on regulatory hierarchy
    const processingOrder = this.determineProcessingOrder(processingDocuments);
    
    // Setup rule conflict resolution
    const conflictResolution = this.setupConflictResolution(processingDocuments);

    return {
      documents: processingDocuments,
      processingOrder,
      ruleConflictResolution: conflictResolution
    };
  }

  /**
   * Map regulatory documents to processing documents with actual file paths
   */
  private mapToProcessingDocuments(
    documents: RegulatoryDocument[],
    context: PropertyContext
  ): ProcessingDocument[] {
    
    const processingDocuments: ProcessingDocument[] = [];

    for (const doc of documents) {
      const filePaths = this.findDocumentFiles(doc, context);
      
      if (filePaths.length === 0) {
        console.warn(`No files found for document: ${doc.name}`);
        continue;
      }

      // Get relevant sections for this context
      const relevantSections = this.getRelevantSections(doc, context);
      
      processingDocuments.push({
        documentId: doc.id,
        name: doc.name,
        level: doc.level,
        filePaths,
        sectionsToProcess: relevantSections.map(s => s.id),
        ruleTypes: this.getRuleTypesForContext(doc, context),
        priority: doc.level // Lower number = higher priority
      });
    }

    return processingDocuments.sort((a, b) => a.priority - b.priority);
  }

  /**
   * Find actual PDF files for a regulatory document
   */
  private findDocumentFiles(doc: RegulatoryDocument, context: PropertyContext): string[] {
    const filePaths: string[] = [];
    
    // Determine LGA directory
    const lgaDir = LGA_DIRECTORY_MAP[context.lga];
    if (!lgaDir) {
      console.warn(`No directory mapping for LGA: ${context.lga}`);
      return filePaths;
    }

    try {
      switch (doc.level) {
        case 3: // SEPP
          const seppDir = path.join(this.docsBasePath, "sepps");
          if (fs.existsSync(seppDir)) {
            const seppFiles = fs.readdirSync(seppDir)
              .filter(file => file.endsWith('.pdf'))
              .filter(file => this.matchesSEPP(file, doc.id));
            filePaths.push(...seppFiles.map(f => path.join(seppDir, f)));
          }
          break;

        case 5: // LEP
          const lepDir = path.join(this.docsBasePath, "leps", lgaDir);
          if (fs.existsSync(lepDir)) {
            const lepFiles = fs.readdirSync(lepDir)
              .filter(file => file.endsWith('.pdf'))
              .filter(file => this.matchesLEP(file, context.lga));
            filePaths.push(...lepFiles.map(f => path.join(lepDir, f)));
          }
          break;

        case 6: // DCP
          const dcpDir = path.join(this.docsBasePath, "dcps", lgaDir);
          if (fs.existsSync(dcpDir)) {
            const dcpFiles = this.findDCPFiles(dcpDir, doc.id, context);
            filePaths.push(...dcpFiles);
          }
          break;
      }
    } catch (error) {
      console.error(`Error finding files for ${doc.name}:`, error);
    }

    return filePaths;
  }

  /**
   * Find specific DCP files based on context
   */
  private findDCPFiles(dcpDir: string, documentId: string, context: PropertyContext): string[] {
    const files = fs.readdirSync(dcpDir).filter(f => f.endsWith('.pdf'));
    const relevantFiles: string[] = [];

    for (const file of files) {
      const filePath = path.join(dcpDir, file);
      const fileName = file.toLowerCase();
      
      // For Inner West - route by former council area
      if (context.lga === "Inner West" && context.formerCouncilArea) {
        if (documentId === "ASHFIELD_DCP_2016" && 
            (fileName.includes('ashfield') || fileName.includes('chapter e'))) {
          relevantFiles.push(filePath);
        } else if (documentId === "LEICHHARDT_DCP_2013" && 
                   (fileName.includes('leichhardt') || fileName.includes('part g'))) {
          relevantFiles.push(filePath);
        } else if (documentId === "MARRICKVILLE_DCP_2011" && 
                   fileName.includes('marrickville')) {
          relevantFiles.push(filePath);
        }
      } else {
        // Generic LGA matching
        if (fileName.includes(context.lga.toLowerCase().replace(' ', ''))) {
          relevantFiles.push(filePath);
        }
      }
    }

    return relevantFiles;
  }

  /**
   * Get relevant sections for this property context
   */
  private getRelevantSections(doc: RegulatoryDocument, context: PropertyContext) {
    return doc.sections.filter(section => {
      // Check zone applicability
      if (section.applies_to.zones && !section.applies_to.zones.includes(context.zone)) {
        return false;
      }
      
      // Check development type applicability 
      if (section.applies_to.development_types && 
          !section.applies_to.development_types.includes(context.developmentType)) {
        return false;
      }
      
      return true;
    });
  }

  /**
   * Get rule types that are relevant for this context
   */
  private getRuleTypesForContext(doc: RegulatoryDocument, context: PropertyContext): string[] {
    const ruleTypes = new Set<string>();
    
    const relevantSections = this.getRelevantSections(doc, context);
    for (const section of relevantSections) {
      section.rule_types.forEach(rt => ruleTypes.add(rt));
    }
    
    return Array.from(ruleTypes);
  }

  /**
   * Determine processing order based on regulatory hierarchy and dependencies
   */
  private determineProcessingOrder(documents: ProcessingDocument[]): string[] {
    // Process in hierarchy order: SEPP → LEP → DCP
    return documents
      .sort((a, b) => a.priority - b.priority)
      .map(doc => doc.documentId);
  }

  /**
   * Setup rule conflict resolution based on regulatory precedence
   */
  private setupConflictResolution(documents: ProcessingDocument[]): ConflictResolution[] {
    const resolutions: ConflictResolution[] = [];
    
    // Group by rule types
    const ruleTypeGroups: { [ruleType: string]: ProcessingDocument[] } = {};
    
    for (const doc of documents) {
      for (const ruleType of doc.ruleTypes) {
        if (!ruleTypeGroups[ruleType]) {
          ruleTypeGroups[ruleType] = [];
        }
        ruleTypeGroups[ruleType].push(doc);
      }
    }

    // Create precedence rules for each rule type
    for (const [ruleType, docs] of Object.entries(ruleTypeGroups)) {
      if (docs.length > 1) {
        const precedenceOrder = docs
          .sort((a, b) => a.priority - b.priority)
          .map(d => d.documentId);
          
        resolutions.push({
          ruleType,
          precedenceOrder,
          notes: `${ruleType} rules: SEPP overrides LEP, LEP overrides DCP`
        });
      }
    }

    return resolutions;
  }

  /**
   * Determine former council area from address/suburb
   */
  public determineFormerCouncilArea(lga: string, suburb?: string): string | undefined {
    if (!suburb || !FORMER_COUNCIL_MAPPING[lga]) {
      return undefined;
    }
    
    return FORMER_COUNCIL_MAPPING[lga].suburbs[suburb];
  }

  /**
   * Helper methods for file matching
   */
  private matchesSEPP(filename: string, seppId: string): boolean {
    const name = filename.toLowerCase();
    
    switch (seppId) {
      case "SEPP_PLANNING_SYSTEMS_2021":
        return name.includes('planning') && name.includes('systems');
      case "SEPP_HOUSING_2021": 
        return name.includes('housing');
      case "SEPP_RESILIENCE_HAZARDS_2021":
        return name.includes('resilience') || name.includes('hazards');
      default:
        return false;
    }
  }

  private matchesLEP(filename: string, lga: string): boolean {
    const name = filename.toLowerCase();
    const lgaName = lga.toLowerCase().replace(' ', '');
    return name.includes(lgaName) && name.includes('lep');
  }

  /**
   * Get processing statistics
   */
  public getProcessingStats(plan: DocumentProcessingPlan) {
    const stats = {
      totalDocuments: plan.documents.length,
      documentsByLevel: {} as { [key: string]: number },
      totalFiles: plan.documents.reduce((sum, doc) => sum + doc.filePaths.length, 0),
      ruleTypes: new Set<string>(),
      conflictResolutions: plan.ruleConflictResolution.length
    };

    for (const doc of plan.documents) {
      const level = `Level_${doc.level}`;
      stats.documentsByLevel[level] = (stats.documentsByLevel[level] || 0) + 1;
      
      doc.ruleTypes.forEach(rt => stats.ruleTypes.add(rt));
    }

    return {
      ...stats,
      ruleTypes: Array.from(stats.ruleTypes)
    };
  }
}