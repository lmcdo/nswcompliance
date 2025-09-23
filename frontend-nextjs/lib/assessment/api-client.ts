/**
 * Assessment API Client
 * Provides typed interfaces to the assessment APIs
 */

import { PropertyData, AssessmentData, ComplianceResult } from './types';

class AssessmentAPIClient {
 private baseUrl = '/api';

 async loadProperty(address: string): Promise<{
 property: PropertyData;
 constraints: any;
 layers: any[];
 }> {
 const response = await fetch(`${this.baseUrl}/assessment`, {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 action: 'loadProperty',
 address
 })
 });

 if (!response.ok) {
 throw new Error(`Failed to load property: ${response.statusText}`);
 }

 const result = await response.json();
 return result.data;
 }

 async getCompliance({
 propertyId,
 zone,
 developmentType,
 assessmentDate
 }: {
 propertyId: number;
 zone: string;
 developmentType: string;
 assessmentDate?: string;
 }): Promise<any> {
 const response = await fetch(`${this.baseUrl}/assessment`, {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 action: 'getCompliance',
 propertyId,
 zone,
 developmentType,
 assessmentDate
 })
 });

 if (!response.ok) {
 throw new Error(`Failed to get compliance: ${response.statusText}`);
 }

 const result = await response.json();
 return result.data;
 }

 async searchProvisions({
 query,
 zone,
 developmentType
 }: {
 query: string;
 zone?: string;
 developmentType?: string;
 }): Promise<any> {
 const response = await fetch(`${this.baseUrl}/assessment`, {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 action: 'searchProvisions',
 query,
 zone,
 developmentType
 })
 });

 if (!response.ok) {
 throw new Error(`Failed to search provisions: ${response.statusText}`);
 }

 const result = await response.json();
 return result.data;
 }

 // Use existing property API directly
 async getPropertyBasic(address: string): Promise<any> {
 const response = await fetch(`${this.baseUrl}/property?address=${encodeURIComponent(address)}`);

 if (!response.ok) {
 throw new Error(`Failed to get property: ${response.statusText}`);
 }

 return response.json();
 }

 // Use existing setbacks API
 async calculateSetbacks(propertyId: number, zone: string): Promise<any> {
 const response = await fetch(`${this.baseUrl}/setbacks/calculate`, {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 property_id: propertyId,
 zone: zone
 })
 });

 if (!response.ok) {
 throw new Error(`Failed to calculate setbacks: ${response.statusText}`);
 }

 return response.json();
 }

 // Use existing TOD parking calculator
 async getTODParking({
 zone,
 developmentType,
 lga
 }: {
 zone: string;
 developmentType: string;
 lga?: string;
 }): Promise<any> {
 const params = new URLSearchParams({
 zone,
 development_type: developmentType,
 ...(lga && { lga })
 });

 const response = await fetch(`${this.baseUrl}/tod/parking-rates?${params}`);

 if (!response.ok) {
 throw new Error(`Failed to get TOD parking: ${response.statusText}`);
 }

 return response.json();
 }
}

export const assessmentAPI = new AssessmentAPIClient();
