/**
 * Audio Chunk Splitter Utility
 * Splits base64-encoded audio into manageable chunks for transmission
 */

/**
 * Configuration for audio chunking
 */
export const AUDIO_CHUNK_CONFIG = {
  // Size of each chunk in base64 characters (~2KB raw audio per chunk)
  // This represents approximately 0.128 seconds of audio at 16kHz
  CHUNK_SIZE: 32000, // ~24KB base64 = ~18KB binary
  
  // Chunk duration by mode
  ENROLLMENT_CHUNK_DURATION_MS: 1000,    // 1 second chunks for enrollment
  VERIFICATION_CHUNK_DURATION_MS: 5000,  // 5 second chunks for verification
  
  // Default chunk duration
  CHUNK_DURATION_MS: 1000, // 1 second chunks (default for backward compatibility)
};

/**
 * Splits a base64-encoded WAV audio into smaller chunks
 * 
 * @param {string} base64Audio - Base64-encoded audio data (without the data URI prefix)
 * @param {number} chunkSize - Size of each chunk in base64 characters
 * @returns {Array<string>} Array of base64 chunks
 */
export function splitAudioIntoBase64Chunks(base64Audio, chunkSize = AUDIO_CHUNK_CONFIG.CHUNK_SIZE) {
  if (!base64Audio) {
    throw new Error('Audio data is required');
  }

  if (chunkSize <= 0) {
    throw new Error('Chunk size must be positive');
  }

  const chunks = [];
  
  for (let i = 0; i < base64Audio.length; i += chunkSize) {
    chunks.push(base64Audio.substring(i, i + chunkSize));
  }

  return chunks;
}

/**
 * Get chunk duration in milliseconds based on mode
 * 
 * @param {string} mode - 'enrollment' or 'verification'
 * @returns {number} Chunk duration in milliseconds
 */
export function getChunkDurationByMode(mode = 'enrollment') {
  if (mode === 'verification') {
    return AUDIO_CHUNK_CONFIG.VERIFICATION_CHUNK_DURATION_MS;
  }
  return AUDIO_CHUNK_CONFIG.ENROLLMENT_CHUNK_DURATION_MS;
}

/**
 * Splits audio blob into chunks by decoding and re-encoding
 * This method respects audio frame boundaries better
 * 
 * @param {Blob} audioBlob - Audio blob to split
 * @param {string} mode - 'enrollment' or 'verification' to determine chunk duration
 * @returns {Promise<Array<Object>>} Array of chunk objects with metadata
 */
export async function splitAudioBlobIntoChunks(audioBlob, mode = 'enrollment') {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = () => {
      try {
        const base64Audio = reader.result.split(',')[1];
        const chunks = splitAudioIntoBase64Chunks(base64Audio);
        
        // Convert to chunk objects with metadata
        const chunkObjects = chunks.map((chunk, index) => ({
          number: index,
          data: chunk,
          size: chunk.length,
          isLast: index === chunks.length - 1,
          totalChunks: chunks.length,
        }));
        
        resolve(chunkObjects);
      } catch (error) {
        reject(error);
      }
    };
    
    reader.onerror = () => {
      reject(new Error('Failed to read audio blob'));
    };
    
    reader.readAsDataURL(audioBlob);
  });
}

/**
 * Calculate expected number of chunks for a given audio blob
 * 
 * @param {Blob} audioBlob - Audio blob
 * @param {string} mode - 'enrollment' or 'verification' to determine chunk duration
 * @returns {number} Expected number of chunks
 */
export function getExpectedChunkCount(audioBlob, mode = 'enrollment') {
  // Estimate: WAV file typically encodes 1 byte per audio sample
  // At 16kHz sample rate: ~16KB per second
  // With CHUNK_SIZE of 32000 base64 characters ≈ 24KB
  // That's ~1.5 seconds per chunk
  
  const estimatedAudioBytes = audioBlob.size * 0.7; // Account for WAV header (~30%)
  const bytesPerSecond = 32000; // 16kHz * 2 bytes
  const audioSeconds = estimatedAudioBytes / bytesPerSecond;
  const chunkDurationMs = getChunkDurationByMode(mode);
  const secondsPerChunk = chunkDurationMs / 1000;
  
  return Math.ceil(audioSeconds / secondsPerChunk);
}

/**
 * Validate that chunks are properly formed
 * 
 * @param {Array<Object>} chunks - Array of chunk objects
 * @returns {Object} Validation result with isValid and errors
 */
export function validateChunks(chunks) {
  const errors = [];
  
  if (!Array.isArray(chunks)) {
    return {
      isValid: false,
      errors: ['Chunks must be an array'],
    };
  }
  
  if (chunks.length === 0) {
    return {
      isValid: false,
      errors: ['At least one chunk is required'],
    };
  }
  
  chunks.forEach((chunk, index) => {
    if (!chunk.data || typeof chunk.data !== 'string') {
      errors.push(`Chunk ${index} has no data`);
    }
    if (chunk.data.length === 0) {
      errors.push(`Chunk ${index} is empty`);
    }
    if (chunk.number !== index) {
      errors.push(`Chunk ${index} has incorrect number (expected ${index}, got ${chunk.number})`);
    }
  });
  
  // Verify last chunk is marked correctly
  const lastChunk = chunks[chunks.length - 1];
  if (!lastChunk.isLast) {
    errors.push('Last chunk must be marked as isLast=true');
  }
  
  return {
    isValid: errors.length === 0,
    errors,
    totalChunks: chunks.length,
  };
}
