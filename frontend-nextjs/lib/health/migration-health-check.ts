export interface HealthCheckResult {
 name: string;
 status: 'healthy' | 'degraded' | 'unhealthy';
 timestamp: string;
 duration: number;
 message?: string;
 details?: Record<string, any>;
}

export interface SystemHealth {
 overall: 'healthy' | 'degraded' | 'unhealthy';
 timestamp: string;
 checks: HealthCheckResult[];
 summary: {
 healthy: number;
 degraded: number;
 unhealthy: number;
 total: number;
 };
}

export interface HealthCheckConfig {
 name: string;
 enabled: boolean;
 timeout: number;
 interval: number;
 retries: number;
 thresholds?: {
 warning: number;
 critical: number;
 };
}

export class MigrationHealthCheck {
 private checks: Map<string, HealthCheckConfig> = new Map();
 private intervals: Map<string, NodeJS.Timeout> = new Map();
 private lastResults: Map<string, HealthCheckResult> = new Map();
 private listeners: Map<string, Function[]> = new Map();

 constructor() {
 this.registerDefaultChecks();
 }

 /**
 * Register default health checks
 */
 private registerDefaultChecks() {
 const defaultChecks: HealthCheckConfig[] = [
 {
 name: 'feature-flags',
 enabled: true,
 timeout: 5000,
 interval: 30000,
 retries: 2,
 },
 {
 name: 'api-endpoints',
 enabled: true,
 timeout: 10000,
 interval: 60000,
 retries: 3,
 },
 {
 name: 'database-connectivity',
 enabled: true,
 timeout: 5000,
 interval: 30000,
 retries: 2,
 },
 {
 name: 'component-rendering',
 enabled: true,
 timeout: 2000,
 interval: 60000,
 retries: 1,
 },
 {
 name: 'memory-usage',
 enabled: true,
 timeout: 1000,
 interval: 120000,
 retries: 1,
 thresholds: {
 warning: 80,
 critical: 95,
 },
 },
 {
 name: 'error-rate',
 enabled: true,
 timeout: 2000,
 interval: 60000,
 retries: 1,
 thresholds: {
 warning: 5,
 critical: 10,
 },
 },
 ];

 defaultChecks.forEach(check => this.registerCheck(check));
 }

 /**
 * Register a health check
 */
 registerCheck(config: HealthCheckConfig) {
 this.checks.set(config.name, config);
 }

 /**
 * Start monitoring all registered checks
 */
 startMonitoring() {
 this.checks.forEach((config, name) => {
 if (config.enabled) {
 this.startCheck(name);
 }
 });
 }

 /**
 * Stop monitoring all checks
 */
 stopMonitoring() {
 this.intervals.forEach((interval, name) => {
 clearInterval(interval);
 });
 this.intervals.clear();
 }

 /**
 * Start monitoring a specific check
 */
 private startCheck(name: string) {
 const config = this.checks.get(name);
 if (!config) return;

 // Run initial check
 this.runCheck(name);

 // Set up interval
 const interval = setInterval(() => {
 this.runCheck(name);
 }, config.interval);

 this.intervals.set(name, interval);
 }

 /**
 * Run a specific health check
 */
 async runCheck(name: string): Promise<HealthCheckResult> {
 const config = this.checks.get(name);
 if (!config) {
 throw new Error(`Health check ${name} not found`);
 }

 const startTime = Date.now();
 let result: HealthCheckResult;

 try {
 const checkResult = await this.executeCheck(name, config);
 const duration = Date.now() - startTime;

 result = {
 name,
 status: checkResult.status,
 timestamp: new Date().toISOString(),
 duration,
 message: checkResult.message,
 details: checkResult.details,
 };
 } catch (error) {
 const duration = Date.now() - startTime;
 result = {
 name,
 status: 'unhealthy',
 timestamp: new Date().toISOString(),
 duration,
 message: error instanceof Error ? error.message : 'Unknown error',
 };
 }

 this.lastResults.set(name, result);
 this.emitEvent('check-complete', result);

 return result;
 }

 /**
 * Execute a specific health check
 */
 private async executeCheck(
 name: string,
 config: HealthCheckConfig
 ): Promise<{ status: HealthCheckResult['status']; message?: string; details?: any }> {
 switch (name) {
 case 'feature-flags':
 return await this.checkFeatureFlags();

 case 'api-endpoints':
 return await this.checkApiEndpoints();

 case 'database-connectivity':
 return await this.checkDatabaseConnectivity();

 case 'component-rendering':
 return await this.checkComponentRendering();

 case 'memory-usage':
 return await this.checkMemoryUsage(config);

 case 'error-rate':
 return await this.checkErrorRate(config);

 default:
 throw new Error(`Unknown health check: ${name}`);
 }
 }

 /**
 * Check feature flags system
 */
 private async checkFeatureFlags(): Promise<{ status: HealthCheckResult['status']; message?: string }> {
 try {
 // Check if feature flags are accessible
 const flags = localStorage.getItem('nsw-compliance-feature-flags');
 const parsedFlags = flags ? JSON.parse(flags) : {};

 const flagCount = Object.keys(parsedFlags).length;

 if (flagCount === 0) {
 return { status: 'degraded', message: 'No feature flags configured' };
 }

 return { status: 'healthy', message: `${flagCount} feature flags active` };
 } catch (error) {
 return { status: 'unhealthy', message: 'Feature flags system unavailable' };
 }
 }

