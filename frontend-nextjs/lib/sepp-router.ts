/**
 * SEPP Router Service
 * Routes SEPP document processing using database regulatory provisions data
 */

export interface SeppMapping {
 identifier: string;
 name: string;
 database_patterns: string[];
 description: string;
}

export interface SeppRoutingResult {
 applicableSepps: string[];
 seppProvisions: { [seppId: string]: any[] };
 totalProvisions: number;
 missing: string[];
}

/**
 * Known SEPP mappings based on current NSW regulations
 */
const SEPP_MAPPINGS: SeppMapping[] = [
 {
 identifier: 'SEPP_HOUSING_2021',
 name: 'SEPP (Housing) 2021',
 database_patterns: ['State_Environmental_Planning_Policy_(Housing)_2021'],
 description: 'Housing development provisions'
 },
 {
 identifier: 'SEPP_PLANNING_SYSTEMS_2021',
 name: 'SEPP (Planning Systems) 2021',
 database_patterns: ['State_Environmental_Planning_Policy_(Planning_Systems)_2021'],
 description: 'Planning systems and processes'
 },
 {
 identifier: 'SEPP_RESILIENCE_HAZARDS_2021',
 name: 'SEPP (Resilience and Hazards) 2021',
 database_patterns: ['State_Environmental_Planning_Policy_(Resilience_and_Hazards)_2021'],
 description: 'Environmental hazards and resilience'
 },
 {
 identifier: 'SEPP_TRANSPORT_INFRASTRUCTURE_2021',
 name: 'SEPP (Transport and Infrastructure) 2021',
 database_patterns: ['State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021'],
 description: 'Transport and infrastructure development'
 },
 {
 identifier: 'SEPP_BIODIVERSITY_CONSERVATION_2017',
 name: 'SEPP (Biodiversity and Conservation) 2017',
 database_patterns: ['State_Environmental_Planning_Policy_(Biodiversity_and_Conservation)_2017'],
 description: 'Biodiversity conservation provisions'
 },
 {
 identifier: 'SEPP_INDUSTRY_EMPLOYMENT_2021',
 name: 'SEPP (Industry and Employment) 2021',
 database_patterns: ['State_Environmental_Planning_Policy_(Industry_and_Employment)_2021'],
 description: 'Industry and employment development'
 },
 {
 identifier: 'SEPP_EXEMPT_COMPLYING_2008',
 name: 'SEPP (Exempt and Complying Development Codes) 2008',
 database_patterns: ['State_Environmental_Planning_Policy_(Exempt_and_Complying_Development_Codes)_2008'],
 description: 'Exempt and complying development codes'
 },
 {
 identifier: 'SEPP_PRIMARY_PRODUCTION_2021',
 name: 'SEPP (Primary Production) 2021',
 database_patterns: ['State_Environmental_Planning_Policy_(Primary_Production)_2021'],
 description: 'Primary production development'
 },
 {
 identifier: 'SEPP_SUSTAINABLE_BUILDINGS_2022',
 name: 'SEPP (Sustainable Buildings) 2022',
 database_patterns: ['State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022'],
 description: 'Sustainable buildings development'
 }
];

export class SeppRouter {

 constructor() {
 // No longer need file system paths - using database
 }

 /**
 * Route SEPP documents based on applicable SEPPs from NSW Planning Portal API
 */
 public async routeApplicableSepps(applicableSepps: string[]): Promise<SeppRoutingResult> {
 console.log('=== SEPP ROUTING (DATABASE) ===');
 console.log('Applicable SEPPs from API:', applicableSepps);

 const result: SeppRoutingResult = {
 applicableSepps,
 seppProvisions: {},
 totalProvisions: 0,
 missing: []
 };

 // Server-side only operations
 if (typeof window === 'undefined') {
 try {
 // Import database connection
 const { spawn } = require('child_process');
 const path = require('path');

 // Use the existing provision search script to get SEPP data
 const scriptPath = path.join(process.cwd(), '..', 'services', 'provision_search.py');
 const pythonPath = path.join(process.cwd(), '..', 'venv_linux', 'Scripts', 'python.exe');

 // Query for SEPP provisions
 const seppData = await this.queryDatabaseForSepps();

 // Match each applicable SEPP to database provisions
 for (const seppId of applicableSepps) {
 const matchedProvisions = this.findProvisionsForSepp(seppId, seppData);

 if (matchedProvisions.length > 0) {
 result.seppProvisions[seppId] = matchedProvisions;
 result.totalProvisions += matchedProvisions.length;
 console.log(`Matched ${matchedProvisions.length} provisions for ${seppId}`);
 } else {
 result.missing.push(seppId);
 console.log(`No provisions found for SEPP: ${seppId}`);
 }
 }
 } catch (error) {
 console.error('Error querying SEPP database:', error);
 result.missing = [...applicableSepps];
 }
 } else {
 // Client-side fallback
 console.log('SEPP routing not available on client-side');
 result.missing = [...applicableSepps];
 }

 return result;
 }

 /**
 * Query database for SEPP provisions
 */
 private async queryDatabaseForSepps(): Promise<any[]> {
 return new Promise((resolve, reject) => {
 const { spawn } = require('child_process');
 const path = require('path');

 const scriptPath = path.join(process.cwd(), '..', 'check_sepp_provisions.py');
 const pythonPath = 'python'; // Use system python

 const python = spawn(pythonPath, [scriptPath]);

 let stdout = '';
 let stderr = '';

 python.stdout.on('data', (data: any) => {
 stdout += data.toString();
 });

 python.stderr.on('data', (data: any) => {
 stderr += data.toString();
 });

 python.on('close', (code: number) => {
 if (code === 0) {
 try {
 // For now, return empty array as we're just removing PDF routing
 resolve([]);
 } catch (parseError) {
 console.error('Failed to parse SEPP data:', stdout);
 resolve([]);
 }
 } else {
 console.error('Python script error:', stderr);
 resolve([]);
 }
 });

 python.on('error', (error: any) => {
 console.error('Failed to start Python script:', error);
 resolve([]);
 });
 });
 }

 /**
 * Find provisions that match a specific SEPP identifier
 */
 private findProvisionsForSepp(seppId: string, seppData: any[]): any[] {
 const mapping = SEPP_MAPPINGS.find(m => m.identifier === seppId);

 if (!mapping) {
 console.warn(`No mapping found for SEPP: ${seppId}`);
 return [];
 }

 // For now, return empty array - the important part is removing PDF routing
 return [];
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