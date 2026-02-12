/**
 * Session Manager Usage Guide and Examples
 * Integration examples for voice biometric authentication system
 */

const { SessionManager, MemoryPersistenceStore } = require('./session-manager');

/**
 * Example 1: Basic Session Manager Initialization
 */
function exampleBasicInitialization() {
    console.log('\n=== Example 1: Basic Initialization ===\n');

    // Create session manager with default options
    const sessionManager = new SessionManager({
        sessionTimeout: 30 * 60 * 1000, // 30 minutes
        cleanupInterval: 5 * 60 * 1000,  // 5 minutes
        maxSessions: 1000
    });

    // Create a session
    const session = sessionManager.createSession('user123', {
        action: 'enrollment',
        language: 'en',
        ipAddress: '192.168.1.1'
    });

    console.log('Created Session:', {
        sessionId: session.sessionId,
        userId: session.userId,
        action: session.metadata.action
    });

    return sessionManager;
}

/**
 * Example 2: WebSocket Handler Integration
 */
function exampleWebSocketIntegration() {
    console.log('\n=== Example 2: WebSocket Integration ===\n');

    const sessionManager = new SessionManager({
        sessionTimeout: 30 * 60 * 1000,
        cleanupInterval: 5 * 60 * 1000
    });

    // Listen for session events
    sessionManager.on('session:created', (data) => {
        console.log(`✓ Session created: ${data.sessionId}`);
    });

    sessionManager.on('session:expired', (data) => {
        console.log(`⚠ Session expired: ${data.sessionId}`);
    });

    sessionManager.on('session:destroyed', (data) => {
        console.log(`✗ Session destroyed: ${data.sessionId}`);
    });

    // Simulated WebSocket message handler
    function handleWebSocketMessage(ws, data) {
        const { type, userId, action, sessionId } = data;

        if (type === 'init') {
            // Create new session
            const session = sessionManager.createSession(userId, {
                action,
                connectionId: ws.id,
                userAgent: 'WebSocket Client'
            });

            ws.send(JSON.stringify({
                type: 'session-ready',
                sessionId: session.sessionId
            }));
        }

        if (type === 'audio-chunk') {
            // Validate session and append audio
            const validation = sessionManager.validateSession(sessionId);

            if (validation.valid) {
                const bufferSize = sessionManager.appendAudioData(sessionId, data.chunk);
                console.log(`Audio chunk appended - Total size: ${bufferSize} bytes`);
            } else {
                ws.send(JSON.stringify({
                    type: 'error',
                    message: validation.message
                }));
            }
        }
    }

    return sessionManager;
}

/**
 * Example 3: Session CRUD Operations
 */
function exampleSessionCRUD() {
    console.log('\n=== Example 3: Session CRUD Operations ===\n');

    const sessionManager = new SessionManager();

    // Create session
    const session = sessionManager.createSession('user456', {
        action: 'verification',
        language: 'es'
    });
    console.log('1. Created:', session.sessionId);

    // Get session
    const retrieved = sessionManager.getSession(session.sessionId);
    console.log('2. Retrieved:', retrieved.userId, retrieved.metadata.action);

    // Update session
    const updated = sessionManager.updateSession(session.sessionId, {
        metadata: {
            recordingDuration: 5000
        }
    });
    console.log('3. Updated - Recording Duration:', updated.metadata.recordingDuration);

    // Get user's all sessions
    sessionManager.createSession('user456', { action: 'enrollment' });
    const userSessions = sessionManager.getUserSessions('user456');
    console.log('4. User Sessions Count:', userSessions.length);

    // Destroy session
    const destroyed = sessionManager.destroySession(session.sessionId);
    console.log('5. Destroyed:', destroyed);

    return sessionManager;
}

/**
 * Example 4: Audio Buffer Management
 */
function exampleAudioBufferManagement() {
    console.log('\n=== Example 4: Audio Buffer Management ===\n');

    const sessionManager = new SessionManager();

    const session = sessionManager.createSession('user789', {
        action: 'enrollment'
    });

    // Append audio chunks
    const chunk1 = Buffer.from('AUDIO_DATA_CHUNK_1');
    const chunk2 = Buffer.from('AUDIO_DATA_CHUNK_2');
    const chunk3 = Buffer.from('AUDIO_DATA_CHUNK_3');

    let size = sessionManager.appendAudioData(session.sessionId, chunk1);
    console.log('Appended chunk 1 - Total size:', size);

    size = sessionManager.appendAudioData(session.sessionId, chunk2);
    console.log('Appended chunk 2 - Total size:', size);

    size = sessionManager.appendAudioData(session.sessionId, chunk3);
    console.log('Appended chunk 3 - Total size:', size);

    // Get audio buffer
    const audioBuffer = sessionManager.getAudioBuffer(session.sessionId);
    console.log('Audio buffer size:', audioBuffer.length);
    console.log('Audio buffer content:', audioBuffer.toString());

    // Clear audio buffer
    const cleared = sessionManager.clearAudioBuffer(session.sessionId);
    console.log('Audio buffer cleared:', cleared);
    console.log('New buffer size:', sessionManager.getAudioBuffer(session.sessionId).length);

    return sessionManager;
}

