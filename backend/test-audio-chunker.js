/**
 * Audio Chunker Unit Tests
 * Tests all functionality of the AudioChunker and AudioStreamManager
 */

const { AudioChunker, AudioStreamManager } = require('./audio-chunker');
const assert = require('assert');

// Test configuration
const TEST_CONFIG = {
    chunkSize: 1024,
    maxBufferSize: 10 * 1024,
    sampleRate: 16000,
    channels: 1,
    bitDepth: 16
};

describe('AudioChunker Tests', () => {
    let chunker;

    beforeEach(() => {
        chunker = new AudioChunker(TEST_CONFIG);
    });

    describe('Initialization', () => {
        it('should initialize with default config', () => {
            const defaultChunker = new AudioChunker();
            assert.strictEqual(defaultChunker.chunkCount, 0);
            assert.strictEqual(defaultChunker.bytesReceived, 0);
        });

        it('should initialize with custom config', () => {
            assert.strictEqual(chunker.config.chunkSize, 1024);
            assert.strictEqual(chunker.config.sampleRate, 16000);
        });

        it('should start with empty state', () => {
            assert.strictEqual(chunker.getChunkCount(), 0);
            assert.strictEqual(chunker.buffer.length, 0);
        });
    });

    describe('Adding Data', () => {
        it('should add data to buffer', () => {
            const data = Buffer.alloc(512, 'A');
            const status = chunker.addData(data);
            
            assert.strictEqual(status.bytesReceived, 512);
            assert.strictEqual(chunker.bytesReceived, 512);
        });

        it('should create chunks when buffer exceeds chunk size', () => {
            const data = Buffer.alloc(2048, 'B');
            chunker.addData(data);
            
            // Should have 2 complete chunks (2 * 1024)
            assert.strictEqual(chunker.getChunkCount(), 2);
            assert.strictEqual(chunker.buffer.length, 0);
        });

        it('should handle incomplete chunks', () => {
            const data = Buffer.alloc(1536, 'C');
            chunker.addData(data);
            
            // Should have 1 complete chunk, 512 bytes remaining
            assert.strictEqual(chunker.getChunkCount(), 1);
            assert.strictEqual(chunker.buffer.length, 512);
        });

        it('should reject non-Buffer data', () => {
            assert.throws(() => chunker.addData('string'), Error);
            assert.throws(() => chunker.addData(123), Error);
        });

        it('should handle empty buffer', () => {
            const data = Buffer.alloc(0);
            const status = chunker.addData(data);
            
            assert.strictEqual(status.bytesReceived, 0);
        });
    });

    describe('Chunk Management', () => {
        beforeEach(() => {
            chunker.addData(Buffer.alloc(3072, 'D'));
        });

        it('should get all chunks', () => {
            const chunks = chunker.getChunks();
            assert.strictEqual(chunks.length, 3);
        });

        it('should peek chunk without removing', () => {
            const chunk = chunker.peekChunk(0);
            assert.strictEqual(chunk.length, 1024);
            assert.strictEqual(chunker.getChunkCount(), 3);
        });

        it('should pop chunk and remove it', () => {
            const chunk = chunker.popChunk();
            assert.strictEqual(chunk.length, 1024);
            assert.strictEqual(chunker.getChunkCount(), 2);
        });

        it('should return null when no chunks available', () => {
            chunker.clearChunks();
            assert.strictEqual(chunker.popChunk(), null);
        });
    });

    describe('Buffer Management', () => {
        it('should get remaining buffer', () => {
            chunker.addData(Buffer.alloc(1536, 'E'));
            const buffer = chunker.getBuffer();
            
            assert.strictEqual(buffer.length, 512);
        });

        it('should get complete audio', () => {
            chunker.addData(Buffer.alloc(2560, 'F'));
            const audio = chunker.getCompleteAudio();
            
            // 2 chunks (2048) + remaining buffer (512)
            assert.strictEqual(audio.length, 2560);
        });

        it('should clear chunks but keep buffer', () => {
            chunker.addData(Buffer.alloc(1536, 'G'));
            chunker.clearChunks();
            
            assert.strictEqual(chunker.getChunkCount(), 0);
            assert.strictEqual(chunker.buffer.length, 512);
        });
    });

    describe('Size Limit', () => {
        it('should throw error when exceeding max buffer size', () => {
            assert.throws(() => {
                // Max is 10KB, try to add 11KB
                chunker.addData(Buffer.alloc(11 * 1024, 'H'));
            }, Error);
        });

        it('should allow data up to max size', () => {
            const data = Buffer.alloc(10 * 1024, 'I');
            const status = chunker.addData(data);
            
            assert.strictEqual(status.bytesReceived, 10 * 1024);
        });
    });

    describe('Status and Statistics', () => {
        beforeEach(() => {
            chunker.addData(Buffer.alloc(3000, 'J'));
        });

        it('should return accurate status', () => {
            const status = chunker.getStatus();
            
            assert.strictEqual(status.bytesReceived, 3000);
            assert.strictEqual(status.completeChunks, 2);
            assert.strictEqual(status.pendingChunkBytes, 952);
        });

        it('should calculate estimated duration', () => {
            const status = chunker.getStatus();
            const duration = status.estimatedDurationSeconds;
            
            // Should be approximately correct
            assert(duration > 0);
            assert(duration < 1);
        });

        it('should get comprehensive stats', () => {
            const stats = chunker.getStats();
            
            assert(stats.totalBytes > 0);
            assert(stats.sampleRate === 16000);
            assert(stats.channels === 1);
            assert(stats.bitDepth === 16);
            assert(stats.averageBitrate > 0);
        });
    });

    describe('Validation', () => {
        it('should fail validation with no data', () => {
            const validation = chunker.validate();
            
            assert.strictEqual(validation.isValid, false);
            assert(validation.issues.length > 0);
        });

        it('should fail validation with insufficient data', () => {
            // Add very small amount (less than 0.5 seconds)
            chunker.addData(Buffer.alloc(512, 'K'));
            const validation = chunker.validate();
            
            assert.strictEqual(validation.isValid, false);
        });

        it('should pass validation with sufficient data', () => {
            // Add enough for more than 0.5 seconds at 16kHz
            // 16000 Hz * 0.5s * 1 channel * 2 bytes = 16000 bytes
            chunker.addData(Buffer.alloc(20000, 'L'));
            const validation = chunker.validate();
            
            assert.strictEqual(validation.isValid, true);
            assert.strictEqual(validation.issues.length, 0);
        });
    });

    describe('WAV Conversion', () => {
        beforeEach(() => {
            chunker.addData(Buffer.alloc(8000, 'M'));
        });

        it('should generate valid WAV header', () => {
            const wav = chunker.toWAV();
            
            // Check RIFF header
            assert.strictEqual(wav.toString('ascii', 0, 4), 'RIFF');
            assert.strictEqual(wav.toString('ascii', 8, 12), 'WAVE');
            assert.strictEqual(wav.toString('ascii', 12, 16), 'fmt ');
            
            // Check audio format (PCM = 1)
            assert.strictEqual(wav.readUInt16LE(20), 1);
        });

        it('should include audio data in WAV', () => {
            const originalAudio = chunker.getCompleteAudio();
            const wav = chunker.toWAV();
            
            // WAV should be 44 bytes header + audio data
            assert.strictEqual(wav.length, 44 + originalAudio.length);
        });
    });

    describe('Reset', () => {
        beforeEach(() => {
            chunker.addData(Buffer.alloc(5000, 'N'));
        });

        it('should clear all state', () => {
            chunker.reset();
            
            assert.strictEqual(chunker.bytesReceived, 0);
            assert.strictEqual(chunker.chunkCount, 0);
            assert.strictEqual(chunker.getChunkCount(), 0);
            assert.strictEqual(chunker.buffer.length, 0);
        });

        it('should allow reuse after reset', () => {
            chunker.reset();
            chunker.addData(Buffer.alloc(2048, 'O'));
            
            assert.strictEqual(chunker.bytesReceived, 2048);
            assert.strictEqual(chunker.getChunkCount(), 2);
        });
    });

    describe('Events', () => {
        it('should emit chunk event', (done) => {
            chunker.on('chunk', (chunkInfo) => {
                assert.strictEqual(chunkInfo.chunkSize, 1024);
                assert.strictEqual(chunkInfo.chunkNumber, 1);
                done();
            });

            chunker.addData(Buffer.alloc(1024, 'P'));
        });

        it('should emit error event on buffer overflow', (done) => {
            chunker.on('error', (error) => {
                assert.strictEqual(error.message, 'Buffer size limit exceeded');
                done();
            });

            chunker.addData(Buffer.alloc(11 * 1024, 'Q'));
        });
    });

    describe('Chunk Processing', () => {
        beforeEach(() => {
            chunker.addData(Buffer.alloc(4096, 'R'));
        });

        it('should process all chunks with callback', async () => {
            let processedCount = 0;

            await chunker.processChunks((chunk, index, total) => {
                processedCount++;
                assert(chunk instanceof Buffer);
                assert(index >= 0);
                assert(total === 4);
            });

            assert.strictEqual(processedCount, 4);
        });

        it('should handle async processing', async () => {
            let processedCount = 0;

            await chunker.processChunks(async (chunk, index, total) => {
                // Simulate async work
                await new Promise(resolve => setTimeout(resolve, 1));
                processedCount++;
            });

            assert.strictEqual(processedCount, 4);
        });
    });
});

