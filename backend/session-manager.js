/**
 * Session Manager for Voice Biometric Authentication
 * Handles session creation, storage, validation, and lifecycle management
 */

const crypto = require('crypto');
const EventEmitter = require('events');

/**
 * Session Manager Class
 * Manages user sessions with timeout and expiration handling
 */
class SessionManager extends EventEmitter {
    constructor(options = {}) {
        super();
        
        // Configuration
        this.sessionTimeout = options.sessionTimeout || 30 * 60 * 1000; // 30 minutes default
        this.cleanupInterval = options.cleanupInterval || 5 * 60 * 1000; // 5 minutes
        this.maxSessions = options.maxSessions || 1000;
        this.enablePersistence = options.enablePersistence || false;
        
        // Storage
        this.sessions = new Map();
        this.userSessions = new Map(); // Map of userId -> Set of sessionIds
        this.timeoutHandles = new Map();
        
        // Persistence storage (optional)
        this.persistenceStore = options.persistenceStore || null;
        
        // Initialize cleanup interval
        this.startCleanupInterval();
        
        console.log('[SessionManager] Initialized with timeout:', this.sessionTimeout / 1000, 'seconds');
    }

    /**
     * Create a new session
     * @param {string} userId - User identifier
     * @param {Object} data - Session data (action, language, etc.)
     * @returns {Object} Session object with sessionId
     */
    createSession(userId, data = {}) {
        // Validate session limit
        if (this.sessions.size >= this.maxSessions) {
            throw new Error('Maximum session limit reached');
        }

        const sessionId = this.generateSessionId();
        const now = Date.now();

        const session = {
            sessionId,
            userId,
            createdAt: now,
            lastActivity: now,
            expiresAt: now + this.sessionTimeout,
            status: 'active',
            ipAddress: data.ipAddress || null,
            userAgent: data.userAgent || null,
            audioBuffer: Buffer.alloc(0),
            metadata: {
                action: data.action || null,
                language: data.language || 'en',
                connectionId: data.connectionId || null,
                ...data
            }
        };

        // Store session
        this.sessions.set(sessionId, session);

        // Track user sessions
        if (!this.userSessions.has(userId)) {
            this.userSessions.set(userId, new Set());
        }
        this.userSessions.get(userId).add(sessionId);

        // Set up timeout
        this.setSessionTimeout(sessionId);

        // Persist if enabled
        if (this.enablePersistence && this.persistenceStore) {
            this.persistenceStore.save(sessionId, session);
        }

        // Emit event
        this.emit('session:created', { sessionId, userId });

        console.log(`[SessionManager] Session created - ID: ${sessionId}, User: ${userId}`);

        return session;
    }

    /**
     * Get session by ID
     * @param {string} sessionId - Session identifier
     * @returns {Object|null} Session object or null if not found/expired
     */
    getSession(sessionId) {
        const session = this.sessions.get(sessionId);

        if (!session) {
            return null;
        }

        // Check if session is expired
        if (session.expiresAt < Date.now()) {
            this.destroySession(sessionId);
            return null;
        }

        return session;
    }

    /**
     * Get all active sessions for a user
     * @param {string} userId - User identifier
     * @returns {Array} Array of session objects
     */
    getUserSessions(userId) {
        const userSessionIds = this.userSessions.get(userId) || new Set();
        const sessions = [];

        userSessionIds.forEach(sessionId => {
            const session = this.getSession(sessionId);
            if (session) {
                sessions.push(session);
            }
        });

        return sessions;
    }

    /**
     * Update session data
     * @param {string} sessionId - Session identifier
     * @param {Object} updates - Data to update
     * @returns {Object|null} Updated session object or null if not found
     */
    updateSession(sessionId, updates = {}) {
        const session = this.getSession(sessionId);

        if (!session) {
            return null;
        }

        // Update session fields
        session.lastActivity = Date.now();
        session.expiresAt = session.lastActivity + this.sessionTimeout;

        // Update metadata
        if (updates.metadata) {
            session.metadata = { ...session.metadata, ...updates.metadata };
        }

        // Update other fields
        Object.keys(updates).forEach(key => {
            if (key !== 'metadata' && key !== 'sessionId' && key !== 'userId' && key !== 'createdAt') {
                session[key] = updates[key];
            }
        });

        // Reset timeout
        this.setSessionTimeout(sessionId);

        // Persist if enabled
        if (this.enablePersistence && this.persistenceStore) {
            this.persistenceStore.update(sessionId, session);
        }

        // Emit event
        this.emit('session:updated', { sessionId, userId: session.userId });

        return session;
    }

