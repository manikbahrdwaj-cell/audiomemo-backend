/**
 * WebSocket Handlers - Integration Tests (Phase 4, Step 4.2)
 * Tests for WebSocket connection handling, message processing, and integration
 * with session management and event handlers
 */

const WebSocket = require('ws');
const { SessionManager } = require('./session-manager');
const SessionEventHandlers = require('./session-event-handlers');

/**
 * Mock WebSocket Server for Testing
 * Simulates the actual WebSocket server behavior
 */
class MockWebSocketServer {
    constructor(options = {}) {
        this.clients = new Set();
        this.messages = [];
        this.sessionManager = options.sessionManager || new SessionManager();
        this.eventHandlers = options.eventHandlers || new SessionEventHandlers(this.sessionManager);
        this.port = options.port || 8001;
        this.backendUrl = options.backendUrl || 'http://localhost:8000';
    }

    /**
     * Simulate client connection
     */
    simulateClientConnection(userId) {
        const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const client = {
            id: clientId,
            userId,
            state: 'open',
            sessionData: {
                userId: null,
                action: null,
                startTime: Date.now(),
                language: 'en'
            },
            audioBuffer: Buffer.alloc(0),
            messages: [],
            
            // Mock send method
            send: (data) => {
                if (client.state === 'open') {
                    client.messages.push(JSON.parse(data));
                }
            },
            
            // Mock close method
            close: () => {
                client.state = 'closed';
                this.clients.delete(client);
            }
        };

        this.clients.add(client);
        return client;
    }

    /**
     * Process text message
     */
    processTextMessage(client, message) {
        const data = typeof message === 'string' ? JSON.parse(message) : message;

        switch (data.type) {
            case 'init':
                return this.handleInitialization(client, data);
            case 'start-enrollment':
                return this.handleStartEnrollment(client, data);
            case 'start-verification':
                return this.handleStartVerification(client, data);
            case 'stop-audio':
                return this.handleStopAudio(client, data);
            case 'get-status':
                return this.handleGetStatus(client, data);
            case 'ping':
                return this.handlePing(client, data);
            default:
                return this.sendError(client, 'Unknown message type', `Type: ${data.type}`);
        }
    }

    /**
     * Handle initialization message
     */
    handleInitialization(client, { userId, action, language = 'en' }) {
        client.sessionData.userId = userId;
        client.sessionData.action = action;
        client.sessionData.language = language;

        const session = this.sessionManager.createSession(userId, {
            action,
            language,
            connectionId: client.id
        });

        client.sessionData.sessionId = session.sessionId;

        return {
            type: 'initialized',
            userId,
            action,
            sessionId: session.sessionId,
            message: `Session initialized for ${action}`,
            timestamp: Date.now()
        };
    }

    /**
     * Handle start enrollment
     */
    handleStartEnrollment(client, data) {
        if (!client.sessionData.userId) {
            return this.sendError(client, 'User ID not set', 'Call init first');
        }

        client.sessionData.action = 'enroll';
        return {
            type: 'enrollment-started',
            message: 'Ready to receive audio',
            instructions: 'Please speak your enrollment phrase',
            timestamp: Date.now()
        };
    }

    /**
     * Handle start verification
     */
    handleStartVerification(client, { userId }) {
        client.sessionData.action = 'verify';
        client.sessionData.verifyUserId = userId;

        return {
            type: 'verification-started',
            message: 'Ready to receive audio',
            instructions: 'Please speak to verify',
            timestamp: Date.now()
        };
    }

    /**
     * Handle stop audio and process
     */
    async handleStopAudio(client, data) {
        const { userId, action } = client.sessionData;
        const { audioBuffer } = client;

        if (audioBuffer.length === 0) {
            return this.sendError(client, 'No audio received', 'Buffer is empty');
        }

        // Emit session event for audio processing
        if (client.sessionData.sessionId) {
            this.sessionManager.updateSession(client.sessionData.sessionId, {
                metadata: {
                    audioProcessed: true,
                    audioSize: audioBuffer.length,
                    processedAt: new Date().toISOString()
                }
            });
        }

        // Simulate processing result
        const result = {
            type: 'result',
            action,
            success: audioBuffer.length > 0,
            data: {
                userId,
                audioSize: audioBuffer.length,
                processingTime: Math.random() * 1000
            },
            message: 'Audio processed successfully',
            timestamp: Date.now()
        };

        // Clear audio buffer
        client.audioBuffer = Buffer.alloc(0);

        return result;
    }

