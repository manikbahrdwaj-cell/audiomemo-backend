/**
 * Comprehensive Test Suite for Session Manager
 * Tests all functionality of the session management system
 */

const assert = require('assert');
const { SessionManager, MemoryPersistenceStore } = require('./session-manager');

class SessionManagerTests {
    constructor() {
        this.passed = 0;
        this.failed = 0;
        this.tests = [];
    }

    /**
     * Run a test
     */
    test(name, fn) {
        this.tests.push({ name, fn });
    }

    /**
     * Execute all tests
     */
    async run() {
        console.log('\n' + '='.repeat(60));
        console.log('Session Manager Test Suite');
        console.log('='.repeat(60) + '\n');

        for (const { name, fn } of this.tests) {
            try {
                const result = fn();
                // Handle promise-based async tests
                if (result && typeof result.then === 'function') {
                    await result;
                }
                this.passed++;
                console.log(`✓ ${name}`);
            } catch (error) {
                this.failed++;
                console.log(`✗ ${name}`);
                console.log(`  Error: ${error.message}\n`);
            }
        }

        this.printSummary();
    }

    /**
     * Print test summary
     */
    printSummary() {
        console.log('\n' + '='.repeat(60));
        console.log(`Tests: ${this.passed + this.failed} | Passed: ${this.passed} | Failed: ${this.failed}`);
        console.log('='.repeat(60) + '\n');
    }
}

// Initialize test suite
const suite = new SessionManagerTests();

// Test 1: Session Creation
suite.test('Create session with valid data', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', { action: 'enrollment' });

    assert(session.sessionId, 'Session ID should exist');
    assert.strictEqual(session.userId, 'user123', 'User ID should match');
    assert.strictEqual(session.metadata.action, 'enrollment', 'Action should match');
    assert.strictEqual(session.status, 'active', 'Status should be active');

    manager.shutdown();
});

// Test 2: Session ID Generation
suite.test('Session IDs should be unique', () => {
    const manager = new SessionManager();
    const session1 = manager.createSession('user1', {});
    const session2 = manager.createSession('user2', {});

    assert.notStrictEqual(session1.sessionId, session2.sessionId, 'Session IDs should be unique');

    manager.shutdown();
});

// Test 3: Retrieve session
suite.test('Get existing session', () => {
    const manager = new SessionManager();
    const created = manager.createSession('user123', { action: 'verification' });
    const retrieved = manager.getSession(created.sessionId);

    assert(retrieved, 'Session should be retrievable');
    assert.strictEqual(retrieved.userId, 'user123', 'Retrieved user should match');

    manager.shutdown();
});

// Test 4: Non-existent session
suite.test('Get non-existent session returns null', () => {
    const manager = new SessionManager();
    const session = manager.getSession('invalid_session_id');

    assert.strictEqual(session, null, 'Non-existent session should return null');

    manager.shutdown();
});

// Test 5: Update session
suite.test('Update session metadata', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {});
    const updated = manager.updateSession(session.sessionId, {
        metadata: { recordingDuration: 5000 }
    });

    assert.strictEqual(updated.metadata.recordingDuration, 5000, 'Metadata should be updated');

    manager.shutdown();
});

// Test 6: Last activity tracking
suite.test('Update session updates lastActivity', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {});
    const originalActivity = session.lastActivity;

    // Wait a bit and update
    setTimeout(() => {
        const updated = manager.updateSession(session.sessionId, {});
        assert(updated.lastActivity > originalActivity, 'lastActivity should increase');
    }, 50);
});

// Test 7: Append audio data
suite.test('Append audio chunks to session', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {});
    const chunk1 = Buffer.from('AUDIO_CHUNK_1');
    const chunk2 = Buffer.from('AUDIO_CHUNK_2');

    let size = manager.appendAudioData(session.sessionId, chunk1);
    assert.strictEqual(size, chunk1.length, 'First chunk size should match');

    size = manager.appendAudioData(session.sessionId, chunk2);
    assert.strictEqual(size, chunk1.length + chunk2.length, 'Total size should be sum of chunks');

    manager.shutdown();
});

// Test 8: Get audio buffer
suite.test('Get audio buffer from session', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {});
    const chunk = Buffer.from('TEST_AUDIO');

    manager.appendAudioData(session.sessionId, chunk);
    const buffer = manager.getAudioBuffer(session.sessionId);

    assert(Buffer.isBuffer(buffer), 'Should return a buffer');
    assert.strictEqual(buffer.toString(), 'TEST_AUDIO', 'Buffer content should match');

    manager.shutdown();
});

// Test 9: Clear audio buffer
suite.test('Clear audio buffer', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {});
    const chunk = Buffer.from('TEST_AUDIO');

    manager.appendAudioData(session.sessionId, chunk);
    let buffer = manager.getAudioBuffer(session.sessionId);
    assert(buffer.length > 0, 'Buffer should have data');

    manager.clearAudioBuffer(session.sessionId);
    buffer = manager.getAudioBuffer(session.sessionId);
    assert.strictEqual(buffer.length, 0, 'Buffer should be empty');

    manager.shutdown();
});

