/**
 * Regulatory Text Retriever
 * Retrieves actual regulatory text from processed LEP chunks
 */

import { readFileSync } from 'fs';
import { join } from 'path';

export interface RegulatoryTextMatch {
 text: string;
 source: string;
 confidence: number;
 chunk_id: string;
}

export class RegulatoryTextRetriever {
 private lepChunks: Map<string, string> = new Map();
 private lepChunksLoaded = false;
 private unifiedData: Map<string, any> = new Map();
 private unifiedDataLoaded = false;
 private seppLightRAG: any = null;
 private lepLightRAG: any = null;

 constructor() {
 this.loadLEPChunks();
 this.loadUnifiedData();
 this.initializeLightRAGInstances();
 }

 /**
 * Initialize LightRAG instances for SEPP and LEP querying
 */
 private initializeLightRAGInstances() {
 try {
 // For now, we'll add LightRAG queries via subprocess calls when needed
 // This avoids complex async initialization in the constructor
 console.log(' LightRAG instances ready for SEPP and LEP queries');
 } catch (error) {
 console.warn('LightRAG initialization failed:', error);
 }
 }

 /**
 * Query SEPP LightRAG storage for regulatory text
 */
 private async querySEPPLightRAG(query: string): Promise<string | null> {
 try {
 const { spawn } = require('child_process');
 const path = require('path');
 
 return new Promise((resolve, reject) => {
 const scriptPath = path.join(process.cwd(), 'scripts', 'query_sepp_lightrag.py');
 const python = spawn('C:\\Users\\lawre\\.pyenv\\pyenv-win\\versions\\3.11.0\\python.exe', [scriptPath, query]);
 
 let output = '';
 let error = '';
 
 python.stdout.on('data', (data: any) => {
 output += data.toString();
 });
 
 python.stderr.on('data', (data: any) => {
 error += data.toString();
 });
 
 python.on('close', (code: number) => {
 if (code === 0 && output.trim()) {
 resolve(output.trim());
 } else {
 console.warn('SEPP LightRAG query failed:', error);
 resolve(null);
 }
 });
 
 // Timeout after 30 seconds
 setTimeout(() => {
 python.kill();
 resolve(null);
 }, 30000);
 });
 } catch (error) {
 console.warn('SEPP LightRAG query error:', error);
 return null;
 }
 }

 /**
 * Query LEP processed storage directly for regulatory text
 */
 private async queryLEPLightRAG(query: string): Promise<string | null> {
 try {
 const { spawn } = require('child_process');
 const path = require('path');
 
 return new Promise((resolve, reject) => {
 let queryType = 'height'; // default
 
 // Determine query type from query content
 if (query.toLowerCase().includes('fsr') || query.toLowerCase().includes('floor space')) {
 queryType = 'fsr';
 } else if (query.toLowerCase().includes('height')) {
 queryType = 'height';
 }
 
 const scriptPath = path.join(process.cwd(), 'scripts', 'direct_lep_access.py');
 const python = spawn('C:\\Users\\lawre\\.pyenv\\pyenv-win\\versions\\3.11.0\\python.exe', [scriptPath, queryType]);
 
 let output = '';
 let error = '';
 
 python.stdout.on('data', (data: any) => {
 output += data.toString();
 });
 
 python.stderr.on('data', (data: any) => {
 error += data.toString();
 });
 
 python.on('close', (code: number) => {
 if (code === 0 && output.trim()) {
 resolve(output.trim());
 } else {
 console.warn(`LEP direct access failed for ${queryType}:`, error);
 resolve(null);
 }
 });
 
 // Timeout after 10 seconds (much faster now)
 setTimeout(() => {
 python.kill();
 resolve(null);
 }, 10000);
 });
 } catch (error) {
 console.warn('LEP direct access error:', error);
 return null;
 }
 }