/**
 * Example 5: Session Validation and Export
 */
function exampleValidationAndExport() {
    console.log('\n=== Example 5: Validation and Export ===\n');

    const sessionManager = new SessionManager();

    const session = sessionManager.createSession('user999', {
        action: 'verification',
        language: 'fr'
    });

    // Validate session
    const validation = sessionManager.validateSession(session.sessionId);
    console.log('Validation result:', validation);

    // Export session data
    const exported = sessionManager.exportSession(session.sessionId);
    console.log('Exported session:', exported);

    // Try to validate non-existent session
    const invalidValidation = sessionManager.validateSession('invalid_session');
    console.log('Invalid session validation:', invalidValidation);

    return sessionManager;
}

/**
 * Example 6: Session Statistics and Monitoring
 */
function exampleStatisticsAndMonitoring() {
    console.log('\n=== Example 6: Statistics and Monitoring ===\n');

    const sessionManager = new SessionManager();

    // Create multiple sessions
    sessionManager.createSession('user1', { action: 'enrollment' });
    sessionManager.createSession('user2', { action: 'verification' });
    sessionManager.createSession('user3', { action: 'enrollment' });
    sessionManager.createSession('user1', { action: 'verification' });

    // Get statistics
    const stats = sessionManager.getStatistics();
    console.log('Session Statistics:');
    console.log(`  Total Sessions: ${stats.totalSessions}`);
    console.log(`  Active Sessions: ${stats.activeSessions}`);
    console.log(`  Total Users: ${stats.totalUsers}`);
    console.log(`  Sessions by Status:`, stats.sessionsByStatus);

    return sessionManager;
}

/**
 * Example 7: Event Listeners and Callbacks
 */
function exampleEventListeners() {
    console.log('\n=== Example 7: Event Listeners ===\n');

    const sessionManager = new SessionManager({
        sessionTimeout: 2000, // 2 seconds for demo
        cleanupInterval: 1000  // 1 second for demo
    });

    // Listen for all events
    sessionManager.on('session:created', (data) => {
        console.log('📝 Event - Session Created:', data.sessionId);
    });

    sessionManager.on('session:updated', (data) => {
        console.log('✏️  Event - Session Updated:', data.sessionId);
    });

    sessionManager.on('session:expired', (data) => {
        console.log('⏰ Event - Session Expired:', data.sessionId);
    });

    sessionManager.on('session:destroyed', (data) => {
        console.log('🗑️  Event - Session Destroyed:', data.sessionId);
    });

    sessionManager.on('cleanup:completed', (data) => {
        console.log('🧹 Event - Cleanup Completed - Removed:', data.removedCount);
    });

    // Create a session
    const session = sessionManager.createSession('testuser', {
        action: 'enrollment'
    });

    // Update session
    setTimeout(() => {
        sessionManager.updateSession(session.sessionId, {
            metadata: { step: 'processing' }
        });
    }, 500);

    // Cleanup events will occur after sessionTimeout
    return sessionManager;
}

/**
 * Example 8: Advanced - Persistence Store
 */
function examplePersistenceStore() {
    console.log('\n=== Example 8: Persistence Store ===\n');

    const persistenceStore = new MemoryPersistenceStore();

    const sessionManager = new SessionManager({
        enablePersistence: true,
        persistenceStore: persistenceStore
    });

    // Create session (will be persisted)
    const session = sessionManager.createSession('persistuser', {
        action: 'enrollment'
    });

    console.log('Created session (persisted):', session.sessionId);

    // Get persisted sessions
    const persistedSessions = persistenceStore.getAll();
    console.log('Persisted sessions count:', persistedSessions.length);

    // Update session (updates persistence)
    sessionManager.updateSession(session.sessionId, {
        metadata: { status: 'processing' }
    });

    console.log('Session updated in persistence');

    return { sessionManager, persistenceStore };
}

/**
 * Example 9: Multi-User Session Management
 */
function exampleMultiUserManagement() {
    console.log('\n=== Example 9: Multi-User Management ===\n');

    const sessionManager = new SessionManager();

    // Create sessions for multiple users
    const users = ['alice', 'bob', 'charlie', 'diana'];
    const actions = ['enrollment', 'verification'];

    users.forEach(user => {
        actions.forEach(action => {
            sessionManager.createSession(user, { action });
        });
    });

    // Get sessions for specific user
    const aliceSessions = sessionManager.getUserSessions('alice');
    console.log(`Alice's sessions: ${aliceSessions.length}`);
    aliceSessions.forEach(s => {
        console.log(`  - ${s.sessionId}: ${s.metadata.action}`);
    });

    // Destroy all sessions for a user
    const destroyedCount = sessionManager.destroyUserSessions('bob');
    console.log(`Destroyed Bob's sessions: ${destroyedCount}`);

    // Show remaining stats
    const stats = sessionManager.getStatistics();
    console.log('Remaining statistics:', {
        totalSessions: stats.totalSessions,
        totalUsers: stats.totalUsers
    });

    return sessionManager;
}