// Test 10: Validate session
suite.test('Validate session returns correct status', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {});

    const validation = manager.validateSession(session.sessionId);
    assert.strictEqual(validation.valid, true, 'Valid session should pass validation');
    assert(validation.session, 'Should return session object');

    manager.shutdown();
});

// Test 11: Validate invalid session
suite.test('Validate non-existent session returns false', () => {
    const manager = new SessionManager();
    const validation = manager.validateSession('invalid_id');

    assert.strictEqual(validation.valid, false, 'Invalid session should fail validation');
    assert(!validation.session, 'Should not return session object');

    manager.shutdown();
});

// Test 12: Destroy session
suite.test('Destroy session removes it', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {});

    const destroyed = manager.destroySession(session.sessionId);
    assert.strictEqual(destroyed, true, 'Destroy should return true');

    const retrieved = manager.getSession(session.sessionId);
    assert.strictEqual(retrieved, null, 'Destroyed session should not be retrievable');

    manager.shutdown();
});

// Test 13: Get user sessions
suite.test('Get all sessions for a user', () => {
    const manager = new SessionManager();
    const user = 'testuser';

    manager.createSession(user, { action: 'enrollment' });
    manager.createSession(user, { action: 'verification' });
    manager.createSession('otheruser', { action: 'enrollment' });

    const userSessions = manager.getUserSessions(user);
    assert.strictEqual(userSessions.length, 2, 'Should have 2 sessions for user');

    manager.shutdown();
});

// Test 14: Destroy user sessions
suite.test('Destroy all sessions for a user', () => {
    const manager = new SessionManager();
    const user = 'testuser';

    manager.createSession(user, {});
    manager.createSession(user, {});
    manager.createSession('otheruser', {});

    const destroyed = manager.destroyUserSessions(user);
    assert.strictEqual(destroyed, 2, 'Should destroy 2 sessions');

    const userSessions = manager.getUserSessions(user);
    assert.strictEqual(userSessions.length, 0, 'User should have no sessions');

    manager.shutdown();
});

// Test 15: Session statistics
suite.test('Get session statistics', () => {
    const manager = new SessionManager();

    manager.createSession('user1', {});
    manager.createSession('user2', {});
    manager.createSession('user1', {});

    const stats = manager.getStatistics();

    assert.strictEqual(stats.totalSessions, 3, 'Total sessions should be 3');
    assert.strictEqual(stats.activeSessions, 3, 'Active sessions should be 3');
    assert.strictEqual(stats.totalUsers, 2, 'Total users should be 2');

    manager.shutdown();
});

// Test 16: Export session data
suite.test('Export session data', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', { action: 'test' });

    const exported = manager.exportSession(session.sessionId);

    assert(exported, 'Should export session');
    assert.strictEqual(exported.userId, 'user123', 'Exported user should match');
    assert.strictEqual(exported.metadata.action, 'test', 'Exported metadata should match');
    assert(!exported.audioBuffer, 'Should not expose raw audio buffer');

    manager.shutdown();
});

// Test 17: Session timeout
suite.test('Session timeout expiration', () => {
    return new Promise((resolve, reject) => {
        const manager = new SessionManager({
            sessionTimeout: 100, // 100ms for testing
            cleanupInterval: 50
        });

        const session = manager.createSession('user123', {});
        const earlierTime = session.expiresAt;

        setTimeout(() => {
            try {
                const retrieved = manager.getSession(session.sessionId);
                assert.strictEqual(retrieved, null, 'Expired session should be null');
                manager.shutdown();
                resolve();
            } catch (error) {
                reject(error);
            }
        }, 150);
    });
});

// Test 18: Event emission - session created
suite.test('Event emitted on session creation', () => {
    return new Promise((resolve, reject) => {
        const manager = new SessionManager();

        manager.on('session:created', (data) => {
            try {
                assert(data.sessionId, 'Event should contain session ID');
                manager.shutdown();
                resolve();
            } catch (error) {
                reject(error);
            }
        });

        manager.createSession('user123', {});
    });
});

// Test 19: Event emission - session destroyed
suite.test('Event emitted on session destruction', () => {
    return new Promise((resolve, reject) => {
        const manager = new SessionManager();
        const session = manager.createSession('user123', {});

        manager.on('session:destroyed', (data) => {
            try {
                assert(data.sessionId, 'Event should contain session ID');
                manager.shutdown();
                resolve();
            } catch (error) {
                reject(error);
            }
        });

        manager.destroySession(session.sessionId);
    });
});

// Test 20: Maximum sessions limit
suite.test('Reject session creation when limit reached', () => {
    const manager = new SessionManager({ maxSessions: 2 });

    manager.createSession('user1', {});
    manager.createSession('user2', {});

    try {
        manager.createSession('user3', {});
        assert.fail('Should throw error when max sessions reached');
    } catch (error) {
        assert(error.message.includes('Maximum'), 'Error should mention maximum');
    }

    manager.shutdown();
});

