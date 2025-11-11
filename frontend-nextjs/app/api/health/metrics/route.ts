/**
 * PRP-A3: Prometheus Metrics Endpoint
 * Cloud-native metrics for monitoring and alerting
 */

import { NextRequest, NextResponse } from 'next/server';
import { postgresComplianceClient } from '@/lib/database/postgres-compliance-client';
import { getCounterValues } from '@/lib/metrics/counters';

interface MetricSample {
  name: string;
  type: 'counter' | 'gauge' | 'histogram' | 'summary';
  help: string;
  value: number;
  labels?: Record<string, string>;
  timestamp?: number;
}

const metricsRegistry = new Map<string, MetricSample>();
const startTime = Date.now();

/**
 * Prometheus metrics endpoint
 * GET /api/health/metrics
 */
export async function GET(request: NextRequest) {
  try {
    const metrics = await collectMetrics();
    const prometheusFormat = formatPrometheusMetrics(metrics);

    return new NextResponse(prometheusFormat, {
      status: 200,
      headers: {
        'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'
      }
    });

  } catch (error) {
    console.error('[PRP-A3] Metrics collection error:', error);

    return NextResponse.json({
      error: 'Failed to collect metrics',
      message: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

/**
 * Collect all application metrics
 */
async function collectMetrics(): Promise<MetricSample[]> {
  const metrics: MetricSample[] = [];
  const now = Date.now();

  // Application info
  metrics.push({
    name: 'app_info',
    type: 'gauge',
    help: 'Application information',
    value: 1,
    labels: {
      version: process.env.APP_VERSION || '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      architecture: process.env.COMPLIANCE_ARCHITECTURE || 'direct_database'
    }
  });

  // Uptime
  metrics.push({
    name: 'app_uptime_seconds',
    type: 'gauge',
    help: 'Application uptime in seconds',
    value: Math.floor((now - startTime) / 1000)
  });

  // Process metrics
  const processMetrics = getProcessMetrics();
  metrics.push(...processMetrics);

  // Database metrics (PRP-A2 compatible)
  const dbMetrics = await getDatabaseMetrics();
  metrics.push(...dbMetrics);

  // HTTP metrics
  const httpMetrics = getHTTPMetrics();
  metrics.push(...httpMetrics);

  // Feature flags
  const featureMetrics = getFeatureMetrics();
  metrics.push(...featureMetrics);

  return metrics;
}

/**
 * Process-level metrics
 */
function getProcessMetrics(): MetricSample[] {
  const memory = process.memoryUsage();
  const usage = process.cpuUsage();

  return [
    {
      name: 'process_memory_bytes',
      type: 'gauge',
      help: 'Process memory usage in bytes',
      value: memory.rss,
      labels: { type: 'rss' }
    },
    {
      name: 'process_memory_bytes',
      type: 'gauge',
      help: 'Process memory usage in bytes',
      value: memory.heapUsed,
      labels: { type: 'heap_used' }
    },
    {
      name: 'process_memory_bytes',
      type: 'gauge',
      help: 'Process memory usage in bytes',
      value: memory.heapTotal,
      labels: { type: 'heap_total' }
    },
    {
      name: 'process_memory_bytes',
      type: 'gauge',
      help: 'Process memory usage in bytes',
      value: memory.external,
      labels: { type: 'external' }
    },
    {
      name: 'process_cpu_user_seconds_total',
      type: 'counter',
      help: 'Total user CPU time spent in seconds',
      value: usage.user / 1000000 // Convert microseconds to seconds
    },
    {
      name: 'process_cpu_system_seconds_total',
      type: 'counter',
      help: 'Total system CPU time spent in seconds',
      value: usage.system / 1000000
    },
    {
      name: 'nodejs_version_info',
      type: 'gauge',
      help: 'Node.js version information',
      value: 1,
      labels: {
        version: process.version,
        major: process.version.split('.')[0]?.replace('v', '') || '0'
      }
    }
  ];
}

/**
 * Database metrics (PRP-A2 direct database)
 */
async function getDatabaseMetrics(): Promise<MetricSample[]> {
  const metrics: MetricSample[] = [];

  try {
    // Connection pool stats
    const poolStats = postgresComplianceClient.getPoolStats();

    metrics.push(
      {
        name: 'database_connections_total',
        type: 'gauge',
        help: 'Total database connections in pool',
        value: poolStats.total
      },
      {
        name: 'database_connections_idle',
        type: 'gauge',
        help: 'Idle database connections',
        value: poolStats.idle
      },
      {
        name: 'database_connections_waiting',
        type: 'gauge',
        help: 'Waiting database connection requests',
        value: poolStats.waiting
      },
      {
        name: 'database_queries_total',
        type: 'counter',
        help: 'Total database queries executed',
        value: getCounterValues().databaseQueries
      },
      {
        name: 'database_errors_total',
        type: 'counter',
        help: 'Total database errors',
        value: getCounterValues().databaseErrors
      }
    );

    // Health check
    const healthResult = await postgresComplianceClient.healthCheck();
    metrics.push({
      name: 'database_healthy',
      type: 'gauge',
      help: 'Database health status (1 = healthy, 0 = unhealthy)',
      value: healthResult.healthy ? 1 : 0
    });

    // Query performance test
    const startTime = Date.now();
    try {
      await postgresComplianceClient.getProvisionDetails('Clause 4.3', 'LEP');
      const queryDuration = Date.now() - startTime;

      metrics.push({
        name: 'database_query_duration_milliseconds',
        type: 'gauge',
        help: 'Sample database query duration',
        value: queryDuration,
        labels: { query_type: 'provision_details' }
      });

    } catch (error) {
      metrics.push({
        name: 'database_query_duration_milliseconds',
        type: 'gauge',
        help: 'Sample database query duration',
        value: -1,
        labels: { query_type: 'provision_details', status: 'error' }
      });
    }

  } catch (error) {
    console.error('[PRP-A3] Database metrics error:', error);

    metrics.push({
      name: 'database_healthy',
      type: 'gauge',
      help: 'Database health status (1 = healthy, 0 = unhealthy)',
      value: 0
    });
  }

  return metrics;
}

/**
 * HTTP request metrics
 */
function getHTTPMetrics(): MetricSample[] {
  const counters = getCounterValues();

  return [
    {
      name: 'http_requests_total',
      type: 'counter',
      help: 'Total HTTP requests',
      value: counters.requestTotal
    },
    {
      name: 'http_request_errors_total',
      type: 'counter',
      help: 'Total HTTP request errors',
      value: counters.requestErrors
    },
    {
      name: 'http_request_success_rate',
      type: 'gauge',
      help: 'HTTP request success rate',
      value: counters.requestTotal > 0 ? (counters.requestTotal - counters.requestErrors) / counters.requestTotal : 1
    }
  ];
}

/**
 * Feature flag metrics
 */
function getFeatureMetrics(): MetricSample[] {
  return [
    {
      name: 'feature_direct_database_enabled',
      type: 'gauge',
      help: 'Direct database feature enabled (PRP-A2)',
      value: process.env.USE_DIRECT_DATABASE === 'true' ? 1 : 0
    },
    {
      name: 'feature_debug_mode_enabled',
      type: 'gauge',
      help: 'Debug mode enabled',
      value: process.env.DEBUG_MODE === 'true' ? 1 : 0
    },
    {
      name: 'feature_performance_mode_enabled',
      type: 'gauge',
      help: 'Performance mode enabled',
      value: process.env.PERFORMANCE_MODE === 'true' ? 1 : 0
    }
  ];
}

/**
 * Format metrics in Prometheus exposition format
 */
function formatPrometheusMetrics(metrics: MetricSample[]): string {
  const lines: string[] = [];

  // Group metrics by name
  const groupedMetrics = new Map<string, MetricSample[]>();
  for (const metric of metrics) {
    if (!groupedMetrics.has(metric.name)) {
      groupedMetrics.set(metric.name, []);
    }
    groupedMetrics.get(metric.name)!.push(metric);
  }

  // Format each metric group
  for (const [name, metricGroup] of groupedMetrics) {
    const firstMetric = metricGroup[0];

    // Add help comment
    lines.push(`# HELP ${name} ${firstMetric.help}`);

    // Add type comment
    lines.push(`# TYPE ${name} ${firstMetric.type}`);

    // Add metric samples
    for (const metric of metricGroup) {
      let line = metric.name;

      // Add labels if present
      if (metric.labels && Object.keys(metric.labels).length > 0) {
        const labelPairs = Object.entries(metric.labels)
          .map(([key, value]) => `${key}="${escapeLabel(value)}"`)
          .join(',');
        line += `{${labelPairs}}`;
      }

      // Add value
      line += ` ${metric.value}`;

      // Add timestamp if present
      if (metric.timestamp) {
        line += ` ${metric.timestamp}`;
      }

      lines.push(line);
    }

    lines.push(''); // Empty line between metric groups
  }

  return lines.join('\n');
}

/**
 * Escape label values for Prometheus format
 */
function escapeLabel(value: string): string {
  return value
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r')
    .replace(/\t/g, '\\t');
}