/**
 * MongoDB Persistence Store for Session Manager
 * Provides persistent storage backend for sessions using MongoDB
 * 
 * Usage:
 *   const { MongoDBPersistenceStore } = require('./mongodb-persistence-store');
 *   const store = new MongoDBPersistenceStore({
 *       url: 'mongodb://localhost:27017',
 *       database: 'voice_biometric'
 *   });
 *   
 *   sessionManager.enablePersistence = true;
 *   sessionManager.persistenceStore = store;
 */

const { MongoClient } = require('mongodb');
const EventEmitter = require('events');

/**
 * MongoDB Persistence Store for Session Manager
 * Handles persistent storage of sessions and audio data to MongoDB
 */
class MongoDBPersistenceStore extends EventEmitter {
    /**
     * Initialize MongoDB Persistence Store
     * 
     * @param {Object} options - Configuration options
     * @param {string} options.url - MongoDB connection URL (default: mongodb://localhost:27017)
     * @param {string} options.database - Database name (default: voice_biometric)
     * @param {string} options.sessionsCollection - Sessions collection name (default: sessions)
     * @param {string} options.audioChunksCollection - Audio chunks collection name (default: audio_chunks)
     * @param {string} options.analyticsCollection - Analytics collection name (default: session_analytics)
     */
    constructor(options = {}) {
        super();
        
        this.url = options.url || 'mongodb://localhost:27017';
        this.database = options.database || 'voice_biometric';
        this.sessionsCollection = options.sessionsCollection || 'sessions';
        this.audioChunksCollection = options.audioChunksCollection || 'audio_chunks';
        this.analyticsCollection = options.analyticsCollection || 'session_analytics';
        
        this.client = null;
        this.db = null;
        this.sessionsCol = null;
        this.audioChunksCol = null;
        this.analyticsCol = null;
        
        console.log('[MongoDBPersistenceStore] Initialized with options:', {
            url: this.url,
            database: this.database
        });
    }

    /**
     * Connect to MongoDB and initialize collections
     * 
     * @returns {Promise<void>}
     */
    async connect() {
        if (this.client) {
            return; // Already connected
        }

        try {
            this.client = new MongoClient(this.url, {
                useUnifiedTopology: true,
                connectTimeoutMS: 5000,
                serverSelectionTimeoutMS: 5000
            });

            await this.client.connect();
            this.db = this.client.db(this.database);

            // Get collection references
            this.sessionsCol = this.db.collection(this.sessionsCollection);
            this.audioChunksCol = this.db.collection(this.audioChunksCollection);
            this.analyticsCol = this.db.collection(this.analyticsCollection);

            // Initialize indexes
            await this._initializeIndexes();

            console.log('[MongoDBPersistenceStore] Connected and initialized');
            this.emit('connected');
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Connection error:', error.message);
            this.emit('error', error);
            throw error;
        }
    }

    /**
     * Initialize MongoDB indexes for optimal performance
     * 
     * @private
     * @returns {Promise<void>}
     */
    async _initializeIndexes() {
        try {
            // Sessions indexes
            await this.sessionsCol.createIndex({ session_id: 1 }, { unique: true });
            await this.sessionsCol.createIndex({ user_id: 1, status: 1 });
            await this.sessionsCol.createIndex({ expires_at: 1 });
            await this.sessionsCol.createIndex({ created_at: -1 });
            await this.sessionsCol.createIndex({ last_activity: -1 });

            // TTL index: automatically delete expired sessions 24 hours after expiration
            try {
                await this.sessionsCol.createIndex({ expires_at: 1 }, { expireAfterSeconds: 86400 });
            } catch (e) {
                // Index may already exist
            }

            // Audio chunks indexes
            await this.audioChunksCol.createIndex({ session_id: 1 });
            await this.audioChunksCol.createIndex({ session_id: 1, chunk_index: 1 });
            await this.audioChunksCol.createIndex({ created_at: -1 });

            // Analytics indexes
            await this.analyticsCol.createIndex({ user_id: 1, date: -1 });
            await this.analyticsCol.createIndex({ session_id: 1 });

            console.log('[MongoDBPersistenceStore] Indexes initialized');
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Index initialization error:', error.message);
        }
    }