 /**
 * Query DCP processed storage directly for setback requirements
 */
 private async queryDCPLightRAG(area: string, setbackType: string): Promise<string | null> {
 try {
 const { spawn } = require('child_process');
 const path = require('path');
 
 return new Promise((resolve, reject) => {
 const validAreas = ['ashfield', 'leichhardt', 'marrickville'];
 const validSetbacks = ['front', 'side', 'rear'];
 
 if (!validAreas.includes(area.toLowerCase()) || !validSetbacks.includes(setbackType.toLowerCase())) {
 resolve(null);
 return;
 }
 
 const scriptPath = path.join(process.cwd(), 'scripts', 'direct_dcp_access.py');
 const python = spawn('C:\\Users\\lawre\\.pyenv\\pyenv-win\\versions\\3.11.0\\python.exe', [scriptPath, area, setbackType]);
 
 let output = '';
 let error = '';
 
 python.stdout.on('data', (data: any) => {
 output += data.toString();
 });
 
 python.stderr.on('data', (data: any) => {
 error += data.toString();
 });
 
 python.on('close', (code: number) => {
 if (code === 0 && output.trim()) {
 resolve(output.trim());
 } else {
 console.warn(`DCP direct access failed for ${area} ${setbackType}:`, error);
 resolve(null);
 }
 });
 
 // Timeout after 10 seconds
 setTimeout(() => {
 python.kill();
 resolve(null);
 }, 10000);
 });
 } catch (error) {
 console.warn('DCP direct access error:', error);
 return null;
 }
 }

 /**
 * Load LEP chunks from processed files
 */
 private loadLEPChunks() {
 if (this.lepChunksLoaded) return;

 try {
 const lepDir = join(process.cwd(), 'temp_extraction_LEP');
 
 // Load chunks 0-69 (we know we have 70 chunks from metadata)
 for (let i = 0; i < 70; i++) {
 try {
 const chunkPath = join(lepDir, `lep_chunk_${i}.txt`);
 const content = readFileSync(chunkPath, 'utf-8');
 
 // Remove the header lines and get the actual LEP text
 const lines = content.split('\n');
 const textStartIndex = lines.findIndex(line => line.trim() === '') + 1;
 const actualText = lines.slice(textStartIndex).join('\n').trim();
 
 if (actualText.length > 100) { // Only store substantial chunks
 this.lepChunks.set(`chunk_${i}`, actualText);
 }
 } catch (e) {
 // Skip missing chunks
 continue;
 }
 }
 
 this.lepChunksLoaded = true;
 console.log(` Loaded ${this.lepChunks.size} LEP regulatory text chunks`);
 
 } catch (error) {
 console.error('Failed to load LEP chunks:', error);
 }
 }

 /**
 * Load unified LightRAG data from processed files
 */
 private loadUnifiedData() {
 if (this.unifiedDataLoaded) return;

 try {
 const areas = ['ashfield', 'leichhardt', 'marrickville'];
 
 for (const area of areas) {
 try {
 const unifiedPath = join(process.cwd(), 'public', 'regulatory-data', 'unified', `${area}_unified.json`);
 const unifiedContent = readFileSync(unifiedPath, 'utf-8');
 const unifiedJson = JSON.parse(unifiedContent);
 this.unifiedData.set(area, unifiedJson);
 console.log(` Loaded unified data for ${area}: ${unifiedJson.enhanced_rules?.length || 0} rules`);
 } catch (error) {
 console.warn(`Could not load unified data for ${area}:`, error);
 }
 }
 } catch (error) {
 console.error('Error loading unified data:', error);
 }

 this.unifiedDataLoaded = true;
 }

 /**
 * Get regulatory text from LightRAG unified data
 */
 private getRegulatoryTextFromUnified(area: string, ruleType: string): RegulatoryTextMatch | null {
 const areaData = this.unifiedData.get(area.toLowerCase());
 if (!areaData || !areaData.enhanced_rules) return null;

 // Find matching rule by type
 const matchingRule = areaData.enhanced_rules.find((rule: any) => 
 rule.rule_type === ruleType && rule.source_grounding?.extraction_text
 );

 if (matchingRule) {
 return {
 text: matchingRule.source_grounding.extraction_text,
 source: `${area} DCP - ${matchingRule.source_grounding.source_location}`,
 confidence: matchingRule.source_grounding.confidence || 0.8,
 chunk_id: matchingRule.rule_id
 };
 }

 return null;
 }

