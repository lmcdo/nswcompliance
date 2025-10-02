/**
 * PRP-A3: Enterprise Health Check API
 * Comprehensive health monitoring for cloud deployment
 *
 * Implements liveness, readiness, and detailed component checks
 */

import { NextRequest, NextResponse } from 'next/server';
import { postgresComplianceClient } from '@/lib/database/postgres-compliance-client';

interface HealthCheck {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  environment: string;
  uptime: number;
  checks: {
    [key: string]: {
      status: 'pass' | 'fail' | 'warn';
      duration?: number;
      message?: string;
      details?: any;
    };
  };
  performance: {
    responseTime: number;
    memory: {
      used: number;
      total: number;
      percentage: number;
    };
    cpu?: {
      usage: number;
    };
  };
}

const startTime = Date.now();

/**
 * Main health check endpoint
 * GET /api/health - Full health check
 * GET /api/health?type=liveness - Liveness probe
 * GET /api/health?type=readiness - Readiness probe
 */
export async function GET(request: NextRequest) {
  const startCheck = Date.now();
  const searchParams = request.nextUrl.searchParams;
  const checkType = searchParams.get('type') || 'full';

  try {
    const health: HealthCheck = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      version: process.env.APP_VERSION || '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      uptime: Math.floor((Date.now() - startTime) / 1000),
      checks: {},
      performance: {
        responseTime: 0,
        memory: getMemoryUsage()
      }
    };

    // Liveness check - basic application health
    if (checkType === 'liveness' || checkType === 'full') {
      health.checks.liveness = await checkLiveness();
    }

    // Readiness check - external dependencies
    if (checkType === 'readiness' || checkType === 'full') {
      const readinessChecks = await Promise.allSettled([
        checkDatabase(),
        checkEnvironmentVariables(),
        checkFileSystem()
      ]);

      health.checks.database = readinessChecks[0].status === 'fulfilled' ?
        readinessChecks[0].value : { status: 'fail', message: 'Database check failed' };

      health.checks.environment = readinessChecks[1].status === 'fulfilled' ?
        readinessChecks[1].value : { status: 'fail', message: 'Environment check failed' };

      health.checks.filesystem = readinessChecks[2].status === 'fulfilled' ?
        readinessChecks[2].value : { status: 'fail', message: 'Filesystem check failed' };
    }

    // Full check - include optional services
    if (checkType === 'full') {
      const optionalChecks = await Promise.allSettled([
        checkExternalAPIs(),
        checkPerformanceMetrics()
      ]);

      health.checks.external_apis = optionalChecks[0].status === 'fulfilled' ?
        optionalChecks[0].value : { status: 'warn', message: 'External API check failed' };

      health.checks.performance = optionalChecks[1].status === 'fulfilled' ?
        optionalChecks[1].value : { status: 'warn', message: 'Performance check failed' };
    }

    // Calculate overall status
    const checkStatuses = Object.values(health.checks).map(check => check.status);
    const hasFailures = checkStatuses.includes('fail');
    const hasWarnings = checkStatuses.includes('warn');

    if (hasFailures) {
      health.status = 'unhealthy';
    } else if (hasWarnings) {
      health.status = 'degraded';
    } else {
      health.status = 'healthy';
    }

    // Calculate response time
    health.performance.responseTime = Date.now() - startCheck;

    // Return appropriate HTTP status
    const httpStatus = health.status === 'healthy' ? 200 :
                      health.status === 'degraded' ? 200 : 503;

    return NextResponse.json(health, { status: httpStatus });

  } catch (error) {
    console.error('[PRP-A3] Health check error:', error);

    const errorHealth: HealthCheck = {
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      version: process.env.APP_VERSION || '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      uptime: Math.floor((Date.now() - startTime) / 1000),
      checks: {
        error: {
          status: 'fail',
          message: error instanceof Error ? error.message : 'Unknown error'
        }
      },
      performance: {
        responseTime: Date.now() - startCheck,
        memory: getMemoryUsage()
      }
    };

    return NextResponse.json(errorHealth, { status: 503 });
  }
}

/**
 * Liveness check - is the application running?
 */
async function checkLiveness() {
  const startTime = Date.now();

  try {
    // Basic application health
    const isHealthy = process.pid > 0 &&
                     process.uptime() > 0 &&
                     typeof global !== 'undefined';

    return {
      status: isHealthy ? 'pass' as const : 'fail' as const,
      duration: Date.now() - startTime,
      message: isHealthy ? 'Application is running' : 'Application is not healthy',
      details: {
        pid: process.pid,
        uptime: process.uptime(),
        nodeVersion: process.version
      }
    };

  } catch (error) {
    return {
      status: 'fail' as const,
      duration: Date.now() - startTime,
      message: error instanceof Error ? error.message : 'Liveness check failed'
    };
  }
}

/**
 * Database connectivity check (PRP-A2 compatible)
 */