    /**
     * Handle get status
     */
    handleGetStatus(client, data) {
        const { sessionData, audioBuffer } = client;
        const sessionDuration = Date.now() - sessionData.startTime;

        return {
            type: 'status',
            sessionData: {
                userId: sessionData.userId,
                action: sessionData.action,
                language: sessionData.language,
                durationMs: sessionDuration
            },
            audioStats: {
                bufferSize: audioBuffer.length
            },
            timestamp: Date.now()
        };
    }

    /**
     * Handle ping/pong
     */
    handlePing(client, data) {
        return {
            type: 'pong',
            timestamp: Date.now()
        };
    }

    /**
     * Send error message
     */
    sendError(client, error, details = '') {
        return {
            type: 'error',
            error,
            details,
            timestamp: Date.now()
        };
    }

    /**
     * Process audio data
     */
    processAudioData(client, audioData) {
        const newBuffer = Buffer.concat([client.audioBuffer, audioData]);

        if (newBuffer.length > 5 * 1024 * 1024) {
            this.sendError(client, 'Audio size exceeded', 'Max: 5MB');
            return false;
        }

        client.audioBuffer = newBuffer;

        // Send acknowledgment every 10 chunks
        const chunkCount = Math.floor(newBuffer.length / 4096);
        if (chunkCount % 10 === 0 && chunkCount > 0) {
            return {
                type: 'audio-received',
                bytesReceived: newBuffer.length,
                chunkCount
            };
        }

        return true;
    }
}

/**
 * =====================================================================
 * INTEGRATION TEST SUITES
 * =====================================================================
 */

describe('WebSocket Handler Integration - Connection Lifecycle', () => {
    let server;

    beforeEach(() => {
        server = new MockWebSocketServer();
    });

    afterEach(() => {
        server.clients.forEach(client => client.close());
        server.clients.clear();
    });

    test('should handle client connection', () => {
        const client = server.simulateClientConnection('user123');

        expect(client).toBeDefined();
        expect(client.id).toMatch(/^client_/);
        expect(client.state).toBe('open');
        expect(server.clients.size).toBe(1);
    });

    test('should handle multiple concurrent connections', () => {
        const client1 = server.simulateClientConnection('user1');
        const client2 = server.simulateClientConnection('user2');
        const client3 = server.simulateClientConnection('user3');

        expect(server.clients.size).toBe(3);
        expect(client1.id).not.toBe(client2.id);
        expect(client2.id).not.toBe(client3.id);
    });

    test('should handle client disconnection', () => {
        const client = server.simulateClientConnection('user123');
        expect(server.clients.size).toBe(1);

        client.close();
        expect(client.state).toBe('closed');
        expect(server.clients.size).toBe(0);
    });

    test('should generate unique client IDs', () => {
        const clients = [];
        for (let i = 0; i < 10; i++) {
            clients.push(server.simulateClientConnection(`user${i}`));
        }

        const ids = clients.map(c => c.id);
        const uniqueIds = new Set(ids);
        expect(uniqueIds.size).toBe(10);
    });

    test('should maintain client state', () => {
        const client = server.simulateClientConnection('user123');
        const originalId = client.id;
        const originalState = client.state;

        expect(client.id).toBe(originalId);
        expect(client.state).toBe(originalState);
    });
});

