/**
 * Session Event Handlers
 * Manages all session lifecycle events and triggers appropriate actions
 * 
 * Events Handled:
 * - session:created
 * - session:updated
 * - session:destroyed
 * - session:expired
 * - cleanup:completed
 * - all-sessions:cleared
 */

const fs = require('fs');
const path = require('path');

class SessionEventHandlers {
    constructor(sessionManager, options = {}) {
        this.sessionManager = sessionManager;
        this.logger = options.logger || console;
        this.enableAnalytics = options.enableAnalytics !== false;
        this.enableAuditing = options.enableAuditing !== false;
        this.analyticsStore = options.analyticsStore || null;
        this.auditLog = options.auditLog || null;
        this.webhookHandlers = options.webhookHandlers || [];
        
        // Event counters for monitoring
        this.eventCounters = {
            'session:created': 0,
            'session:updated': 0,
            'session:destroyed': 0,
            'session:expired': 0,
            'cleanup:completed': 0,
            'all-sessions:cleared': 0
        };
        
        // Initialize handlers
        this.initializeHandlers();
        
        this.logger.log('[SessionEventHandlers] Initialized');
    }

    /**
     * Initialize all event handlers
     * @private
     */
    initializeHandlers() {
        if (!this.sessionManager) {
            throw new Error('SessionManager instance is required');
        }

        // Session created
        this.sessionManager.on('session:created', (data) => {
            this.handleSessionCreated(data);
        });

        // Session updated
        this.sessionManager.on('session:updated', (data) => {
            this.handleSessionUpdated(data);
        });

        // Session destroyed
        this.sessionManager.on('session:destroyed', (data) => {
            this.handleSessionDestroyed(data);
        });

        // Session expired
        this.sessionManager.on('session:expired', (data) => {
            this.handleSessionExpired(data);
        });

        // Cleanup completed
        this.sessionManager.on('cleanup:completed', (data) => {
            this.handleCleanupCompleted(data);
        });

        // All sessions cleared
        this.sessionManager.on('all-sessions:cleared', (data) => {
            this.handleAllSessionsCleared(data);
        });

        this.logger.log('[SessionEventHandlers] All event listeners registered');
    }

    /**
     * Handle session:created event
     * @private
     * @param {Object} data - Event data { sessionId, userId }
     */
    handleSessionCreated(data) {
        const { sessionId, userId } = data;
        this.eventCounters['session:created']++;

        const timestamp = new Date().toISOString();
        
        try {
            // Log event
            this.logger.log(`[EVENT] Session Created - ID: ${sessionId}, User: ${userId}, Time: ${timestamp}`);

            // Record audit
            if (this.enableAuditing && this.auditLog) {
                this.recordAuditLog('session:created', {
                    sessionId,
                    userId,
                    timestamp,
                    eventNumber: this.eventCounters['session:created']
                });
            }

            // Record analytics
            if (this.enableAnalytics && this.analyticsStore) {
                this.recordAnalyticsEvent(sessionId, userId, 'session_created', {
                    action: 'Session initialization',
                    timestamp
                });
            }

            // Trigger webhooks
            this.triggerWebhooks('session:created', {
                sessionId,
                userId,
                timestamp,
                status: 'success'
            });

            // Additional initialization tasks
            this.initializeSessionResources(sessionId, userId);

        } catch (error) {
            this.logger.error(`[ERROR] Failed to handle session:created event: ${error.message}`);
        }
    }

    /**
     * Handle session:updated event
     * @private
     * @param {Object} data - Event data { sessionId, userId }
     */
    handleSessionUpdated(data) {
        const { sessionId, userId } = data;
        this.eventCounters['session:updated']++;

        const timestamp = new Date().toISOString();

        try {
            const session = this.sessionManager.getSession(sessionId);
            
            if (!session) {
                this.logger.warn(`[WARN] Session not found for update: ${sessionId}`);
                return;
            }

            this.logger.log(`[EVENT] Session Updated - ID: ${sessionId}, User: ${userId}, Time: ${timestamp}`);

            // Record audit
            if (this.enableAuditing && this.auditLog) {
                this.recordAuditLog('session:updated', {
                    sessionId,
                    userId,
                    timestamp,
                    sessionMetadata: session.metadata,
                    eventNumber: this.eventCounters['session:updated']
                });
            }

            // Record analytics
            if (this.enableAnalytics && this.analyticsStore) {
                this.recordAnalyticsEvent(sessionId, userId, 'session_updated', {
                    action: 'Session data modified',
                    timestamp,
                    audioBufferSize: session.audioBuffer.length
                });
            }

            // Trigger webhooks
            this.triggerWebhooks('session:updated', {
                sessionId,
                userId,
                timestamp,
                sessionData: this.sessionManager.exportSession(sessionId),
                status: 'success'
            });

        } catch (error) {
            this.logger.error(`[ERROR] Failed to handle session:updated event: ${error.message}`);
        }
    }

