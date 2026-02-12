/**
 * WebSocket Handlers - Integration Tests (Phase 4, Step 4.2)
 * Core integration tests for WebSocket connection handling and message processing
 * 
 * This is a simplified, focused integration test suite that validates:
 * - WebSocket connection lifecycle
 * - Text message handling  
 * - Audio data accumulation
 * - Session management integration
 * - Event handler integration
 * - Error handling basics
 */

const { SessionManager } = require('./session-manager');
const SessionEventHandlers = require('./session-event-handlers');

/**
 * Mock WebSocket Server for Testing
 */
class MockWebSocketServer {
    constructor(options = {}) {
        this.clients = new Set();
        this.sessionManager = options.sessionManager || new SessionManager();
        this.eventHandlers = options.eventHandlers || new SessionEventHandlers(this.sessionManager);
    }

    simulateClientConnection(userId) {
        const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const client = {
            id: clientId,
            userId,
            state: 'open',
            sessionData: { userId: null, action: null, startTime: Date.now(), language: 'en' },
            audioBuffer: Buffer.alloc(0),
            messages: []
        };
        this.clients.add(client);
        return client;
    }

    //
 Text message processing
    processTextMessage(client, message) {
        const data = typeof message === 'string' ? JSON.parse(message) : message;
        
        switch (data.type) {
            case 'init':
                return this.handleInitialization(client, data);
            case 'start-enrollment':
                return this.handleStartEnrollment(client, data);
            case 'start-verification':
                return this.handleStartVerification(client, data);
            case 'get-status':
                return this.handleGetStatus(client, data);
            case 'ping':
                return { type: 'pong', timestamp: Date.now() };
            default:
                return { type: 'error', error: 'Unknown message type', timestamp: Date.now() };
        }
    }

    handleInitialization(client, { userId, action, language = 'en' }) {
        client.sessionData.userId = userId;
        client.sessionData.action = action;
        client.sessionData.language = language;
        
        const session = this.sessionManager.createSession(userId, {
            action, language, connectionId: client.id
        });
        client.sessionData.sessionId = session.sessionId;
        
        return {
            type: 'initialized',
            userId, action, sessionId: session.sessionId,
            message: `Session initialized for ${action}`,
            timestamp: Date.now()
        };
    }

    handleStartEnrollment(client, data) {
        if (!client.sessionData.userId) {
            return { type: 'error', error: 'User ID not set', timestamp: Date.now() };
        }
        client.sessionData.action = 'enroll';
        return {
            type: 'enrollment-started',
            message: 'Ready to receive audio',
            timestamp: Date.now()
        };
    }

    handleStartVerification(client, { userId }) {
        client.sessionData.action = 'verify';
        client.sessionData.verifyUserId = userId;
        return {
            type: 'verification-started',
            message: 'Ready to receive audio',
            timestamp: Date.now()
        };
    }

    handleGetStatus(client, data) {
        const { sessionData, audioBuffer } = client;
        const sessionDuration = Date.now() - sessionData.startTime;
        
        return {
            type: 'status',
            sessionData: {
                userId: sessionData.userId,
                action: sessionData.action,
                durationMs: sessionDuration
            },
            audioStats: { bufferSize: audioBuffer.length },
            timestamp: Date.now()
        };
    }

    // Audio processing
    processAudioData(client, audioData) {
        const newBuffer = Buffer.concat([client.audioBuffer, audioData]);
        
        if (newBuffer.length > 5 * 1024 * 1024) {
            return false; // Size exceeded
        }
        
        client.audioBuffer = newBuffer;
        return true;
    }

    // Helper to simulate audio processing completion
    async completeAudioProcessing(client) {
        if (client.audioBuffer.length === 0) {
            return { success: false, error: 'No audio data' };
        }
        
        // Update session with processing result
        if (client.sessionData.sessionId) {
            this.sessionManager.updateSession(client.sessionData.sessionId, {
                metadata: {
                    audioProcessed: true,
                    audioSize: client.audioBuffer.length,
                    processedAt: new Date().toISOString()
                }
            });
        }
        
        const result = {
            success: true,
            audioProcessed: client.audioBuffer.length,
            processingTime: Math.random() * 1000
        };
        
        client.audioBuffer = Buffer.alloc(0);
        return result;
    }
}

/**
 * ===========================================================================================
 * INTEGRATION TEST SUITES
 * =============================================================================================================
 */

