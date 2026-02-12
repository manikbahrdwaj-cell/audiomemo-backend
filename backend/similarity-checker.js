/**
 * Similarity Checker Service
 * Calculates cosine similarity between voice embeddings
 * Determines if two voice samples match based on similarity threshold
 */

const { EventEmitter } = require('events');

/**
 * Similarity Checker Class
 * Handles embedding comparison and similarity scoring
 */
class SimilarityChecker extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            embeddingDimension: config.embeddingDimension || 192,
            similarityThreshold: config.similarityThreshold || 0.75,
            minSimilarityThreshold: config.minSimilarityThreshold || 0.5,
            maxSimilarityThreshold: config.maxSimilarityThreshold || 1.0,
            ...config
        };

        this.logger = config.logger || console;
        this.validationEnabled = config.validationEnabled !== false;
    }

    /**
     * Validate embedding vector
     * Checks dimensions, data type, and for finite values
     * @param {Array} embedding - Embedding vector to validate
     * @param {string} embeddingName - Name for error messages
     * @returns {Object} Validation result with status and details
     */
    validateEmbedding(embedding, embeddingName = 'embedding') {
        const result = {
            isValid: true,
            dimension: 0,
            hasNaN: false,
            hasInfinity: false,
            message: ''
        };

        // Check if embedding exists
        if (!embedding) {
            result.isValid = false;
            result.message = `${embeddingName} is null or undefined`;
            return result;
        }

        // Check if embedding is an array
        if (!Array.isArray(embedding)) {
            result.isValid = false;
            result.message = `${embeddingName} must be an array`;
            return result;
        }

        // Check if embedding is not empty
        if (embedding.length === 0) {
            result.isValid = false;
            result.message = `${embeddingName} is empty`;
            return result;
        }

        // Check dimension
        result.dimension = embedding.length;
        if (result.dimension !== this.config.embeddingDimension) {
            result.isValid = false;
            result.message = `${embeddingName} has incorrect dimension: expected ${this.config.embeddingDimension}, got ${result.dimension}`;
            return result;
        }

        // Check for NaN and Infinity values
        for (let i = 0; i < embedding.length; i++) {
            const value = embedding[i];

            if (!Number.isFinite(value)) {
                if (Number.isNaN(value)) {
                    result.hasNaN = true;
                } else if (!Number.isFinite(value)) {
                    result.hasInfinity = true;
                }
            }
        }

        // Flag as invalid if there are NaN or Infinity values
        if (result.hasNaN || result.hasInfinity) {
            result.isValid = false;
            const issues = [];
            if (result.hasNaN) issues.push('NaN values');
            if (result.hasInfinity) issues.push('Infinity values');
            result.message = `${embeddingName} contains ${issues.join(' and ')}`;
            return result;
        }

        result.message = `${embeddingName} is valid`;
        return result;
    }

    /**
     * Calculate L2 norm (magnitude) of a vector
     * @param {Array} embedding - Embedding vector
     * @returns {number} L2 norm of the vector
     */
    calculateL2Norm(embedding) {
        let sumOfSquares = 0;

        for (let i = 0; i < embedding.length; i++) {
            const value = embedding[i];
            if (Number.isFinite(value)) {
                sumOfSquares += value * value;
            }
        }

        return Math.sqrt(sumOfSquares);
    }

    /**
     * Calculate dot product (inner product) of two vectors
     * @param {Array} embedding1 - First embedding vector
     * @param {Array} embedding2 - Second embedding vector
     * @returns {number} Dot product of the two vectors
     */
    calculateDotProduct(embedding1, embedding2) {
        let dotProduct = 0;

        for (let i = 0; i < embedding1.length; i++) {
            const val1 = embedding1[i];
            const val2 = embedding2[i];

            if (Number.isFinite(val1) && Number.isFinite(val2)) {
                dotProduct += val1 * val2;
            }
        }

        return dotProduct;
    }

    /**
     * Calculate cosine similarity between two embeddings
     * Returns a score between 0 and 1
     * Maps cosine similarity from [-1, 1] to [0, 1] range
     *
     * Formula: similarity = (dot_product(A, B)) / (||A|| * ||B||)
     * Then maps from [-1, 1] to [0, 1]: (similarity + 1) / 2
     *
     * @param {Array} embedding1 - First embedding vector (192-dimensional)
     * @param {Array} embedding2 - Second embedding vector (192-dimensional)
     * @returns {Object} Result object with similarity score and validation status
     */
    calculateSimilarity(embedding1, embedding2) {
        const result = {
            similarity: 0,
            isValid: true,
            message: '',
            validation: {
                embedding1: null,
                embedding2: null
            }
        };

        // Validate embeddings if validation is enabled
        if (this.validationEnabled) {
            result.validation.embedding1 = this.validateEmbedding(embedding1, 'embedding1');
            result.validation.embedding2 = this.validateEmbedding(embedding2, 'embedding2');

            if (!result.validation.embedding1.isValid) {
                result.isValid = false;
                result.message = result.validation.embedding1.message;
                return result;
            }

            if (!result.validation.embedding2.isValid) {
                result.isValid = false;
                result.message = result.validation.embedding2.message;
                return result;
            }
        }

        // Calculate L2 norms
        const norm1 = this.calculateL2Norm(embedding1);
        const norm2 = this.calculateL2Norm(embedding2);

        // Handle zero norm case
        if (norm1 === 0 || norm2 === 0) {
            result.similarity = 0;
            result.isValid = false;
            result.message = 'One or both embeddings have zero magnitude';
            return result;
        }

        // Calculate cosine similarity
        const dotProduct = this.calculateDotProduct(embedding1, embedding2);
        let cosineSimilarity = dotProduct / (norm1 * norm2);

        // Clamp value to [-1, 1] to handle floating point errors
        cosineSimilarity = Math.max(-1, Math.min(1, cosineSimilarity));

        // Map from [-1, 1] to [0, 1]
        result.similarity = (cosineSimilarity + 1) / 2;
        result.message = 'Similarity calculated successfully';

        return result;
    }

    /**
     * Compare two embeddings and determine if they match
     * Uses the configured similarity threshold for decision making
     *
     * @param {Array} enrolledEmbedding - Stored enrollment embedding
     * @param {Array} verificationEmbedding - New verification embedding
     * @param {number} customThreshold - Optional custom threshold (uses config default if not provided)
     * @returns {Object} Comparison result with match status and details
     */
    compareEmbeddings(enrolledEmbedding, verificationEmbedding, customThreshold = null) {
        const result = {
            isMatch: false,
            similarity: 0,
            threshold: customThreshold || this.config.similarityThreshold,
            isValid: true,
            message: '',
            details: {}
        };

        // Validate threshold
        if (result.threshold < this.config.minSimilarityThreshold || 
            result.threshold > this.config.maxSimilarityThreshold) {
            result.isValid = false;
            result.message = `Threshold must be between ${this.config.minSimilarityThreshold} and ${this.config.maxSimilarityThreshold}`;
            return result;
        }

        // Calculate similarity
        const similarityResult = this.calculateSimilarity(enrolledEmbedding, verificationEmbedding);

        if (!similarityResult.isValid) {
            result.isValid = false;
            result.message = similarityResult.message;
            result.details = similarityResult.validation;
            return result;
        }

        // Store similarity score
        result.similarity = similarityResult.similarity;

        // Determine if there's a match
        result.isMatch = result.similarity >= result.threshold;

        // Generate message
        if (result.isMatch) {
            result.message = `Voice match confirmed (similarity: ${(result.similarity * 100).toFixed(2)}%)`;
        } else {
            result.message = `Voice match rejected (similarity: ${(result.similarity * 100).toFixed(2)}%, threshold: ${(result.threshold * 100).toFixed(2)}%)`;
        }

        return result;
    }

    /**
     * Compare multiple enrolled embeddings against a verification embedding
     * Returns the best match and overall comparison results
     *
     * @param {Array<Array>} enrolledEmbeddings - Array of stored enrollment embeddings
     * @param {Array} verificationEmbedding - New verification embedding
     * @param {number} customThreshold - Optional custom threshold
     * @returns {Object} Aggregated comparison result with best match info
     */
    compareMultipleEmbeddings(enrolledEmbeddings, verificationEmbedding, customThreshold = null) {
        const result = {
            isMatch: false,
            bestSimilarity: 0,
            bestMatchIndex: -1,
            averageSimilarity: 0,
            threshold: customThreshold || this.config.similarityThreshold,
            totalComparisons: 0,
            matchCount: 0,
            isValid: true,
            message: '',
            comparisonDetails: []
        };

        // Validate input
        if (!Array.isArray(enrolledEmbeddings) || enrolledEmbeddings.length === 0) {
            result.isValid = false;
            result.message = 'enrolledEmbeddings must be a non-empty array';
            return result;
        }

        // Compare against each enrolled embedding
        let similaritySum = 0;

        for (let i = 0; i < enrolledEmbeddings.length; i++) {
            const comparison = this.compareEmbeddings(
                enrolledEmbeddings[i],
                verificationEmbedding,
                result.threshold
            );

            result.comparisonDetails.push({
                index: i,
                ...comparison
            });

            if (comparison.isValid) {
                result.totalComparisons++;
                similaritySum += comparison.similarity;

                // Track best match
                if (comparison.similarity > result.bestSimilarity) {
                    result.bestSimilarity = comparison.similarity;
                    result.bestMatchIndex = i;
                }

                // Count matches
                if (comparison.isMatch) {
                    result.matchCount++;
                }
            }
        }

        // Calculate average similarity
        if (result.totalComparisons > 0) {
            result.averageSimilarity = similaritySum / result.totalComparisons;
        }

        // Determine overall match (requires at least 4 matching chunks for security)
        result.isMatch = result.matchCount >= 4;

        // Generate message
        if (result.isMatch) {
            result.message = `Match found: ${result.matchCount} matching chunks (Best similarity ${(result.bestSimilarity * 100).toFixed(2)}% at index ${result.bestMatchIndex})`;
        } else {
            result.message = `No match found: Only ${result.matchCount} matching chunks (requires 4+). Best similarity ${(result.bestSimilarity * 100).toFixed(2)}% (threshold: ${(result.threshold * 100).toFixed(2)}%)`;
        }

        return result;
    }

    /**
     * Batch compare verification embeddings against a set of enrolled embeddings
     * Useful for verifying multiple speakers or multiple attempts
     *
     * @param {Array<Array>} enrolledEmbeddings - Enrolled speaker embeddings
     * @param {Array<Array>} verificationEmbeddings - Multiple verification embeddings
     * @param {number} customThreshold - Optional custom threshold
     * @returns {Array<Object>} Array of comparison results for each verification embedding
     */
    batchCompare(enrolledEmbeddings, verificationEmbeddings, customThreshold = null) {
        if (!Array.isArray(verificationEmbeddings)) {
            this.logger.error('verificationEmbeddings must be an array');
            return [];
        }

        return verificationEmbeddings.map((verificationEmbedding, index) => {
            const result = this.compareMultipleEmbeddings(
                enrolledEmbeddings,
                verificationEmbedding,
                customThreshold
            );
            result.verificationIndex = index;
            return result;
        });
    }

    /**
     * Set the similarity threshold for comparisons
     * @param {number} threshold - Threshold value between 0 and 1
     * @returns {boolean} Whether the threshold was set successfully
     */
    setThreshold(threshold) {
        if (threshold < this.config.minSimilarityThreshold || 
            threshold > this.config.maxSimilarityThreshold) {
            this.logger.error(
                `Threshold must be between ${this.config.minSimilarityThreshold} and ${this.config.maxSimilarityThreshold}`
            );
            return false;
        }

        this.config.similarityThreshold = threshold;
        this.logger.info(`Similarity threshold updated to ${threshold}`);
        return true;
    }

    /**
     * Get current configuration
     * @returns {Object} Current configuration object
     */
    getConfig() {
        return { ...this.config };
    }
}

module.exports = SimilarityChecker;