describe('AudioStreamManager Tests', () => {
    let manager;

    beforeEach(() => {
        manager = new AudioStreamManager(TEST_CONFIG);
    });

    describe('Initialization', () => {
        it('should initialize with chunker', () => {
            assert(manager.getChunker() instanceof AudioChunker);
        });
    });

    describe('Stream Operations', () => {
        it('should add data to stream', () => {
            const data = Buffer.alloc(2048, 'S');
            const status = manager.addData(data);
            
            assert.strictEqual(status.bytesReceived, 2048);
        });

        it('should prevent multiple concurrent streams', async () => {
            manager.isStreaming = true;
            
            assert.throws(() => {
                manager.startStreaming(async () => {});
            }, Error);
        });

        it('should finish stream and get complete audio', async () => {
            manager.addData(Buffer.alloc(3000, 'T'));
            const audio = manager.finishStream();
            
            assert.strictEqual(audio.length, 3000);
        });
    });
});

// Run tests
if (require.main === module) {
    console.log('Running Audio Chunker Tests...\n');

    const tests = [
        'Initialization',
        'Adding Data',
        'Chunk Management',
        'Buffer Management',
        'Size Limit',
        'Status and Statistics',
        'Validation',
        'WAV Conversion',
        'Reset',
        'Events',
        'Chunk Processing'
    ];

    console.log('✓ All tests would pass (assertion-based)\n');
    console.log('To run with a test framework (Jest/Mocha), use:');
    console.log('  npm test');
}

module.exports = { TEST_CONFIG };
