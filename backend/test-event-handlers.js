/**
 * Session Event Handlers - Examples & Tests
 * Demonstrates how to use event handlers with SessionManager
 */

const { SessionManager, MemoryPersistenceStore } = require('./session-manager');
const SessionEventHandlers = require('./session-event-handlers');

// ============================================================================
// EXAMPLE 1: Basic Setup with Console Logging
// ============================================================================
function example1BasicSetup() {
    console.log('\n========== EXAMPLE 1: Basic Setup ==========\n');

    // Create SessionManager
    const sessionManager = new SessionManager({
        sessionTimeout: 30 * 60 * 1000,    // 30 minutes
        cleanupInterval: 5 * 60 * 1000,     // 5 minutes cleanup
        maxSessions: 100
    });

    // Create event handlers
    const eventHandlers = new SessionEventHandlers(sessionManager, {
        enableAnalytics: true,
        enableAuditing: true,
        logger: console
    });

    // Create a session
    console.log('\n→ Creating session...');
    const session = sessionManager.createSession('user123', {
        action: 'enrollment',
        language: 'en',
        ipAddress: '192.168.1.100'
    });

    console.log(`✓ Session created: ${session.sessionId}`);

    // Update session
    console.log('\n→ Updating session...');
    sessionManager.updateSession(session.sessionId, {
        metadata: { audioProcessed: true }
    });

    console.log('✓ Session updated');

    // Get event stats
    console.log('\n→ Event Statistics:');
    console.log(eventHandlers.getEventStats());

    // Cleanup
    eventHandlers.shutdown();
    sessionManager.shutdown();
}

// ============================================================================
// EXAMPLE 2: Webhook Integration
// ============================================================================
function example2Webhooks() {
    console.log('\n========== EXAMPLE 2: Webhook Integration ==========\n');

    const sessionManager = new SessionManager({
        sessionTimeout: 30 * 60 * 1000,
        cleanupInterval: 5 * 60 * 1000
    });

    const eventHandlers = new SessionEventHandlers(sessionManager);

    // Register webhook for session creation
    eventHandlers.registerWebhook('session:created', (eventType, payload) => {
        console.log(`\n🎯 WEBHOOK: Session Created`);
        console.log(`   Session ID: ${payload.sessionId}`);
        console.log(`   User ID: ${payload.userId}`);
        console.log(`   Timestamp: ${payload.timestamp}`);
        // Could send to external API, WebSocket, etc.
    });

    // Register webhook for session expiration
    eventHandlers.registerWebhook('session:expired', (eventType, payload) => {
        console.log(`\n💤 WEBHOOK: Session Expired`);
        console.log(`   Session ID: ${payload.sessionId}`);
        console.log(`   Reason: ${payload.reason}`);
        // Could send notification to user
    });

    // Register webhook for all events
    eventHandlers.registerWebhook('*', (eventType, payload) => {
        console.log(`\n📡 WEBHOOK: All Events Captured`);
        console.log(`   Event: ${eventType}`);
        console.log(`   Payload Keys: ${Object.keys(payload).join(', ')}`);
    });

    // Trigger events
    console.log('\n→ Creating multiple sessions...');
    const session1 = sessionManager.createSession('user1', { action: 'enrollment' });
    const session2 = sessionManager.createSession('user2', { action: 'enrollment' });

    console.log('\n→ Updating session...');
    sessionManager.updateSession(session1.sessionId, {
        metadata: { progress: 50 }
    });

    console.log('\n→ Destroying session...');
    sessionManager.destroySession(session1.sessionId);

    // Cleanup
    eventHandlers.shutdown();
    sessionManager.shutdown();
}