 /**
 * Get regulatory text for height requirements following SEPP > LEP hierarchy
 */
 async getHeightRegulatoryText(): Promise<RegulatoryTextMatch | null> {
 try {
 // Try LEP first (most specific for Inner West) - use semantic query
 const lepResult = await this.queryLEPLightRAG('Extract only the operative clause from 4.3 height requirements: the single sentence that states the height limitation rule');
 if (lepResult && lepResult.length > 100) {
 return {
 text: lepResult,
 source: 'Inner West Local Environmental Plan 2022 - Clause 4.3',
 confidence: 0.95,
 chunk_id: 'lep_height_4_3'
 };
 }

 // Fallback to SEPP (state-wide requirements) 
 const seppResult = await this.querySEPPLightRAG('What are the state environmental planning policy requirements for building height limitations? Include specific height controls and exemptions.');
 if (seppResult && seppResult.length > 100) {
 return {
 text: seppResult,
 source: 'State Environmental Planning Policy - Height Controls',
 confidence: 0.9,
 chunk_id: 'sepp_height_controls'
 };
 }
 
 // Final fallback to local chunks
 const heightKeywords = ['4.3 Height of buildings', 'must not exceed the maximum height', 'Height of Buildings Map', 'building height'];
 const excludeKeywords = ['exception', '4.3A', 'affordable housing', 'additional height', 'development control plan'];
 return this.searchForRegulatoryTextWithExclusions(heightKeywords, excludeKeywords, 'Height Requirements (Clause 4.3)');
 
 } catch (error) {
 console.warn('Failed to query LightRAG for height requirements:', error);
 // Fallback to local search
 const heightKeywords = ['4.3 Height of buildings', 'must not exceed the maximum height', 'Height of Buildings Map', 'building height'];
 const excludeKeywords = ['exception', '4.3A', 'affordable housing', 'additional height', 'development control plan'];
 return this.searchForRegulatoryTextWithExclusions(heightKeywords, excludeKeywords, 'Height Requirements (Clause 4.3)');
 }
 }

 /**
 * Get regulatory text for FSR requirements following SEPP > LEP hierarchy
 */
 async getFSRRegulatoryText(): Promise<RegulatoryTextMatch | null> {
 try {
 // Try LEP first (most specific for Inner West) - use semantic query
 const lepResult = await this.queryLEPLightRAG('Extract only the operative clause from 4.4 FSR requirements: the single sentence that states the floor space ratio limitation rule');
 if (lepResult && lepResult.length > 100) {
 return {
 text: lepResult,
 source: 'Inner West Local Environmental Plan 2022 - Clause 4.4',
 confidence: 0.95,
 chunk_id: 'lep_fsr_4_4'
 };
 }

 // Fallback to SEPP (state-wide requirements)
 const seppResult = await this.querySEPPLightRAG('What are the state environmental planning policy requirements for floor space ratio controls? Include specific FSR limitations and bonus provisions.');
 if (seppResult && seppResult.length > 100) {
 return {
 text: seppResult,
 source: 'State Environmental Planning Policy - Floor Space Ratio Controls',
 confidence: 0.9,
 chunk_id: 'sepp_fsr_controls'
 };
 }
 
 // Final fallback to local chunks
 const fsrKeywords = ['4.4', 'floor space ratio', 'Floor Space Ratio Map', 'maximum floor space'];
 return this.searchForRegulatoryText(fsrKeywords, 'Floor Space Ratio (Clause 4.4)');
 
 } catch (error) {
 console.warn('Failed to query LightRAG for FSR requirements:', error);
 // Fallback to local search
 const fsrKeywords = ['4.4', 'floor space ratio', 'Floor Space Ratio Map', 'maximum floor space'];
 return this.searchForRegulatoryText(fsrKeywords, 'Floor Space Ratio (Clause 4.4)');
 }
 }

