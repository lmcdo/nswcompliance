/**
 * PostgreSQL Direct Compliance Client - PRP-A2 Architecture Refactor
 * Replaces subprocess spawning with native TypeScript database integration
 *
 * This implementation eliminates all Python subprocess calls for compliance data
 * providing massive performance improvements and cloud readiness
 */

import { Pool, PoolClient } from 'pg';

// Type definitions for compliance data
export interface ProvisionContent {
  id: number;
  ref_number: string;
  section_header: string;
  provision_text: string;
  document_id: string;
  provision_type: string;
  zone?: string;
  development_type?: string;
  page_number?: number;
}

export interface ComplianceConstraint {
  type: 'height' | 'fsr' | 'setback' | 'heritage' | 'environmental' | 'special';
  value: string | number;
  unit?: string;
  source: {
    clause: string;
    document: string;
    authority_level: 'LEP' | 'DCP' | 'SEPP';
    amendment?: string;
    effective_date?: string;
  };
  provisions?: ProvisionContent[];
}

export interface ComplianceData {
  building_envelope: ComplianceConstraint[];
  environmental: ComplianceConstraint[];
  special_provisions: ComplianceConstraint[];
}

export interface DatabaseConfig {
  host: string;
  database: string;
  user: string;
  password: string;
  port: number;
  max: number;
  idleTimeoutMillis: number;
  connectionTimeoutMillis: number;
}

export class PostgreSQLComplianceClient {
  private pool: Pool;
  private static instance: PostgreSQLComplianceClient;
  private readonly TIMEOUT_MS = 30000; // 30 seconds per CLAUDE.md

  constructor(config?: DatabaseConfig) {
    const defaultConfig = {
      host: process.env.DB_HOST || process.env.DATABASE_HOST || '127.0.0.1',
      database: process.env.DB_NAME || process.env.DATABASE_NAME || 'nsw_planning',
      user: process.env.DB_USER || process.env.DATABASE_USER || 'postgres',
      password: process.env.DB_PASSWORD || process.env.DATABASE_PASSWORD || '',
      port: parseInt(process.env.DB_PORT || process.env.DATABASE_PORT || '5432'),
      max: 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000,
    };

    const finalConfig = config || defaultConfig;

    this.pool = new Pool({
      ...finalConfig,
      ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : undefined,
      statement_timeout: this.TIMEOUT_MS,
      query_timeout: this.TIMEOUT_MS,
    });

    // Pool error handling
    this.pool.on('error', (err) => {
      console.error('[PRP-A2] PostgreSQL pool error:', err);
    });

    // Connection monitoring
    this.pool.on('connect', () => {
      console.log('[PRP-A2] PostgreSQL client connected - Direct database (no subprocess)');
    });

    console.log('[PRP-A2] PostgreSQL compliance client initialized for direct database access');
  }

  static getInstance(config?: DatabaseConfig): PostgreSQLComplianceClient {
    if (!PostgreSQLComplianceClient.instance) {
      PostgreSQLComplianceClient.instance = new PostgreSQLComplianceClient(config);
    }
    return PostgreSQLComplianceClient.instance;
  }

  /**
   * Get detailed provision content - REPLACES Python subprocess
   */
  async getProvisionDetails(
    clauseReference: string,
    documentType: 'LEP' | 'DCP' | 'SEPP'
  ): Promise<ProvisionContent[]> {
    const startTime = Date.now();
    let client: PoolClient | null = null;

    try {
      client = await this.pool.connect();

      // Document patterns (matching Python logic)
      const docPattern = documentType === 'LEP' ? '%Local_Environmental_Plan%' :
                        documentType === 'DCP' ? '%DCP%' :
                        documentType === 'SEPP' ? '%Environmental_Planning_Policy%' : '%';

      const query = `
        SELECT
          id,
          ref_number,
          section_header,
          provision_text,
          document_id,
          provision_type,
          zone,
          development_type,
          page_number
        FROM regulatory_provisions_canonical
        WHERE (
          ref_number ILIKE $1
          OR ref_number ILIKE $2
          OR provision_text ILIKE $3
        )
        AND document_id ILIKE $4
        AND provision_text IS NOT NULL
        AND LENGTH(provision_text) > 50
        ORDER BY
          CASE
            WHEN ref_number ILIKE $5 THEN 1
            WHEN ref_number ILIKE $6 THEN 2
            ELSE 3
          END,
          LENGTH(provision_text) DESC
        LIMIT 10
      `;

      const params = [
        `%${clauseReference}%`,
        `%${clauseReference.replace("Clause ", "")}%`,
        `%${clauseReference}%`,
        docPattern,
        clauseReference,
        clauseReference.replace("Clause ", "")
      ];

      const result = await client.query(query, params);

      const processingTime = Date.now() - startTime;
      console.log(`[PRP-A2] Provision query completed in ${processingTime}ms (direct DB, no subprocess)`);

      return result.rows as ProvisionContent[];

    } catch (error) {
      console.error('[PRP-A2] Provision query error:', error);

      // Graceful degradation
      return [];
    } finally {
      if (client) client.release();
    }
  }