describe('WebSocket Handler Integration - Connection Lifecycle', () => {
    let server;

    beforeEach(() => {
        server = new MockWebSocketServer();
    });

    afterEach(() => {
        server.clients.forEach(c => c.state = 'closed');
        server.clients.clear();
    });

    test('should initialize with no clients', () => {
        expect(server.clients.size).toBe(0);
    });

    test('should handle single client connection', () => {
        const client = server.simulateClientConnection('user123');
        expect(server.clients.size).toBe(1);
        expect(client.state).toBe('open');
    });

    test('should handle multiple concurrent connections', () => {
        for (let i = 0; i < 10; i++) {
            server.simulateClientConnection(`user${i}`);
        }
        expect(server.clients.size).toBe(10);
    });

    test('should generate unique client IDs', () => {
        const clients = [];
        for (let i = 0; i < 5; i++) {
            clients.push(server.simulateClientConnection(`user${i}`));
        }
        
        const ids = clients.map(c => c.id);
        const uniqueIds = new Set(ids);
        expect(uniqueIds.size).toBe(5);
    });

    test('should remove disconnected clients', () => {
        const client = server.simulateClientConnection('user123');
        expect(server.clients.size).toBe(1);
        
        client.state = 'closed';
        server.clients.delete(client);
        
        expect(server.clients.size).toBe(0);
    });
});

describe('WebSocket Handler Integration - Message Handling', () => {
    let server, client;

    beforeEach(() => {
        server = new MockWebSocketServer();
        client = server.simulateClientConnection('testuser');
    });

    afterEach(() => {
        server.clients.clear();
    });

    test('should process init message', () => {
        const response = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        expect(response.type).toBe('initialized');
        expect(response.userId).toBe('user123');
        expect(response.sessionId).toBeDefined();
        expect(client.sessionData.userId).toBe('user123');
    });

    test('should process enrollment start message', () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const response = server.processTextMessage(client, {
            type: 'start-enrollment'
        });

        expect(response.type).toBe('enrollment-started');
    });

    test('should process verification start message', () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'verify'
        });

        const response = server.processTextMessage(client, {
            type: 'start-verification',
            userId: 'user456'
        });

        expect(response.type).toBe('verification-started');
    });

    test('should process status message', () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const response = server.processTextMessage(client, {
            type: 'get-status'
        });

        expect(response.type).toBe('status');
        expect(response.sessionData.userId).toBe('user123');
    });

    test('should process ping message', () => {
        const response = server.processTextMessage(client, {
            type: 'ping'
        });

        expect(response.type).toBe('pong');
        expect(response.timestamp).toBeDefined();
    });

    test('should handle unknown message type', () => {
        const response = server.processTextMessage(client, {
            type: 'unknown'
        });

        expect(response.type).toBe('error');
    });

    test('should reject enrollment start without init', () => {
        const response = server.processTextMessage(client, {
            type: 'start-enrollment'
        });

        expect(response.type).toBe('error');
    });
});

describe('WebSocket Handler Integration - Audio Processing', () => {
    let server, client;

    beforeEach(() => {
        server = new MockWebSocketServer();
        client = server.simulateClientConnection('testuser');
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });
    });

    afterEach(() => {
        server.clients.clear();
    });

    test('should accumulate audio data', () => {
        const chunk1 = Buffer.from([1, 2, 3, 4]);
        const chunk2 = Buffer.from([5, 6, 7, 8]);

        server.processAudioData(client, chunk1);
        expect(client.audioBuffer.length).toBe(4);

        server.processAudioData(client, chunk2);
        expect(client.audioBuffer.length).toBe(8);
    });

    test('should reject audio exceeding size limit', () => {
        const hugeBuffer = Buffer.alloc(6 * 1024 * 1024);
        const result = server.processAudioData(client, hugeBuffer);

        expect(result).toBe(false);
    });

    test('should maintain audio data integrity', () => {
        const originalData = Buffer.from([0x52, 0x49, 0x46, 0x46]);
        server.processAudioData(client, originalData);

        expect(client.audioBuffer.slice(0, 4)).toEqual(originalData);
    });

    test('should process empty audio gracefully', async () => {
        const result = await server.completeAudioProcessing(client);

        expect(result.success).toBe(false);
        expect(result.error).toBeDefined();
    });

    test('should process audio and update session', async () => {
        const audioData = Buffer.alloc(1000);
        server.processAudioData(client, audioData);

        const result = await server.completeAudioProcessing(client);

        expect(result.success).toBe(true);
        expect(result.audioProcessed).toBe(1000);
        expect(client.audioBuffer.length).toBe(0);
    });

    test('should clear buffer after processing', async () => {
        server.processAudioData(client, Buffer.alloc(500));
        expect(client.audioBuffer.length).toBe(500);

        await server.completeAudioProcessing(client);
        expect(client.audioBuffer.length).toBe(0);
    });
});

