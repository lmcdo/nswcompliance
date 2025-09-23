/**
 * SEPP Router Service
 * Routes SEPP document processing based on NSW Planning Portal special provisions data
 */

// Conditional imports for Next.js compatibility
let fs: any = null;
let path: any = null;

if (typeof window === 'undefined') {
 // Server-side only
 fs = require('fs');
 path = require('path');
}

export interface SeppMapping {
 identifier: string;
 name: string;
 filename_patterns: string[];
 description: string;
}

export interface SeppRoutingResult {
 applicableSepps: string[];
 seppFiles: { [seppId: string]: string[] };
 totalFiles: number;
 missing: string[];
}

/**
 * Known SEPP mappings based on current NSW regulations
 */
const SEPP_MAPPINGS: SeppMapping[] = [
 {
 identifier: 'SEPP_HOUSING_2021',
 name: 'SEPP (Housing) 2021', 
 filename_patterns: ['housing', 'sepp.*housing'],
 description: 'Housing development provisions'
 },
 {
 identifier: 'SEPP_PLANNING_SYSTEMS_2021',
 name: 'SEPP (Planning Systems) 2021',
 filename_patterns: ['planning.*systems', 'systems.*planning', '\\(planning systems\\)'],
 description: 'Planning systems and processes'
 },
 {
 identifier: 'SEPP_RESILIENCE_HAZARDS_2021',
 name: 'SEPP (Resilience and Hazards) 2021', 
 filename_patterns: ['resilience', 'hazards', 'resilience.*hazards'],
 description: 'Environmental hazards and resilience'
 },
 {
 identifier: 'SEPP_TRANSPORT_INFRASTRUCTURE_2021',
 name: 'SEPP (Transport and Infrastructure) 2021',
 filename_patterns: ['transport', 'infrastructure'],
 description: 'Transport and infrastructure development'
 },
 {
 identifier: 'SEPP_BIODIVERSITY_CONSERVATION_2017',
 name: 'SEPP (Biodiversity and Conservation) 2017',
 filename_patterns: ['biodiversity', 'conservation'],
 description: 'Biodiversity conservation provisions'
 },
 {
 identifier: 'SEPP_INDUSTRY_EMPLOYMENT_2021',
 name: 'SEPP (Industry and Employment) 2021',
 filename_patterns: ['industry', 'employment'],
 description: 'Industry and employment development'
 },
 {
 identifier: 'SEPP_EXEMPT_COMPLYING_2008',
 name: 'SEPP (Exempt and Complying Development Codes) 2008',
 filename_patterns: ['exempt', 'complying'],
 description: 'Exempt and complying development codes'
 },
 {
 identifier: 'SEPP_PRIMARY_PRODUCTION_2021',
 name: 'SEPP (Primary Production) 2021',
 filename_patterns: ['primary.*production', 'production'],
 description: 'Primary production development'
 },
 {
 identifier: 'SEPP_SUSTAINABLE_BUILDINGS_2022',
 name: 'SEPP (Sustainable Buildings) 2022',
 filename_patterns: ['sustainable.*buildings', 'sustainable'],
 description: 'Sustainable buildings development'
 }
];

export class SeppRouter {
 private seppDirectory: string;
 
 constructor(docsBasePath: string = 'docs') {
 this.seppDirectory = path ? path.join(docsBasePath, 'sepps') : '';
 }

 /**
 * Route SEPP documents based on applicable SEPPs from NSW Planning Portal API
 */
 public routeApplicableSepps(applicableSepps: string[]): SeppRoutingResult {
 console.log('=== SEPP ROUTING ===');
 console.log('Applicable SEPPs from API:', applicableSepps);
 
 const result: SeppRoutingResult = {
 applicableSepps,
 seppFiles: {},
 totalFiles: 0,
 missing: []
 };

 // Server-side only operations
 if (typeof window === 'undefined' && fs && path) {
 // Check if SEPP directory exists
 if (!fs.existsSync(this.seppDirectory)) {
 console.error(`SEPP directory not found: ${this.seppDirectory}`);
 result.missing = [...applicableSepps];
 return result;
 }

 // Get all available SEPP files
 const availableFiles = fs.readdirSync(this.seppDirectory)
 .filter((file: string) => file.toLowerCase().endsWith('.pdf'))
 .map((file: string) => ({
 filename: file,
 fullPath: path.join(this.seppDirectory, file)
 }));

 console.log(`Found ${availableFiles.length} SEPP files in ${this.seppDirectory}`);
 availableFiles.forEach(file => console.log(` - ${file.filename}`));

 // Match each applicable SEPP to files
 for (const seppId of applicableSepps) {
 const matchedFiles = this.findFilesForSepp(seppId, availableFiles);
 
 if (matchedFiles.length > 0) {
 result.seppFiles[seppId] = matchedFiles;
 result.totalFiles += matchedFiles.length;
 console.log(`Matched ${matchedFiles.length} files for ${seppId}:`, matchedFiles.map(f => path.basename(f)));
 } else {
 result.missing.push(seppId);
 console.warn(`No files found for SEPP: ${seppId}`);
 }
 }
 } else {
 // Client-side fallback
 console.log('SEPP routing not available on client-side');
 result.missing = [...applicableSepps];
 }

 return result;
 }