 /**
 * Check API endpoints
 */
 private async checkApiEndpoints(): Promise<{ status: HealthCheckResult['status']; message?: string; details?: any }> {
 const endpoints = [
 '/api/property',
 '/api/compliance/status',
 '/api/compliance/checklist',
 ];

 const results = await Promise.allSettled(
 endpoints.map(async (endpoint) => {
 const response = await fetch(endpoint + '?healthCheck=true', {
 method: 'GET',
 headers: { 'Accept': 'application/json' },
 });
 return { endpoint, ok: response.ok, status: response.status };
 })
 );

 const successful = results.filter(r => r.status === 'fulfilled' && r.value.ok).length;
 const total = endpoints.length;

 if (successful === total) {
 return { status: 'healthy', message: `All ${total} API endpoints responding` };
 } else if (successful > 0) {
 return {
 status: 'degraded',
 message: `${successful}/${total} API endpoints responding`,
 details: { successful, total }
 };
 } else {
 return { status: 'unhealthy', message: 'No API endpoints responding' };
 }
 }

 /**
 * Check database connectivity
 */
 private async checkDatabaseConnectivity(): Promise<{ status: HealthCheckResult['status']; message?: string }> {
 try {
 const response = await fetch('/api/health/database');
 if (response.ok) {
 return { status: 'healthy', message: 'Database connected' };
 } else {
 return { status: 'unhealthy', message: `Database check failed: ${response.status}` };
 }
 } catch (error) {
 return { status: 'unhealthy', message: 'Database unreachable' };
 }
 }

 /**
 * Check component rendering
 */
 private async checkComponentRendering(): Promise<{ status: HealthCheckResult['status']; message?: string }> {
 const migrationComponents = document.querySelectorAll('[data-migration-component]');
 const count = migrationComponents.length;

 if (count > 0) {
 return { status: 'healthy', message: `${count} migration components rendered` };
 } else {
 return { status: 'degraded', message: 'No migration components detected' };
 }
 }

 /**
 * Check memory usage
 */
 private async checkMemoryUsage(config: HealthCheckConfig): Promise<{ status: HealthCheckResult['status']; message?: string; details?: any }> {
 if ('memory' in performance) {
 const memory = (performance as any).memory;
 const usedPercent = (memory.usedJSHeapSize / memory.totalJSHeapSize) * 100;

 const status = usedPercent > (config.thresholds?.critical || 95) ? 'unhealthy' :
 usedPercent > (config.thresholds?.warning || 80) ? 'degraded' : 'healthy';

 return {
 status,
 message: `Memory usage: ${usedPercent.toFixed(1)}%`,
 details: {
 usedPercent,
 usedMB: Math.round(memory.usedJSHeapSize / 1024 / 1024),
 totalMB: Math.round(memory.totalJSHeapSize / 1024 / 1024),
 }
 };
 } else {
 return { status: 'degraded', message: 'Memory metrics not available' };
 }
 }

 /**
 * Check error rate
 */
 private async checkErrorRate(config: HealthCheckConfig): Promise<{ status: HealthCheckResult['status']; message?: string }> {
 // In a real implementation, this would check error tracking service
 const mockErrorRate = Math.random() * 15; // Simulate 0-15% error rate

 const status = mockErrorRate > (config.thresholds?.critical || 10) ? 'unhealthy' :
 mockErrorRate > (config.thresholds?.warning || 5) ? 'degraded' : 'healthy';

 return {
 status,
 message: `Error rate: ${mockErrorRate.toFixed(1)}%`
 };
 }

 /**
 * Get current system health
 */
 async getSystemHealth(): Promise<SystemHealth> {
 const checks = Array.from(this.checks.keys());
 const results = await Promise.all(
 checks.map(name => this.runCheck(name))
 );

 const summary = {
 healthy: results.filter(r => r.status === 'healthy').length,
 degraded: results.filter(r => r.status === 'degraded').length,
 unhealthy: results.filter(r => r.status === 'unhealthy').length,
 total: results.length,
 };

 const overall = summary.unhealthy > 0 ? 'unhealthy' :
 summary.degraded > 0 ? 'degraded' : 'healthy';

 return {
 overall,
 timestamp: new Date().toISOString(),
 checks: results,
 summary,
 };
 }

 /**
 * Get latest results for all checks
 */
 getLatestResults(): HealthCheckResult[] {
 return Array.from(this.lastResults.values());
 }

 /**
 * Add event listener
 */
 on(eventType: string, callback: Function) {
 if (!this.listeners.has(eventType)) {
 this.listeners.set(eventType, []);
 }
 this.listeners.get(eventType)!.push(callback);
 }

 /**
 * Emit event
 */
 private emitEvent(type: string, data: any) {
 const listeners = this.listeners.get(type) || [];
 listeners.forEach(callback => callback(data));
 }
}

// Singleton instance
export const migrationHealthCheck = new MigrationHealthCheck();