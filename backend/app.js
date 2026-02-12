#!/usr/bin/env node

/**
 * WebSocket Server Application Entry Point
 * Starts the WebSocket server for voice biometric authentication
 */

const WebSocketAudioHandler = require('./websocket-handler');
require('dotenv').config();

const PORT = process.env.WS_PORT || 8001;
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';
const NODE_ENV = process.env.NODE_ENV || 'development';

/**
 * Main application startup
 */
async function main() {
    console.log('\n╔════════════════════════════════════════════════════╗');
    console.log('║  Voice Biometric WebSocket Server                 ║');
    console.log('║  Starting Application...                          ║');
    console.log('╚════════════════════════════════════════════════════╝\n');

    try {
        const handler = new WebSocketAudioHandler(PORT);
        
        // Start the server
        await handler.start();
        
        console.log('╔════════════════════════════════════════════════════╗');
        console.log('║  ✓ Server Started Successfully!                   ║');
        console.log(`║  WebSocket: ws://0.0.0.0:${PORT}${'                   '.substring(0, 20 - PORT.toString().length)}║`);
        console.log(`║  Backend:   ${BACKEND_URL}${'              '.substring(0, 32 - BACKEND_URL.length)}║`);
        console.log(`║  Mode:      ${NODE_ENV}${'                        '.substring(0, 25 - NODE_ENV.length)}║`);
        console.log('╚════════════════════════════════════════════════════╝\n');
        
        // Expose handler globally for debugging
        global.wsHandler = handler;
        console.log('💡 Tip: Access handler as global.wsHandler in Node console\n');
        
        // Display periodic stats
        const statsInterval = setInterval(() => {
            const stats = handler.getStats();
            if (stats.connectedClients > 0 || stats.activeSessions > 0) {
                console.log(`📊 Stats - Clients: ${stats.connectedClients}, Sessions: ${stats.activeSessions}`);
            }
        }, 30000);
        
        // Graceful shutdown handling
        process.on('SIGTERM', async () => {
            console.log('\n⚠️  SIGTERM received - Shutting down...');
            clearInterval(statsInterval);
            await handler.stop();
            process.exit(0);
        });
        
        process.on('SIGINT', async () => {
            console.log('\n⚠️  SIGINT received - Shutting down...');
            clearInterval(statsInterval);
            await handler.stop();
            process.exit(0);
        });
        
    } catch (error) {
        console.error('\n❌ Failed to start server:', error.message);
        console.error('\nTroubleshooting:');
        console.error('1. Check if port is already in use');
        console.error('2. Verify .env file configuration');
        console.error('3. Check backend API is running at', BACKEND_URL);
        process.exit(1);
    }
}

// Run application
main();
