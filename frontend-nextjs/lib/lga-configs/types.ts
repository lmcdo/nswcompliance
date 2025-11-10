/**
 * LGA Configuration Types
 *
 * Defines structure and conventions for each LGA's DCP documents
 * Enables scalable handling of different DCP formats across NSW
 */

export type NumberingStyle = 'decimal' | 'clause' | 'hybrid';
export type AppendixLocation = 'inline' | 'separate';

export interface LGAStructure {
  /** Chapter type patterns (glob-style) */
  chapterTypes: {
    generic?: string;         // e.g., "2_*" - Generic controls like parking
    development?: string;     // e.g., "4_*" - Development type controls
    heritage?: string;        // e.g., "8_*" - Heritage areas
    precincts?: string;       // e.g., "9_*" - Location-specific precincts
    [key: string]: string | undefined;
  };

  /** Documents that are precinct-specific */
  precinctDocs?: string[];

  /** Master plan documents */
  masterPlans?: string[];
}

export interface LGAConventions {
  /** Primary numbering style used */
  numberingStyle: NumberingStyle;

  /** Regex pattern for finding figures */
  figurePattern: string;

  /** Regex pattern for finding tables */
  tablePattern?: string;

  /** Regex pattern for finding diagrams */
  diagramPattern?: string;

  /** Whether control codes (C17, H01) are used */
  controlCodes: boolean;

  /** Control code pattern if used */
  controlCodePattern?: string;
}

export interface LGAQuirks {
  /** Alternative names for figures */
  figureAliases?: string[];

  /** Alternative names for tables */
  tableAliases?: string[];

  /** Where appendices are located */
  appendixLocation?: AppendixLocation;

  /** Custom section header patterns */
  customHeaderPatterns?: string[];

  /** Known edge cases */
  edgeCases?: {
    description: string;
    pattern: string;
    handling: string;
  }[];
}

export interface LGAConfig {
  /** LGA name */
  lga: string;

  /** Former council areas (if merged LGA) */
  councils?: string[];

  /** Document structure patterns */
  structure: LGAStructure;

  /** Numbering and reference conventions */
  conventions: LGAConventions;

  /** Special cases and quirks */
  quirks?: LGAQuirks;

  /** Config metadata */
  meta?: {
    version: string;
    lastUpdated: string;
    author?: string;
    notes?: string;
  };
}

/**
 * Extracted section result
 */
export interface ExtractedSection {
  sectionRef: string;
  sectionType: 'figure' | 'table' | 'diagram' | 'section' | 'appendix';
  content: string;
  startPosition: number;
  endPosition: number;
  hasImages: boolean;
  imageCount: number;
  images: string[];
}

/**
 * Cache entry for extracted sections
 */
export interface CachedSection extends ExtractedSection {
  documentId: string;
  extractedAt: number;  // Timestamp
  expiresAt: number;    // Timestamp
}
