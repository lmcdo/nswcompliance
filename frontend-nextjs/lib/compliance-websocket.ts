import { ComplianceUpdate } from '@/components/compliance/types';

export interface UploadProgress {
 jobId: string;
 itemId: string;
 fileName: string;
 progress: number;
 status: 'pending' | 'uploading' | 'complete' | 'error';
}

export class ComplianceWebSocketManager {
 private connections: Map<string, WebSocket> = new Map();
 private reconnectAttempts: Map<string, number> = new Map();
 private maxReconnectAttempts = 5;
 private reconnectInterval = 1000; // Base interval in ms

 connect(assessmentId: string, onUpdate: (update: ComplianceUpdate) => void): void {
 if (this.connections.has(assessmentId)) {
 this.disconnect(assessmentId);
 }

 try {
 const wsUrl = this.getWebSocketUrl(assessmentId);
 const ws = new WebSocket(wsUrl);

 ws.onopen = () => {
 console.log(`Compliance WebSocket connected for assessment ${assessmentId}`);
 this.reconnectAttempts.set(assessmentId, 0);
 };

 ws.onmessage = (event) => {
 try {
 const update: ComplianceUpdate = JSON.parse(event.data);
 onUpdate(update);
 } catch (error) {
 console.error('Failed to parse compliance update:', error);
 }
 };

 ws.onclose = (event) => {
 console.log(`Compliance WebSocket closed for assessment ${assessmentId}`, event.code);
 this.handleReconnect(assessmentId, onUpdate);
 };

 ws.onerror = (error) => {
 console.error(`Compliance WebSocket error for assessment ${assessmentId}:`, error);
 };

 this.connections.set(assessmentId, ws);
 } catch (error) {
 console.error('Failed to create WebSocket connection:', error);
 this.handleReconnect(assessmentId, onUpdate);
 }
 }

 disconnect(assessmentId: string): void {
 const ws = this.connections.get(assessmentId);
 if (ws) {
 ws.close();
 this.connections.delete(assessmentId);
 this.reconnectAttempts.delete(assessmentId);
 }
 }

 disconnectAll(): void {
 for (const [assessmentId] of this.connections) {
 this.disconnect(assessmentId);
 }
 }

 private getWebSocketUrl(assessmentId: string): string {
 const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
 const host = process.env.NEXT_PUBLIC_WS_HOST || window.location.host;
 return `${protocol}//${host}/api/compliance/ws/${assessmentId}`;
 }

 private handleReconnect(assessmentId: string, onUpdate: (update: ComplianceUpdate) => void): void {
 const attempts = this.reconnectAttempts.get(assessmentId) || 0;

 if (attempts < this.maxReconnectAttempts) {
 const delay = Math.min(this.reconnectInterval * Math.pow(2, attempts), 30000);

 setTimeout(() => {
 console.log(`Attempting to reconnect WebSocket for assessment ${assessmentId} (attempt ${attempts + 1})`);
 this.connect(assessmentId, onUpdate);
 this.reconnectAttempts.set(assessmentId, attempts + 1);
 }, delay);
 } else {
 console.error(`Max reconnection attempts reached for assessment ${assessmentId}`);
 }
 }

 isConnected(assessmentId: string): boolean {
 const ws = this.connections.get(assessmentId);
 return ws ? ws.readyState === WebSocket.OPEN : false;
 }

 getConnectionStatus(assessmentId: string): string {
 const ws = this.connections.get(assessmentId);
 if (!ws) return 'disconnected';

 switch (ws.readyState) {
 case WebSocket.CONNECTING: return 'connecting';
 case WebSocket.OPEN: return 'connected';
 case WebSocket.CLOSING: return 'closing';
 case WebSocket.CLOSED: return 'closed';
 default: return 'unknown';
 }
 }
}

export const complianceWebSocketManager = new ComplianceWebSocketManager();

// Cleanup on page unload
if (typeof window !== 'undefined') {
 window.addEventListener('beforeunload', () => {
 complianceWebSocketManager.disconnectAll();
 });
}