    /**
     * Append audio data to session
     * @param {string} sessionId - Session identifier
     * @param {Buffer} audioChunk - Audio data chunk
     * @returns {number} Total audio buffer size
     */
    appendAudioData(sessionId, audioChunk) {
        const session = this.getSession(sessionId);

        if (!session) {
            throw new Error('Session not found or expired');
        }

        if (!Buffer.isBuffer(audioChunk)) {
            throw new Error('Invalid audio data format');
        }

        session.audioBuffer = Buffer.concat([session.audioBuffer, audioChunk]);
        session.lastActivity = Date.now();
        session.expiresAt = session.lastActivity + this.sessionTimeout;

        // Reset timeout
        this.setSessionTimeout(sessionId);

        return session.audioBuffer.length;
    }

    /**
     * Get audio buffer from session
     * @param {string} sessionId - Session identifier
     * @returns {Buffer|null} Audio buffer or null if not found
     */
    getAudioBuffer(sessionId) {
        const session = this.getSession(sessionId);
        return session ? session.audioBuffer : null;
    }

    /**
     * Clear audio buffer from session
     * @param {string} sessionId - Session identifier
     * @returns {boolean} Success status
     */
    clearAudioBuffer(sessionId) {
        const session = this.getSession(sessionId);

        if (!session) {
            return false;
        }

        session.audioBuffer = Buffer.alloc(0);
        return true;
    }

    /**
     * Validate session
     * @param {string} sessionId - Session identifier
     * @returns {Object} Validation result { valid: boolean, message: string, session: Object|null }
     */
    validateSession(sessionId) {
        const session = this.sessions.get(sessionId);

        if (!session) {
            return { valid: false, message: 'Session not found', session: null };
        }

        if (session.status === 'expired') {
            return { valid: false, message: 'Session has expired', session: null };
        }

        if (session.status === 'destroyed') {
            return { valid: false, message: 'Session has been destroyed', session: null };
        }

        if (session.expiresAt < Date.now()) {
            session.status = 'expired';
            return { valid: false, message: 'Session has expired', session: null };
        }

        if (session.status !== 'active') {
            return { valid: false, message: `Session is ${session.status}`, session: null };
        }

        return { valid: true, message: 'Session is valid', session };
    }

    /**
     * Destroy session
     * @param {string} sessionId - Session identifier
     * @returns {boolean} Success status
     */
    destroySession(sessionId) {
        const session = this.sessions.get(sessionId);

        if (!session) {
            return false;
        }

        // Clear timeout
        if (this.timeoutHandles.has(sessionId)) {
            clearTimeout(this.timeoutHandles.get(sessionId));
            this.timeoutHandles.delete(sessionId);
        }

        // Remove from user sessions
        const userSessions = this.userSessions.get(session.userId);
        if (userSessions) {
            userSessions.delete(sessionId);
            if (userSessions.size === 0) {
                this.userSessions.delete(session.userId);
            }
        }

        // Remove persistence if enabled
        if (this.enablePersistence && this.persistenceStore) {
            this.persistenceStore.delete(sessionId);
        }

        // Delete session
        this.sessions.delete(sessionId);

        // Emit event
        this.emit('session:destroyed', { sessionId, userId: session.userId });

        console.log(`[SessionManager] Session destroyed - ID: ${sessionId}`);

        return true;
    }

    /**
     * Destroy all sessions for a user
     * @param {string} userId - User identifier
     * @returns {number} Number of sessions destroyed
     */
    destroyUserSessions(userId) {
        const userSessionIds = this.userSessions.get(userId);

        if (!userSessionIds) {
            return 0;
        }

        let count = 0;
        userSessionIds.forEach(sessionId => {
            if (this.destroySession(sessionId)) {
                count++;
            }
        });

        return count;
    }

    /**
     * Get session statistics
     * @returns {Object} Statistics object
     */
    getStatistics() {
        const stats = {
            totalSessions: this.sessions.size,
            activeSessions: 0,
            expiredSessions: 0,
            destroyedSessions: 0,
            totalUsers: this.userSessions.size,
            sessionsByStatus: {}
        };

        this.sessions.forEach(session => {
            stats.sessionsByStatus[session.status] = (stats.sessionsByStatus[session.status] || 0) + 1;

            if (session.status === 'active') {
                stats.activeSessions++;
            } else if (session.status === 'expired') {
                stats.expiredSessions++;
            } else if (session.status === 'destroyed') {
                stats.destroyedSessions++;
            }
        });

        return stats;
    }