    /**
     * Handle session:destroyed event
     * @private
     * @param {Object} data - Event data { sessionId, userId }
     */
    handleSessionDestroyed(data) {
        const { sessionId, userId } = data;
        this.eventCounters['session:destroyed']++;

        const timestamp = new Date().toISOString();

        try {
            this.logger.log(`[EVENT] Session Destroyed - ID: ${sessionId}, User: ${userId}, Time: ${timestamp}`);

            // Record audit
            if (this.enableAuditing && this.auditLog) {
                this.recordAuditLog('session:destroyed', {
                    sessionId,
                    userId,
                    timestamp,
                    reason: 'User initiated or cleanup',
                    eventNumber: this.eventCounters['session:destroyed']
                });
            }

            // Record analytics
            if (this.enableAnalytics && this.analyticsStore) {
                this.recordAnalyticsEvent(sessionId, userId, 'session_destroyed', {
                    action: 'Session terminated',
                    timestamp
                });
            }

            // Trigger webhooks
            this.triggerWebhooks('session:destroyed', {
                sessionId,
                userId,
                timestamp,
                status: 'destroyed'
            });

            // Cleanup resources
            this.cleanupSessionResources(sessionId);

        } catch (error) {
            this.logger.error(`[ERROR] Failed to handle session:destroyed event: ${error.message}`);
        }
    }

    /**
     * Handle session:expired event
     * @private
     * @param {Object} data - Event data { sessionId, userId }
     */
    handleSessionExpired(data) {
        const { sessionId, userId } = data;
        this.eventCounters['session:expired']++;

        const timestamp = new Date().toISOString();

        try {
            this.logger.log(`[EVENT] Session Expired - ID: ${sessionId}, User: ${userId}, Time: ${timestamp}`);

            // Record audit
            if (this.enableAuditing && this.auditLog) {
                this.recordAuditLog('session:expired', {
                    sessionId,
                    userId,
                    timestamp,
                    reason: 'Session timeout',
                    eventNumber: this.eventCounters['session:expired']
                });
            }

            // Record analytics
            if (this.enableAnalytics && this.analyticsStore) {
                this.recordAnalyticsEvent(sessionId, userId, 'session_expired', {
                    action: 'Session timeout',
                    timestamp
                });
            }

            // Trigger webhooks
            this.triggerWebhooks('session:expired', {
                sessionId,
                userId,
                timestamp,
                status: 'expired',
                reason: 'Timeout'
            });

            // Send user notification
            this.notifySessionExpiration(userId, sessionId);

        } catch (error) {
            this.logger.error(`[ERROR] Failed to handle session:expired event: ${error.message}`);
        }
    }

    /**
     * Handle cleanup:completed event
     * @private
     * @param {Object} data - Event data { removedCount }
     */
    handleCleanupCompleted(data) {
        const { removedCount } = data;
        this.eventCounters['cleanup:completed']++;

        const timestamp = new Date().toISOString();

        try {
            this.logger.log(`[EVENT] Cleanup Completed - Removed: ${removedCount}, Time: ${timestamp}`);

            // Record audit
            if (this.enableAuditing && this.auditLog) {
                this.recordAuditLog('cleanup:completed', {
                    removedCount,
                    timestamp,
                    eventNumber: this.eventCounters['cleanup:completed']
                });
            }

            // Trigger webhooks
            this.triggerWebhooks('cleanup:completed', {
                timestamp,
                removedCount,
                status: 'completed'
            });

            // Generate cleanup report
            this.generateCleanupReport(removedCount, timestamp);

        } catch (error) {
            this.logger.error(`[ERROR] Failed to handle cleanup:completed event: ${error.message}`);
        }
    }

