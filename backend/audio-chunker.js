/**
 * Audio Chunker Utility
 * Handles efficient audio data chunking, buffering, and stream processing
 * Optimized for real-time WebSocket audio streaming
 */

const { EventEmitter } = require('events');

// Default configuration
const DEFAULT_CONFIG = {
    chunkSize: 4096,           // Size of each audio chunk in bytes
    maxBufferSize: 5 * 1024 * 1024, // Max buffer size (5MB)
    sampleRate: 16000,         // Sample rate in Hz
    channels: 1,               // Number of audio channels
    bitDepth: 16,              // Bits per sample
};

/**
 * AudioChunker class
 * Manages audio data chunking and streaming
 */
class AudioChunker extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.buffer = Buffer.alloc(0);
        this.chunks = [];
        this.isProcessing = false;
        this.bytesReceived = 0;
        this.chunkCount = 0;
        this.startTime = Date.now();
    }

    /**
     * Add audio data to the chunker
     * @param {Buffer} data - Audio data to add
     * @returns {Object} Status object with buffer info
     */
    addData(data) {
        if (!Buffer.isBuffer(data)) {
            throw new Error('Data must be a Buffer');
        }

        if (data.length === 0) {
            return this.getStatus();
        }

        // Check buffer size limit
        const newSize = this.buffer.length + data.length;
        if (newSize > this.config.maxBufferSize) {
            const error = new Error('Buffer size limit exceeded');
            error.currentSize = this.buffer.length;
            error.maxSize = this.config.maxBufferSize;
            this.emit('error', error);
            throw error;
        }

        // Concatenate new data
        this.buffer = Buffer.concat([this.buffer, data]);
        this.bytesReceived += data.length;

        // Extract complete chunks
        this._extractChunks();

        return this.getStatus();
    }

    /**
     * Extract complete chunks from buffer
     * @private
     */
    _extractChunks() {
        while (this.buffer.length >= this.config.chunkSize) {
            const chunk = this.buffer.slice(0, this.config.chunkSize);
            this.chunks.push(chunk);
            this.buffer = this.buffer.slice(this.config.chunkSize);
            this.chunkCount++;

            this.emit('chunk', {
                chunk,
                chunkNumber: this.chunkCount,
                chunkSize: chunk.length
            });
        }
    }

    /**
     * Get all complete chunks
     * @returns {Array<Buffer>} Array of audio chunks
     */
    getChunks() {
        return [...this.chunks];
    }

    /**
     * Get next chunk without removing it
     * @param {number} index - Chunk index
     * @returns {Buffer|null} Chunk or null if not available
     */
    peekChunk(index = 0) {
        return this.chunks[index] || null;
    }

    /**
     * Get and remove next chunk
     * @returns {Buffer|null} Chunk or null if no chunks available
     */
    popChunk() {
        return this.chunks.length > 0 ? this.chunks.shift() : null;
    }

    /**
     * Get remaining buffer data (incomplete chunk)
     * @returns {Buffer} Remaining buffer
     */
    getBuffer() {
        return Buffer.from(this.buffer);
    }

    /**
     * Get complete audio data including remaining buffer
     * @returns {Buffer} Complete audio buffer
     */
    getCompleteAudio() {
        const completeChunks = Buffer.concat(this.chunks);
        return Buffer.concat([completeChunks, this.buffer]);
    }

    /**
     * Reset chunker state
     */
    reset() {
        this.buffer = Buffer.alloc(0);
        this.chunks = [];
        this.bytesReceived = 0;
        this.chunkCount = 0;
        this.startTime = Date.now();
        this.isProcessing = false;
    }

    /**
     * Get current status
     * @returns {Object} Status object
     */
    getStatus() {
        const elapsedTime = Date.now() - this.startTime;
        const bytesPerSecond = elapsedTime > 0 ? (this.bytesReceived / elapsedTime) * 1000 : 0;

        return {
            bytesReceived: this.bytesReceived,
            completeChunks: this.chunks.length,
            pendingChunkBytes: this.buffer.length,
            totalChunksProcessed: this.chunkCount,
            elapsedTimeMs: elapsedTime,
            bytesPerSecond: Math.round(bytesPerSecond),
            estimatedDurationSeconds: this._estimateDuration()
        };
    }

    /**
     * Estimate audio duration based on sample rate
     * @private
     * @returns {number} Estimated duration in seconds
     */
    _estimateDuration() {
        // Bytes per sample: (bitDepth / 8) * channels
        const bytesPerSample = (this.config.bitDepth / 8) * this.config.channels;
        const totalSamples = this.bytesReceived / bytesPerSample;
        return totalSamples / this.config.sampleRate;
    }

    /**
     * Validate audio data
     * @returns {Object} Validation result
     */
    validate() {
        const issues = [];

        // Check minimum data
        if (this.bytesReceived === 0) {
            issues.push('No audio data received');
        }

        // Check for sufficient data (at least 0.5 seconds)
        const minBytes = (this.config.sampleRate * 0.5) * 
                        (this.config.bitDepth / 8) * 
                        this.config.channels;
        if (this.bytesReceived < minBytes) {
            issues.push(`Insufficient audio data. Minimum: ${minBytes} bytes, Received: ${this.bytesReceived} bytes`);
        }

        // Check for valid chunk count
        if (this.chunkCount === 0 && this.buffer.length === 0) {
            issues.push('No complete audio chunks processed');
        }

        return {
            isValid: issues.length === 0,
            issues,
            audioStats: this.getStatus()
        };
    }

    /**
     * Convert audio to WAV format (simplified)
     * @returns {Buffer} WAV formatted audio data
     */
    toWAV() {
        const audioData = this.getCompleteAudio();
        const sampleRate = this.config.sampleRate;
        const channels = this.config.channels;
        const bitDepth = this.config.bitDepth;
        
        const byteRate = sampleRate * channels * (bitDepth / 8);
        const blockAlign = channels * (bitDepth / 8);
        const subChunk2Size = audioData.length;
        const chunkSize = 36 + subChunk2Size;

        const wav = Buffer.alloc(44 + subChunk2Size);
        let offset = 0;

        // RIFF header
        wav.write('RIFF', offset); offset += 4;
        wav.writeUInt32LE(chunkSize, offset); offset += 4;
        wav.write('WAVE', offset); offset += 4;

        // fmt subchunk
        wav.write('fmt ', offset); offset += 4;
        wav.writeUInt32LE(16, offset); offset += 4; // Subchunk1Size
        wav.writeUInt16LE(1, offset); offset += 2;  // Audio format (1 = PCM)
        wav.writeUInt16LE(channels, offset); offset += 2;
        wav.writeUInt32LE(sampleRate, offset); offset += 4;
        wav.writeUInt32LE(byteRate, offset); offset += 4;
        wav.writeUInt16LE(blockAlign, offset); offset += 2;
        wav.writeUInt16LE(bitDepth, offset); offset += 2;

        // data subchunk
        wav.write('data', offset); offset += 4;
        wav.writeUInt32LE(subChunk2Size, offset); offset += 4;

        // Audio data
        audioData.copy(wav, offset);

        return wav;
    }

    /**
     * Get statistics summary
     * @returns {Object} Statistics summary
     */
    getStats() {
        const duration = this._estimateDuration();
        const bytesPerSecond = duration > 0 ? this.bytesReceived / duration : 0;

        return {
            totalBytes: this.bytesReceived,
            completeChunks: this.chunks.length,
            chunkSize: this.config.chunkSize,
            totalChunksCreated: this.chunkCount,
            incompleteChunkBytes: this.buffer.length,
            estimatedDurationSeconds: duration,
            averageBitrate: Math.round(bytesPerSecond * 8 / 1000), // kbps
            sampleRate: this.config.sampleRate,
            channels: this.config.channels,
            bitDepth: this.config.bitDepth
        };
    }

    /**
     * Iterate through chunks with callback
     * @param {Function} callback - Function to call for each chunk
     * @returns {Promise<void>}
     */
    async processChunks(callback) {
        if (typeof callback !== 'function') {
            throw new Error('Callback must be a function');
        }

        this.isProcessing = true;
        try {
            for (let i = 0; i < this.chunks.length; i++) {
                await callback(this.chunks[i], i, this.chunks.length);
            }
        } finally {
            this.isProcessing = false;
        }
    }

    /**
     * Check if chunker has complete chunks
     * @returns {boolean}
     */
    hasChunks() {
        return this.chunks.length > 0;
    }

    /**
     * Get number of complete chunks
     * @returns {number}
     */
    getChunkCount() {
        return this.chunks.length;
    }

    /**
     * Clear all chunks but keep configuration
     */
    clearChunks() {
        this.chunks = [];
    }
}

/**
 * AudioStreamManager class
 * Manages streaming of audio data
 */
class AudioStreamManager extends EventEmitter {
    constructor(config = {}) {
        super();
        this.chunker = new AudioChunker(config);
        this.isStreaming = false;
    }

    /**
     * Add data to stream
     * @param {Buffer} data - Audio data
     * @returns {Object} Status
     */
    addData(data) {
        return this.chunker.addData(data);
    }

    /**
     * Start streaming chunks
     * @param {Function} onChunk - Callback for each chunk
     */
    async startStreaming(onChunk) {
        if (this.isStreaming) {
            throw new Error('Already streaming');
        }

        this.isStreaming = true;
        try {
            await this.chunker.processChunks(onChunk);
        } finally {
            this.isStreaming = false;
        }
    }

    /**
     * Finish streaming and get complete audio
     * @returns {Buffer} Complete audio data
     */
    finishStream() {
        this.isStreaming = false;
        return this.chunker.getCompleteAudio();
    }

    /**
     * Get chunker reference
     * @returns {AudioChunker}
     */
    getChunker() {
        return this.chunker;
    }
}

module.exports = {
    AudioChunker,
    AudioStreamManager,
    DEFAULT_CONFIG
};
