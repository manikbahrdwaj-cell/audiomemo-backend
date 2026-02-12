/**
 * Embedding Service
 * Handles voice embedding generation, storage, and verification
 * Communicates with Python FastAPI backend for ML operations
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');
const FormData = require('form-data');

/**
 * Embedding Service Class
 * Manages all embedding-related operations and API communication
 */
class EmbeddingService extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            apiBaseUrl: config.apiBaseUrl || 'http://localhost:8000',
            timeout: config.timeout || 30000,
            retryAttempts: config.retryAttempts || 3,
            retryDelay: config.retryDelay || 1000,
            similarityThreshold: config.similarityThreshold || 0.75,
            ...config
        };

        this.client = axios.create({
            baseURL: this.config.apiBaseUrl,
            timeout: this.config.timeout,
            headers: {
                'Content-Type': 'application/json'
            }
        });

        this.isConnected = false;
        this.initPromise = this._initializeService();
    }

    /**
     * Initialize the embedding service
     * Verifies connection to Python backend
     * @private
     */
    async _initializeService() {
        try {
            // Attempt to connect to the API
            const response = await this.client.get('/docs');
            this.isConnected = true;
            this.emit('connected');
            console.log('[EmbeddingService] Connected to API backend');
            return true;
        } catch (error) {
            console.error('[EmbeddingService] Failed to connect to API:', error.message);
            this.emit('error', error);
            return false;
        }
    }

    /**
     * Wait for service initialization
     */
    async waitForConnection() {
        await this.initPromise;
        return this.isConnected;
    }

    /**
     * Generate embedding from audio data
     * @param {Buffer|string} audioData - Audio file buffer or file path
     * @returns {Promise<Array>} Speaker embedding vector (192-dimensional)
     */
    async generateEmbedding(audioData) {
        try {
            const formData = new FormData();

            // Handle both Buffer and file path inputs
            if (typeof audioData === 'string') {
                if (!fs.existsSync(audioData)) {
                    throw new Error(`Audio file not found: ${audioData}`);
                }
                formData.append('file', fs.createReadStream(audioData));
            } else if (Buffer.isBuffer(audioData)) {
                formData.append('file', audioData, { filename: 'audio.wav' });
            } else {
                throw new Error('Audio data must be Buffer or file path');
            }

            const response = await this._retryRequest(
                () => this.client.post('/generate-embedding', formData, {
                    headers: formData.getHeaders()
                })
            );

            if (!response.data.embedding) {
                throw new Error('No embedding in response');
            }

            this.emit('embedding-generated', {
                success: true,
                embeddingDim: response.data.embedding.length,
                timestamp: new Date().toISOString()
            });

            return response.data.embedding;
        } catch (error) {
            this._handleError('generateEmbedding', error);
            throw error;
        }
    }

    /**
     * Enroll a user with voice sample
     * @param {Buffer|string} audioData - Audio file buffer or file path
     * @param {string} phoneNumber - User's phone number
     * @returns {Promise<Object>} Enrollment response with vector ID
     */
    async enrollVoice(audioData, phoneNumber) {
        try {
            if (!phoneNumber || typeof phoneNumber !== 'string') {
                throw new Error('Phone number is required and must be a string');
            }

            const formData = new FormData();
            formData.append('phone_number', phoneNumber);

            if (typeof audioData === 'string') {
                if (!fs.existsSync(audioData)) {
                    throw new Error(`Audio file not found: ${audioData}`);
                }
                formData.append('file', fs.createReadStream(audioData));
            } else if (Buffer.isBuffer(audioData)) {
                formData.append('file', audioData, { filename: 'audio.wav' });
            } else {
                throw new Error('Audio data must be Buffer or file path');
            }

            const response = await this._retryRequest(
                () => this.client.post('/enroll', formData, {
                    headers: formData.getHeaders()
                })
            );

            if (!response.data.success) {
                throw new Error(response.data.message || 'Enrollment failed');
            }

            this.emit('voice-enrolled', {
                phoneNumber,
                vectorId: response.data.vector_id,
                timestamp: new Date().toISOString()
            });

            return {
                success: true,
                phoneNumber,
                vectorId: response.data.vector_id,
                message: response.data.message
            };
        } catch (error) {
            this._handleError('enrollVoice', error);
            throw error;
        }
    }

    /**
     * Verify a user's voice
     * @param {Buffer|string} audioData - Audio file buffer or file path
     * @param {string} phoneNumber - User's phone number to verify against
     * @returns {Promise<Object>} Verification result with similarity score
     */
    async verifyVoice(audioData, phoneNumber) {
        try {
            if (!phoneNumber || typeof phoneNumber !== 'string') {
                throw new Error('Phone number is required and must be a string');
            }

            const formData = new FormData();
            formData.append('phone_number', phoneNumber);

            if (typeof audioData === 'string') {
                if (!fs.existsSync(audioData)) {
                    throw new Error(`Audio file not found: ${audioData}`);
                }
                formData.append('file', fs.createReadStream(audioData));
            } else if (Buffer.isBuffer(audioData)) {
                formData.append('file', audioData, { filename: 'audio.wav' });
            } else {
                throw new Error('Audio data must be Buffer or file path');
            }

            const response = await this._retryRequest(
                () => this.client.post('/verify', formData, {
                    headers: formData.getHeaders()
                })
            );

            const isMatch = response.data.is_match || 
                          response.data.similarity_score >= this.config.similarityThreshold;

            this.emit('voice-verified', {
                phoneNumber,
                isMatch,
                score: response.data.similarity_score,
                timestamp: new Date().toISOString()
            });

            return {
                success: response.data.success,
                phoneNumber,
                similarityScore: response.data.similarity_score,
                isMatch: isMatch,
                threshold: this.config.similarityThreshold,
                message: response.data.message
            };
        } catch (error) {
            this._handleError('verifyVoice', error);
            throw error;
        }
    }

    /**
     * Check if a user is enrolled
     * @param {string} phoneNumber - User's phone number
     * @returns {Promise<Object>} Enrollment status
     */
    async checkEnrollment(phoneNumber) {
        try {
            if (!phoneNumber || typeof phoneNumber !== 'string') {
                throw new Error('Phone number is required and must be a string');
            }

            const response = await this._retryRequest(
                () => this.client.get('/check', {
                    params: { phone_number: phoneNumber }
                })
            );

            return {
                phoneNumber,
                enrolled: response.data.enrolled,
                message: response.data.message
            };
        } catch (error) {
            this._handleError('checkEnrollment', error);
            throw error;
        }
    }

    /**
     * Calculate cosine similarity between two embeddings
     * @param {Array} embedding1 - First embedding vector
     * @param {Array} embedding2 - Second embedding vector
     * @returns {Promise<number>} Similarity score (0-1)
     */
    async calculateSimilarity(embedding1, embedding2) {
        try {
            if (!Array.isArray(embedding1) || !Array.isArray(embedding2)) {
                throw new Error('Both embeddings must be arrays');
            }

            if (embedding1.length !== embedding2.length) {
                throw new Error('Embeddings must have the same dimension');
            }

            const response = await this._retryRequest(
                () => this.client.post('/calculate-similarity', {
                    embedding1,
                    embedding2
                })
            );

            return response.data.similarity || 0;
        } catch (error) {
            this._handleError('calculateSimilarity', error);
            throw error;
        }
    }

    /**
     * Health check - verify service connectivity
     * @returns {Promise<Object>} Health status
     */
    async healthCheck() {
        try {
            const response = await this.client.get('/health', {
                timeout: 5000
            });
            
            this.isConnected = true;
            return {
                healthy: true,
                status: response.data.status,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            this.isConnected = false;
            return {
                healthy: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Retry a request with exponential backoff
     * @private
     */
    async _retryRequest(requestFn, attempt = 1) {
        try {
            return await requestFn();
        } catch (error) {
            if (attempt < this.config.retryAttempts && 
                (error.code === 'ECONNREFUSED' || 
                 error.code === 'ETIMEDOUT' ||
                 error.response?.status >= 500)) {
                
                const delay = this.config.retryDelay * Math.pow(2, attempt - 1);
                await new Promise(resolve => setTimeout(resolve, delay));
                return this._retryRequest(requestFn, attempt + 1);
            }
            throw error;
        }
    }

    /**
     * Handle errors and emit events
     * @private
     */
    _handleError(operation, error) {
        const errorDetails = {
            operation,
            message: error.message,
            code: error.code,
            timestamp: new Date().toISOString()
        };

        if (error.response) {
            errorDetails.status = error.response.status;
            errorDetails.data = error.response.data;
        }

        console.error(`[EmbeddingService] ${operation} error:`, errorDetails);
        this.emit('error', errorDetails);
    }

    /**
     * Get current service configuration
     * @returns {Object} Service configuration
     */
    getConfig() {
        return { ...this.config };
    }

    /**
     * Update service configuration
     * @param {Object} newConfig - Configuration updates
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        this.client.defaults.timeout = this.config.timeout;
    }

    /**
     * Close the service and cleanup
     */
    async close() {
        try {
            this.isConnected = false;
            this.removeAllListeners();
            this.emit('closed');
            console.log('[EmbeddingService] Service closed');
        } catch (error) {
            console.error('[EmbeddingService] Error closing service:', error);
        }
    }
}

// Export the service
module.exports = EmbeddingService;