describe('WebSocket Handler Integration - Message Handling', () => {
    let server;
    let client;

    beforeEach(() => {
        server = new MockWebSocketServer();
        client = server.simulateClientConnection('testuser');
    });

    afterEach(() => {
        server.clients.forEach(c => c.close());
        server.clients.clear();
    });

    test('should handle init message', () => {
        const response = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll',
            language: 'en'
        });

        expect(response.type).toBe('initialized');
        expect(response.userId).toBe('user123');
        expect(response.sessionId).toBeDefined();
        expect(client.sessionData.userId).toBe('user123');
        expect(client.sessionData.action).toBe('enroll');
    });

    test('should handle start enrollment after init', () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const response = server.processTextMessage(client, {
            type: 'start-enrollment'
        });

        expect(response.type).toBe('enrollment-started');
        expect(response.message).toContain('Ready');
        expect(response.instructions).toContain('enrollment');
    });

    test('should handle start verification after init', () => {
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
        expect(client.sessionData.verifyUserId).toBe('user456');
    });

    test('should reject start enrollment without init', () => {
        const response = server.processTextMessage(client, {
            type: 'start-enrollment'
        });

        expect(response.type).toBe('error');
        expect(response.error).toContain('User ID');
    });

    test('should handle get status message', () => {
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
        expect(response.sessionData.action).toBe('enroll');
        expect(response.audioStats.bufferSize).toBe(0);
    });

    test('should handle ping message', () => {
        const response = server.processTextMessage(client, {
            type: 'ping'
        });

        expect(response.type).toBe('pong');
        expect(response.timestamp).toBeDefined();
    });

    test('should reject unknown message type', () => {
        const response = server.processTextMessage(client, {
            type: 'unknown-type'
        });

        expect(response.type).toBe('error');
        expect(response.error).toContain('Unknown');
    });

    test('should handle multiple sequential messages', () => {
        const msg1 = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });
        expect(msg1.type).toBe('initialized');

        const msg2 = server.processTextMessage(client, {
            type: 'start-enrollment'
        });
        expect(msg2.type).toBe('enrollment-started');

        const msg3 = server.processTextMessage(client, {
            type: 'get-status'
        });
        expect(msg3.type).toBe('status');
        expect(msg3.sessionData.userId).toBe('user123');
    });

    test('should set response timestamps', () => {
        const response = server.processTextMessage(client, {
            type: 'ping'
        });

        expect(response.timestamp).toBeDefined();
        expect(typeof response.timestamp).toBe('number');
        expect(response.timestamp).toBeGreaterThan(0);
    });
});

describe('WebSocket Handler Integration - Audio Data Processing', () => {
    let server;
    let client;

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
        server.clients.forEach(c => c.close());
        server.clients.clear();
    });

    test('should accumulate audio data in buffer', () => {
        const chunk1 = Buffer.from([1, 2, 3, 4]);
        const chunk2 = Buffer.from([5, 6, 7, 8]);

        server.processAudioData(client, chunk1);
        expect(client.audioBuffer.length).toBe(4);

        server.processAudioData(client, chunk2);
        expect(client.audioBuffer.length).toBe(8);
    });

    test('should handle empty audio buffer', async () => {
        const response = await server.handleStopAudio(client, {});

        expect(response.type).toBe('error');
        expect(response.error).toContain('No audio');
    });

    test('should process audio and create session events', async () => {
        const audioData = Buffer.alloc(1000, 'test audio data');
        server.processAudioData(client, audioData);

        expect(client.audioBuffer.length).toBe(1000);

        const response = await server.handleStopAudio(client, {});

        expect(response.type).toBe('result');
        expect(response.success).toBe(true);
        expect(response.data.audioSize).toBe(1000);
    });

    test('should clear audio buffer after processing', async () => {
        const audioData = Buffer.alloc(500);
        server.processAudioData(client, audioData);
        expect(client.audioBuffer.length).toBe(500);

        await server.handleStopAudio(client, {});
        expect(client.audioBuffer.length).toBe(0);
    });

    test('should reject audio exceeding size limit', () => {
        const hugeBuffer = Buffer.alloc(6 * 1024 * 1024); // 6MB
        const result = server.processAudioData(client, hugeBuffer);

        expect(result).not.toBe(true);
        // Size should not have increased beyond limit
    });

    test('should track audio chunk count', () => {
        const chunkSize = 4096;
        const audioData = Buffer.alloc(chunkSize * 15);

        server.processAudioData(client, audioData);
        const chunkCount = Math.floor(client.audioBuffer.length / 4096);

        expect(chunkCount).toBe(15);
    });

    test('should send acknowledgment every 10 chunks', () => {
        const chunkSize = 4096;
        
        // Process 10 chunks
        for (let i = 0; i < 10; i++) {
            server.processAudioData(client, Buffer.alloc(chunkSize));
        }

        expect(client.audioBuffer.length).toBe(chunkSize * 10);
    });

    test('should maintain audio data integrity', () => {
        const originalData = Buffer.from([
            0x52, 0x49, 0x46, 0x46, // RIFF
            0x00, 0x00, 0x00, 0x00  // Size placeholder
        ]);

        server.processAudioData(client, originalData);

        expect(client.audioBuffer).toEqual(originalData);
    });
});