    /**
     * Handle all-sessions:cleared event
     * @private
     * @param {Object} data - Event data { count }
     */
    handleAllSessionsCleared(data) {
        const { count } = data;
        this.eventCounters['all-sessions:cleared']++;

        const timestamp = new Date().toISOString();

        try {
            this.logger.warn(`[EVENT] All Sessions Cleared - Count: ${count}, Time: ${timestamp}`);

            // Record audit (important event)
            if (this.enableAuditing && this.auditLog) {
                this.recordAuditLog('all-sessions:cleared', {
                    count,
                    timestamp,
                    severity: 'high',
                    eventNumber: this.eventCounters['all-sessions:cleared']
                });
            }

            // Trigger webhooks
            this.triggerWebhooks('all-sessions:cleared', {
                timestamp,
                clearedCount: count,
                status: 'cleared',
                severity: 'high'
            });

        } catch (error) {
            this.logger.error(`[ERROR] Failed to handle all-sessions:cleared event: ${error.message}`);
        }
    }

    /**
     * Record audit log entry
     * @private
     * @param {string} eventType - Type of event
     * @param {Object} data - Event data to log
     */
    recordAuditLog(eventType, data) {
        if (!this.auditLog) {
            return;
        }

        try {
            const logEntry = {
                timestamp: new Date().toISOString(),
                eventType,
                ...data
            };

            // Async logging if available
            if (typeof this.auditLog.log === 'function') {
                this.auditLog.log(logEntry);
            } else {
                this.logger.log(`[AUDIT] ${eventType}:`, logEntry);
            }
        } catch (error) {
            this.logger.error(`[ERROR] Failed to record audit log: ${error.message}`);
        }
    }

    /**
     * Record analytics event
     * @private
     * @param {string} sessionId - Session identifier
     * @param {string} userId - User identifier
     * @param {string} eventType - Type of event
     * @param {Object} data - Event details
     */
    recordAnalyticsEvent(sessionId, userId, eventType, data) {
        if (!this.analyticsStore) {
            return;
        }

        try {
            const event = {
                sessionId,
                userId,
                eventType,
                timestamp: new Date().toISOString(),
                ...data
            };

            // Async recording if available
            if (typeof this.analyticsStore.record === 'function') {
                this.analyticsStore.record(event);
            } else {
                this.logger.log(`[ANALYTICS] ${eventType}:`, event);
            }
        } catch (error) {
            this.logger.error(`[ERROR] Failed to record analytics: ${error.message}`);
        }
    }

    /**
     * Trigger registered webhooks
     * @private
     * @param {string} eventType - Type of event
     * @param {Object} payload - Event payload
     */
    triggerWebhooks(eventType, payload) {
        if (!this.webhookHandlers || this.webhookHandlers.length === 0) {
            return;
        }

        this.webhookHandlers.forEach(handler => {
            try {
                if (handler.eventTypes.includes(eventType) || handler.eventTypes.includes('*')) {
                    // Handle async webhooks
                    if (handler.handler instanceof Promise || typeof handler.handler.then === 'function') {
                        handler.handler(eventType, payload).catch(err => {
                            this.logger.error(`[ERROR] Webhook handler failed: ${err.message}`);
                        });
                    } else {
                        handler.handler(eventType, payload);
                    }
                }
            } catch (error) {
                this.logger.error(`[ERROR] Failed to trigger webhook: ${error.message}`);
            }
        });
    }

    /**
     * Initialize session resources (custom hooks)
     * @private
     * @param {string} sessionId - Session identifier
     * @param {string} userId - User identifier
     */
    initializeSessionResources(sessionId, userId) {
        try {
            // Could be extended to initialize:
            // - Temp file pools
            // - Resource reservations
            // - Cache entries
            // - Monitoring metrics
            
            this.logger.log(`[INIT] Resources initialized for session ${sessionId}`);
        } catch (error) {
            this.logger.error(`[ERROR] Failed to initialize session resources: ${error.message}`);
        }
    }

