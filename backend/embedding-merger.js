/**
 * Embedding Merger Service
 * Handles averaging, merging, and normalizing speaker embeddings
 * Combines multiple chunk embeddings into final unified embeddings
 */

const { EventEmitter } = require('events');

/**
 * Embedding Merger Class
 * Manages embedding aggregation and normalization operations
 */
class EmbeddingMerger extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            embeddingDimension: config.embeddingDimension || 192,
            normalizeMethod: config.normalizeMethod || 'l2', // 'l2' or 'l1'
            maxChunks: config.maxChunks || 1000,
            nanThreshold: config.nanThreshold || 0.1, // Percentage of NaN values allowed
            ...config
        };

        this.logger = config.logger || console;
    }

    /**
     * Validate embedding array
     * @param {Array<Array>} embeddings - Array of embedding vectors
     * @returns {Object} Validation result with status and details
     */
    validateEmbeddings(embeddings) {
        const result = {
            isValid: true,
            totalEmbeddings: embeddings.length,
            invalidEmbeddings: [],
            nanCount: 0,
            nanPercentage: 0,
            message: ''
        };

        if (!Array.isArray(embeddings)) {
            result.isValid = false;
            result.message = 'Embeddings must be an array';
            return result;
        }

        if (embeddings.length === 0) {
            result.isValid = false;
            result.message = 'Cannot merge zero embeddings';
            return result;
        }

        if (embeddings.length > this.config.maxChunks) {
            result.isValid = false;
            result.message = `Exceeded maximum chunks: ${embeddings.length} > ${this.config.maxChunks}`;
            return result;
        }

        // Validate each embedding
        embeddings.forEach((embedding, index) => {
            if (!Array.isArray(embedding)) {
                result.invalidEmbeddings.push({
                    index,
                    reason: 'Not an array'
                });
                result.isValid = false;
                return;
            }

            if (embedding.length !== this.config.embeddingDimension) {
                result.invalidEmbeddings.push({
                    index,
                    reason: `Wrong dimension: ${embedding.length} != ${this.config.embeddingDimension}`
                });
                result.isValid = false;
            }

            // Check for NaN values
            embedding.forEach((value, dimIndex) => {
                if (!Number.isFinite(value)) {
                    result.nanCount++;
                }
            });
        });

        // Calculate NaN percentage
        const totalValues = embeddings.length * this.config.embeddingDimension;
        result.nanPercentage = (result.nanCount / totalValues) * 100;

        // Check NaN threshold
        if (result.nanPercentage > this.config.nanThreshold) {
            result.isValid = false;
            result.message = `NaN percentage exceeds threshold: ${result.nanPercentage.toFixed(2)}% > ${this.config.nanThreshold}%`;
        }

        if (result.isValid && result.invalidEmbeddings.length === 0) {
            result.message = `Valid embeddings: ${embeddings.length}, NaN: ${result.nanPercentage.toFixed(2)}%`;
        }

        return result;
    }

    /**
     * Average embeddings into a single embedding vector
     * Handles NaN values by skipping them
     * @param {Array<Array>} embeddings - Array of embedding vectors (192-dimensional)
     * @returns {Array} Averaged embedding vector
     */
    averageEmbeddings(embeddings) {
        // Validate input
        const validation = this.validateEmbeddings(embeddings);
        if (!validation.isValid) {
            throw new Error(`Invalid embeddings: ${validation.message}`);
        }

        const result = new Array(this.config.embeddingDimension).fill(0);
        const counts = new Array(this.config.embeddingDimension).fill(0);

        // Sum embeddings while tracking valid values
        embeddings.forEach(embedding => {
            embedding.forEach((value, index) => {
                if (Number.isFinite(value)) {
                    result[index] += value;
                    counts[index]++;
                }
            });
        });

        // Calculate averages
        for (let i = 0; i < this.config.embeddingDimension; i++) {
            if (counts[i] > 0) {
                result[i] /= counts[i];
            } else {
                // All values for this dimension were NaN - use 0
                result[i] = 0;
            }
        }

        return result;
    }

    /**
     * Normalize embedding vector using L2 normalization
     * Ensures the vector has unit magnitude
     * @param {Array} embedding - Embedding vector to normalize
     * @returns {Array} Normalized embedding vector
     */
    normalizeL2(embedding) {
        if (!Array.isArray(embedding) || embedding.length === 0) {
            throw new Error('Invalid embedding for normalization');
        }

        // Calculate L2 norm (Euclidean distance from origin)
        let magnitude = 0;
        for (let i = 0; i < embedding.length; i++) {
            if (Number.isFinite(embedding[i])) {
                magnitude += embedding[i] * embedding[i];
            }
        }
        magnitude = Math.sqrt(magnitude);

        // Handle zero magnitude
        if (magnitude === 0) {
            this.logger.warn('Embedding has zero magnitude, returning as-is');
            return [...embedding];
        }

        // Normalize by dividing by magnitude
        return embedding.map(value => 
            Number.isFinite(value) ? value / magnitude : 0
        );
    }

    /**
     * Normalize embedding vector using L1 normalization
     * Sum of absolute values equals 1
     * @param {Array} embedding - Embedding vector to normalize
     * @returns {Array} Normalized embedding vector
     */
    normalizeL1(embedding) {
        if (!Array.isArray(embedding) || embedding.length === 0) {
            throw new Error('Invalid embedding for normalization');
        }

        // Calculate L1 norm (sum of absolute values)
        let sum = 0;
        for (let i = 0; i < embedding.length; i++) {
            if (Number.isFinite(embedding[i])) {
                sum += Math.abs(embedding[i]);
            }
        }

        // Handle zero sum
        if (sum === 0) {
            this.logger.warn('Embedding has zero L1 norm, returning as-is');
            return [...embedding];
        }

        // Normalize by dividing by sum
        return embedding.map(value =>
            Number.isFinite(value) ? value / sum : 0
        );
    }

    /**
     * Normalize embedding vector using configured method
     * @param {Array} embedding - Embedding vector to normalize
     * @param {String} method - Normalization method ('l2' or 'l1')
     * @returns {Array} Normalized embedding vector
     */
    normalizeEmbedding(embedding, method = null) {
        const normalizeMethod = method || this.config.normalizeMethod;

        if (normalizeMethod === 'l2') {
            return this.normalizeL2(embedding);
        } else if (normalizeMethod === 'l1') {
            return this.normalizeL1(embedding);
        } else {
            throw new Error(`Unknown normalization method: ${normalizeMethod}`);
        }
    }

    /**
     * Merge multiple chunk embeddings into a single final embedding
     * Main workflow: average -> normalize
     * @param {Array<Array>} chunkEmbeddings - Array of chunk embeddings
     * @param {Object} options - Merge options
     * @returns {Object} Merged embedding result with metadata
     */
    mergeEmbeddings(chunkEmbeddings, options = {}) {
        const startTime = Date.now();
        
        try {
            // Validate input
            const validation = this.validateEmbeddings(chunkEmbeddings);
            if (!validation.isValid) {
                throw new Error(`Validation failed: ${validation.message}`);
            }

            // Step 1: Average embeddings
            const averaged = this.averageEmbeddings(chunkEmbeddings);

            // Step 2: Normalize
            const normalized = this.normalizeEmbedding(
                averaged,
                options.normalizeMethod || this.config.normalizeMethod
            );

            const processingTime = Date.now() - startTime;

            const result = {
                success: true,
                embedding: normalized,
                metadata: {
                    chunksProcessed: chunkEmbeddings.length,
                    embeddingDimension: this.config.embeddingDimension,
                    normalizationMethod: options.normalizeMethod || this.config.normalizeMethod,
                    processingTimeMs: processingTime,
                    magnitude: this.calculateMagnitude(normalized),
                    nanValidation: validation
                }
            };

            this.emit('merged', result);
            return result;

        } catch (error) {
            const processingTime = Date.now() - startTime;
            const errorResult = {
                success: false,
                error: error.message,
                metadata: {
                    processingTimeMs: processingTime,
                    chunksAttempted: chunkEmbeddings.length
                }
            };

            this.emit('error', errorResult);
            throw error;
        }
    }

    /**
     * Calculate magnitude of embedding vector
     * @param {Array} embedding - Embedding vector
     * @returns {Number} Vector magnitude
     */
    calculateMagnitude(embedding) {
        if (!Array.isArray(embedding)) {
            return null;
        }

        let sumSquares = 0;
        for (let i = 0; i < embedding.length; i++) {
            if (Number.isFinite(embedding[i])) {
                sumSquares += embedding[i] * embedding[i];
            }
        }
        return Math.sqrt(sumSquares);
    }

    /**
     * Calculate statistics for an embedding
     * @param {Array} embedding - Embedding vector
     * @returns {Object} Statistics (mean, std, min, max)
     */
    calculateStatistics(embedding) {
        if (!Array.isArray(embedding) || embedding.length === 0) {
            return null;
        }

        const finiteValues = embedding.filter(v => Number.isFinite(v));
        if (finiteValues.length === 0) {
            return null;
        }

        const mean = finiteValues.reduce((a, b) => a + b, 0) / finiteValues.length;
        const variance = finiteValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / finiteValues.length;
        const std = Math.sqrt(variance);
        const min = Math.min(...finiteValues);
        const max = Math.max(...finiteValues);

        return {
            mean,
            std,
            min,
            max,
            validValues: finiteValues.length,
            totalDimensions: embedding.length
        };
    }

    /**
     * Compare two embeddings for similarity (cosine distance)
     * @param {Array} embedding1 - First embedding
     * @param {Array} embedding2 - Second embedding
     * @returns {Number} Cosine similarity (-1 to 1)
     */
    cosineSimilarity(embedding1, embedding2) {
        if (!Array.isArray(embedding1) || !Array.isArray(embedding2)) {
            throw new Error('Both embeddings must be arrays');
        }

        if (embedding1.length !== embedding2.length) {
            throw new Error('Embeddings must have same dimension');
        }

        let dotProduct = 0;
        let magnitude1 = 0;
        let magnitude2 = 0;

        for (let i = 0; i < embedding1.length; i++) {
            const v1 = embedding1[i];
            const v2 = embedding2[i];

            if (Number.isFinite(v1) && Number.isFinite(v2)) {
                dotProduct += v1 * v2;
                magnitude1 += v1 * v1;
                magnitude2 += v2 * v2;
            }
        }

        magnitude1 = Math.sqrt(magnitude1);
        magnitude2 = Math.sqrt(magnitude2);

        if (magnitude1 === 0 || magnitude2 === 0) {
            return 0;
        }

        return dotProduct / (magnitude1 * magnitude2);
    }

    /**
     * Batch merge multiple enrollment sessions
     * Useful for multi-day or multi-session enrollments
     * @param {Array<Array<Array>>} sessionEmbeddings - Array of session embedding arrays
     * @returns {Object} Merged embedding from all sessions
     */
    mergeMultipleSessions(sessionEmbeddings, options = {}) {
        try {
            // Merge embeddings from each session first
            const sessionMergedEmbeddings = sessionEmbeddings.map((session, index) => {
                try {
                    const result = this.mergeEmbeddings(session, options);
                    return result.embedding;
                } catch (error) {
                    this.logger.error(`Failed to merge session ${index}:`, error.message);
                    return null;
                }
            });

            // Filter out null results
            const validMergedEmbeddings = sessionMergedEmbeddings.filter(e => e !== null);
            
            if (validMergedEmbeddings.length === 0) {
                throw new Error('All sessions failed to merge');
            }

            // Merge the session embeddings
            return this.mergeEmbeddings(validMergedEmbeddings, options);

        } catch (error) {
            this.logger.error('Failed to merge multiple sessions:', error.message);
            throw error;
        }
    }

    /**
     * Get default config
     * @static
     * @returns {Object} Default configuration
     */
    static getDefaultConfig() {
        return {
            embeddingDimension: 192,
            normalizeMethod: 'l2',
            maxChunks: 1000,
            nanThreshold: 0.1
        };
    }
}

module.exports = EmbeddingMerger;
