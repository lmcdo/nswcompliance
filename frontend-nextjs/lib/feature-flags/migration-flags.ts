/**
 * Feature Flags for PostgreSQL Migration
 * Enables safe rollback and A/B testing during migration
 */

export interface MigrationFlags {
  usePostgreSQLProvisions: boolean;
  usePostgreSQLLiveCheck: boolean;
  usePostgreSQLVersions: boolean;
  usePostgreSQLTODRates: boolean;
  usePostgreSQLVersionCompliance: boolean;
  enableABTesting: boolean;
  abTestingPercentage: number;
}

/**
 * Get migration feature flags from environment variables
 */
export function getMigrationFlags(): MigrationFlags {
  return {
    usePostgreSQLProvisions: process.env.USE_POSTGRESQL_PROVISIONS === 'true',
    usePostgreSQLLiveCheck: process.env.USE_POSTGRESQL_LIVE_CHECK === 'true',
    usePostgreSQLVersions: process.env.USE_POSTGRESQL_VERSIONS === 'true',
    usePostgreSQLTODRates: process.env.USE_POSTGRESQL_TOD_RATES === 'true',
    usePostgreSQLVersionCompliance: process.env.USE_POSTGRESQL_VERSION_COMPLIANCE === 'true',
    enableABTesting: process.env.ENABLE_MIGRATION_AB_TESTING === 'true',
    abTestingPercentage: parseInt(process.env.AB_TESTING_PERCENTAGE || '50')
  };
}

/**
 * Determine if request should use new PostgreSQL implementation
 */
export function shouldUsePostgreSQL(endpoint: string, requestId?: string): boolean {
  const flags = getMigrationFlags();

  // If A/B testing is disabled, use feature flags directly
  if (!flags.enableABTesting) {
    switch (endpoint) {
      case 'provisions':
        return flags.usePostgreSQLProvisions;
      case 'live-check':
        return flags.usePostgreSQLLiveCheck;
      case 'versions':
        return flags.usePostgreSQLVersions;
      case 'tod-rates':
        return flags.usePostgreSQLTODRates;
      case 'version-compliance':
        return flags.usePostgreSQLVersionCompliance;
      default:
        return false;
    }
  }

  // A/B testing logic
  const hash = requestId ? simpleHash(requestId) : Math.random();
  const usePostgreSQL = (hash * 100) < flags.abTestingPercentage;

  console.log(`[A/B Testing] ${endpoint}: ${usePostgreSQL ? 'PostgreSQL' : 'Python subprocess'} (${flags.abTestingPercentage}% split)`);

  return usePostgreSQL;
}

/**
 * Simple hash function for consistent A/B testing
 */
function simpleHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash) / Math.pow(2, 31);
}

/**
 * Log migration performance metrics
 */
export function logMigrationMetrics(
  endpoint: string,
  implementation: 'postgresql' | 'subprocess',
  responseTime: number,
  success: boolean,
  errorDetails?: string
) {
  const metrics = {
    endpoint,
    implementation,
    responseTime,
    success,
    timestamp: new Date().toISOString(),
    errorDetails
  };

  console.log(`[Migration Metrics]`, JSON.stringify(metrics));

  // In production, this would send to monitoring service
  // Example: sendToDatadog(metrics) or sendToCloudWatch(metrics)
}