    /**
     * Save session to MongoDB
     * 
     * @param {string} sessionId - Session identifier
     * @param {Object} session - Session object to save
     * @returns {Promise<string>} - Document ID
     */
    async save(sessionId, session) {
        if (!this.sessionsCol) {
            await this.connect();
        }

        try {
            // Convert session to MongoDB document format
            const doc = {
                session_id: sessionId,
                user_id: session.userId,
                status: session.status || 'active',
                created_at: new Date(session.createdAt),
                last_activity: new Date(session.lastActivity),
                expires_at: new Date(session.expiresAt),
                ip_address: session.ipAddress || null,
                user_agent: session.userAgent || null,
                metadata: session.metadata || {},
                audio_chunks_count: 0,
                total_audio_size: 0,
                updated_at: new Date()
            };

            // Upsert the session
            const result = await this.sessionsCol.updateOne(
                { session_id: sessionId },
                { $set: doc },
                { upsert: true }
            );

            console.log(`[MongoDBPersistenceStore] Session saved: ${sessionId}`);
            return result.upsertedId || sessionId;
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Save error:', error.message);
            this.emit('error', { operation: 'save', error, sessionId });
            throw error;
        }
    }

    /**
     * Load session from MongoDB
     * 
     * @param {string} sessionId - Session identifier
     * @returns {Promise<Object|null>} - Session object or null if not found
     */
    async load(sessionId) {
        if (!this.sessionsCol) {
            await this.connect();
        }

        try {
            const doc = await this.sessionsCol.findOne({ session_id: sessionId });

            if (doc) {
                // Convert MongoDB document to session object format
                const session = {
                    sessionId: doc.session_id,
                    userId: doc.user_id,
                    status: doc.status,
                    createdAt: doc.created_at.getTime(),
                    lastActivity: doc.last_activity.getTime(),
                    expiresAt: doc.expires_at.getTime(),
                    ipAddress: doc.ip_address,
                    userAgent: doc.user_agent,
                    metadata: doc.metadata,
                    audioBuffer: Buffer.alloc(0), // Audio will be loaded separately
                    _id: doc._id.toString()
                };

                console.log(`[MongoDBPersistenceStore] Session loaded: ${sessionId}`);
                return session;
            }

            return null;
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Load error:', error.message);
            this.emit('error', { operation: 'load', error, sessionId });
            throw error;
        }
    }

    /**
     * Update session in MongoDB
     * 
     * @param {string} sessionId - Session identifier
     * @param {Object} updates - Fields to update
     * @returns {Promise<boolean>} - True if updated, false if not found
     */
    async update(sessionId, updates) {
        if (!this.sessionsCol) {
            await this.connect();
        }

        try {
            const doc = {};
            if (updates.status) doc.status = updates.status;
            if (updates.metadata) doc.metadata = updates.metadata;
            if (updates.lastActivity) doc.last_activity = new Date(updates.lastActivity);
            if (updates.expiresAt) doc.expires_at = new Date(updates.expiresAt);
            
            doc.updated_at = new Date();

            const result = await this.sessionsCol.updateOne(
                { session_id: sessionId },
                { $set: doc }
            );

            console.log(`[MongoDBPersistenceStore] Session updated: ${sessionId}`);
            return result.modifiedCount > 0;
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Update error:', error.message);
            this.emit('error', { operation: 'update', error, sessionId });
            throw error;
        }
    }

    /**
     * Delete session from MongoDB
     * 
     * @param {string} sessionId - Session identifier
     * @returns {Promise<boolean>} - True if deleted, false if not found
     */
    async delete(sessionId) {
        if (!this.sessionsCol) {
            await this.connect();
        }

        try {
            const result = await this.sessionsCol.deleteOne({ session_id: sessionId });

            // Also delete associated audio chunks
            if (this.audioChunksCol) {
                await this.audioChunksCol.deleteMany({ session_id: sessionId });
            }

            console.log(`[MongoDBPersistenceStore] Session deleted: ${sessionId}`);
            return result.deletedCount > 0;
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Delete error:', error.message);
            this.emit('error', { operation: 'delete', error, sessionId });
            throw error;
        }
    }

    /**
     * Save audio chunk for a session
     * 
     * @param {string} sessionId - Session identifier
     * @param {number} chunkIndex - Index of the chunk
     * @param {Buffer} audioData - Audio data buffer
     * @returns {Promise<string>} - Document ID
     */
    async saveAudioChunk(sessionId, chunkIndex, audioData) {
        if (!this.audioChunksCol) {
            await this.connect();
        }

        try {
            const chunk = {
                session_id: sessionId,
                chunk_index: chunkIndex,
                audio_data: audioData,
                size_bytes: audioData.length,
                created_at: new Date()
            };

            const result = await this.audioChunksCol.insertOne(chunk);

            // Update session audio tracking
            await this.sessionsCol.updateOne(
                { session_id: sessionId },
                {
                    $inc: {
                        audio_chunks_count: 1,
                        total_audio_size: audioData.length
                    }
                }
            );

            console.log(`[MongoDBPersistenceStore] Audio chunk saved for session ${sessionId} (${audioData.length} bytes)`);
            return result.insertedId.toString();
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Save audio chunk error:', error.message);
            this.emit('error', { operation: 'saveAudioChunk', error, sessionId });
            throw error;
        }
    }