    /**
     * Export session data
     * @param {string} sessionId - Session identifier
     * @returns {Object|null} Serializable session data
     */
    exportSession(sessionId) {
        const session = this.getSession(sessionId);

        if (!session) {
            return null;
        }

        return {
            sessionId: session.sessionId,
            userId: session.userId,
            createdAt: session.createdAt,
            lastActivity: session.lastActivity,
            expiresAt: session.expiresAt,
            status: session.status,
            ipAddress: session.ipAddress,
            userAgent: session.userAgent,
            audioBufferSize: session.audioBuffer.length,
            metadata: session.metadata
        };
    }

    /**
     * Set session timeout
     * @private
     * @param {string} sessionId - Session identifier
     */
    setSessionTimeout(sessionId) {
        const session = this.sessions.get(sessionId);

        if (!session) {
            return;
        }

        // Clear existing timeout
        if (this.timeoutHandles.has(sessionId)) {
            clearTimeout(this.timeoutHandles.get(sessionId));
        }

        // Set new timeout
        const handle = setTimeout(() => {
            this.expireSession(sessionId);
        }, this.sessionTimeout);

        this.timeoutHandles.set(sessionId, handle);
    }

    /**
     * Expire session
     * @private
     * @param {string} sessionId - Session identifier
     */
    expireSession(sessionId) {
        const session = this.sessions.get(sessionId);

        if (!session) {
            return;
        }

        session.status = 'expired';
        this.timeoutHandles.delete(sessionId);

        // Emit event
        this.emit('session:expired', { sessionId, userId: session.userId });

        console.log(`[SessionManager] Session expired - ID: ${sessionId}`);
    }

    /**
     * Start cleanup interval
     * @private
     */
    startCleanupInterval() {
        this.cleanupIntervalHandle = setInterval(() => {
            this.cleanup();
        }, this.cleanupInterval);
    }

    /**
     * Stop cleanup interval
     */
    stopCleanupInterval() {
        if (this.cleanupIntervalHandle) {
            clearInterval(this.cleanupIntervalHandle);
            this.cleanupIntervalHandle = null;
        }
    }

    /**
     * Cleanup expired sessions
     * @private
     */
    cleanup() {
        let cleanedCount = 0;

        this.sessions.forEach((session, sessionId) => {
            if (session.status === 'expired' || session.expiresAt < Date.now()) {
                this.destroySession(sessionId);
                cleanedCount++;
            }
        });

        if (cleanedCount > 0) {
            console.log(`[SessionManager] Cleanup completed - Removed ${cleanedCount} expired sessions`);
            this.emit('cleanup:completed', { removedCount: cleanedCount });
        }
    }

    /**
     * Generate unique session ID
     * @private
     * @returns {string} Session ID
     */
    generateSessionId() {
        return `sess_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
    }

    /**
     * Clear all sessions (for testing or shutdown)
     */
    clearAllSessions() {
        const count = this.sessions.size;

        // Clear all timeouts
        this.timeoutHandles.forEach(handle => clearTimeout(handle));
        this.timeoutHandles.clear();

        // Clear sessions
        this.sessions.clear();
        this.userSessions.clear();

        console.log(`[SessionManager] Cleared all ${count} sessions`);
        this.emit('all-sessions:cleared', { count });
    }

    /**
     * Shutdown session manager
     */
    shutdown() {
        this.stopCleanupInterval();
        this.clearAllSessions();
        this.removeAllListeners();
        console.log('[SessionManager] Shutdown complete');
    }
}

/**
 * Simple In-Memory Persistence Store (for demonstration)
 */
class MemoryPersistenceStore {
    constructor() {
        this.store = new Map();
    }

    save(sessionId, session) {
        this.store.set(sessionId, JSON.parse(JSON.stringify(session)));
    }

    update(sessionId, session) {
        this.save(sessionId, session);
    }

    get(sessionId) {
        return this.store.get(sessionId);
    }

    delete(sessionId) {
        this.store.delete(sessionId);
    }

    getAll() {
        return Array.from(this.store.values());
    }

    clear() {
        this.store.clear();
    }
}

/**
 * Export Session Manager
 */
module.exports = {
    SessionManager,
    MemoryPersistenceStore
};