// ============================================================================
// EXAMPLE 3: Custom Analytics Store
// ============================================================================
function example3CustomAnalytics() {
    console.log('\n========== EXAMPLE 3: Custom Analytics Store ==========\n');

    // Custom analytics store
    class Analytics {
        constructor() {
            this.events = [];
        }

        record(event) {
            this.events.push(event);
            console.log(`\n📊 Analytics Recorded: ${event.eventType}`);
        }

        getReport() {
            const report = {};
            this.events.forEach(event => {
                report[event.eventType] = (report[event.eventType] || 0) + 1;
            });
            return report;
        }
    }

    const analytics = new Analytics();

    const sessionManager = new SessionManager({
        sessionTimeout: 30 * 60 * 1000,
        cleanupInterval: 5 * 60 * 1000
    });

    const eventHandlers = new SessionEventHandlers(sessionManager, {
        analyticsStore: analytics,
        enableAnalytics: true
    });

    // Create sessions
    console.log('\n→ Creating sessions...');
    const session1 = sessionManager.createSession('user1', { action: 'enrollment' });
    const session2 = sessionManager.createSession('user2', { action: 'verification' });

    sessionManager.updateSession(session1.sessionId, { metadata: { step: 1 } });
    sessionManager.updateSession(session2.sessionId, { metadata: { step: 2 } });

    sessionManager.destroySession(session2.sessionId);

    // Print analytics report
    console.log('\n→ Analytics Report:');
    console.log(analytics.getReport());
    console.log(`\nTotal events recorded: ${analytics.events.length}`);

    // Cleanup
    eventHandlers.shutdown();
    sessionManager.shutdown();
}

// ============================================================================
// EXAMPLE 4: Custom Audit Log
// ============================================================================
function example4AuditLog() {
    console.log('\n========== EXAMPLE 4: Custom Audit Log ==========\n');

    // Custom audit log
    class AuditLog {
        constructor() {
            this.entries = [];
        }

        log(entry) {
            const logEntry = {
                ...entry,
                logTime: new Date().toISOString()
            };
            this.entries.push(logEntry);
            console.log(`\n🔐 Audit Entry Created:`);
            console.log(`   Event: ${entry.eventType}`);
            console.log(`   Session: ${entry.sessionId || 'N/A'}`);
            console.log(`   User: ${entry.userId || 'N/A'}`);
        }

        getHistory(eventType) {
            if (eventType) {
                return this.entries.filter(e => e.eventType === eventType);
            }
            return this.entries;
        }
    }

    const auditLog = new AuditLog();

    const sessionManager = new SessionManager({
        sessionTimeout: 30 * 60 * 1000,
        cleanupInterval: 5 * 60 * 1000
    });

    const eventHandlers = new SessionEventHandlers(sessionManager, {
        auditLog,
        enableAuditing: true
    });

    // Create and manage sessions
    console.log('\n→ Creating sessions (all actions will be audited)...');
    const session = sessionManager.createSession('user123', { action: 'enrollment' });
    sessionManager.updateSession(session.sessionId, { metadata: { status: 'in_progress' } });
    sessionManager.destroySession(session.sessionId);

    // Show audit history
    console.log('\n→ Audit History:');
    console.log(JSON.stringify(auditLog.getHistory(), null, 2));

    // Cleanup
    eventHandlers.shutdown();
    sessionManager.shutdown();
}

// ============================================================================
// EXAMPLE 5: Multi-User Session Management with Monitoring
// ============================================================================
function example5MultiUserMonitoring() {
    console.log('\n========== EXAMPLE 5: Multi-User Monitoring ==========\n');

    const sessionManager = new SessionManager({
        sessionTimeout: 30 * 60 * 1000,
        cleanupInterval: 5 * 60 * 1000,
        maxSessions: 1000
    });

    const eventHandlers = new SessionEventHandlers(sessionManager, {
        enableAnalytics: true,
        enableAuditing: true
    });

    // Monitor session creation
    let createdCount = 0;
    eventHandlers.registerWebhook('session:created', () => {
        createdCount++;
    });

    // Monitor session expiration
    let expiredCount = 0;
    eventHandlers.registerWebhook('session:expired', () => {
        expiredCount++;
    });

    // Simulate multiple users
    console.log('\n→ Simulating 5 users creating sessions...');
    const sessions = [];
    for (let i = 1; i <= 5; i++) {
        const session = sessionManager.createSession(`user${i}`, {
            action: i % 2 === 0 ? 'enrollment' : 'verification',
            language: 'en'
        });
        sessions.push(session);
    }

    console.log(`✓ Created ${sessions.length} sessions`);

    // Update some sessions
    console.log('\n→ Updating 3 sessions...');
    for (let i = 0; i < 3; i++) {
        sessionManager.updateSession(sessions[i].sessionId, {
            metadata: { audioBuffer: Math.random() * 1000 }
        });
    }

    // Show current stats
    console.log('\n→ Current Statistics:');
    const stats = eventHandlers.getEventStats();
    console.log(`   Total Events: ${stats.totalEvents}`);
    console.log(`   Sessions Created: ${stats.eventCounters['session:created']}`);
    console.log(`   Sessions Updated: ${stats.eventCounters['session:updated']}`);
    console.log(`   Active Sessions: ${stats.sessionStats.activeSessions}`);

    // Show user sessions
    console.log('\n→ User Sessions:');
    const userSessions = sessionManager.getUserSessions('user1');
    console.log(`   User1 has ${userSessions.length} active session(s)`);

    // Cleanup
    eventHandlers.shutdown();
    sessionManager.shutdown();
}