    /**
     * Load all audio chunks for a session
     * 
     * @param {string} sessionId - Session identifier
     * @returns {Promise<Buffer>} - Combined audio buffer
     */
    async loadAudioChunks(sessionId) {
        if (!this.audioChunksCol) {
            await this.connect();
        }

        try {
            const chunks = await this.audioChunksCol
                .find({ session_id: sessionId })
                .sort({ chunk_index: 1 })
                .toArray();

            if (chunks.length === 0) {
                return Buffer.alloc(0);
            }

            // Concatenate all chunks
            const buffers = chunks.map(chunk => chunk.audio_data);
            const audioBuffer = Buffer.concat(buffers);

            console.log(`[MongoDBPersistenceStore] Loaded ${chunks.length} audio chunks for session ${sessionId}`);
            return audioBuffer;
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Load audio chunks error:', error.message);
            this.emit('error', { operation: 'loadAudioChunks', error, sessionId });
            throw error;
        }
    }

    /**
     * Record a session event for analytics
     * 
     * @param {string} sessionId - Session identifier
     * @param {string} userId - User identifier
     * @param {string} eventType - Type of event
     * @param {Object} eventData - Event details
     * @returns {Promise<string>} - Document ID
     */
    async recordEvent(sessionId, userId, eventType, eventData = {}) {
        if (!this.analyticsCol) {
            await this.connect();
        }

        try {
            const now = new Date();
            const event = {
                session_id: sessionId,
                user_id: userId,
                event_type: eventType,
                details: eventData,
                created_at: now,
                date: now.toISOString().split('T')[0] // YYYY-MM-DD format
            };

            const result = await this.analyticsCol.insertOne(event);

            console.log(`[MongoDBPersistenceStore] Event recorded: ${eventType} for session ${sessionId}`);
            return result.insertedId.toString();
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Record event error:', error.message);
            this.emit('error', { operation: 'recordEvent', error, sessionId });
            throw error;
        }
    }

    /**
     * Get session statistics
     * 
     * @returns {Promise<Object>} - Statistics object
     */
    async getStatistics() {
        if (!this.sessionsCol) {
            await this.connect();
        }

        try {
            const now = new Date();
            
            const stats = {
                total_sessions: await this.sessionsCol.countDocuments({}),
                active_sessions: await this.sessionsCol.countDocuments({
                    status: 'active',
                    expires_at: { $gt: now }
                }),
                expired_sessions: await this.sessionsCol.countDocuments({
                    expires_at: { $lt: now }
                }),
                timestamp: now.toISOString()
            };

            console.log('[MongoDBPersistenceStore] Statistics retrieved');
            return stats;
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Get statistics error:', error.message);
            this.emit('error', { operation: 'getStatistics', error });
            throw error;
        }
    }

    /**
     * Clean up expired sessions
     * 
     * @returns {Promise<number>} - Number of sessions deleted
     */
    async cleanupExpiredSessions() {
        if (!this.sessionsCol) {
            await this.connect();
        }

        try {
            const result = await this.sessionsCol.deleteMany({
                expires_at: { $lt: new Date() }
            });

            console.log(`[MongoDBPersistenceStore] Cleaned up ${result.deletedCount} expired sessions`);
            return result.deletedCount;
        } catch (error) {
            console.error('[MongoDBPersistenceStore] Cleanup error:', error.message);
            this.emit('error', { operation: 'cleanupExpiredSessions', error });
            throw error;
        }
    }

    /**
     * Disconnect from MongoDB
     * 
     * @returns {Promise<void>}
     */
    async disconnect() {
        if (this.client) {
            try {
                await this.client.close();
                this.client = null;
                this.db = null;
                console.log('[MongoDBPersistenceStore] Disconnected');
            } catch (error) {
                console.error('[MongoDBPersistenceStore] Disconnect error:', error.message);
            }
        }
    }
}

module.exports = { MongoDBPersistenceStore };
