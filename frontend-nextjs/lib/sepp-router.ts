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

 /**
 * Route SEPP documents based on applicable SEPPs from NSW Planning Portal API.
 * SEPP provision lookup via database is not yet implemented — returns all SEPPs as missing.
 */
 public routeApplicableSepps(applicableSepps: string[]): SeppRoutingResult {
 return {
 applicableSepps,
 seppProvisions: {},
 totalProvisions: 0,
 missing: [...applicableSepps]
 };
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
 }

 // Sustainable buildings often apply to residential
 if (!contextualSepps.includes('SEPP_SUSTAINABLE_BUILDINGS_2022')) {
 contextualSepps.push('SEPP_SUSTAINABLE_BUILDINGS_2022');
 }
 }

 // Add transport SEPP for developments near transport infrastructure
 if (!contextualSepps.includes('SEPP_TRANSPORT_INFRASTRUCTURE_2021')) {
 contextualSepps.push('SEPP_TRANSPORT_INFRASTRUCTURE_2021');
 }

 // Add biodiversity SEPP for heritage or environmentally sensitive sites
 if (heritage && !contextualSepps.includes('SEPP_BIODIVERSITY_CONSERVATION_2017')) {
 contextualSepps.push('SEPP_BIODIVERSITY_CONSERVATION_2017');
 }

 // Add exempt and complying for minor developments
 if (!contextualSepps.includes('SEPP_EXEMPT_COMPLYING_2008')) {
 contextualSepps.push('SEPP_EXEMPT_COMPLYING_2008');
 }

 return contextualSepps;
 }
}