// Test 21: Clear all sessions
suite.test('Clear all sessions', () => {
    const manager = new SessionManager();

    manager.createSession('user1', {});
    manager.createSession('user2', {});

    let stats = manager.getStatistics();
    assert.strictEqual(stats.totalSessions, 2, 'Should have 2 sessions');

    manager.clearAllSessions();

    stats = manager.getStatistics();
    assert.strictEqual(stats.totalSessions, 0, 'Should have 0 sessions');

    manager.shutdown();
});

// Test 22: Persistence store integration
suite.test('Persistence store saves sessions', () => {
    const persistenceStore = new MemoryPersistenceStore();
    const manager = new SessionManager({
        enablePersistence: true,
        persistenceStore
    });

    const session = manager.createSession('user123', { action: 'test' });

    const persisted = persistenceStore.get(session.sessionId);
    assert(persisted, 'Session should be persisted');
    assert.strictEqual(persisted.userId, 'user123', 'Persisted user should match');

    manager.shutdown();
});

// Test 23: Persistence store deletion
suite.test('Persistence store deletes sessions', () => {
    const persistenceStore = new MemoryPersistenceStore();
    const manager = new SessionManager({
        enablePersistence: true,
        persistenceStore
    });

    const session = manager.createSession('user123', {});

    manager.destroySession(session.sessionId);

    const persisted = persistenceStore.get(session.sessionId);
    assert(!persisted, 'Session should be deleted from persistence');

    manager.shutdown();
});

// Test 24: Audio data error handling
suite.test('Append audio to non-existent session throws error', () => {
    const manager = new SessionManager();
    const chunk = Buffer.from('AUDIO');

    try {
        manager.appendAudioData('invalid_session', chunk);
        assert.fail('Should throw error');
    } catch (error) {
        assert(error.message.includes('Session not found'), 'Should mention session not found');
    }

    manager.shutdown();
});

// Test 25: Invalid audio data throws error
suite.test('Append non-buffer audio throws error', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {});

    try {
        manager.appendAudioData(session.sessionId, 'not a buffer');
        assert.fail('Should throw error');
    } catch (error) {
        assert(error.message.includes('Invalid audio'), 'Should mention invalid audio');
    }

    manager.shutdown();
});

// Test 26: Session IP and User Agent tracking
suite.test('Track session IP and User Agent', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {
        ipAddress: '192.168.1.1',
        userAgent: 'Mozilla/5.0'
    });

    assert.strictEqual(session.ipAddress, '192.168.1.1', 'IP should be stored');
    assert.strictEqual(session.userAgent, 'Mozilla/5.0', 'User Agent should be stored');

    manager.shutdown();
});

// Test 27: Session status transitions
suite.test('Session status transitions correctly', () => {
    const manager = new SessionManager({
        sessionTimeout: 50,
        cleanupInterval: 25
    });

    const session = manager.createSession('user123', {});
    assert.strictEqual(session.status, 'active', 'Initial status should be active');

    // Wait for expiration
    setTimeout(() => {
        const retrieved = manager.getSession(session.sessionId);
        assert.strictEqual(retrieved, null, 'Expired session should be null');
    }, 100);
});

// Test 28: Multiple audio chunks handling
suite.test('Handle multiple audio chunks correctly', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {});

    const chunks = [
        Buffer.from('CHUNK_1'),
        Buffer.from('CHUNK_2'),
        Buffer.from('CHUNK_3'),
        Buffer.from('CHUNK_4'),
        Buffer.from('CHUNK_5')
    ];

    let totalSize = 0;
    chunks.forEach((chunk, index) => {
        const size = manager.appendAudioData(session.sessionId, chunk);
        totalSize += chunk.length;
        assert.strictEqual(size, totalSize, `Size at chunk ${index + 1} should match total`);
    });

    manager.shutdown();
});

// Test 29: Cleanup interval removes expired sessions
suite.test('Cleanup interval removes expired sessions', () => {
    return new Promise((resolve, reject) => {
        const manager = new SessionManager({
            sessionTimeout: 50,
            cleanupInterval: 100
        });

        const session = manager.createSession('user123', {});

        manager.on('cleanup:completed', (data) => {
            try {
                assert(data.removedCount > 0, 'Should remove expired sessions');
                manager.shutdown();
                resolve();
            } catch (error) {
                reject(error);
            }
        });

        // Wait for cleanup to run
        setTimeout(() => {
            // Session should be expired and cleaned up
        }, 200);
    });
});

// Test 30: Session validation after update
suite.test('Session validation after update', () => {
    const manager = new SessionManager();
    const session = manager.createSession('user123', {});

    manager.updateSession(session.sessionId, {
        metadata: { step: 'processing' }
    });

    const validation = manager.validateSession(session.sessionId);
    assert.strictEqual(validation.valid, true, 'Updated session should be valid');

    manager.shutdown();
});

// Export and run tests
if (require.main === module) {
    suite.run();
}

module.exports = {
    SessionManagerTests,
    suite
};
