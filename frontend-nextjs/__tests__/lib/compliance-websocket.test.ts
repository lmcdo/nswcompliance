import { ComplianceWebSocketManager } from '@/lib/compliance-websocket';

// Mock WebSocket
class MockWebSocket {
 readyState = WebSocket.CONNECTING;
 onopen?: () => void;
 onmessage?: (event: { data: string }) => void;
 onclose?: (event: { code: number }) => void;
 onerror?: (error: any) => void;

 constructor(url: string) {}

 close() {
 this.readyState = WebSocket.CLOSED;
 this.onclose?.({ code: 1000 });
 }

 send(data: string) {}
}

// @ts-ignore
global.WebSocket = MockWebSocket;

describe('ComplianceWebSocketManager', () => {
 let manager: ComplianceWebSocketManager;

 beforeEach(() => {
 manager = new ComplianceWebSocketManager();
 });

 afterEach(() => {
 manager.disconnectAll();
 });

 test('connects to WebSocket', () => {
 const onUpdate = jest.fn();

 manager.connect('test-assessment', onUpdate);

 expect(manager.getConnectionStatus('test-assessment')).toBe('connecting');
 });

 test('handles WebSocket messages', () => {
 const onUpdate = jest.fn();

 manager.connect('test-assessment', onUpdate);

 // Simulate connection opening
 const ws = (manager as any).connections.get('test-assessment');
 ws.readyState = WebSocket.OPEN;
 ws.onopen?.();

 // Simulate message
 const mockUpdate = {
 type: 'status_change',
 checkId: 'test-check',
 status: 'compliant',
 timestamp: new Date().toISOString(),
 };

 ws.onmessage?.({ data: JSON.stringify(mockUpdate) });

 expect(onUpdate).toHaveBeenCalledWith(mockUpdate);
 });

 test('disconnects WebSocket', () => {
 const onUpdate = jest.fn();

 manager.connect('test-assessment', onUpdate);
 manager.disconnect('test-assessment');

 expect(manager.getConnectionStatus('test-assessment')).toBe('disconnected');
 });

 test('returns correct connection status', () => {
 expect(manager.isConnected('test-assessment')).toBe(false);

 const onUpdate = jest.fn();
 manager.connect('test-assessment', onUpdate);

 const ws = (manager as any).connections.get('test-assessment');
 ws.readyState = WebSocket.OPEN;

 expect(manager.isConnected('test-assessment')).toBe(true);
 });
});