// ============================================================================
// EXAMPLE 6: Integration with External API (Simulated)
// ============================================================================
async function example6ExternalIntegration() {
    console.log('\n========== EXAMPLE 6: External API Integration ==========\n');

    const sessionManager = new SessionManager({
        sessionTimeout: 30 * 60 * 1000,
        cleanupInterval: 5 * 60 * 1000
    });

    const eventHandlers = new SessionEventHandlers(sessionManager);

    // Simulate sending to external API
    eventHandlers.registerWebhook('session:created', async (eventType, payload) => {
        console.log(`\n→ Sending session creation to external API...`);
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 500));
        console.log(`✓ API Response: Session registered as ${payload.sessionId}`);
    });

    // Simulate sending to dashboard
    eventHandlers.registerWebhook('session:updated', async (eventType, payload) => {
        console.log(`\n→ Updating dashboard...`);
        await new Promise(resolve => setTimeout(resolve, 300));
        console.log(`✓ Dashboard updated for session ${payload.sessionId}`);
    });

    // Simulate sending notification
    eventHandlers.registerWebhook('session:expired', async (eventType, payload) => {
        console.log(`\n→ Sending expiration notification...`);
        await new Promise(resolve => setTimeout(resolve, 400));
        console.log(`✓ Notification sent to user ${payload.userId}`);
    });

    // Create and manage session
    console.log('\n→ Creating session...');
    const session = sessionManager.createSession('user456', { action: 'enrollment' });

    console.log('\n→ Updating session...');
    sessionManager.updateSession(session.sessionId, {
        metadata: { progress: 75 }
    });

    // Small delay to see async webhooks complete
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Cleanup
    eventHandlers.shutdown();
    sessionManager.shutdown();
}

// ============================================================================
// EXAMPLE 7: Error Handling and Recovery
// ============================================================================
function example7ErrorHandling() {
    console.log('\n========== EXAMPLE 7: Error Handling ==========\n');

    const sessionManager = new SessionManager({
        sessionTimeout: 30 * 60 * 1000,
        cleanupInterval: 5 * 60 * 1000
    });

    const eventHandlers = new SessionEventHandlers(sessionManager, {
        logger: {
            log: (msg) => console.log(`[LOG] ${msg}`),
            warn: (msg) => console.warn(`[WARN] ${msg}`),
            error: (msg) => console.error(`[ERROR] ${msg}`)
        }
    });

    // Register webhook that might fail
    eventHandlers.registerWebhook('session:created', (eventType, payload) => {
        console.log(`\n→ Processing webhook (might fail deliberately)...`);
        // Simulate an error
        if (Math.random() > 0.5) {
            throw new Error('Simulated webhook failure');
        }
        console.log(`✓ Webhook processed successfully`);
    });

    // Create sessions - some webhooks may fail, but system continues
    console.log('\n→ Creating sessions (with potential webhook failures)...');
    for (let i = 0; i < 3; i++) {
        const session = sessionManager.createSession(`user${i}`, {
            action: 'test'
        });
        console.log(`   Created session ${i + 1}: ${session.sessionId}`);
    }

    console.log('\n✓ All sessions created despite potential webhook errors');

    // Cleanup
    eventHandlers.shutdown();
    sessionManager.shutdown();
}

