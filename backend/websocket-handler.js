/**
 * WebSocket Handler for Voice Biometric Authentication
 * Manages real-time audio streaming, enrollment, and verification
 * 
 * Architecture:
 * - WebSocket Server (ws library) receives audio chunks
 * - Session Manager tracks user sessions and audio buffers
 * - FastAPI Backend processes audio and generates embeddings
 * - Real-time messaging for status updates
 */

const WebSocket = require('ws');
const http = require('http');
const { EventEmitter } = require('events');
const axios = require('axios');
const { SessionManager } = require('./session-manager');
const { ChunkProcessor, AUDIO_CONFIG: CHUNK_AUDIO_CONFIG } = require('./chunk-processor');
require('dotenv').config();

// Configuration
const WS_PORT = process.env.WS_PORT || 8001;
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';
const NODE_ENV = process.env.NODE_ENV || 'development';

// Constants
const MESSAGE_TYPES = {
    // Server -> Client
    CONNECTION: 'connection',
    INITIALIZED: 'initialized',
    ENROLLMENT_STARTED: 'enrollment-started',
    VERIFICATION_STARTED: 'verification-started',
    AUDIO_RECEIVED: 'audio-received',
    CHUNK_PROCESSED: 'chunk-processed',
    PROCESSING: 'processing',
    RESULT: 'result',
    ERROR: 'error',
    STATUS: 'status',
    PONG: 'pong',
    
    // Client -> Server
    INIT: 'init',
    START_ENROLLMENT: 'start-enrollment',
    START_VERIFICATION: 'start-verification',
    AUDIO_DATA: 'audio',
    STOP_AUDIO: 'stop-audio',
    GET_STATUS: 'get-status',
    PING: 'ping'
};

const AUDIO_CONFIG = {
    SAMPLE_RATE: 16000,
    CHANNELS: 1,
    BITS_PER_SAMPLE: 16,
    CHUNK_SIZE: 16384 // 16KB chunks
};

/**
 * WebSocket Audio Handler Class
 * Main server managing all client connections and audio processing
 */
class WebSocketAudioHandler extends EventEmitter {
    constructor(port = WS_PORT) {
        super();
        this.port = port;
        this.server = null;
        this.wss = null;
        this.sessionManager = new SessionManager({
            sessionTimeout: 30 * 60 * 1000, // 30 minutes
            maxSessions: 1000
        });
        this.chunkProcessor = new ChunkProcessor({
            backendUrl: BACKEND_API_URL,
            similarityThreshold: 0.75,
            minChunksForMatch: 4 // Security requirement: minimum 4 matching chunks
        });
        this.clients = new Map(); // Map of ws -> clientInfo
        this.clientId = 0;
        
        console.log('[WSHandler] Initialized on port', port);
    }

    /**
     * Start the WebSocket server
     */
    start() {
        return new Promise((resolve, reject) => {
            try {
                this.server = http.createServer();
                this.wss = new WebSocket.Server({ server: this.server });

                this.wss.on('connection', (ws, req) => this.handleConnection(ws, req));

                this.server.listen(this.port, () => {
                    console.log(`[WSHandler] WebSocket server listening on ws://0.0.0.0:${this.port}`);
                    resolve();
                });

                this.server.on('error', (err) => {
                    console.error('[WSHandler] Server error:', err);
                    reject(err);
                });

            } catch (err) {
                console.error('[WSHandler] Failed to start server:', err);
                reject(err);
            }
        });
    }

    /**
     * Stop the WebSocket server
     */
    stop() {
        return new Promise((resolve) => {
            if (this.wss) {
                this.wss.close(() => {
                    console.log('[WSHandler] WebSocket server stopped');
                    if (this.server) {
                        this.server.close(() => {
                            resolve();
                        });
                    } else {
                        resolve();
                    }
                });
            } else {
                resolve();
            }
        });
    }

