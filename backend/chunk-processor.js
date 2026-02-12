/**
 * Chunk-Based Audio Processing for Voice Biometrics
 * Handles real-time chunking, embedding generation, and comparison
 * 
 * Architecture:
 * - Enrollment: 1-second chunks (16,000 samples at 16kHz)
 * - Verification: 5-second chunks (80,000 samples at 16kHz)
 * - Per-chunk embedding generation and storage
 * - Chunk-by-chunk comparison during verification
 */

const { EventEmitter } = require('events');
const axios = require('axios');

// Configuration
const AUDIO_CONFIG = {
  SAMPLE_RATE: 16000,
  CHANNELS: 1,
  BITS_PER_SAMPLE: 16,
  ENROLLMENT_CHUNK_SIZE: 32000, // 1 second in bytes (16000 * 2 bytes per sample)
  VERIFICATION_CHUNK_SIZE: 160000, // 5 seconds in bytes (80000 * 2 bytes per sample)
  MIN_CHUNK_SIZE: 8000 // Minimum 0.25 seconds
};

// Chunk states
const CHUNK_STATE = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  PROCESSED: 'processed',
  FAILED: 'failed'
};

/**
 * ChunkBuffer class
 * Manages buffering of audio data into chunks
 */
class ChunkBuffer extends EventEmitter {
  constructor(chunkSize) {
    super();
    this.chunkSize = chunkSize;
    this.buffer = Buffer.alloc(0);
    this.chunks = [];
    this.isComplete = false;
  }

  /**
   * Add data to buffer
   */
  addData(data) {
    if (!(data instanceof Buffer)) {
      throw new Error('Data must be a Buffer');
    }

    this.buffer = Buffer.concat([this.buffer, data]);
    this._extractChunks();

    return {
      totalBytes: this.buffer.length,
      completedChunks: this.chunks.length,
      bufferBytes: this.buffer.length
    };
  }

  /**
   * Extract complete chunks from buffer
   */
  _extractChunks() {
    while (this.buffer.length >= this.chunkSize) {
      const chunk = this.buffer.slice(0, this.chunkSize);
      this.chunks.push(chunk);
      this.buffer = this.buffer.slice(this.chunkSize);

      this.emit('chunk-ready', {
        chunkIndex: this.chunks.length - 1,
        chunkSize: chunk.length,
        totalChunks: this.chunks.length
      });
    }
  }

  /**
   * Get all completed chunks
   */
  getCompletedChunks() {
    return [...this.chunks];
  }

  /**
   * Get remaining buffer
   */
  getRemainingBuffer() {
    return Buffer.from(this.buffer);
  }

  /**
   * Finalize and get any remaining data as a chunk
   */
  finalize() {
    if (this.buffer.length >= AUDIO_CONFIG.MIN_CHUNK_SIZE) {
      this.chunks.push(this.buffer);
      const chunk = this.chunks[this.chunks.length - 1];
      this.emit('chunk-ready', {
        chunkIndex: this.chunks.length - 1,
        chunkSize: chunk.length,
        totalChunks: this.chunks.length,
        isFinal: true
      });
      this.buffer = Buffer.alloc(0);
    }
    this.isComplete = true;
    return this.chunks;
  }

  /**
   * Reset buffer
   */
  reset() {
    this.buffer = Buffer.alloc(0);
    this.chunks = [];
    this.isComplete = false;
  }

  /**
   * Get statistics
   */
  getStats() {
    return {
      chunkSize: this.chunkSize,
      completedChunks: this.chunks.length,
      bufferBytes: this.buffer.length,
      totalBytes: this.chunks.reduce((sum, chunk) => sum + chunk.length, 0) + this.buffer.length,
      isComplete: this.isComplete
    };
  }
}

/**
 * ChunkProcessor class
 * Manages chunk processing, embedding generation, and comparison
 */
