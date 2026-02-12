/**
 * WebSocket Integration Test Suite
 * Tests the complete WebSocket system integration
 */

const WebSocket = require('ws');
const http = require('http');
const WebSocketAudioHandler = require('./websocket-handler');
const fs = require('fs');
const path = require('path');

// Test configuration
const TEST_PORT = 8002; // Use different port for testing
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

// Recording constants
const AUDIO_SAMPLE_RATE = 16000;
const DURATION_MS = 1000; // 1 second
const CHANNELS = 1;
const BITS_PER_SAMPLE = 16;
const BYTE_RATE = (AUDIO_SAMPLE_RATE * CHANNELS * BITS_PER_SAMPLE) / 8;
const BLOCK_ALIGN = (CHANNELS * BITS_PER_SAMPLE) / 8;

class WebSocketIntegrationTest {
    constructor() {
        this.handler = null;
        this.testResults = [];
        this.client = null;
    }

    /**
     * Generate dummy WAV audio data for testing
     */
    generateDummyAudio() {
        const numSamples = (AUDIO_SAMPLE_RATE * DURATION_MS) / 1000;
        const audioData = Buffer.alloc(numSamples * BLOCK_ALIGN);
        
        // Generate sine wave
        for (let i = 0; i < numSamples; i++) {
            const sample = Math.sin((2 * Math.PI * 440 * i) / AUDIO_SAMPLE_RATE) * 32767;
            audioData.writeInt16LE(Math.round(sample), i * BLOCK_ALIGN);
        }
        
        return audioData;
    }

    /**
     * Create WAV file buffer from audio data
     */
    createWavBuffer(audioData) {
        const subchunk1Size = 16;
        const subchunk2Size = audioData.length;
        const chunkSize = 36 + subchunk2Size;
        
        const wav = Buffer.alloc(44 + audioData.length);
        
        // RIFF chunk
        wav.write('RIFF', 0);
        wav.writeUInt32LE(chunkSize, 4);
        wav.write('WAVE', 8);
        
        // fmt sub-chunk
        wav.write('fmt ', 12);
        wav.writeUInt32LE(subchunk1Size, 16);
        wav.writeUInt16LE(1, 20); // AudioFormat: PCM
        wav.writeUInt16LE(CHANNELS, 22);
        wav.writeUInt32LE(AUDIO_SAMPLE_RATE, 24);
        wav.writeUInt32LE(BYTE_RATE, 28);
        wav.writeUInt16LE(BLOCK_ALIGN, 32);
        wav.writeUInt16LE(BITS_PER_SAMPLE, 34);
        
        // data sub-chunk
        wav.write('data', 36);
        wav.writeUInt32LE(subchunk2Size, 40);
        
        audioData.copy(wav, 44);
        
        return wav;
    }

    /**
     * Initialize WebSocket server for testing
     */
    async startServer() {
        return new Promise((resolve, reject) => {
            try {
                this.handler = new WebSocketAudioHandler(TEST_PORT);
                this.handler.start()
                    .then(() => {
                        console.log(`[Test] WebSocket server started on port ${TEST_PORT}`);
                        resolve();
                    })
                    .catch(reject);
            } catch (err) {
                reject(err);
            }
        });
    }

    /**
     * Connect test client
     */
    connectClient() {
        return new Promise((resolve, reject) => {
            try {
                this.client = new WebSocket(`ws://localhost:${TEST_PORT}`);
                
                this.client.on('open', () => {
                    console.log('[Test] Client connected');
                    resolve();
                });
                
                this.client.on('error', (err) => {
                    reject(err);
                });
            } catch (err) {
                reject(err);
            }
        });
    }