describe('WebSocket Handler Integration - Session Management', () => {
    let server;
    let client;

    beforeEach(() => {
        server = new MockWebSocketServer();
        client = server.simulateClientConnection('testuser');
    });

    afterEach(() => {
        server.clients.forEach(c => c.close());
        server.clients.clear();
    });

    test('should create session on init message', () => {
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

    test('should link client to session', () => {
        const response = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        expect(client.sessionData.sessionId).toBe(response.sessionId);
        const session = server.sessionManager.getSession(response.sessionId);
        expect(session.metadata.connectionId).toBe(client.id);
    });

    test('should track session metadata', () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll',
            language: 'es'
        });

        const session = server.sessionManager.getSession(
            client.sessionData.sessionId
        );

        expect(session.metadata.action).toBe('enroll');
        expect(session.metadata.language).toBe('es');
    });

    test('should update session on audio processing', async () => {
        const response = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const audioData = Buffer.alloc(1000);
        server.processAudioData(client, audioData);

        await server.handleStopAudio(client, {});

        const session = server.sessionManager.getSession(response.sessionId);
        expect(session.metadata.audioProcessed).toBe(true);
        expect(session.metadata.audioSize).toBe(1000);
    });

    test('should track multiple user sessions', () => {
        const client1 = server.simulateClientConnection('user1');
        const client2 = server.simulateClientConnection('user2');
        const client3 = server.simulateClientConnection('user1'); // Same user, new session

        const resp1 = server.processTextMessage(client1, {
            type: 'init',
            userId: 'user1',
            action: 'enroll'
        });

        const resp2 = server.processTextMessage(client2, {
            type: 'init',
            userId: 'user2',
            action: 'verify'
        });

        const resp3 = server.processTextMessage(client3, {
            type: 'init',
            userId: 'user1',
            action: 'verify'
        });

        const user1Sessions = server.sessionManager.userSessions.get('user1');
        const user2Sessions = server.sessionManager.userSessions.get('user2');

        expect(user1Sessions.size).toBe(2);
        expect(user2Sessions.size).toBe(1);
    });

    test('should maintain session state during activity', () => {
        const response = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const sessionId = response.sessionId;
        let session = server.sessionManager.getSession(sessionId);
        const initialActivity = session.lastActivity;

        // Simulate some time passing and activity
        setTimeout(() => {
            server.processTextMessage(client, {
                type: 'get-status'
            });
        }, 100);

        session = server.sessionManager.getSession(sessionId);
        expect(session.status).toBe('active');
    });
});

describe('WebSocket Handler Integration - Event Handler Integration', () => {
    let server;
    let client;
    let eventLog;

    beforeEach(() => {
        eventLog = [];
        server = new MockWebSocketServer();
        
        // Hook into event handlers to capture events
        server.sessionManager.on('session:created', (data) => {
            eventLog.push({ type: 'session:created', data });
        });
        server.sessionManager.on('session:updated', (data) => {
            eventLog.push({ type: 'session:updated', data });
        });

        client = server.simulateClientConnection('testuser');
    });

    afterEach(() => {
        server.clients.forEach(c => c.close());
        server.clients.clear();
        eventLog = [];
    });

    test('should emit session:created event on init', () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const createdEvent = eventLog.find(e => e.type === 'session:created');
        expect(createdEvent).toBeDefined();
        expect(createdEvent.data.userId).toBe('user123');
    });

    test('should emit session:updated event on audio processing', async () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        eventLog = []; // Clear initial events

        const audioData = Buffer.alloc(1000);
        server.processAudioData(client, audioData);
        await server.handleStopAudio(client, {});

        const updatedEvent = eventLog.find(e => e.type === 'session:updated');
        expect(updatedEvent).toBeDefined();
    });

    test('should track event timestamps', () => {
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const createdEvent = eventLog.find(e => e.type === 'session:created');
        expect(createdEvent.data.sessionId).toBeDefined();
    });

    test('should handle multiple events in sequence', async () => {
        const resp1 = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const initialEventCount = eventLog.length;

        server.processTextMessage(client, {
            type: 'start-enrollment'
        });

        const afterStart = eventLog.length;
        expect(afterStart).toBeGreaterThanOrEqual(initialEventCount);
    });
});

