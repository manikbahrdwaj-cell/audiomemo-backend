/**
 * Audio Chunker Integration Guide
 * Examples of how to use audio-chunker.js in your WebSocket handler
 */

const { AudioChunker, AudioStreamManager } = require('./audio-chunker');

/**
 * Example 1: Basic Usage in WebSocket Handler
 * 
 * Replace the handleAudioData function with:
 */
function handleAudioData_WithChunker(ws, clientConnection, data) {
    try {
        // Initialize chunker if not exists
        if (!clientConnection.chunker) {
            clientConnection.chunker = new AudioChunker({
                chunkSize: 4096,
                maxBufferSize: 5 * 1024 * 1024
            });

            // Listen to chunk events
            clientConnection.chunker.on('chunk', (chunkInfo) => {
                console.log(`Complete chunk received: #${chunkInfo.chunkNumber}`);
            });

            clientConnection.chunker.on('error', (error) => {
                console.error('Chunker error:', error.message);
                sendError(ws, 'Audio processing error', error.message);
            });
        }

        // Add data to chunker
        const status = clientConnection.chunker.addData(data);

        // Send acknowledgment every 10 chunks
        if (status.totalChunksProcessed % 10 === 0) {
            sendMessage(ws, {
                type: 'audio-received',
                bytesReceived: status.bytesReceived,
                chunkCount: status.completeChunks,
                estimatedDuration: status.estimatedDurationSeconds.toFixed(2)
            });
        }
    } catch (error) {
        console.error('Error adding audio data:', error.message);
        sendError(ws, 'Failed to process audio', error.message);
    }
}

/**
 * Example 2: Handle Stop Audio with Validation
 * 
 * Replace the handleStopAudio function with:
 */
async function handleStopAudio_WithChunker(ws, clientConnection) {
    const { userId, action, verifyUserId } = clientConnection.sessionData;

    if (!clientConnection.chunker) {
        sendError(ws, 'No audio session', 'Audio chunker not initialized');
        return;
    }

    try {
        // Validate audio
        const validation = clientConnection.chunker.validate();
        console.log('Audio validation:', validation);

        if (!validation.isValid) {
            sendError(ws, 'Invalid audio', validation.issues.join(', '));
            return;
        }

        sendMessage(ws, {
            type: 'processing',
            message: 'Processing audio...',
            stats: clientConnection.chunker.getStats()
        });

        // Convert to WAV format
        const audioWAV = clientConnection.chunker.toWAV();
        
        let result;
        if (action === 'enroll') {
            result = await enrollVoice(ws, userId, audioWAV);
        } else if (action === 'verify') {
            result = await verifyVoice(ws, verifyUserId || userId, audioWAV);
        } else {
            sendError(ws, 'Invalid action', `Action: ${action}`);
            return;
        }

        // Send result with detailed stats
        sendMessage(ws, {
            type: 'result',
            action,
            success: result.success,
            data: result.data,
            message: result.message,
            audioStats: clientConnection.chunker.getStats()
        });

        // Clean up
        clientConnection.chunker.reset();

    } catch (error) {
        console.error(`Error processing audio for ${userId}:`, error.message);
        sendError(ws, 'Audio processing failed', error.message);
    }
}

/**
 * Example 3: Stream Processing with AudioStreamManager
 */
async function handleAudioData_WithStream(ws, clientConnection, data) {
    try {
        // Initialize stream manager if not exists
        if (!clientConnection.streamManager) {
            clientConnection.streamManager = new AudioStreamManager({
                chunkSize: 4096,
                maxBufferSize: 5 * 1024 * 1024
            });
        }

        const status = clientConnection.streamManager.addData(data);
        
        if (status.totalChunksProcessed % 10 === 0) {
            sendMessage(ws, {
                type: 'audio-received',
                stat: status
            });
        }
    } catch (error) {
        sendError(ws, 'Stream error', error.message);
    }
}

/**
 * Example 4: Process Chunks Asynchronously
 */
async function processChunksAsync(clientConnection) {
    const chunker = clientConnection.chunker;
    
    try {
        await chunker.processChunks(async (chunk, index, total) => {
            // Process each chunk
            console.log(`Processing chunk ${index + 1}/${total}`);
            
            // Example: Send to ML model for processing
            // const embedding = await sendToMLModel(chunk);
            
            // Simulate processing
            await new Promise(resolve => setTimeout(resolve, 10));
        });

        console.log('All chunks processed');
    } catch (error) {
        console.error('Error processing chunks:', error);
    }
}

/**
 * Example 5: Get Detailed Statistics
 */
function getAudioStats(clientConnection) {
    if (!clientConnection.chunker) {
        return null;
    }

    const stats = clientConnection.chunker.getStats();
    const status = clientConnection.chunker.getStatus();

    return {
        // Size information
        totalBytes: stats.totalBytes,
        incompleteBytes: stats.incompleteChunkBytes,
        
        // Chunk information
        completeChunks: stats.completeChunks,
        chunkSize: stats.chunkSize,
        
        // Audio information
        estimatedDuration: stats.estimatedDurationSeconds,
        sampleRate: stats.sampleRate,
        channels: stats.channels,
        bitDepth: stats.bitDepth,
        averageBitrate: stats.averageBitrate,
        
        // Streaming information
        elapsedTime: status.elapsedTimeMs,
        bytesPerSecond: status.bytesPerSecond
    };
}

/**
 * Example 6: Handle Client Initialization
 * 
 * In handleInitialization function:
 */
function handleInitialization_WithChunker(ws, clientConnection, { userId, action, language }) {
    clientConnection.sessionData.userId = userId;
    clientConnection.sessionData.action = action;
    clientConnection.sessionData.language = language;
    clientConnection.sessionData.startTime = Date.now();
    
    // Initialize new chunker for this session
    clientConnection.chunker = new AudioChunker({
        chunkSize: 4096,
        maxBufferSize: 5 * 1024 * 1024,
        sampleRate: 16000,
        channels: 1,
        bitDepth: 16
    });

    sendMessage(ws, {
        type: 'initialized',
        userId,
        action,
        message: `Session initialized for ${action}`
    });

    console.log(`[WS] Session initialized - User: ${userId}, Action: ${action}`);
}

/**
 * Integration Steps:
 * 
 * 1. Import the audio chunker:
 *    const { AudioChunker, AudioStreamManager } = require('./audio-chunker');
 * 
 * 2. Initialize chunker in handleInitialization:
 *    clientConnection.chunker = new AudioChunker({ ... });
 * 
 * 3. Replace handleAudioData implementation with chunker version
 * 
 * 4. Replace handleStopAudio with chunker validation version
 * 
 * 5. Use toWAV() to convert audio to WAV format for API calls
 * 
 * 6. Cleanup by calling chunker.reset() after processing
 * 
 * Key Features:
 * - Efficient chunk management
 * - Audio validation
 * - WAV format conversion
 * - Event-based notifications
 * - Stream processing
 * - Detailed statistics
 * - Error handling
 */

module.exports = {
    handleAudioData_WithChunker,
    handleStopAudio_WithChunker,
    handleAudioData_WithStream,
    processChunksAsync,
    getAudioStats,
    handleInitialization_WithChunker
};