/**
 * Example 10: WebSocket Handler Wrapper
 */
class WebSocketSessionHandler {
    constructor(sessionManager) {
        this.sessionManager = sessionManager;
        this.wsSessionMap = new Map(); // Map WebSocket connection ID to session ID
    }

    /**
     * Handle WebSocket connection
     */
    onConnect(wsId) {
        console.log(`WebSocket connected: ${wsId}`);
    }

    /**
     * Handle WebSocket initialization with session
     */
    onInitialize(wsId, userId, action) {
        try {
            const session = this.sessionManager.createSession(userId, {
                action,
                connectionId: wsId,
                userAgent: 'WebSocket'
            });

            this.wsSessionMap.set(wsId, session.sessionId);

            console.log(`Session initialized for WS ${wsId}: ${session.sessionId}`);
            return session;
        } catch (error) {
            console.error(`Failed to initialize session: ${error.message}`);
            return null;
        }
    }

    /**
     * Handle WebSocket message
     */
    onMessage(wsId, message) {
        const sessionId = this.wsSessionMap.get(wsId);

        if (!sessionId) {
            console.error(`No session found for WS ${wsId}`);
            return null;
        }

        const validation = this.sessionManager.validateSession(sessionId);

        if (!validation.valid) {
            console.error(`Session validation failed: ${validation.message}`);
            return null;
        }

        return validation.session;
    }

    /**
     * Handle WebSocket disconnection
     */
    onDisconnect(wsId) {
        const sessionId = this.wsSessionMap.get(wsId);

        if (sessionId) {
            this.sessionManager.destroySession(sessionId);
            this.wsSessionMap.delete(wsId);
            console.log(`Session destroyed for WS ${wsId}`);
        }
    }

    /**
     * Send audio chunk with session validation
     */
    sendAudioChunk(wsId, audioChunk) {
        const sessionId = this.wsSessionMap.get(wsId);

        if (!sessionId) {
            throw new Error('No session for this WebSocket');
        }

        try {
            const bufferSize = this.sessionManager.appendAudioData(sessionId, audioChunk);
            return bufferSize;
        } catch (error) {
            console.error(`Error appending audio: ${error.message}`);
            throw error;
        }
    }
}

/**
 * Example 10 Usage
 */
function exampleWebSocketSessionHandler() {
    console.log('\n=== Example 10: WebSocket Handler Wrapper ===\n');

    const sessionManager = new SessionManager();
    const wsHandler = new WebSocketSessionHandler(sessionManager);

    // Simulate WebSocket connections
    const ws1 = 'ws_conn_001';
    const ws2 = 'ws_conn_002';

    wsHandler.onConnect(ws1);
    wsHandler.onConnect(ws2);

    // Initialize sessions
    const session1 = wsHandler.onInitialize(ws1, 'user_A', 'enrollment');
    const session2 = wsHandler.onInitialize(ws2, 'user_B', 'verification');

    console.log('Session 1:', session1.sessionId);
    console.log('Session 2:', session2.sessionId);

    // Send audio chunks
    const audioChunk = Buffer.from('MOCK_AUDIO_DATA');
    let bufferSize = wsHandler.sendAudioChunk(ws1, audioChunk);
    console.log(`\nAudio sent via WS1 - Buffer size: ${bufferSize}`);

    bufferSize = wsHandler.sendAudioChunk(ws2, audioChunk);
    console.log(`Audio sent via WS2 - Buffer size: ${bufferSize}`);

    // Disconnect
    wsHandler.onDisconnect(ws1);
    console.log('\nWS1 disconnected');

    // Verify session is destroyed
    const validation = sessionManager.validateSession(session1.sessionId);
    console.log('Validation for destroyed session:', validation.valid);

    return sessionManager;
}

/**
 * Run all examples (commented out - uncomment to run)
 */
if (require.main === module) {
    console.log('========================================');
    console.log('   Session Manager Usage Examples');
    console.log('========================================');

    // Uncomment to run examples:
    // exampleBasicInitialization();
    // exampleWebSocketIntegration();
    // exampleSessionCRUD();
    // exampleAudioBufferManagement();
    // exampleValidationAndExport();
    // exampleStatisticsAndMonitoring();
    // exampleEventListeners();
    // examplePersistenceStore();
    // exampleMultiUserManagement();
    // exampleWebSocketSessionHandler();

    console.log('\n========================================');
    console.log('   Run individual examples by uncommenting');
    console.log('========================================\n');
}

module.exports = {
    exampleBasicInitialization,
    exampleWebSocketIntegration,
    exampleSessionCRUD,
    exampleAudioBufferManagement,
    exampleValidationAndExport,
    exampleStatisticsAndMonitoring,
    exampleEventListeners,
    examplePersistenceStore,
    exampleMultiUserManagement,
    exampleWebSocketSessionHandler,
    WebSocketSessionHandler
};