class ChunkProcessor extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      backendUrl: config.backendUrl || 'http://localhost:8000',
      enrollmentChunkSize: AUDIO_CONFIG.ENROLLMENT_CHUNK_SIZE,
      verificationChunkSize: AUDIO_CONFIG.VERIFICATION_CHUNK_SIZE,
      similarityThreshold: config.similarityThreshold || 0.75,
      minChunksForMatch: config.minChunksForMatch || 4,
      ...config
    };

    this.buffers = new Map(); // sessionId -> ChunkBuffer
    this.chunkEmbeddings = new Map(); // sessionId -> { chunkIndex: embedding }
    this.chunkMetadata = new Map(); // sessionId -> { chunkIndex: metadata }
    this.processingQueue = new Map(); // sessionId -> tasks[]
    this.logger = config.logger || console;
  }

  /**
   * Initialize chunking for a session
   */
  initializeChunking(sessionId, action = 'enroll') {
    const chunkSize = action === 'enroll' 
      ? this.config.enrollmentChunkSize 
      : this.config.verificationChunkSize;

    const buffer = new ChunkBuffer(chunkSize);

    // Listen for chunk readiness
    buffer.on('chunk-ready', (chunkInfo) => {
      this.emit('chunk-ready', {
        sessionId,
        action,
        ...chunkInfo
      });

      // Queue chunk for processing
      this.queueChunkProcessing(sessionId, chunkInfo.chunkIndex);
    });

    this.buffers.set(sessionId, buffer);
    this.chunkEmbeddings.set(sessionId, {});
    this.chunkMetadata.set(sessionId, {});
    this.processingQueue.set(sessionId, []);

    this.logger.info(
      `[ChunkProcessor] Initialized chunking for session ${sessionId} (${action}, chunk size: ${chunkSize} bytes)`
    );
  }

  /**
   * Add audio data for a session
   */
  addAudioData(sessionId, audioBuffer) {
    if (!this.buffers.has(sessionId)) {
      throw new Error(`Session ${sessionId} not initialized`);
    }

    const buffer = this.buffers.get(sessionId);
    const status = buffer.addData(audioBuffer);

    this.emit('audio-data-added', {
      sessionId,
      ...status
    });

    return status;
  }

  /**
   * Queue chunk for processing
   */
  queueChunkProcessing(sessionId, chunkIndex) {
    if (!this.processingQueue.has(sessionId)) {
      this.processingQueue.set(sessionId, []);
    }

    const queue = this.processingQueue.get(sessionId);
    queue.push(chunkIndex);

    // Process immediately
    this.processNextChunk(sessionId);
  }

  /**
   * Process next chunk in queue
   */
  async processNextChunk(sessionId) {
    const queue = this.processingQueue.get(sessionId);
    if (!queue || queue.length === 0) return;

    const chunkIndex = queue[0];
    const buffer = this.buffers.get(sessionId);
    const chunks = buffer.getCompletedChunks();

    if (chunkIndex >= chunks.length) return;

    const chunk = chunks[chunkIndex];

    try {
      this.logger.info(`[ChunkProcessor] Processing chunk ${chunkIndex} for session ${sessionId}`);

      // Generate embedding for chunk
      const embedding = await this.generateChunkEmbedding(sessionId, chunkIndex, chunk);

      // Store embedding
      const embeddings = this.chunkEmbeddings.get(sessionId);
      embeddings[chunkIndex] = embedding;

      // Update metadata
      const metadata = this.chunkMetadata.get(sessionId);
      metadata[chunkIndex] = {
        timestamp: Date.now(),
        size: chunk.length,
        state: CHUNK_STATE.PROCESSED,
        embeddingGenerated: true
      };

      queue.shift(); // Remove from queue

      this.emit('chunk-processed', {
        sessionId,
        chunkIndex,
        embeddingDimension: embedding.length,
        metadata: metadata[chunkIndex]
      });

      // Process next chunk
      this.processNextChunk(sessionId);

    } catch (error) {
      this.logger.error(`[ChunkProcessor] Error processing chunk ${chunkIndex}:`, error.message);

      const metadata = this.chunkMetadata.get(sessionId);
      if (metadata) {
        metadata[chunkIndex] = {
          timestamp: Date.now(),
          size: chunk.length,
          state: CHUNK_STATE.FAILED,
          error: error.message
        };
      }

      const queue = this.processingQueue.get(sessionId);
      if (queue && queue.length > 0) {
        queue.shift(); // Remove from queue
      }

      this.emit('chunk-processing-error', {
        sessionId,
        chunkIndex,
        error: error.message
      });

      // Process next chunk even if one fails
      this.processNextChunk(sessionId);
    }
  }

  /**
   * Generate embedding for a chunk
   */
  async generateChunkEmbedding(sessionId, chunkIndex, chunkBuffer) {
    try {
      // Convert buffer to base64 for transmission
      const base64Audio = chunkBuffer.toString('base64');

      // Call backend to generate embedding
      const response = await axios.post(
        `${this.config.backendUrl}/embedding/generate`,
        {
          audio_data: base64Audio,
          sample_rate: AUDIO_CONFIG.SAMPLE_RATE,
          chunk_index: chunkIndex
        },
        { timeout: 30000 }
      );

      if (!response.data.success) {
        throw new Error(response.data.error || 'Failed to generate embedding');
      }

      return response.data.embedding;
    } catch (error) {
      this.logger.error(`[ChunkProcessor] Embedding generation error for chunk ${chunkIndex}:`, error.message);
      throw error;
    }
  }

  /**
   * Finalize chunking and get all chunks
   */
  finalizeChunking(sessionId) {
    if (!this.buffers.has(sessionId)) {
      throw new Error(`Session ${sessionId} not initialized`);
    }

    const buffer = this.buffers.get(sessionId);
    const finalChunks = buffer.finalize();

    const stats = {
      totalChunks: finalChunks.length,
      totalBytes: finalChunks.reduce((sum, chunk) => sum + chunk.length, 0),
      embeddings: Object.keys(this.chunkEmbeddings.get(sessionId) || {}).length,
      chunkSize: buffer.chunkSize
    };

    this.emit('chunking-finalized', {
      sessionId,
      stats
    });

    return {
      chunks: finalChunks,
      embeddings: this.chunkEmbeddings.get(sessionId),
      metadata: this.chunkMetadata.get(sessionId),
      stats
    };
  }

  /**
   * Compare verification chunks against enrolled chunks
   */
  async compareChunks(sessionId, enrolledEmbeddings, verificationEmbeddings) {
    try {
      const comparisonResult = {
        totalEnrolledChunks: enrolledEmbeddings.length,
        totalVerificationChunks: Object.keys(verificationEmbeddings).length,
        comparisons: [],
        matchCount: 0,
        bestMatches: [],
        averageSimilarity: 0,
        isMatch: false,
        details: {}
      };

      // Compare each verification chunk against all enrolled chunks
      const similarities = [];

      for (const [verifyIdx, verifyEmbedding] of Object.entries(verificationEmbeddings)) {
        const verifyChunkIdx = parseInt(verifyIdx);
        let bestSimilarity = 0;
        let bestMatchIdx = -1;

        for (let enrollIdx = 0; enrollIdx < enrolledEmbeddings.length; enrollIdx++) {
          const similarity = this.calculateSimilarity(
            enrolledEmbeddings[enrollIdx],
            verifyEmbedding
          );

          similarities.push(similarity);

          if (similarity >= this.config.similarityThreshold) {
            if (similarity > bestSimilarity) {
              bestSimilarity = similarity;
              bestMatchIdx = enrollIdx;
            }
          }

          comparisonResult.comparisons.push({
            verificationChunkIdx,
            enrolledChunkIdx: enrollIdx,
            similarity
          });
        }

        // Count as match if similarity exceeds threshold
        if (bestSimilarity >= this.config.similarityThreshold) {
          comparisonResult.matchCount++;
          comparisonResult.bestMatches.push({
            verificationChunkIdx,
            enrolledChunkIdx: bestMatchIdx,
            similarity: bestSimilarity
          });
        }
      }

      // Calculate average similarity
      if (similarities.length > 0) {
        comparisonResult.averageSimilarity = 
          similarities.reduce((a, b) => a + b, 0) / similarities.length;
      }

      // Determine overall match (requires minimum matching chunks)
      comparisonResult.isMatch = comparisonResult.matchCount >= this.config.minChunksForMatch;

      comparisonResult.details = {
        threshold: this.config.similarityThreshold,
        minChunksRequired: this.config.minChunksForMatch,
        matchingChunks: comparisonResult.matchCount,
        successMessage: comparisonResult.isMatch
          ? `Match verified: ${comparisonResult.matchCount} matching chunks (requires ${this.config.minChunksForMatch}+)`
          : `Match failed: Only ${comparisonResult.matchCount} matching chunks (requires ${this.config.minChunksForMatch}+)`
      };

      this.logger.info(
        `[ChunkProcessor] Session ${sessionId}: ${comparisonResult.matchCount} matching chunks (${comparisonResult.isMatch ? 'MATCH' : 'NO MATCH'})`
      );

      return comparisonResult;
    } catch (error) {
      this.logger.error('[ChunkProcessor] Error comparing chunks:', error.message);
      throw error;
    }
  }

  /**
   * Calculate similarity between two embeddings
   */
  calculateSimilarity(embedding1, embedding2) {
    if (!Array.isArray(embedding1) || !Array.isArray(embedding2)) {
      return 0;
    }

    if (embedding1.length !== embedding2.length) {
      return 0;
    }

    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;

    for (let i = 0; i < embedding1.length; i++) {
      dotProduct += embedding1[i] * embedding2[i];
      norm1 += embedding1[i] * embedding1[i];
      norm2 += embedding2[i] * embedding2[i];
    }

    norm1 = Math.sqrt(norm1);
    norm2 = Math.sqrt(norm2);

    if (norm1 === 0 || norm2 === 0) {
      return 0;
    }

    const cosineSimilarity = dotProduct / (norm1 * norm2);
    // Convert from [-1, 1] to [0, 1]
    return (cosineSimilarity + 1) / 2;
  }

  /**
   * Get session chunks
   */
  getSessionChunks(sessionId) {
    if (!this.buffers.has(sessionId)) {
      return null;
    }

    const buffer = this.buffers.get(sessionId);
    return buffer.getCompletedChunks();
  }

  /**
   * Get session embeddings
   */
  getSessionEmbeddings(sessionId) {
    return this.chunkEmbeddings.get(sessionId) || {};
  }

  /**
   * Get session statistics
   */
  getSessionStats(sessionId) {
    const buffer = this.buffers.get(sessionId);
    const embeddings = this.chunkEmbeddings.get(sessionId);
    const metadata = this.chunkMetadata.get(sessionId);

    if (!buffer) {
      return null;
    }

    return {
      ...buffer.getStats(),
      embeddingsGenerated: Object.keys(embeddings || {}).length,
      metadata: metadata || {},
      queue: this.processingQueue.get(sessionId) || []
    };
  }

  /**
   * Clear session data
   */
  clearSession(sessionId) {
    this.buffers.delete(sessionId);
    this.chunkEmbeddings.delete(sessionId);
    this.chunkMetadata.delete(sessionId);
    this.processingQueue.delete(sessionId);

    this.logger.info(`[ChunkProcessor] Cleared session ${sessionId}`);
  }

  /**
   * Get overall statistics
   */
  getStats() {
    return {
      activeSessions: this.buffers.size,
      totalChunksProcessed: Array.from(this.chunkEmbeddings.values())
        .reduce((sum, embeddings) => sum + Object.keys(embeddings).length, 0),
      config: this.config
    };
  }
}

module.exports = {
  ChunkBuffer,
  ChunkProcessor,
  AUDIO_CONFIG,
  CHUNK_STATE
};