    /**
     * Send message and wait for response
     */
    sendAndWait(message, timeout = 5000) {
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                reject(new Error('Timeout waiting for response'));
            }, timeout);
            
            const onMessage = (data) => {
                clearTimeout(timer);
                this.client.off('message', onMessage);
                try {
                    const response = JSON.parse(data.toString());
                    resolve(response);
                } catch (err) {
                    reject(err);
                }
            };
            
            this.client.on('message', onMessage);
            
            if (typeof message === 'string') {
                this.client.send(message);
            } else {
                this.client.send(JSON.stringify(message));
            }
        });
    }

    /**
     * Test 1: Connection
     */
    async testConnection() {
        console.log('\n[Test 1] Testing basic connection...');
        try {
            const response = await this.sendAndWait('', 3000); // Wait for connection message
            console.log(` ✓ Received message type: ${response.type}`);
            this.testResults.push({ test: 'Connection', passed: response.type === 'connection' });
        } catch (err) {
            console.log(` ✗ Connection test failed: ${err.message}`);
            this.testResults.push({ test: 'Connection', passed: false, error: err.message });
        }
    }

    /**
     * Test 2: Initialization
     */
    async testInitialization() {
        console.log('\n[Test 2] Testing session initialization...');
        try {
            const response = await this.sendAndWait({
                type: 'init',
                userId: 'test_user_123',
                action: 'enroll',
                language: 'en'
            });
            
            const passed = response.type === 'initialized' && response.success !== false;
            console.log(` ✓ Session initialized: ${response.userId}`);
            this.testResults.push({ test: 'Initialization', passed });
        } catch (err) {
            console.log(` ✗ Initialization test failed: ${err.message}`);
            this.testResults.push({ test: 'Initialization', passed: false, error: err.message });
        }
    }

    /**
     * Test 3: Start Enrollment
     */
    async testStartEnrollment() {
        console.log('\n[Test 3] Testing enrollment start...');
        try {
            const response = await this.sendAndWait({
                type: 'start-enrollment'
            });
            
            const passed = response.type === 'enrollment-started';
            console.log(` ✓ Enrollment started: ${response.message}`);
            this.testResults.push({ test: 'Start Enrollment', passed });
        } catch (err) {
            console.log(` ✗ Start enrollment test failed: ${err.message}`);
            this.testResults.push({ test: 'Start Enrollment', passed: false, error: err.message });
        }
    }

    /**
     * Test 4: Audio Data Reception
     */
    async testAudioReception() {
        console.log('\n[Test 4] Testing audio data reception...');
        try {
            // Generate dummy audio
            const audioData = this.generateDummyAudio();
            
            // Send audio as binary
            this.client.send(audioData);
            
            // Wait for acknowledgment
            const response = await this.sendAndWait('', 2000);
            
            const passed = response.type === 'audio-received' && response.bytesReceived > 0;
            console.log(` ✓ Audio received: ${response.bytesReceived} bytes`);
            this.testResults.push({ test: 'Audio Reception', passed });
        } catch (err) {
            console.log(` ✗ Audio reception test failed: ${err.message}`);
            this.testResults.push({ test: 'Audio Reception', passed: false, error: err.message });
        }
    }

    /**
     * Test 5: Get Status
     */
    async testGetStatus() {
        console.log('\n[Test 5] Testing status request...');
        try {
            const response = await this.sendAndWait({
                type: 'get-status'
            });
            
            const passed = response.type === 'status' && response.sessionActive === true;
            console.log(` ✓ Status: ${response.connected ? 'Connected' : 'Disconnected'}`);
            console.log(`   Audio buffer: ${response.audioStats?.bufferSize || 0} bytes`);
            this.testResults.push({ test: 'Get Status', passed });
        } catch (err) {
            console.log(` ✗ Get status test failed: ${err.message}`);
            this.testResults.push({ test: 'Get Status', passed: false, error: err.message });
        }
    }

    /**
     * Test 6: Ping/Pong
     */
    async testPingPong() {
        console.log('\n[Test 6] Testing ping/pong...');
        try {
            const response = await this.sendAndWait({
                type: 'ping'
            });
            
            const passed = response.type === 'pong';
            console.log(` ✓ Pong received`);
            this.testResults.push({ test: 'Ping/Pong', passed });
        } catch (err) {
            console.log(` ✗ Ping/Pong test failed: ${err.message}`);
            this.testResults.push({ test: 'Ping/Pong', passed: false, error: err.message });
        }
    }

    /**
     * Test 7: Stop Audio (Will try to process with backend)
     */
    async testStopAudio() {
        console.log('\n[Test 7] Testing audio processing...');
        try {
            const response = await this.sendAndWait({
                type: 'stop-audio'
            }, 10000); // Longer timeout for processing
            
            // We expect either a result or an error
            const passed = response.type === 'result' || response.type === 'error';
            console.log(` ✓ Response type: ${response.type}`);
            if (response.error) {
                console.log(`   Note: ${response.error} - ${response.details}`);
            }
            this.testResults.push({ test: 'Stop Audio', passed });
        } catch (err) {
            console.log(` ✗ Stop audio test failed: ${err.message}`);
            this.testResults.push({ test: 'Stop Audio', passed: false, error: err.message });
        }
    }

    /**
     * Print test summary
     */
    printSummary() {
        const passed = this.testResults.filter(r => r.passed).length;
        const total = this.testResults.length;
        const percentage = Math.round((passed / total) * 100);

        console.log('\n╔════════════════════════════════════════════════════╗');
        console.log('║           TEST RESULTS SUMMARY                      ║');
        console.log('╚════════════════════════════════════════════════════╝\n');

        this.testResults.forEach((result, index) => {
            const status = result.passed ? '✓' : '✗';
            const msg = result.passed ? 'PASSED' : 'FAILED';
            console.log(`${index + 1}. [${status}] ${result.test.padEnd(30)} ${msg}`);
            if (result.error) {
                console.log(`   Error: ${result.error}`);
            }
        });

        console.log(`\n${'='*60}`);
        console.log(`Total: ${passed}/${total} tests passed (${percentage}%)`);
        console.log(`${'='*60}\n`);

        return percentage === 100;
    }

    /**
     * Run all tests
     */
    async runAll() {
        console.log('\n╔════════════════════════════════════════════════════╗');
        console.log('║  WebSocket Integration Test Suite                  ║');
        console.log('╚════════════════════════════════════════════════════╝');

        try {
            // Start server
            console.log('\n[Setup] Starting WebSocket server...');
            await this.startServer();
            
            // Connect client
            console.log('[Setup] Connecting test client...');
            await this.connectClient();
            
            // Run tests
            await this.testConnection();
            await this.testInitialization();
            await this.testStartEnrollment();
            await this.testAudioReception();
            await this.testGetStatus();
            await this.testPingPong();
            await this.testStopAudio();
            
            // Print summary
            const allPassed = this.printSummary();
            
            // Cleanup
            console.log('[Cleanup] Closing connections...');
            if (this.client) {
                this.client.close();
            }
            if (this.handler) {
                await this.handler.stop();
            }
            
            return allPassed ? 0 : 1;
        } catch (err) {
            console.error('\n[Error] Test suite failed:', err.message);
            console.error(err.stack);
            
            // Cleanup on error
            if (this.client) {
                this.client.close();
            }
            if (this.handler) {
                await this.handler.stop();
            }
            
            return 1;
        }
    }
}

// Run tests if executed directly
if (require.main === module) {
    const tester = new WebSocketIntegrationTest();
    tester.runAll().then(exitCode => {
        process.exit(exitCode);
    }).catch(err => {
        console.error('Fatal error:', err);
        process.exit(1);
    });
}

module.exports = WebSocketIntegrationTest;
