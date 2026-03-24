import { FeatureFlags } from './feature-flags';

export interface FeatureFlagService {
 getFlags(): Promise<FeatureFlags>;
 getFlag(name: string): Promise<boolean>;
 updateFlag(name: string, value: boolean): Promise<void>;
 resetFlags(): Promise<void>;
}

class LocalStorageFeatureFlagService implements FeatureFlagService {
 private readonly STORAGE_KEY = 'nsw-compliance-feature-flags';

 async getFlags(): Promise<FeatureFlags> {
 try {
 const stored = localStorage.getItem(this.STORAGE_KEY);
 if (stored) {
 return JSON.parse(stored);
 }
 } catch (error) {
 console.warn('Failed to load feature flags from localStorage:', error);
 }

 // Return default flags
 return {
 authoritativeRouteMigration: false,
 newDevelopmentSelector: false,
 newComplianceStatus: false,
 newComplianceChecklist: false,
 unifiedStateManagement: false,
 legacyRouteFallback: true,
 enableCaching: true,
 enableAnalytics: false,
 };
 }

 async getFlag(name: string): Promise<boolean> {
 const flags = await this.getFlags();
 return flags[name as keyof FeatureFlags] || false;
 }

 async updateFlag(name: string, value: boolean): Promise<void> {
 const flags = await this.getFlags();
 const updatedFlags = { ...flags, [name]: value };

 try {
 localStorage.setItem(this.STORAGE_KEY, JSON.stringify(updatedFlags));
 } catch (error) {
 console.error('Failed to save feature flags to localStorage:', error);
 }
 }

 async resetFlags(): Promise<void> {
 try {
 localStorage.removeItem(this.STORAGE_KEY);
 } catch (error) {
 console.error('Failed to reset feature flags:', error);
 }
 }
}

class ServerFeatureFlagService implements FeatureFlagService {
 private readonly baseUrl: string;

 constructor(baseUrl: string = '/api/feature-flags') {
 this.baseUrl = baseUrl;
 }

 async getFlags(): Promise<FeatureFlags> {
 try {
 const response = await fetch(this.baseUrl);
 if (!response.ok) {
 throw new Error(`HTTP ${response.status}`);
 }
 return await response.json();
 } catch (error) {
 console.warn('Failed to fetch feature flags from server:', error);
 // Fallback to localStorage
 const localService = new LocalStorageFeatureFlagService();
 return await localService.getFlags();
 }
 }

 async getFlag(name: string): Promise<boolean> {
 const flags = await this.getFlags();
 return flags[name as keyof FeatureFlags] || false;
 }

 async updateFlag(name: string, value: boolean): Promise<void> {
 try {
 await fetch(`${this.baseUrl}/${name}`, {
 method: 'PATCH',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ value }),
 });
 } catch (error) {
 console.error('Failed to update feature flag on server:', error);
 // Fallback to localStorage
 const localService = new LocalStorageFeatureFlagService();
 await localService.updateFlag(name, value);
 }
 }

 async resetFlags(): Promise<void> {
 try {
 await fetch(this.baseUrl, { method: 'DELETE' });
 } catch (error) {
 console.error('Failed to reset feature flags on server:', error);
 }
 }
}

// Export singleton instance
export const featureFlagService: FeatureFlagService =
 typeof window !== 'undefined'
 ? new ServerFeatureFlagService()
 : new LocalStorageFeatureFlagService();

export { LocalStorageFeatureFlagService, ServerFeatureFlagService };