 /**
 * Find PDF files that match a specific SEPP identifier
 */
 private findFilesForSepp(seppId: string, availableFiles: { filename: string; fullPath: string }[]): string[] {
 const mapping = SEPP_MAPPINGS.find(m => m.identifier === seppId);
 
 if (!mapping) {
 console.warn(`No mapping found for SEPP: ${seppId}`);
 // Try direct matching with SEPP ID
 const directMatches = availableFiles.filter(file => 
 file.filename.toLowerCase().includes(seppId.toLowerCase().replace('_', ''))
 );
 return directMatches.map(f => f.fullPath);
 }

 const matchedFiles: string[] = [];

 for (const file of availableFiles) {
 const fileName = file.filename.toLowerCase();
 
 // Check each pattern for this SEPP
 for (const pattern of mapping.filename_patterns) {
 const regex = new RegExp(pattern, 'i');
 if (regex.test(fileName)) {
 matchedFiles.push(file.fullPath);
 console.log(`Pattern "${pattern}" matched file: ${file.filename}`);
 break; // Don't match the same file multiple times
 }
 }
 }

 return matchedFiles;
 }

 /**
 * Get all SEPP files without filtering (fallback for testing)
 */
 public getAllSeppFiles(): string[] {
 if (!fs.existsSync(this.seppDirectory)) {
 return [];
 }

 return fs.readdirSync(this.seppDirectory)
 .filter(file => file.toLowerCase().endsWith('.pdf'))
 .map(file => path.join(this.seppDirectory, file));
 }

 /**
 * Get SEPP mapping information
 */
 public getSeppMappings(): SeppMapping[] {
 return SEPP_MAPPINGS;
 }

 /**
 * Add fallback SEPP routing based on development context
 */
 public addContextualSepps(
 developmentType: string,
 zone: string,
 heritage: boolean,
 applicableSepps: string[]
 ): string[] {
 const contextualSepps = [...applicableSepps];

 // Add SEPPs that commonly apply to residential development
 if (developmentType.includes('residential') && zone.startsWith('R')) {
 if (!contextualSepps.includes('SEPP_HOUSING_2021')) {
 contextualSepps.push('SEPP_HOUSING_2021');
 console.log('Added SEPP_HOUSING_2021 for residential development');
 }
 
 // Sustainable buildings often apply to residential
 if (!contextualSepps.includes('SEPP_SUSTAINABLE_BUILDINGS_2022')) {
 contextualSepps.push('SEPP_SUSTAINABLE_BUILDINGS_2022');
 console.log('Added SEPP_SUSTAINABLE_BUILDINGS_2022 for sustainable development');
 }
 }

 // Add transport SEPP for developments near transport infrastructure
 if (!contextualSepps.includes('SEPP_TRANSPORT_INFRASTRUCTURE_2021')) {
 contextualSepps.push('SEPP_TRANSPORT_INFRASTRUCTURE_2021');
 console.log('Added SEPP_TRANSPORT_INFRASTRUCTURE_2021 as commonly applicable');
 }

 // Add biodiversity SEPP for heritage or environmentally sensitive sites
 if (heritage && !contextualSepps.includes('SEPP_BIODIVERSITY_CONSERVATION_2017')) {
 contextualSepps.push('SEPP_BIODIVERSITY_CONSERVATION_2017');
 console.log('Added SEPP_BIODIVERSITY_CONSERVATION_2017 for heritage site');
 }

 // Add exempt and complying for minor developments
 if (!contextualSepps.includes('SEPP_EXEMPT_COMPLYING_2008')) {
 contextualSepps.push('SEPP_EXEMPT_COMPLYING_2008');
 console.log('Added SEPP_EXEMPT_COMPLYING_2008 for minor developments');
 }

 return contextualSepps;
 }
}