 /**
 * Get regulatory text for setback requirements
 * Uses direct DCP storage access for real regulatory text
 */
 async getSetbackRegulatoryText(ruleType?: string, formerCouncilArea?: string): Promise<RegulatoryTextMatch | null> {
 // Try DCP direct storage access first (highest priority for setbacks)
 if (ruleType && formerCouncilArea) {
 try {
 const dcpResult = await this.queryDCPLightRAG(formerCouncilArea, ruleType);
 if (dcpResult && dcpResult.includes('DCP') && dcpResult.includes('minimum')) {
 return {
 text: dcpResult,
 source: `${formerCouncilArea} DCP - Direct Storage Access`,
 confidence: 0.95,
 chunk_id: `dcp_${formerCouncilArea.toLowerCase()}_${ruleType}`
 };
 }
 } catch (error) {
 console.warn(`DCP direct access failed for ${formerCouncilArea} ${ruleType}:`, error);
 }
 }

 // Fallback: Try LightRAG unified data
 if (ruleType && formerCouncilArea) {
 const unifiedText = this.getRegulatoryTextFromUnified(formerCouncilArea, ruleType);
 if (unifiedText) {
 console.log(` Found LightRAG unified text for ${ruleType} in ${formerCouncilArea}`);
 return unifiedText;
 }
 }

 // Fallback: Try precise citations from old data
 const preciseText = this.getPreciseCitation(ruleType, formerCouncilArea);
 if (preciseText) {
 return preciseText;
 }
 
 // Final fallback to keyword search
 const setbackKeywords = ['setback', 'rear boundary', 'side boundary', 'front boundary', 'building envelope'];
 return this.searchForRegulatoryText(setbackKeywords, 'Setback Requirements');
 }
 
 /**
 * Get precise citation from unified extraction data
 */
 private getPreciseCitation(ruleType?: string, formerCouncilArea?: string): RegulatoryTextMatch | null {
 if (!ruleType || !formerCouncilArea) return null;
 
 try {
 const fs = require('fs');
 const path = require('path');
 
 // Try to load unified extraction data
 const unifiedFile = path.join(process.cwd(), 'public', 'regulatory-data', 'unified', `${formerCouncilArea.toLowerCase()}_unified.json`);
 
 if (fs.existsSync(unifiedFile)) {
 const unifiedData = JSON.parse(fs.readFileSync(unifiedFile, 'utf8'));
 
 // Find rule matching the type
 const matchingRule = unifiedData.enhanced_rules?.find((rule: any) => 
 rule.rule_type === ruleType && rule.source_grounding?.exact_sentence
 );
 
 if (matchingRule) {
 return {
 text: matchingRule.source_grounding.extraction_text || matchingRule.source_grounding.exact_sentence,
 source: `${formerCouncilArea} DCP - Precise Extraction`,
 confidence: matchingRule.overall_confidence || 0.9,
 chunk_id: `precise_${matchingRule.rule_id}`
 };
 }
 }
 } catch (error) {
 console.log(`Could not load precise citations for ${formerCouncilArea}: ${error.message}`);
 }
 
 return null;
 }

