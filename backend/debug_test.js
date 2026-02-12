#!/usr/bin/env node

/**
 * Simplified Debug Test
 * Tests basic WebSocket functionality with logging
 */

const WebSocket = require('ws');

const WS_URL = 'ws://localhost:8001';

console.log('🔧 Debug WebSocket Connection Test');
console.log('═'.repeat(50));
console.log(`Connecting to: ${WS_URL}`);

const ws = new WebSocket(WS_URL);

ws.on('open', () => {
    console.log('✅ WebSocket connected!');
    console.log('Sending init message...');
    
    const msg = {
        type: 'init',
        userId: 'test_user',
        action: 'enroll'
    };
    
    const msgStr = JSON.stringify(msg);
    console.log(`📤 Sending: ${msgStr}`);
    
    ws.send(msgStr);
});

ws.on('message', (data) => {
    console.log('📥 Message received (length:', data.length, ')');
    
    try {
        const msg = JSON.parse(data);
        console.log('✅ Parsed JSON:', JSON.stringify(msg, null, 2));
    } catch (err) {
        console.log('❌ Binary data received');
    }
});

ws.on('error', (err) => {
    console.error('❌ Error:', err.message);
});

ws.on('close', () => {
    console.log('❌ Connection closed');
    process.exit(0);
});

setTimeout(() => {
    console.log('⏰ Timeout - no response received');
    ws.close();
    process.exit(1);
}, 5000);
