/**
 * API Caching Layer
 * Provides intelligent caching for assessment API calls
 */

import { AssessmentStorage, STORAGE_CONFIGS } from './storage';

export interface CacheEntry<T> {
 data: T;
 timestamp: number;
 key: string;
}

export interface CacheConfig {
 ttl: number; // Time to live in milliseconds
 staleWhileRevalidate?: boolean; // Serve stale data while fetching fresh
 maxEntries?: number; // Maximum cache entries
}

export class APICache {
 private static cache = new Map<string, CacheEntry<any>>();
 private static readonly DEFAULT_CONFIG: CacheConfig = {
 ttl: 15 * 60 * 1000, // 15 minutes
 staleWhileRevalidate: true,
 maxEntries: 100
 };

 /**
 * Generate cache key from request parameters
 */
 private static generateKey(endpoint: string, params?: any): string {
 const paramString = params ? JSON.stringify(params) : '';
 return `${endpoint}_${btoa(paramString)}`;
 }

 /**
 * Check if cache entry is expired
 */
 private static isExpired(entry: CacheEntry<any>, ttl: number): boolean {
 return Date.now() - entry.timestamp > ttl;
 }

 /**
 * Clean up expired entries
 */
 private static cleanup(maxEntries: number): void {
 if (this.cache.size <= maxEntries) return;

 const entries = Array.from(this.cache.entries());
 entries.sort((a, b) => a[1].timestamp - b[1].timestamp);

 // Remove oldest entries
 const toRemove = entries.slice(0, entries.length - maxEntries);
 toRemove.forEach(([key]) => this.cache.delete(key));
 }

 /**
 * Get cached data
 */
 static get<T>(endpoint: string, params?: any, config: Partial<CacheConfig> = {}): T | null {
 const mergedConfig = { ...this.DEFAULT_CONFIG, ...config };
 const key = this.generateKey(endpoint, params);
 const entry = this.cache.get(key);

 if (!entry) return null;

 const expired = this.isExpired(entry, mergedConfig.ttl);

 if (expired && !mergedConfig.staleWhileRevalidate) {
 this.cache.delete(key);
 return null;
 }

 return entry.data;
 }

 /**
 * Set cached data
 */
 static set<T>(endpoint: string, params: any, data: T, config: Partial<CacheConfig> = {}): void {
 const mergedConfig = { ...this.DEFAULT_CONFIG, ...config };
 const key = this.generateKey(endpoint, params);

 const entry: CacheEntry<T> = {
 data,
 timestamp: Date.now(),
 key
 };

 this.cache.set(key, entry);
 this.cleanup(mergedConfig.maxEntries || 100);

 // Also save to localStorage for persistence
 this.saveToStorage(key, entry);
 }

 /**
 * Clear cache
 */
 static clear(): void {
 this.cache.clear();
 AssessmentStorage.remove(STORAGE_CONFIGS.API_CACHE);
 }

 /**
 * Get cache statistics
 */
 static getStats(): {
 size: number;
 entries: Array<{ key: string; age: number; size: number }>;
 } {
 const entries = Array.from(this.cache.entries()).map(([key, entry]) => ({
 key,
 age: Date.now() - entry.timestamp,
 size: JSON.stringify(entry.data).length
 }));

 return {
 size: this.cache.size,
 entries
 };
 }

 /**
 * Save cache entry to localStorage
 */
 private static saveToStorage<T>(key: string, entry: CacheEntry<T>): void {
 try {
 const storageKey = `cache_${key}`;
 AssessmentStorage.save({ key: storageKey, ttl: 60 * 60 * 1000 }, entry);
 } catch (error) {
 console.warn('Failed to save cache to storage:', error);
 }
 }

 /**
 * Load cache from localStorage
 */
 static loadFromStorage(): void {
 try {
 const stats = AssessmentStorage.getStorageStats();
 console.log(`Loading cache from storage: ${stats.assessmentKeys} entries`);

 // This would load cache entries from localStorage
 // Implementation depends on storage structure
 } catch (error) {
 console.warn('Failed to load cache from storage:', error);
 }
 }
}

/**
 * Cached API wrapper
 */
export async function cachedFetch<T>(
 endpoint: string,
 options: RequestInit = {},
 params?: any,
 cacheConfig?: Partial<CacheConfig>
): Promise<T> {
 // Try to get from cache first
 const cached = APICache.get<T>(endpoint, params, cacheConfig);
 if (cached && (!cacheConfig?.staleWhileRevalidate || !((APICache as any).isExpired(cached as any, cacheConfig.ttl || 15 * 60 * 1000)))) {
 return cached;
 }

 // Fetch fresh data
 try {
 const response = await fetch(endpoint, options);
 if (!response.ok) {
 throw new Error(`HTTP ${response.status}: ${response.statusText}`);
 }

 const data = await response.json();

 // Cache the fresh data
 APICache.set(endpoint, params, data, cacheConfig);

 return data;
 } catch (error) {
 // If we have stale cached data, return it as fallback
 if (cached && cacheConfig?.staleWhileRevalidate) {
 console.warn('Using stale cache due to fetch error:', error);
 return cached;
 }
 throw error;
 }
}