 /**
 * Search for regulatory text containing specific keywords while excluding others
 */
 private searchForRegulatoryTextWithExclusions(keywords: string[], excludeKeywords: string[], source: string): RegulatoryTextMatch | null {
 let bestMatch: { chunk: string; content: string; score: number; operativeText?: string } | null = null;

 for (const [chunkId, content] of this.lepChunks) {
 const contentLower = content.toLowerCase();
 
 // Skip chunks containing excluded keywords ONLY if we're not looking for specific operative text
 // For height/FSR, we'll look for the exact clause even if the chunk contains exceptions elsewhere
 const skipDueToExclusion = source.includes('Height') || source.includes('Floor Space') ? 
 false : // Don't skip for height/FSR - we'll find the exact clause
 excludeKeywords.some(exclude => contentLower.includes(exclude.toLowerCase()));
 
 if (skipDueToExclusion) continue;
 
 let score = 0;
 let operativeText: string | undefined;

 // Look for specific operative clauses (prioritize these)
 if (source.includes('Height')) {
 // Look for the specific operative height clause - capture from 4.3 to the end of subclause (2)
 const heightMatch = content.match(/4\.3 Height of buildings[^]*?\(2\) The height of a building on any land is not to exceed the maximum height shown for the land on the Height of Buildings Map\./);
 if (heightMatch) {
 operativeText = heightMatch[0];
 score += 1000; // High priority for exact operative text
 }
 } else if (source.includes('Floor Space')) {
 // Look for the specific operative FSR clause
 const fsrMatch = content.match(/4\.4 Floor space ratio[\s\S]*?\(2\)[^()]*The maximum floor space ratio for a building on any land is not to exceed[^.]+\./);
 if (fsrMatch) {
 operativeText = fsrMatch[0];
 score += 1000; // High priority for exact operative text
 }
 }

 // Fallback to keyword scoring
 for (const keyword of keywords) {
 const keywordLower = keyword.toLowerCase();
 const matches = (contentLower.match(new RegExp(keywordLower, 'g')) || []).length;
 score += matches * keyword.length;
 }

 if (score > 0 && (!bestMatch || score > bestMatch.score)) {
 bestMatch = { chunk: chunkId, content, score, operativeText };
 }
 }

 if (!bestMatch) return null;

 // If we found the exact operative text, return it
 if (bestMatch.operativeText) {
 return {
 text: bestMatch.operativeText,
 source: `Inner West Local Environmental Plan 2022 - ${source}`,
 confidence: 0.99, // Very high confidence for exact match
 chunk_id: bestMatch.chunk
 };
 }

 return this.extractRelevantText(bestMatch, keywords, source);
 }

 /**
 * Search for regulatory text containing specific keywords
 */
 private searchForRegulatoryText(keywords: string[], source: string): RegulatoryTextMatch | null {
 let bestMatch: { chunk: string; content: string; score: number } | null = null;

 for (const [chunkId, content] of this.lepChunks) {
 const contentLower = content.toLowerCase();
 let score = 0;

 // Score based on keyword matches
 for (const keyword of keywords) {
 const keywordLower = keyword.toLowerCase();
 const matches = (contentLower.match(new RegExp(keywordLower, 'g')) || []).length;
 score += matches * keyword.length; // Longer keywords get higher weight
 }

 if (score > 0 && (!bestMatch || score > bestMatch.score)) {
 bestMatch = { chunk: chunkId, content, score };
 }
 }

 if (!bestMatch) return null;

 return this.extractRelevantText(bestMatch, keywords, source);
 }

 /**
 * Extract relevant text from a matched chunk
 */
 private extractRelevantText(bestMatch: { chunk: string; content: string; score: number }, keywords: string[], source: string): RegulatoryTextMatch {
 // Extract the most relevant portion (first 500 characters containing keywords)
 const content = bestMatch.content;
 let relevantText = content;

 // Try to find the specific clause section
 for (const keyword of keywords) {
 const keywordLower = keyword.toLowerCase();
 const index = content.toLowerCase().indexOf(keywordLower);
 if (index !== -1) {
 // Extract text around the keyword (up to 800 characters)
 const start = Math.max(0, index - 100);
 const end = Math.min(content.length, index + 700);
 relevantText = content.substring(start, end);
 
 // Clean up partial sentences at the beginning - find complete sentence boundaries
 const sentences = relevantText.split(/\. /);
 if (sentences.length > 1) {
 // Skip the first sentence if it appears to be a fragment (starts with lowercase or is very short)
 const firstSentence = sentences[0].trim();
 if (firstSentence.length < 20 || (firstSentence.length > 0 && firstSentence[0] >= 'a' && firstSentence[0] <= 'z')) {
 relevantText = sentences.slice(1).join('. ');
 // Ensure it starts with a capital letter
 if (relevantText.length > 0 && relevantText[0] >= 'a' && relevantText[0] <= 'z') {
 relevantText = relevantText[0].toUpperCase() + relevantText.slice(1);
 }
 }
 }
 break;
 }
 }

 return {
 text: relevantText.trim(),
 source: `Inner West Local Environmental Plan 2022 - ${source}`,
 confidence: Math.min(0.95, bestMatch.score / 100), // Cap confidence at 95%
 chunk_id: bestMatch.chunk
 };
 }
}