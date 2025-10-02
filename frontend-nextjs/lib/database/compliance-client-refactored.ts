/**
 * Compliance Data Client - PRP-A2 REFACTORED VERSION
 * Supports both subprocess (legacy) and direct database (new) modes
 *
 * This allows gradual migration from subprocess to direct database
 * Set COMPLIANCE_ARCHITECTURE=direct_database to enable direct mode
 */

import { spawn } from 'child_process';
import path from 'path';
import {
  PostgreSQLComplianceClient,
  postgresComplianceClient,
  type ProvisionContent,
  type ComplianceConstraint,
  type ComplianceData
} from './postgres-compliance-client';

export { ProvisionContent, ComplianceConstraint, ComplianceData };

export class ComplianceDataClient {
  private pythonPath: string;
  private scriptBasePath: string;
  private readonly TIMEOUT_MS = 30000; // 30 second timeout per CLAUDE.md
  private useDirectDatabase: boolean;
  private dbClient?: PostgreSQLComplianceClient;

  constructor() {
    // Feature flag for gradual migration
    this.useDirectDatabase = process.env.COMPLIANCE_ARCHITECTURE === 'direct_database' ||
                            process.env.USE_DIRECT_DATABASE === 'true';

    if (this.useDirectDatabase) {
      console.log('[PRP-A2] ComplianceDataClient using DIRECT DATABASE mode (no subprocess)');
      this.dbClient = postgresComplianceClient;
    } else {
      console.log('[LEGACY] ComplianceDataClient using subprocess mode');
    }

    // Legacy subprocess config (will be removed after migration)
    this.pythonPath = 'python';
    this.scriptBasePath = path.join(process.cwd(), '..');

    console.log(`[PRP-A2] ComplianceDataClient initialized - Mode: ${this.useDirectDatabase ? 'DIRECT DATABASE' : 'SUBPROCESS'}`);
  }