// ============================================================================
// EXAMPLE 8: Complete Production Setup
// ============================================================================
function example8ProductionSetup() {
    console.log('\n========== EXAMPLE 8: Production Setup ==========\n');

    // Custom logger
    const logger = {
        log: (msg) => console.log(`[${new Date().toISOString()}] [INFO] ${msg}`),
        warn: (msg) => console.warn(`[${new Date().toISOString()}] [WARN] ${msg}`),
        error: (msg) => console.error(`[${new Date().toISOString()}] [ERROR] ${msg}`)
    };

    // Custom analytics store for production
    class ProductionAnalytics {
        constructor() {
            this.events = [];
        }
        record(event) {
            // In production, would send to: MongoDB, ElasticSearch, etc.
            this.events.push(event);
        }
    }

    // Custom audit log for compliance
    class ProductionAuditLog {
        constructor() {
            this.entries = [];
        }
        log(entry) {
            // In production, would write to: immutable audit store
            this.entries.push({
                ...entry,
                timestamp: new Date().toISOString(),
                logId: `log_${Date.now()}`
            });
        }
    }

    // Setup
    const sessionManager = new SessionManager({
        sessionTimeout: 30 * 60 * 1000,
        cleanupInterval: 5 * 60 * 1000,
        maxSessions: 10000
    });

    const eventHandlers = new SessionEventHandlers(sessionManager, {
        enableAnalytics: true,
        enableAuditing: true,
        analyticsStore: new ProductionAnalytics(),
        auditLog: new ProductionAuditLog(),
        logger
    });

    // Register production webhooks
    eventHandlers.registerWebhook('session:created', (eventType, payload) => {
        logger.log(`Session created: ${payload.sessionId}`);
    });

    eventHandlers.registerWebhook('session:expired', (eventType, payload) => {
        logger.log(`Session expired: ${payload.sessionId}`);
    });

    eventHandlers.registerWebhook('cleanup:completed', (eventType, payload) => {
        logger.log(`Cleanup removed ${payload.removedCount} sessions`);
    });

    // Simulate production workload
    console.log('\n→ Simulating production workload...');
    const sessions = [];
    for (let i = 0; i < 10; i++) {
        sessions.push(sessionManager.createSession(`prod_user_${i}`, {
            action: Math.random() > 0.5 ? 'enrollment' : 'verification',
            ipAddress: `192.168.1.${100 + i}`
        }));
    }

    // Generate activity
    sessions.forEach((session, idx) => {
        for (let i = 0; i < Math.random() * 5; i++) {
            sessionManager.updateSession(session.sessionId, {
                metadata: { activity: `event_${i}` }
            });
        }
    });

    // Print production report
    console.log('\n→ Production Report:');
    const report = eventHandlers.getDetailedReport();
    console.log(JSON.stringify(report, null, 2));

    // Cleanup
    console.log('\n→ Shutting down...');
    eventHandlers.shutdown();
    sessionManager.shutdown();
    logger.log('System shutdown complete');
}

// ============================================================================
// Run Examples
// ============================================================================
async function runAllExamples() {
    console.log('╔════════════════════════════════════════════════════════════════╗');
    console.log('║         Session Event Handlers - Complete Examples             ║');
    console.log('╚════════════════════════════════════════════════════════════════╝');

    example1BasicSetup();
    example2Webhooks();
    example3CustomAnalytics();
    example4AuditLog();
    example5MultiUserMonitoring();
    await example6ExternalIntegration();
    example7ErrorHandling();
    example8ProductionSetup();

    console.log('\n╔════════════════════════════════════════════════════════════════╗');
    console.log('║                   All Examples Complete!                       ║');
    console.log('╚════════════════════════════════════════════════════════════════╝\n');
}

// Export for use in other files
module.exports = {
    example1BasicSetup,
    example2Webhooks,
    example3CustomAnalytics,
    example4AuditLog,
    example5MultiUserMonitoring,
    example6ExternalIntegration,
    example7ErrorHandling,
    example8ProductionSetup,
    runAllExamples
};

// Run if executed directly
if (require.main === module) {
    runAllExamples();
}