describe('WebSocket Handler Integration - Session Management', () => {
    let server, client;

    beforeEach(() => {
        server = new MockWebSocketServer();
        client = server.simulateClientConnection('testuser');
    });

    afterEach(() => {
        server.clients.clear();
    });

    test('should create session on initialization', () => {
        const response = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        expect(response.sessionId).toBeDefined();
        const session = server.sessionManager.getSession(response.sessionId);
        expect(session).toBeDefined();
        expect(session.userId).toBe('user123');
    });

    test('should track session metadata', () => {
        const response = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll',
            language: 'es'
        });

        const session = server.sessionManager.getSession(response.sessionId);
        expect(session.metadata.action).toBe('enroll');
        expect(session.metadata.language).toBe('es');
    });

    test('should link client to session', () => {
        const response = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        expect(client.sessionData.sessionId).toBe(response.sessionId);
    });

    test('should track multiple user sessions', () => {
        const client1 = server.simulateClientConnection('user1');
        const client2 = server.simulateClientConnection('user2');

        server.processTextMessage(client1, {
            type: 'init',
            userId: 'user1',
            action: 'enroll'
        });

        server.processTextMessage(client2, {
            type: 'init',
            userId: 'user2',
            action: 'verify'
        });

        const user1Sessions = server.sessionManager.userSessions.get('user1');
        const user2Sessions = server.sessionManager.userSessions.get('user2');

        expect(user1Sessions.size).toBe(1);
        expect(user2Sessions.size).toBe(1);
    });

    test('should update session with audio processing metadata', async () => {
        const response = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        server.processAudioData(client, Buffer.alloc(1000));
        await server.completeAudioProcessing(client);

        const session = server.sessionManager.getSession(response.sessionId);
        expect(session.metadata.audioProcessed).toBe(true);
        expect(session.metadata.audioSize).toBe(1000);
    });
});

describe('WebSocket Handler Integration - Event Handler Integration', () => {
    let server, client, eventLog;

    beforeEach(() => {
        eventLog = [];
        server = new MockWebSocketServer();
        
        server.sessionManager.on('session:created', (data) => {
            eventLog.push({ type: 'session:created', data });
        });
        server.sessionManager.on('session:updated', (data) => {
            eventLog.push({ type: 'session:updated', data });
        });
        
        client = server.simulateClientConnection('testuser');
    });

    afterEach(() => {
        server.clients.clear();
        eventLog = [];
    });

    test('should emit session:created event', () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        expect(eventLog.length).toBeGreaterThan(0);
        expect(eventLog[0].type).toBe('session:created');
        expect(eventLog[0].data.userId).toBe('user123');
    });

    test('should emit session:updated event on audio processing', async () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        eventLog = []; // Clear after init

        server.processAudioData(client, Buffer.alloc(1000));
        await server.completeAudioProcessing(client);

        const updatedEvent = eventLog.find(e => e.type === 'session:updated');
        expect(updatedEvent).toBeDefined();
    });

    test('should track event data correctly', () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const createdEvent = eventLog[0];
        expect(createdEvent.data.sessionId).toBeDefined();
        expect(createdEvent.data.userId).toBe('user123');
    });
});

describe('WebSocket Handler Integration - Stress & Scale', () => {
    let server;

    beforeEach(() => {
        server = new MockWebSocketServer();
    });

    afterEach(() => {
        server.clients.clear();
    });

    test('should handle 50 concurrent connections', () => {
        const clients = [];
        for (let i = 0; i < 50; i++) {
            clients.push(server.simulateClientConnection(`user${i}`));
        }

        expect(server.clients.size).toBe(50);
    });

    test('should handle sequential messaging', () => {
        const client = server.simulateClientConnection('user123');
        let response;

        response = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });
        expect(response.type).toBe('initialized');

        response = server.processTextMessage(client, {
            type: 'start-enrollment'
        });
        expect(response.type).toBe('enrollment-started');

        response = server.processTextMessage(client, {
            type: 'get-status'
        });
        expect(response.type).toBe('status');
    });

    test('should handle rapid ping messages', () => {
        const client = server.simulateClientConnection('user123');
        
        for (let i = 0; i < 100; i++) {
            const response = server.processTextMessage(client, {
                type: 'ping'
            });
            expect(response.type).toBe('pong');
        }
    });

    test('should handle large audio chunks', () => {
        const client = server.simulateClientConnection('user123');
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const largeAudio = Buffer.alloc(1024 * 1024, 'audio data');
        server.processAudioData(client, largeAudio);

        expect(client.audioBuffer.length).toBe(1024 * 1024);
    });

    test('should handle multiple clients with different operations', () => {
        const clients = [];
        
        for (let i = 0; i < 10; i++) {
            const c = server.simulateClientConnection(`user${i}`);
            
            if (i % 2 === 0) {
                server.processTextMessage(c, {
                    type: 'init',
                    userId: `user${i}`,
                    action: 'enroll'
                });
            } else {
                server.processTextMessage(c, {
                    type: 'init',
                    userId: `user${i}`,
                    action: 'verify'
                });
            }
            
            clients.push(c);
        }

        expect(server.clients.size).toBe(10);
        expect(server.sessionManager.sessions.size).toBe(10);
    });
});

module.exports = { MockWebSocketServer };
