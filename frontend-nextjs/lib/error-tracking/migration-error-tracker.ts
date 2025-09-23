export interface ErrorEvent {
 id: string;
 timestamp: string;
 level: 'error' | 'warning' | 'info';
 message: string;
 stack?: string;
 context: {
 phase?: string;
 component?: string;
 user?: string;
 url?: string;
 userAgent?: string;
 };
 tags: string[];
 fingerprint: string;
 count: number;
}

export interface ErrorMetrics {
 totalErrors: number;
 errorRate: number;
 topErrors: ErrorEvent[];
 errorsByPhase: Record<string, number>;
 errorsByComponent: Record<string, number>;
 timeRange: {
 start: string;
 end: string;
 };
}

export class MigrationErrorTracker {
 private errors: Map<string, ErrorEvent> = new Map();
 private listeners: Map<string, Function[]> = new Map();
 private maxErrors = 1000;

 constructor() {
 this.setupGlobalErrorHandlers();
 }

 /**
 * Set up global error handlers
 */
 private setupGlobalErrorHandlers() {
 // Handle uncaught JavaScript errors
 window.addEventListener('error', (event) => {
 this.captureError(event.error || new Error(event.message), {
 component: 'global',
 url: window.location.href,
 });
 });

 // Handle unhandled promise rejections
 window.addEventListener('unhandledrejection', (event) => {
 this.captureError(
 new Error(`Unhandled Promise Rejection: ${event.reason}`),
 {
 component: 'promise',
 url: window.location.href,
 }
 );
 });

 // Handle React error boundaries (if available)
 if (typeof window !== 'undefined' && window.React) {
 const originalError = console.error;
 console.error = (...args) => {
 if (args[0] && typeof args[0] === 'string' && args[0].includes('React')) {
 this.captureError(new Error(args.join(' ')), {
 component: 'react',
 url: window.location.href,
 });
 }
 originalError.apply(console, args);
 };
 }
 }

 /**
 * Capture an error
 */
 captureError(
 error: Error,
 context: Partial<ErrorEvent['context']> = {},
 tags: string[] = [],
 level: ErrorEvent['level'] = 'error'
 ): string {
 const fingerprint = this.generateFingerprint(error, context);
 const timestamp = new Date().toISOString();

 const existingError = this.errors.get(fingerprint);
 if (existingError) {
 // Update existing error count
 existingError.count++;
 existingError.timestamp = timestamp;
 } else {
 // Create new error event
 const errorEvent: ErrorEvent = {
 id: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
 timestamp,
 level,
 message: error.message,
 stack: error.stack,
 context: {
 url: window.location.href,
 userAgent: navigator.userAgent,
 ...context,
 },
 tags: ['migration', ...tags],
 fingerprint,
 count: 1,
 };

 this.errors.set(fingerprint, errorEvent);

 // Maintain error limit
 if (this.errors.size > this.maxErrors) {
 const oldestKey = Array.from(this.errors.keys())[0];
 this.errors.delete(oldestKey);
 }
 }

 // Emit error event
 this.emitEvent('error-captured', this.errors.get(fingerprint)!);

 // Send to external error tracking service (optional)
 this.sendToExternalService(this.errors.get(fingerprint)!);

 return fingerprint;
 }

 /**
 * Generate fingerprint for error deduplication
 */
 private generateFingerprint(error: Error, context: Partial<ErrorEvent['context']>): string {
 const key = [
 error.message,
 error.stack?.split('\n')[0] || '',
 context.component || '',
 context.phase || '',
 ].join('|');

 // Simple hash function
 let hash = 0;
 for (let i = 0; i < key.length; i++) {
 const char = key.charCodeAt(i);
 hash = ((hash << 5) - hash) + char;
 hash = hash & hash; // Convert to 32-bit integer
 }

 return hash.toString(36);
 }