async function checkDatabase() {
  const startTime = Date.now();

  try {
    // Use direct database client from PRP-A2
    const healthResult = await postgresComplianceClient.healthCheck();
    const poolStats = postgresComplianceClient.getPoolStats();

    if (healthResult.healthy) {
      return {
        status: 'pass' as const,
        duration: Date.now() - startTime,
        message: 'Database connection healthy',
        details: {
          connections: healthResult.connections,
          pool: poolStats,
          architecture: 'direct_database' // PRP-A2
        }
      };
    } else {
      return {
        status: 'fail' as const,
        duration: Date.now() - startTime,
        message: `Database unhealthy: ${healthResult.error}`,
        details: {
          error: healthResult.error,
          connections: healthResult.connections
        }
      };
    }

  } catch (error) {
    return {
      status: 'fail' as const,
      duration: Date.now() - startTime,
      message: `Database check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      details: {
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    };
  }
}

/**
 * Environment variables check
 */
async function checkEnvironmentVariables() {
  const startTime = Date.now();

  try {
    const requiredVars = [
      'NODE_ENV',
      'DB_HOST',
      'DB_NAME',
      'DB_USER'
    ];

    const missingVars = requiredVars.filter(varName => !process.env[varName]);
    const isHealthy = missingVars.length === 0;

    return {
      status: isHealthy ? 'pass' as const : 'warn' as const,
      duration: Date.now() - startTime,
      message: isHealthy ?
        'All required environment variables present' :
        `Missing variables: ${missingVars.join(', ')}`,
      details: {
        required: requiredVars.length,
        present: requiredVars.length - missingVars.length,
        missing: missingVars,
        compliance_architecture: process.env.COMPLIANCE_ARCHITECTURE || 'direct_database'
      }
    };

  } catch (error) {
    return {
      status: 'fail' as const,
      duration: Date.now() - startTime,
      message: error instanceof Error ? error.message : 'Environment check failed'
    };
  }
}

/**
 * File system check
 */
async function checkFileSystem() {
  const startTime = Date.now();

  try {
    const fs = require('fs').promises;
    const path = require('path');

    // Check if we can write to temp directory
    const tempDir = process.cwd();
    const testFile = path.join(tempDir, '.health-check');

    await fs.writeFile(testFile, 'health-check');
    await fs.unlink(testFile);

    return {
      status: 'pass' as const,
      duration: Date.now() - startTime,
      message: 'File system is writable',
      details: {
        cwd: process.cwd(),
        writable: true
      }
    };

  } catch (error) {
    return {
      status: 'fail' as const,
      duration: Date.now() - startTime,
      message: `File system check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      details: {
        cwd: process.cwd(),
        writable: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    };
  }
}

/**
 * External APIs check
 */
async function checkExternalAPIs() {
  const startTime = Date.now();

  try {
    const checks = [];

    // NSW Planning Portal API
    if (process.env.NSW_PLANNING_API_URL) {
      checks.push(checkAPI('NSW Planning', process.env.NSW_PLANNING_API_URL, 10000));
    }

    // Google Maps API
    if (process.env.GOOGLE_MAPS_API_KEY) {
      checks.push(checkAPI('Google Maps', 'https://maps.googleapis.com/maps/api/js', 5000));
    }

    const results = await Promise.allSettled(checks);
    const successful = results.filter(r => r.status === 'fulfilled').length;
    const total = results.length;

    return {
      status: successful === total ? 'pass' as const :
              successful > 0 ? 'warn' as const : 'fail' as const,
      duration: Date.now() - startTime,
      message: `External APIs: ${successful}/${total} healthy`,
      details: {
        total,
        successful,
        results: results.map((r, i) => ({
          api: ['NSW Planning', 'Google Maps'][i],
          status: r.status,
          value: r.status === 'fulfilled' ? r.value : undefined,
          reason: r.status === 'rejected' ? r.reason?.message : undefined
        }))
      }
    };

  } catch (error) {
    return {
      status: 'warn' as const,
      duration: Date.now() - startTime,
      message: 'External API check failed',
      details: {
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    };
  }
}

/**
 * Check individual API endpoint
 */
async function checkAPI(name: string, url: string, timeout: number) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      method: 'HEAD',
      signal: controller.signal,
      headers: {
        'User-Agent': 'NSW-Compliance-Engine/1.0 Health-Check'
      }
    });

    clearTimeout(timeoutId);
    return {
      name,
      status: response.ok,
      statusCode: response.status,
      responseTime: Date.now()
    };

  } catch (error) {
    clearTimeout(timeoutId);
    throw new Error(`${name} API check failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Performance metrics check
 */
async function checkPerformanceMetrics() {
  const startTime = Date.now();

  try {
    const memory = getMemoryUsage();
    const memoryThreshold = 0.9; // 90% memory usage threshold

    const isHealthy = memory.percentage < memoryThreshold;

    return {
      status: isHealthy ? 'pass' as const : 'warn' as const,
      duration: Date.now() - startTime,
      message: isHealthy ?
        'Performance metrics within limits' :
        `High memory usage: ${Math.round(memory.percentage * 100)}%`,
      details: {
        memory,
        thresholds: {
          memory: memoryThreshold
        },
        uptime: process.uptime()
      }
    };

  } catch (error) {
    return {
      status: 'warn' as const,
      duration: Date.now() - startTime,
      message: 'Performance metrics check failed',
      details: {
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    };
  }
}

/**
 * Get memory usage information
 */
function getMemoryUsage() {
  const usage = process.memoryUsage();
  const total = usage.heapTotal + usage.external;
  const used = usage.heapUsed + usage.external;

  return {
    used: Math.round(used / 1024 / 1024), // MB
    total: Math.round(total / 1024 / 1024), // MB
    percentage: used / total,
    heap: {
      used: Math.round(usage.heapUsed / 1024 / 1024),
      total: Math.round(usage.heapTotal / 1024 / 1024)
    },
    external: Math.round(usage.external / 1024 / 1024),
    rss: Math.round(usage.rss / 1024 / 1024)
  };
}