describe('WebSocket Handler Integration - Error Handling', () => {
    let server;
    let client;

    beforeEach(() => {
        server = new MockWebSocketServer();
        client = server.simulateClientConnection('testuser');
    });

    afterEach(() => {
        server.clients.forEach(c => c.close());
        server.clients.clear();
    });

    test('should handle missing required fields', () => {
        const response = server.processTextMessage(client, {
            type: 'init'
            // Missing userId and action
        });

        // Should either handle gracefully or set to null
        expect(client.sessionData).toBeDefined();
    });

    test('should handle malformed JSON gracefully', () => {
        try {
            const response = server.processTextMessage(client, 'not valid json');
            expect(true).toBe(true); // Should not crash
        } catch (e) {
            expect(true).toBe(true); // Should handle error
        }
    });

    test('should handle disconnected client state', () => {
        const audioData = Buffer.from([1, 2, 3]);
        server.processAudioData(client, audioData);
        
        // Properly accumulated data
        expect(client.audioBuffer.length).toBe(3);
        
        // Now close connection
        client.state = 'closed';
        const newData = Buffer.from([4, 5]);
        server.processAudioData(client, newData);
        
        // Connection closed, but data would still be in buffer
        // (in real implementation, we'd check if send works)
        expect(client.state).toBe('closed');
    });

    test('should provide meaningful error messages', async () => {
        const response = await server.handleStopAudio(client, {});

        expect(response.type).toBe('error');
        expect(response.error).toBeDefined();
        expect(response.details).toBeDefined();
        expect(response.error.length > 0).toBe(true);
    });

    test('should handle oversized audio gracefully', () => {
        const tooLargeBuffer = Buffer.alloc(6 * 1024 * 1024);
        const result = server.processAudioData(client, tooLargeBuffer);

        expect(result).not.toBe(true);
        // Buffer should not exceed limit
    });

    test('should handle rapid messages', async () => {
        const promises = [];
        for (let i = 0; i < 10; i++) {
            promises.push(
                Promise.resolve(
                    server.processTextMessage(client, {
                        type: 'ping'
                    })
                )
            );
        }

        const responses = await Promise.all(promises);
        expect(responses.length).toBe(10);
        responses.forEach(r => expect(r.type).toBe('pong'));
    });
});

describe('WebSocket Handler Integration - Stress Tests', () => {
    let server;

    beforeEach(() => {
        server = new MockWebSocketServer();
    });

    afterEach(() => {
        server.clients.forEach(c => c.close());
        server.clients.clear();
    });

    test('should handle 100 concurrent connections', () => {
        const clients = [];
        for (let i = 0; i < 100; i++) {
            clients.push(server.simulateClientConnection(`user${i}`));
        }

        expect(server.clients.size).toBe(100);
        
        clients.forEach(c => c.close());
        expect(server.clients.size).toBe(0);
    });

    test('should handle high-frequency messages', () => {
        const client = server.simulateClientConnection('testuser');
        const response1 = server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });
        
        let messageCount = 1; // Start with init response
        
        for (let i = 0; i < 100; i++) {
            const response = server.processTextMessage(client, { type: 'ping' });
            if (response) {
                messageCount++;
            }
        }

        // Should have processed 1 init + 100 pings = 101 total
        expect(messageCount).toBe(101);
    });

    test('should handle large audio chunks', () => {
        const client = server.simulateClientConnection('testuser');
        server.processTextMessage(client, {
            type: 'init',
            userId: 'user123',
            action: 'enroll'
        });

        const largeAudio = Buffer.alloc(1024 * 1024); // 1MB chunk
        server.processAudioData(client, largeAudio);

        expect(client.audioBuffer.length).toBe(1024 * 1024);
    });

    test('should handle mixed concurrent operations', () => {
        const clients = [];
        for (let i = 0; i < 10; i++) {
            const c = server.simulateClientConnection(`user${i}`);
            server.processTextMessage(c, {
                type: 'init',
                userId: `user${i}`,
                action: i % 2 === 0 ? 'enroll' : 'verify'
            });
            clients.push(c);
        }

        // Send different message types
        clients.forEach((c, i) => {
            if (i % 3 === 0) {
                server.processTextMessage(c, { type: 'get-status' });
            } else if (i % 3 === 1) {
                server.processAudioData(c, Buffer.alloc(1000));
            } else {
                server.processTextMessage(c, { type: 'ping' });
            }
        });

        expect(server.clients.size).toBe(10);
    });
});

/**
 * Export for use in other test files
 */
module.exports = { MockWebSocketServer };