    /**
     * Cleanup session resources
     * @private
     * @param {string} sessionId - Session identifier
     */
    cleanupSessionResources(sessionId) {
        try {
            // Cleanup:
            // - Temp files
            // - Reserved resources
            // - Cache entries
            // - Monitoring data
            
            this.logger.log(`[CLEANUP] Resources cleaned for session ${sessionId}`);
        } catch (error) {
            this.logger.error(`[ERROR] Failed to cleanup session resources: ${error.message}`);
        }
    }

    /**
     * Notify user of session expiration
     * @private
     * @param {string} userId - User identifier
     * @param {string} sessionId - Session identifier
     */
    notifySessionExpiration(userId, sessionId) {
        try {
            // Could be extended to:
            // - Send email notification
            // - Send push notification
            // - Log to user notification service
            
            this.logger.log(`[NOTIFY] Session expiration notification for user ${userId}`);
        } catch (error) {
            this.logger.error(`[ERROR] Failed to send notification: ${error.message}`);
        }
    }

    /**
     * Generate cleanup report
     * @private
     * @param {number} removedCount - Number of sessions removed
     * @param {string} timestamp - Cleanup timestamp
     */
    generateCleanupReport(removedCount, timestamp) {
        try {
            const stats = this.sessionManager.getStatistics();
            const report = {
                timestamp,
                cleanupAction: {
                    removedCount,
                    timestamp
                },
                beforeCleanup: {
                    // Would track before cleanup
                },
                afterCleanup: stats,
                eventCounters: this.eventCounters
            };

            this.logger.log(`[REPORT] Cleanup Report:`, report);

            // Could save report to persistent storage
        } catch (error) {
            this.logger.error(`[ERROR] Failed to generate cleanup report: ${error.message}`);
        }
    }

    /**
     * Register a webhook handler
     * @param {string|Array} eventTypes - Event type(s) to listen to
     * @param {Function} handler - Handler function(eventType, payload)
     */
    registerWebhook(eventTypes, handler) {
        const types = Array.isArray(eventTypes) ? eventTypes : [eventTypes];
        
        this.webhookHandlers.push({
            eventTypes: types,
            handler
        });

        this.logger.log(`[WEBHOOK] Registered handler for events:`, types);
    }

    /**
     * Get event statistics
     * @returns {Object} Event counter statistics
     */
    getEventStats() {
        return {
            timestamp: new Date().toISOString(),
            eventCounters: { ...this.eventCounters },
            totalEvents: Object.values(this.eventCounters).reduce((a, b) => a + b, 0),
            sessionStats: this.sessionManager.getStatistics()
        };
    }

    /**
     * Reset event counters
     */
    resetEventCounters() {
        Object.keys(this.eventCounters).forEach(key => {
            this.eventCounters[key] = 0;
        });
        this.logger.log('[RESET] Event counters reset');
    }

    /**
     * Get detailed event report
     * @returns {Object} Comprehensive event report
     */
    getDetailedReport() {
        const stats = this.sessionManager.getStatistics();
        
        return {
            timestamp: new Date().toISOString(),
            events: {
                counters: { ...this.eventCounters },
                total: Object.values(this.eventCounters).reduce((a, b) => a + b, 0)
            },
            sessions: stats,
            enabledFeatures: {
                analytics: this.enableAnalytics,
                auditing: this.enableAuditing,
                webhooks: this.webhookHandlers.length > 0
            }
        };
    }

    /**
     * Shutdown event handlers
     */
    shutdown() {
        try {
            this.logger.log('[SHUTDOWN] Session Event Handlers shutting down');
            
            // Remove all listeners
            this.sessionManager.removeAllListeners('session:created');
            this.sessionManager.removeAllListeners('session:updated');
            this.sessionManager.removeAllListeners('session:destroyed');
            this.sessionManager.removeAllListeners('session:expired');
            this.sessionManager.removeAllListeners('cleanup:completed');
            this.sessionManager.removeAllListeners('all-sessions:cleared');

            this.webhookHandlers = [];
            
            this.logger.log('[SHUTDOWN] Event handlers shutdown complete');
        } catch (error) {
            this.logger.error(`[ERROR] Failed to shutdown event handlers: ${error.message}`);
        }
    }
}

module.exports = SessionEventHandlers;