 /**
 * Send error to external tracking service
 */
 private async sendToExternalService(errorEvent: ErrorEvent) {
 try {
 // In a real implementation, send to Sentry, LogRocket, etc.
 await fetch('/api/errors/track', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify(errorEvent),
 });
 } catch (e) {
 console.warn('Failed to send error to external service:', e);
 }
 }

 /**
 * Get error metrics for a time range
 */
 getErrorMetrics(hoursBack: number = 24): ErrorMetrics {
 const now = new Date();
 const startTime = new Date(now.getTime() - (hoursBack * 60 * 60 * 1000));

 const recentErrors = Array.from(this.errors.values())
 .filter(error => new Date(error.timestamp) >= startTime);

 const errorsByPhase: Record<string, number> = {};
 const errorsByComponent: Record<string, number> = {};

 recentErrors.forEach(error => {
 if (error.context.phase) {
 errorsByPhase[error.context.phase] = (errorsByPhase[error.context.phase] || 0) + error.count;
 }
 if (error.context.component) {
 errorsByComponent[error.context.component] = (errorsByComponent[error.context.component] || 0) + error.count;
 }
 });

 const topErrors = recentErrors
 .sort((a, b) => b.count - a.count)
 .slice(0, 10);

 const totalErrors = recentErrors.reduce((sum, error) => sum + error.count, 0);
 const totalRequests = this.estimateRequestCount(hoursBack);
 const errorRate = totalRequests > 0 ? (totalErrors / totalRequests) * 100 : 0;

 return {
 totalErrors,
 errorRate,
 topErrors,
 errorsByPhase,
 errorsByComponent,
 timeRange: {
 start: startTime.toISOString(),
 end: now.toISOString(),
 },
 };
 }

 /**
 * Estimate request count (in real app, this would come from analytics)
 */
 private estimateRequestCount(hoursBack: number): number {
 // Mock calculation - in real app, get from analytics
 return hoursBack * 100; // Assume 100 requests per hour
 }

 /**
 * Get all errors
 */
 getAllErrors(): ErrorEvent[] {
 return Array.from(this.errors.values())
 .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
 }

 /**
 * Get errors by phase
 */
 getErrorsByPhase(phase: string): ErrorEvent[] {
 return this.getAllErrors().filter(error => error.context.phase === phase);
 }

 /**
 * Clear all errors
 */
 clearErrors(): void {
 this.errors.clear();
 this.emitEvent('errors-cleared', {});
 }

 /**
 * Mark error as resolved
 */
 resolveError(fingerprint: string): boolean {
 const error = this.errors.get(fingerprint);
 if (error) {
 error.tags.push('resolved');
 this.emitEvent('error-resolved', error);
 return true;
 }
 return false;
 }

 /**
 * Add tag to error
 */
 tagError(fingerprint: string, tag: string): boolean {
 const error = this.errors.get(fingerprint);
 if (error && !error.tags.includes(tag)) {
 error.tags.push(tag);
 this.emitEvent('error-tagged', { error, tag });
 return true;
 }
 return false;
 }

 /**
 * Set up phase-specific error tracking
 */
 trackPhase(phase: string): () => void {
 const originalCapture = this.captureError.bind(this);

 // Override capture to include phase context
 this.captureError = (error, context = {}, tags = [], level = 'error') => {
 return originalCapture(error, { ...context, phase }, tags, level);
 };

 // Return cleanup function
 return () => {
 this.captureError = originalCapture;
 };
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
 listeners.forEach(callback => {
 try {
 callback(data);
 } catch (e) {
 console.error('Error in error tracker listener:', e);
 }
 });
 }

 /**
 * Get error summary for dashboard
 */
 getSummary(): {
 totalErrors: number;
 recentErrors: number;
 criticalErrors: number;
 topPhases: Array<{ phase: string; count: number }>;
 } {
 const allErrors = this.getAllErrors();
 const recentErrors = allErrors.filter(
 error => Date.now() - new Date(error.timestamp).getTime() < 60 * 60 * 1000 // Last hour
 );
 const criticalErrors = allErrors.filter(error => error.level === 'error');

 const phaseGroups = new Map<string, number>();
 allErrors.forEach(error => {
 if (error.context.phase) {
 phaseGroups.set(error.context.phase, (phaseGroups.get(error.context.phase) || 0) + error.count);
 }
 });

 const topPhases = Array.from(phaseGroups.entries())
 .map(([phase, count]) => ({ phase, count }))
 .sort((a, b) => b.count - a.count)
 .slice(0, 5);

 return {
 totalErrors: allErrors.reduce((sum, error) => sum + error.count, 0),
 recentErrors: recentErrors.reduce((sum, error) => sum + error.count, 0),
 criticalErrors: criticalErrors.reduce((sum, error) => sum + error.count, 0),
 topPhases,
 };
 }
}

// Singleton instance
export const migrationErrorTracker = new MigrationErrorTracker();