  /**
   * Get setback provisions - REPLACES Python subprocess
   */
  async getSetbackProvisions(zone: string): Promise<ProvisionContent[]> {
    const startTime = Date.now();
    let client: PoolClient | null = null;

    try {
      client = await this.pool.connect();

      // Build dynamic query for setback terms
      const setbackTerms = ['setback', 'front yard', 'side yard', 'rear yard', 'building line'];
      const setbackConditions = setbackTerms.map(() => 'provision_text ILIKE ?').join(' OR ');

      const query = `
        SELECT
          id,
          ref_number,
          section_header,
          provision_text,
          document_id,
          provision_type,
          zone,
          development_type,
          page_number
        FROM regulatory_provisions_canonical
        WHERE (${setbackTerms.map(() => 'provision_text ILIKE ?').join(' OR ')})
        AND (zone ILIKE ? OR provision_text ILIKE ?)
        AND document_id ILIKE ?
        AND provision_text IS NOT NULL
        AND LENGTH(provision_text) > 30
        ORDER BY
          CASE
            WHEN provision_text ILIKE '%front%setback%' THEN 1
            WHEN provision_text ILIKE '%side%setback%' THEN 2
            WHEN provision_text ILIKE '%rear%setback%' THEN 3
            WHEN provision_text ILIKE '%setback%' THEN 4
            ELSE 5
          END,
          LENGTH(provision_text) DESC
        LIMIT 15
      `;

      // Build parameters array
      const params: string[] = [];
      setbackTerms.forEach(term => params.push(`%${term}%`));
      params.push(`%${zone}%`, `%${zone}%`, '%DCP%');

      // Use numbered parameters for PostgreSQL
      let paramIndex = 1;
      const numberedQuery = query.replace(/\?/g, () => `$${paramIndex++}`);

      const result = await client.query(numberedQuery, params);

      const processingTime = Date.now() - startTime;
      console.log(`[PRP-A2] Setback query completed in ${processingTime}ms (direct DB)`);

      return result.rows as ProvisionContent[];

    } catch (error) {
      console.error('[PRP-A2] Setback query error:', error);
      return [];
    } finally {
      if (client) client.release();
    }
  }

  /**
   * Get comprehensive compliance data - MAIN METHOD
   * This replaces ALL subprocess calls with direct database queries
   */
  async getComplianceData(
    zone: string,
    heritage: boolean,
    constraints: any
  ): Promise<ComplianceData> {
    const startTime = Date.now();

    try {
      console.log(`[PRP-A2] Starting direct database compliance retrieval for zone: ${zone}`);

      // Parallel execution for maximum performance
      const promises: Promise<any>[] = [];

      // Height provisions
      if (constraints?.maxHeight) {
        promises.push(this.getProvisionDetails('Clause 4.3', 'LEP'));
      } else {
        promises.push(Promise.resolve([]));
      }

      // FSR provisions
      if (constraints?.maxFsr) {
        promises.push(this.getProvisionDetails('Clause 4.4', 'LEP'));
      } else {
        promises.push(Promise.resolve([]));
      }

      // Setback provisions
      promises.push(this.getSetbackProvisions(zone));

      // Heritage provisions
      if (heritage) {
        promises.push(this.getProvisionDetails('Clause 5.10', 'LEP'));
      } else {
        promises.push(Promise.resolve([]));
      }

      // Execute all queries in parallel
      const [heightProvisions, fsrProvisions, setbackProvisions, heritageProvisions] = await Promise.all(promises);

      // Build response structure
      const buildingEnvelope: ComplianceConstraint[] = [];

      if (constraints?.maxHeight) {
        buildingEnvelope.push({
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

      if (constraints?.maxFsr) {
        buildingEnvelope.push({
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

      if (setbackProvisions.length > 0) {
        buildingEnvelope.push({
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

      // Environmental constraints
      const environmental: ComplianceConstraint[] = [];

      if (heritage) {
        environmental.push({
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

      // Special provisions
      const specialProvisions: ComplianceConstraint[] = [];

      if (constraints?.basixWater) {
        specialProvisions.push({
          type: 'special',
          value: constraints.basixWater,
          source: {
            clause: 'SEPP Sustainable Buildings',
            document: 'State Environmental Planning Policy (Sustainable Buildings) 2022',
            authority_level: 'SEPP'
          }
        });
      }

      const processingTime = Date.now() - startTime;
      console.log(`[PRP-A2] Compliance data retrieved in ${processingTime}ms (vs ~5000ms subprocess)`);

      return {
        building_envelope: buildingEnvelope,
        environmental: environmental,
        special_provisions: specialProvisions
      };

    } catch (error) {
      console.error('[PRP-A2] Compliance data error:', error);

      // Return empty structure on error (graceful degradation)
      return {
        building_envelope: [],
        environmental: [],
        special_provisions: []
      };
    }
  }

  /**
   * Health check for connection pool
   */
  async healthCheck(): Promise<{ healthy: boolean; connections: number; error?: string }> {
    try {
      const client = await this.pool.connect();
      const result = await client.query('SELECT 1 as check');
      client.release();

      return {
        healthy: result.rows[0].check === 1,
        connections: this.pool.totalCount
      };
    } catch (error) {
      return {
        healthy: false,
        connections: 0,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Get pool statistics
   */
  getPoolStats() {
    return {
      total: this.pool.totalCount,
      idle: this.pool.idleCount,
      waiting: this.pool.waitingCount
    };
  }

  /**
   * Close pool connections
   */
  async close() {
    await this.pool.end();
    console.log('[PRP-A2] PostgreSQL pool closed');
  }
}

// Export singleton instance
export const postgresComplianceClient = PostgreSQLComplianceClient.getInstance();