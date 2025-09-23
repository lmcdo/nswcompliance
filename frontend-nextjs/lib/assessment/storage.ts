/**
 * Assessment Storage Utilities
 * Manages localStorage for assessment state persistence
 */

export interface StorageConfig {
 key: string;
 ttl?: number; // Time to live in milliseconds
 compress?: boolean;
}

export class AssessmentStorage {
 private static readonly DEFAULT_TTL = 24 * 60 * 60 * 1000; // 24 hours
 private static readonly STORAGE_PREFIX = 'nsw_assessment_';

 /**
 * Save data to localStorage with optional TTL
 */
 static save<T>(config: StorageConfig, data: T): boolean {
 try {
 const now = Date.now();
 const storageData = {
 data,
 timestamp: now,
 expires: config.ttl ? now + config.ttl : now + this.DEFAULT_TTL
 };

 const serialized = JSON.stringify(storageData);
 const key = this.STORAGE_PREFIX + config.key;

 localStorage.setItem(key, serialized);
 return true;
 } catch (error) {
 console.warn('Failed to save to localStorage:', error);
 return false;
 }
 }

 /**
 * Load data from localStorage with expiration check
 */
 static load<T>(config: StorageConfig): T | null {
 try {
 const key = this.STORAGE_PREFIX + config.key;
 const stored = localStorage.getItem(key);

 if (!stored) return null;

 const parsed = JSON.parse(stored);
 const now = Date.now();

 // Check if data has expired
 if (parsed.expires && now > parsed.expires) {
 this.remove(config);
 return null;
 }

 return parsed.data;
 } catch (error) {
 console.warn('Failed to load from localStorage:', error);
 return null;
 }
 }

 /**
 * Remove data from localStorage
 */
 static remove(config: StorageConfig): boolean {
 try {
 const key = this.STORAGE_PREFIX + config.key;
 localStorage.removeItem(key);
 return true;
 } catch (error) {
 console.warn('Failed to remove from localStorage:', error);
 return false;
 }
 }

 /**
 * Clear all assessment data from localStorage
 */
 static clearAll(): boolean {
 try {
 const keys = Object.keys(localStorage);
 const assessmentKeys = keys.filter(key => key.startsWith(this.STORAGE_PREFIX));

 assessmentKeys.forEach(key => localStorage.removeItem(key));
 return true;
 } catch (error) {
 console.warn('Failed to clear localStorage:', error);
 return false;
 }
 }

 /**
 * Get storage statistics
 */
 static getStorageStats(): {
 totalKeys: number;
 assessmentKeys: number;
 totalSize: number;
 assessmentSize: number;
 } {
 try {
 const keys = Object.keys(localStorage);
 const assessmentKeys = keys.filter(key => key.startsWith(this.STORAGE_PREFIX));

 let totalSize = 0;
 let assessmentSize = 0;

 keys.forEach(key => {
 const size = (localStorage.getItem(key) || '').length;
 totalSize += size;
 if (key.startsWith(this.STORAGE_PREFIX)) {
 assessmentSize += size;
 }
 });

 return {
 totalKeys: keys.length,
 assessmentKeys: assessmentKeys.length,
 totalSize,
 assessmentSize
 };
 } catch (error) {
 console.warn('Failed to get storage stats:', error);
 return { totalKeys: 0, assessmentKeys: 0, totalSize: 0, assessmentSize: 0 };
 }
 }
}

// Storage configuration presets
export const STORAGE_CONFIGS = {
 ASSESSMENT_STATE: { key: 'current_assessment', ttl: 7 * 24 * 60 * 60 * 1000 }, // 7 days
 API_CACHE: { key: 'api_cache', ttl: 30 * 60 * 1000 }, // 30 minutes
 PROPERTY_CACHE: { key: 'property_cache', ttl: 60 * 60 * 1000 }, // 1 hour
 COMPLIANCE_CACHE: { key: 'compliance_cache', ttl: 15 * 60 * 1000 }, // 15 minutes
 USER_PREFERENCES: { key: 'user_preferences', ttl: 30 * 24 * 60 * 60 * 1000 }, // 30 days
} as const;