  /**
   * Get comprehensive compliance data for a property
   * Automatically uses direct database or subprocess based on configuration
   */
  async getComplianceData(
    zone: string,
    heritage: boolean,
    constraints: any
  ): Promise<ComplianceData> {
    const startTime = Date.now();
    console.log(`[PRP-A2] Starting compliance data retrieval - Mode: ${this.useDirectDatabase ? 'DIRECT' : 'SUBPROCESS'}`);

    if (this.useDirectDatabase && this.dbClient) {
      // NEW: Direct database implementation
      try {
        const result = await this.dbClient.getComplianceData(zone, heritage, constraints);
        const processingTime = Date.now() - startTime;
        console.log(`[PRP-A2] Direct database retrieval completed in ${processingTime}ms`);
        return result;
      } catch (error) {
        console.error('[PRP-A2] Direct database error:', error);
        throw new Error(`Failed to retrieve compliance data: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    } else {
      // OLD: Subprocess implementation (will be deprecated)
      try {
        const buildingEnvelope = await this.getBuildingEnvelopeConstraints(zone, constraints);
        const environmental = await this.getEnvironmentalConstraints(heritage, constraints);
        const specialProvisions = await this.getSpecialProvisions(constraints);

        const processingTime = Date.now() - startTime;
        console.log(`[LEGACY] Subprocess retrieval completed in ${processingTime}ms`);

        return {
          building_envelope: buildingEnvelope,
          environmental: environmental,
          special_provisions: specialProvisions
        };
      } catch (error) {
        console.error('[LEGACY] Subprocess error:', error);
        throw new Error(`Failed to retrieve compliance data: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }
  }

  /**
   * Get detailed provision content for a specific clause
   * Automatically uses direct database or subprocess based on configuration
   */
  async getProvisionDetails(
    clauseReference: string,
    documentType: 'LEP' | 'DCP' | 'SEPP'
  ): Promise<ProvisionContent[]> {
    const startTime = Date.now();

    if (this.useDirectDatabase && this.dbClient) {
      // NEW: Direct database implementation
      try {
        const result = await this.dbClient.getProvisionDetails(clauseReference, documentType);
        const processingTime = Date.now() - startTime;
        console.log(`[PRP-A2] Direct provision query completed in ${processingTime}ms`);
        return result;
      } catch (error) {
        console.error('[PRP-A2] Direct provision query error:', error);
        return []; // Graceful degradation
      }
    } else {
      // OLD: Subprocess implementation
      return this.getProvisionDetailsSubprocess(clauseReference, documentType);
    }
  }

  /**
   * Get setback provisions
   * Automatically uses direct database or subprocess based on configuration
   */
  private async getSetbackProvisions(zone: string): Promise<ProvisionContent[]> {
    const startTime = Date.now();

    if (this.useDirectDatabase && this.dbClient) {
      // NEW: Direct database implementation
      try {
        const result = await this.dbClient.getSetbackProvisions(zone);
        const processingTime = Date.now() - startTime;
        console.log(`[PRP-A2] Direct setback query completed in ${processingTime}ms`);
        return result;
      } catch (error) {
        console.error('[PRP-A2] Direct setback query error:', error);
        return [];
      }
    } else {
      // OLD: Subprocess implementation
      return this.getSetbackProvisionsSubprocess(zone);
    }
  }

  /**
   * Performance comparison method - useful for testing
   */
  async comparePerformance(zone: string, heritage: boolean, constraints: any) {
    if (!this.dbClient) {
      console.log('Direct database client not initialized');
      return;
    }

    console.log('=== Performance Comparison: Subprocess vs Direct Database ===');

    // Test subprocess
    const subprocessStart = Date.now();
    const originalMode = this.useDirectDatabase;
    this.useDirectDatabase = false;
    await this.getComplianceData(zone, heritage, constraints);
    const subprocessTime = Date.now() - subprocessStart;

    // Test direct database
    const directStart = Date.now();
    this.useDirectDatabase = true;
    await this.getComplianceData(zone, heritage, constraints);
    const directTime = Date.now() - directStart;

    // Restore original mode
    this.useDirectDatabase = originalMode;

    console.log(`Subprocess: ${subprocessTime}ms`);
    console.log(`Direct DB: ${directTime}ms`);
    console.log(`Improvement: ${Math.round((1 - directTime/subprocessTime) * 100)}% faster`);
  }

  // ============= LEGACY SUBPROCESS METHODS (will be deprecated) =============

  private async getProvisionDetailsSubprocess(
    clauseReference: string,
    documentType: 'LEP' | 'DCP' | 'SEPP'
  ): Promise<ProvisionContent[]> {
    const startTime = Date.now();
    console.log(`[LEGACY] Starting subprocess provision retrieval: ${clauseReference} (${documentType})`);

    return new Promise((resolve, reject) => {
      const scriptPath = path.join(this.scriptBasePath, 'get_provision_details.py');

      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => {
          reject(new Error(`Database operation timeout (${this.TIMEOUT_MS}ms limit per CLAUDE.md)`));
        }, this.TIMEOUT_MS);
      });

      const subprocessPromise = new Promise<ProvisionContent[]>((resolve, reject) => {
        const python = spawn(this.pythonPath, [
          scriptPath,
          '--clause', clauseReference,
          '--document-type', documentType,
          '--format', 'json'
        ]);

        let stdout = '';
        let stderr = '';

        python.stdout.on('data', (data) => {
          stdout += data.toString();
        });

        python.stderr.on('data', (data) => {
          stderr += data.toString();
        });

        python.on('close', (code) => {
          const processingTime = Date.now() - startTime;
          console.log(`[LEGACY] Subprocess provision retrieval completed in ${processingTime}ms`);

          if (code === 0) {
            try {
              const result = JSON.parse(stdout);
              resolve(result.provisions || []);
            } catch (parseError) {
              console.error('[LEGACY] Failed to parse provision details:', stdout);
              resolve([]);
            }
          } else {
            console.error('[LEGACY] Provision details script error:', stderr);
            resolve([]);
          }
        });

        python.on('error', (error) => {
          console.error('[LEGACY] Failed to start provision details script:', error);
          reject(error);
        });
      });

      Promise.race([subprocessPromise, timeoutPromise])
        .then(resolve)
        .catch((error) => {
          console.error('[LEGACY] Database operation failed:', error);
          resolve([]);
        });
    });
  }

  private async getSetbackProvisionsSubprocess(zone: string): Promise<ProvisionContent[]> {
    const startTime = Date.now();
    console.log(`[LEGACY] Starting subprocess setback retrieval for zone: ${zone}`);

    return new Promise((resolve, reject) => {
      const scriptPath = path.join(this.scriptBasePath, 'get_setback_provisions.py');

      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => {
          reject(new Error(`Setback query timeout (${this.TIMEOUT_MS}ms limit per CLAUDE.md)`));
        }, this.TIMEOUT_MS);
      });

      const subprocessPromise = new Promise<ProvisionContent[]>((resolve, reject) => {
        const python = spawn(this.pythonPath, [
          scriptPath,
          '--zone', zone,
          '--format', 'json'
        ]);

        let stdout = '';
        let stderr = '';

        python.stdout.on('data', (data) => {
          stdout += data.toString();
        });

        python.stderr.on('data', (data) => {
          stderr += data.toString();
        });

        python.on('close', (code) => {
          const processingTime = Date.now() - startTime;
          console.log(`[LEGACY] Subprocess setback retrieval completed in ${processingTime}ms`);

          if (code === 0) {
            try {
              const result = JSON.parse(stdout);
              resolve(result.provisions || []);
            } catch (parseError) {
              console.error('[LEGACY] Failed to parse setback provisions:', stdout);
              resolve([]);
            }
          } else {
            console.error('[LEGACY] Setback provisions script error:', stderr);
            resolve([]);
          }
        });

        python.on('error', (error) => {
          console.error('[LEGACY] Failed to start setback provisions script:', error);
          reject(error);
        });
      });

      Promise.race([subprocessPromise, timeoutPromise])
        .then(resolve)
        .catch((error) => {
          console.error('[LEGACY] Setback operation failed:', error);
          resolve([]);
        });
    });
  }

  private async getBuildingEnvelopeConstraints(
    zone: string,
    constraints: any
  ): Promise<ComplianceConstraint[]> {
    const envelopeConstraints: ComplianceConstraint[] = [];

    if (constraints.maxHeight) {
      const heightProvisions = await this.getProvisionDetails('Clause 4.3', 'LEP');
      envelopeConstraints.push({
        type: 'height',
        value: constraints.maxHeight,
        unit: 'm',
        source: {
          clause: 'Clause 4.3',
          document: 'Inner West Local Environmental Plan 2022',
          authority_level: 'LEP'
        },
        provisions: heightProvisions
      });
    }

    if (constraints.maxFsr) {
      const fsrProvisions = await this.getProvisionDetails('Clause 4.4', 'LEP');
      envelopeConstraints.push({
        type: 'fsr',
        value: constraints.maxFsr,
        unit: ':1',
        source: {
          clause: 'Clause 4.4',
          document: 'Inner West Local Environmental Plan 2022',
          authority_level: 'LEP'
        },
        provisions: fsrProvisions
      });
    }

    const setbackProvisions = await this.getSetbackProvisions(zone);
    if (setbackProvisions.length > 0) {
      envelopeConstraints.push({
        type: 'setback',
        value: 'Various',
        source: {
          clause: 'DCP Setback Requirements',
          document: 'Inner West DCP',
          authority_level: 'DCP'
        },
        provisions: setbackProvisions
      });
    }

    return envelopeConstraints;
  }

  private async getEnvironmentalConstraints(
    heritage: boolean,
    constraints: any
  ): Promise<ComplianceConstraint[]> {
    const environmentalConstraints: ComplianceConstraint[] = [];

    if (heritage) {
      const heritageProvisions = await this.getProvisionDetails('Clause 5.10', 'LEP');
      environmentalConstraints.push({
        type: 'heritage',
        value: 'Heritage Item',
        source: {
          clause: 'Clause 5.10',
          document: 'Inner West Local Environmental Plan 2022',
          authority_level: 'LEP'
        },
        provisions: heritageProvisions
      });
    }

    return environmentalConstraints;
  }

  private async getSpecialProvisions(constraints: any): Promise<ComplianceConstraint[]> {
    const specialConstraints: ComplianceConstraint[] = [];

    if (constraints.basixWater) {
      specialConstraints.push({
        type: 'special',
        value: constraints.basixWater,
        source: {
          clause: 'SEPP Sustainable Buildings',
          document: 'State Environmental Planning Policy (Sustainable Buildings) 2022',
          authority_level: 'SEPP'
        }
      });
    }

    return specialConstraints;
  }
}

// Export for backward compatibility
export default ComplianceDataClient;