    /**
     * Handle new client connection
     */
    handleConnection(ws, req) {
        const clientId = `client_${Date.now()}_${++this.clientId}`;
        const clientIp = req.socket.remoteAddress;

        const clientInfo = {
            id: clientId,
            ws: ws,
            connected: true,
            connectedAt: Date.now(),
            sessionId: null,
            userId: null,
            messageCount: 0
        };

        this.clients.set(ws, clientInfo);

        console.log(`[WSHandler] Client connected: ${clientId} from ${clientIp}`);

        // Send connection acknowledgment
        this.sendMessage(ws, {
            type: MESSAGE_TYPES.CONNECTION,
            clientId: clientId,
            message: 'Connected to WebSocket server',
            timestamp: Date.now()
        });

        // Handle incoming messages
        ws.on('message', (data) => this.handleMessage(ws, data));

        // Handle errors
        ws.on('error', (err) => {
            console.error(`[WSHandler] Client error (${clientId}):`, err.message);
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'WebSocket error',
                details: err.message,
                timestamp: Date.now()
            });
        });

        // Handle client disconnect
        ws.on('close', () => {
            console.log(`[WSHandler] Client disconnected: ${clientId}`);
            
            const client = this.clients.get(ws);
            if (client && client.sessionId) {
                this.sessionManager.destroySession(client.sessionId);
            }
            
            this.clients.delete(ws);
        });
    }

    /**
     * Handle incoming messages from client
     */
    handleMessage(ws, data) {
        const client = this.clients.get(ws);
        if (!client) return;

        try {
            // Try to parse as JSON first (text message)
            if (Buffer.isBuffer(data) || typeof data === 'string') {
                let message = null;
                try {
                    // Convert buffer to string if needed
                    const dataStr = typeof data === 'string' ? data : data.toString('utf8');
                    message = JSON.parse(dataStr);
                    // Successfully parsed JSON - it's a control message
                    this.handleJsonMessage(ws, message);
                } catch (parseErr) {
                    // Not JSON - treat as binary audio data
                    if (Buffer.isBuffer(data)) {
                        this.handleAudioData(ws, data);
                    } else {
                        // It's a string but not valid JSON
                        throw new Error('Invalid message format: expected JSON or binary audio');
                    }
                }
            }
        } catch (err) {
            console.error(`[WSHandler] Message handling error (${client.id}):`, err.message);
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'Failed to process message',
                details: err.message,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Handle JSON text messages
     */
    handleJsonMessage(ws, message) {
        const client = this.clients.get(ws);
        if (!client) return;

        client.messageCount++;
        const type = message.type;

        console.log(`[WSHandler] Message from ${client.id}: ${type}`);

        switch (type) {
            case MESSAGE_TYPES.INIT:
                this.handleInitialization(ws, message);
                break;
            case MESSAGE_TYPES.START_ENROLLMENT:
                this.handleStartEnrollment(ws);
                break;
            case MESSAGE_TYPES.START_VERIFICATION:
                this.handleStartVerification(ws, message);
                break;
            case MESSAGE_TYPES.STOP_AUDIO:
                this.handleStopAudio(ws);
                break;
            case MESSAGE_TYPES.GET_STATUS:
                this.handleGetStatus(ws);
                break;
            case MESSAGE_TYPES.PING:
                this.handlePing(ws);
                break;
            default:
                console.warn(`[WSHandler] Unknown message type: ${type}`);
                this.sendMessage(ws, {
                    type: MESSAGE_TYPES.ERROR,
                    error: 'Unknown message type',
                    details: `Message type '${type}' is not recognized`,
                    timestamp: Date.now()
                });
        }
    }

    /**
     * Initialize session
     */
    handleInitialization(ws, message) {
        const client = this.clients.get(ws);
        if (!client) return;

        const { userId, action, language = 'en' } = message;

        if (!userId) {
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'Invalid initialization',
                details: 'userId is required',
                timestamp: Date.now()
            });
            return;
        }

        try {
            // Create session
            const session = this.sessionManager.createSession(userId, {
                action,
                language,
                connectionId: client.id
            });

            client.sessionId = session.sessionId;
            client.userId = userId;

            this.sendMessage(ws, {
                type: MESSAGE_TYPES.INITIALIZED,
                userId: userId,
                action: action,
                message: `Session initialized for ${action}`,
                timestamp: Date.now()
            });

            console.log(`[WSHandler] Session created for ${userId}: ${session.sessionId}`);
        } catch (err) {
            console.error('[WSHandler] Initialization error:', err.message);
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'Failed to initialize session',
                details: err.message,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Start enrollment
     */
    handleStartEnrollment(ws) {
        const client = this.clients.get(ws);
        if (!client || !client.sessionId) {
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'No active session',
                details: 'Please initialize session first',
                timestamp: Date.now()
            });
            return;
        }

        try {
            const session = this.sessionManager.getSession(client.sessionId);
            if (!session) {
                throw new Error('Session not found or expired');
            }

            // Clear any previous audio
            this.sessionManager.clearAudioBuffer(client.sessionId);

            // Initialize chunk processing (1-second chunks for enrollment)
            this.chunkProcessor.initializeChunking(client.sessionId, 'enroll');

            // Update session action
            this.sessionManager.updateSession(client.sessionId, {
                metadata: { action: 'enroll', startedAt: Date.now(), chunked: true }
            });

            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ENROLLMENT_STARTED,
                message: 'Ready to receive audio for enrollment with chunking',
                instructions: 'Please speak your enrollment phrase (1-second chunks will be processed)',
                timestamp: Date.now()
            });

            console.log(`[WSHandler] Enrollment started for session ${client.sessionId} with chunk processing`);
        } catch (err) {
            console.error('[WSHandler] Enrollment start error:', err.message);
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'Failed to start enrollment',
                details: err.message,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Start verification
     */
    handleStartVerification(ws, message) {
        const client = this.clients.get(ws);
        if (!client || !client.sessionId) {
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'No active session',
                details: 'Please initialize session first',
                timestamp: Date.now()
            });
            return;
        }

        try {
            const session = this.sessionManager.getSession(client.sessionId);
            if (!session) {
                throw new Error('Session not found or expired');
            }

            // Clear any previous audio
            this.sessionManager.clearAudioBuffer(client.sessionId);

            // Initialize chunk processing (5-second chunks for verification)
            this.chunkProcessor.initializeChunking(client.sessionId, 'verify');

            // Update session action
            this.sessionManager.updateSession(client.sessionId, {
                metadata: { action: 'verify', startedAt: Date.now(), chunked: true }
            });

            this.sendMessage(ws, {
                type: MESSAGE_TYPES.VERIFICATION_STARTED,
                message: 'Ready to receive audio for verification with chunking',
                instructions: 'Please speak to verify your identity (5-second chunks will be processed)',
                timestamp: Date.now()
            });

            console.log(`[WSHandler] Verification started for session ${client.sessionId} with chunk processing`);
        } catch (err) {
            console.error('[WSHandler] Verification start error:', err.message);
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'Failed to start verification',
                details: err.message,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Handle audio data chunks
     */
    handleAudioData(ws, audioBuffer) {
        const client = this.clients.get(ws);
        if (!client || !client.sessionId) {
            console.warn('[WSHandler] Audio received but no active session');
            return;
        }

        try {
            const session = this.sessionManager.getSession(client.sessionId);
            if (!session) {
                this.sendMessage(ws, {
                    type: MESSAGE_TYPES.ERROR,
                    error: 'Session expired',
                    details: 'Your session has expired. Please reinitialize.',
                    timestamp: Date.now()
                });
                return;
            }

            // Add audio data to chunk processor for real-time chunk processing
            const status = this.chunkProcessor.addAudioData(client.sessionId, audioBuffer);

            // Also append to session buffer for fallback processing
            const totalSize = this.sessionManager.appendAudioData(client.sessionId, audioBuffer);

            // Get updated session for stats
            const updatedSession = this.sessionManager.getSession(client.sessionId);

            // Send confirmation with chunk info
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.AUDIO_RECEIVED,
                bytesReceived: audioBuffer.length,
                totalBytes: totalSize,
                chunkCount: status.completedChunks,
                bufferBytes: status.bufferBytes,
                timestamp: Date.now()
            });

            console.log(
              `[WSHandler] Audio received - Session: ${client.sessionId}, ` +
              `Size: ${audioBuffer.length}B, Total: ${totalSize}B, ` +
              `Chunks: ${status.completedChunks}/${Math.ceil(totalSize / 32000)}`
            );
        } catch (err) {
            console.error('[WSHandler] Audio handling error:', err.message);
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'Failed to process audio',
                details: err.message,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Stop audio and process
     */
    handleStopAudio(ws) {
        const client = this.clients.get(ws);
        if (!client || !client.sessionId) {
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'No active session',
                timestamp: Date.now()
            });
            return;
        }

        try {
            const session = this.sessionManager.getSession(client.sessionId);
            if (!session) {
                throw new Error('Session not found or expired');
            }

            // Finalize chunking - process any remaining audio
            const chunkingResult = this.chunkProcessor.finalizeChunking(client.sessionId);
            
            console.log(
              `[WSHandler] Chunking finalized for session ${client.sessionId}: ` +
              `${chunkingResult.stats.totalChunks} total chunks, ` +
              `${chunkingResult.stats.embeddings} embeddings generated`
            );

            const audioBuffer = this.sessionManager.getAudioBuffer(client.sessionId);
            if (!audioBuffer || audioBuffer.length === 0) {
                this.sendMessage(ws, {
                    type: MESSAGE_TYPES.ERROR,
                    error: 'No audio recorded',
                    details: 'Please record some audio before stopping',
                    timestamp: Date.now()
                });
                return;
            }

            // Send processing message
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.PROCESSING,
                message: 'Processing audio with chunk-based analysis...',
                audioSize: audioBuffer.length,
                chunksProcessed: chunkingResult.stats.embeddings,
                timestamp: Date.now()
            });

            // Process audio with backend
            this.processAudioWithBackend(ws, session, audioBuffer, chunkingResult);

        } catch (err) {
            console.error('[WSHandler] Stop audio error:', err.message);
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'Failed to process audio',
                details: err.message,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Process audio with FastAPI backend
     */
    async processAudioWithBackend(ws, session, audioBuffer, chunkingResult = null) {
        const client = this.clients.get(ws);
        if (!client) return;

        try {
            const action = session.metadata?.action || 'verify';
            const endpoint = action === 'enroll' ? '/enroll' : '/verify';

            // Prepare form data
            const FormData = require('form-data');
            const Readable = require('stream').Readable;
            const form = new FormData();

            // Create readable stream from buffer
            const stream = new Readable();
            stream.push(audioBuffer);
            stream.push(null);

            form.append('phone_number', client.userId);
            form.append('file', stream, 'audio.wav');

            // Include chunk information if available
            if (chunkingResult && chunkingResult.stats) {
                form.append('chunk_count', chunkingResult.stats.totalChunks.toString());
                form.append('embeddings_generated', chunkingResult.stats.embeddings.toString());
                form.append('processing_mode', 'chunk-based');
            }

            // Send to FastAPI backend
            console.log(`[WSHandler] Sending ${action} request to ${BACKEND_API_URL}${endpoint}`);

            const response = await axios.post(
                `${BACKEND_API_URL}${endpoint}`,
                form,
                {
                    headers: form.getHeaders(),
                    timeout: 30000
                }
            );

            const result = response.data;

            // Enhance result with chunk processing info
            const enhancedResult = {
                ...result,
                chunkProcessing: chunkingResult ? {
                    totalChunks: chunkingResult.stats.totalChunks,
                    embeddingsGenerated: chunkingResult.stats.embeddings,
                    totalBytes: chunkingResult.stats.totalBytes,
                    mode: 'chunk-based'
                } : null
            };

            // Send result to client
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.RESULT,
                action: action,
                success: result.success,
                data: enhancedResult,
                message: result.message,
                timestamp: Date.now()
            });

            // Clear audio buffer after processing
            this.sessionManager.clearAudioBuffer(client.sessionId);
            
            // Clear chunk processor after processing
            this.chunkProcessor.clearSession(client.sessionId);

            console.log(`[WSHandler] ${action} completed for ${client.userId}:`, result.success);

        } catch (err) {
            console.error('[WSHandler] Backend processing error:', err.message);
            
            // Check if it's a connection error
            const errorMessage = err.response?.data?.detail || err.message;
            
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'Processing failed',
                details: errorMessage,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Get session status
     */
    handleGetStatus(ws) {
        const client = this.clients.get(ws);
        if (!client || !client.sessionId) {
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.STATUS,
                connected: true,
                sessionActive: false,
                timestamp: Date.now()
            });
            return;
        }

        try {
            const session = this.sessionManager.getSession(client.sessionId);
            
            if (!session) {
                this.sendMessage(ws, {
                    type: MESSAGE_TYPES.STATUS,
                    connected: true,
                    sessionActive: false,
                    timestamp: Date.now()
                });
                return;
            }

            const audioBuffer = this.sessionManager.getAudioBuffer(client.sessionId);

            this.sendMessage(ws, {
                type: MESSAGE_TYPES.STATUS,
                connected: true,
                sessionActive: true,
                sessionData: {
                    userId: session.userId,
                    action: session.metadata?.action,
                    language: session.metadata?.language,
                    createdAt: session.createdAt,
                    expiresAt: session.expiresAt
                },
                audioStats: {
                    bufferSize: audioBuffer ? audioBuffer.length : 0,
                    chunkCount: audioBuffer ? Math.ceil(audioBuffer.length / AUDIO_CONFIG.CHUNK_SIZE) : 0
                },
                timestamp: Date.now()
            });

        } catch (err) {
            console.error('[WSHandler] Status error:', err.message);
            this.sendMessage(ws, {
                type: MESSAGE_TYPES.ERROR,
                error: 'Failed to get status',
                details: err.message,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Handle ping
     */
    handlePing(ws) {
        this.sendMessage(ws, {
            type: MESSAGE_TYPES.PONG,
            timestamp: Date.now()
        });
    }

    /**
     * Send message to client
     */
    sendMessage(ws, message) {
        if (ws.readyState === WebSocket.OPEN) {
            try {
                ws.send(JSON.stringify(message));
            } catch (err) {
                console.error('[WSHandler] Failed to send message:', err.message);
            }
        }
    }

    /**
     * Broadcast message to all connected clients
     */
    broadcast(message) {
        const data = JSON.stringify(message);
        this.wss.clients.forEach((client) => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(data);
            }
        });
    }

    /**
     * Get server stats
     */
    getStats() {
        return {
            port: this.port,
            connectedClients: this.clients.size,
            activeSessions: this.sessionManager.sessions.size,
            uptime: process.uptime(),
            memory: process.memoryUsage(),
            clients: Array.from(this.clients.values()).map(c => ({
                id: c.id,
                userId: c.userId,
                sessionId: c.sessionId,
                connectedAt: c.connectedAt,
                messageCount: c.messageCount
            }))
        };
    }
}

// Export for use in other modules
module.exports = WebSocketAudioHandler;

// Start server if running directly
if (require.main === module) {
    const handler = new WebSocketAudioHandler(WS_PORT);
    
    handler.start()
        .then(() => {
            console.log(`\n✓ WebSocket server started successfully!`);
            console.log(`✓ URL: ws://localhost:${WS_PORT}`);
            console.log(`✓ Backend API: ${BACKEND_API_URL}`);
            console.log(`✓ Environment: ${NODE_ENV}\n`);
            
            // Log stats periodically
            setInterval(() => {
                const stats = handler.getStats();
                console.log(`[Stats] Connected: ${stats.connectedClients}, Sessions: ${stats.activeSessions}`);
            }, 30000);
        })
        .catch((err) => {
            console.error('Failed to start WebSocket server:', err);
            process.exit(1);
        });

    // Handle graceful shutdown
    process.on('SIGTERM', async () => {
        console.log('\n[WSHandler] Received SIGTERM, shutting down gracefully...');
        await handler.stop();
        process.exit(0);
    });

    process.on('SIGINT', async () => {
        console.log('\n[WSHandler] Received SIGINT, shutting down gracefully...');
        await handler.stop();
        process.exit(0);
    });
}
