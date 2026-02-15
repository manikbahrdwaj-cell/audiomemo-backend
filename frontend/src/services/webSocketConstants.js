/**
 * WebSocket Constants and Message Type Definitions
 * Centralized configuration for message types and protocol constants
 */

/**
 * WebSocket message types matching backend protocol
 */
export const MESSAGE_TYPES = {
  // Audio operations
  AUDIO: 'audio',

  // Verification and enrollment
  VERIFY: 'verify',
  VERIFY_CONFIRMED: 'verify_confirmed',
  ENROLL: 'enroll',
  ENROLLMENT_STATUS: 'enrollment_status',
  ENROLLMENT_CONFIRMED: 'enrollment_confirmed',

  // System control
  PING: 'ping',
  PONG: 'pong',
  RESET: 'reset',
  STATUS: 'status',

  // Configuration
  CONFIG: 'config',

  // Error handling
  ERROR: 'error',

  // Response types
  RESPONSE: 'response',
  SUCCESS: 'success',
  FAILURE: 'failure'
};

/**
 * Response status codes
 */
export const RESPONSE_STATUS = {
  SUCCESS: 'success',
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  VERIFIED: 'verified',
  REJECTED: 'rejected',
  ENROLLED: 'enrolled',
  ERROR: 'error'
};

/**
 * Connection states
 */
export const CONNECTION_STATES = {
  NOT_INITIALIZED: 'NOT_INITIALIZED',
  CONNECTING: 'CONNECTING',
  CONNECTED: 'CONNECTED',
  DISCONNECTING: 'DISCONNECTING',
  DISCONNECTED: 'DISCONNECTED',
  ERROR: 'ERROR',
  RECONNECTING: 'RECONNECTING'
};

/**
 * Configuration defaults
 */
export const CONFIG_DEFAULTS = {
  // Connection settings
  maxConnectionAttempts: 5,
  initialReconnectDelay: 1000, // ms
  maxReconnectDelay: 30000, // ms
  reconnectDelayMultiplier: 1.5,

  // Heartbeat/keep-alive
  heartbeatInterval: 30000, // ms
  heartbeatTimeout: 60000, // ms

  // Message settings
  maxMessageSize: 1024 * 1024, // 1MB
  messageQueueMaxSize: 100,
  messageTimeout: 30000, // ms

  // Connection timeout
  connectionTimeout: 10000, // ms

  // Audio settings
  audioChunkSize: 4096, // bytes
  audioSampleRate: 16000 // Hz

  // Logging
  // debug: false
};

/**
 * Error codes and messages
 */
export const ERROR_CODES = {
  CONNECTION_FAILED: 'CONNECTION_FAILED',
  CONNECTION_TIMEOUT: 'CONNECTION_TIMEOUT',
  DISCONNECTED: 'DISCONNECTED',
  MESSAGE_SEND_FAILED: 'MESSAGE_SEND_FAILED',
  MAX_ATTEMPTS_REACHED: 'MAX_ATTEMPTS_REACHED',
  NOT_CONNECTED: 'NOT_CONNECTED',
  INVALID_MESSAGE: 'INVALID_MESSAGE',
  MESSAGE_QUEUE_FULL: 'MESSAGE_QUEUE_FULL',
  UNKNOWN_ERROR: 'UNKNOWN_ERROR'
};

/**
 * Error messages
 */
export const ERROR_MESSAGES = {
  [ERROR_CODES.CONNECTION_FAILED]: 'Failed to establish WebSocket connection',
  [ERROR_CODES.CONNECTION_TIMEOUT]: 'WebSocket connection timed out',
  [ERROR_CODES.DISCONNECTED]: 'WebSocket disconnected',
  [ERROR_CODES.MESSAGE_SEND_FAILED]: 'Failed to send message',
  [ERROR_CODES.MAX_ATTEMPTS_REACHED]: 'Maximum connection attempts reached',
  [ERROR_CODES.NOT_CONNECTED]: 'WebSocket not connected',
  [ERROR_CODES.INVALID_MESSAGE]: 'Invalid message format',
  [ERROR_CODES.MESSAGE_QUEUE_FULL]: 'Message queue is full',
  [ERROR_CODES.UNKNOWN_ERROR]: 'Unknown error occurred'
};

/**
 * Event types
 */
export const EVENT_TYPES = {
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
  MESSAGE: 'message',
  HEARTBEAT: 'heartbeat',
  RECONNECT_ATTEMPT: 'reconnect_attempt',
  STATE_CHANGED: 'state_changed',
  MESSAGE_QUEUED: 'message_queued',
  MESSAGE_SENT: 'message_sent'
};

export default {
  MESSAGE_TYPES,
  RESPONSE_STATUS,
  CONNECTION_STATES,
  CONFIG_DEFAULTS,
  ERROR_CODES,
  ERROR_MESSAGES,
  EVENT_TYPES
};
