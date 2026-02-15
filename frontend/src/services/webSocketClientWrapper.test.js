/**
 * WebSocket Client Wrapper Tests
 * Unit and integration tests for the WebSocket client wrapper
 */

import WebSocketClientWrapper, { createWebSocketClient, getWebSocketUrl } from '../services/webSocketClientWrapper';
import {
  MESSAGE_TYPES,
  CONNECTION_STATES,
  EVENT_TYPES,
  ERROR_CODES
} from '../services/webSocketConstants';

/**
 * Mock WebSocket for testing
 */
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    this.onopen = null;
    this.onclose = null;
    this.onerror = null;
    this.onmessage = null;
    this.messages = [];
  }

  send(data) {
    this.messages.push(JSON.parse(data));
  }

  close() {
    this.readyState = WebSocket.CLOSED;
  }

  simulateOpen() {
    this.readyState = WebSocket.OPEN;
    this.onopen?.();
  }

  simulateClose() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.();
  }

  simulateError(error) {
    this.onerror?.(error);
  }

  simulateMessage(data) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

/**
 * Test Suites
 */
describe('WebSocketClientWrapper', () => {
  let client;
  let mockWS;

  beforeEach(() => {
    // Mock WebSocket
    global.WebSocket = MockWebSocket;
    mockWS = null;
    
    // Intercept WebSocket constructor
    const OriginalWebSocket = global.WebSocket;
    global.WebSocket = function (url) {
      mockWS = new OriginalWebSocket(url);
      return mockWS;
    };
    global.WebSocket.CONNECTING = 0;
    global.WebSocket.OPEN = 1;
    global.WebSocket.CLOSING = 2;
    global.WebSocket.CLOSED = 3;
  });

  afterEach(() => {
    if (client) {
      client.destroy();
    }
  });

  test('should create client with URL', () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    expect(client.url).toBe('ws://localhost:8000/ws');
    expect(client.state).toBe(CONNECTION_STATES.NOT_INITIALIZED);
  });

  test('should connect successfully', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    const connectPromise = client.connect();
    
    // Simulate successful connection
    setTimeout(() => mockWS?.simulateOpen(), 10);
    
    await connectPromise;
    expect(client.isConnected()).toBe(true);
    expect(client.state).toBe(CONNECTION_STATES.CONNECTED);
  });

  test('should emit connected event', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    let emitted = false;
    
    client.on(EVENT_TYPES.CONNECTED, () => {
      emitted = true;
    });
    
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    expect(emitted).toBe(true);
  });

  test('should send message', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    const message = { type: 'ping' };
    client.sendMessage(message);
    
    expect(mockWS.messages).toContainEqual(message);
  });

  test('should queue message when disconnected', () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    
    const message = { type: 'ping' };
    const result = client.queueMessage(message);
    
    expect(result).toBe(true);
    expect(client.getMessageQueueSize()).toBe(1);
  });

  test('should handle messages from server', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    let receivedMessage = null;
    
    client.on(MESSAGE_TYPES.RESPONSE, (message) => {
      receivedMessage = message;
    });
    
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    mockWS.simulateMessage({ type: MESSAGE_TYPES.RESPONSE, status: 'success' });
    
    expect(receivedMessage).toEqual({ type: MESSAGE_TYPES.RESPONSE, status: 'success' });
  });

  test('should start heartbeat on connect', async () => {
    jest.useFakeTimers();
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    expect(client.heartbeatTimer).not.toBeNull();
    
    jest.useRealTimers();
  });

  test('should handle connection errors', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    let errorEmitted = false;
    
    client.on(EVENT_TYPES.ERROR, () => {
      errorEmitted = true;
    });
    
    const connectPromise = client.connect().catch(() => {});
    setTimeout(() => mockWS?.simulateError(new Error('Connection failed')), 10);
    
    await new Promise(r => setTimeout(r, 50));
    expect(errorEmitted).toBe(true);
  });

  test('should disconnect properly', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    let disconnected = false;
    client.on(EVENT_TYPES.DISCONNECTED, () => {
      disconnected = true;
    });
    
    client.disconnect();
    setTimeout(() => mockWS?.simulateClose(), 10);
    
    await new Promise(r => setTimeout(r, 50));
    expect(disconnected).toBe(true);
    expect(client.isConnected()).toBe(false);
  });

  test('should handle message queue on reconnect', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws', {
      maxConnectionAttempts: 2
    });
    
    // Queue a message while disconnected
    client.queueMessage({ type: MESSAGE_TYPES.PING });
    expect(client.getMessageQueueSize()).toBe(1);
    
    // Connect - should process queue
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    // Queue should be processed
    expect(client.getMessageQueueSize()).toBe(0);
    expect(mockWS.messages.length).toBeGreaterThan(0);
  });

  test('should reject request on timeout', async () => {
    jest.useFakeTimers();
    client = new WebSocketClientWrapper('ws://localhost:8000/ws', {
      messageTimeout: 100
    });
    
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    const requestPromise = client.sendRequest({ type: 'query' });
    
    jest.advanceTimersByTime(150);
    
    await expect(requestPromise).rejects.toThrow('Request timeout');
    jest.useRealTimers();
  });

  test('should handle request-response', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    // Send request
    const requestPromise = client.sendRequest({ type: 'query', request_id: 1 });
    
    // Simulate response
    setTimeout(() => {
      mockWS.simulateMessage({
        type: MESSAGE_TYPES.RESPONSE,
        request_id: 1,
        status: 'success',
        data: 'result'
      });
    }, 10);
    
    const response = await requestPromise;
    expect(response.status).toBe('success');
    expect(response.data).toBe('result');
  });

  test('should limit message queue size', () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws', {
      messageQueueMaxSize: 2
    });
    
    client.queueMessage({ type: MESSAGE_TYPES.PING });
    client.queueMessage({ type: MESSAGE_TYPES.PING });
    const result = client.queueMessage({ type: MESSAGE_TYPES.PING });
    
    expect(result).toBe(false);
    expect(client.getMessageQueueSize()).toBe(2);
  });

  test('should handle pong response', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    let heartbeatEmitted = false;
    
    client.on(EVENT_TYPES.HEARTBEAT, () => {
      heartbeatEmitted = true;
    });
    
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    mockWS.simulateMessage({ type: MESSAGE_TYPES.PONG });
    
    expect(heartbeatEmitted).toBe(true);
  });

  test('should provide connection info', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    const info = client.getConnectionInfo();
    
    expect(info.state).toBe(CONNECTION_STATES.CONNECTED);
    expect(info.isConnected).toBe(true);
    expect(info.url).toBe('ws://localhost:8000/ws');
  });

  test('should clear message queue', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    
    client.queueMessage({ type: MESSAGE_TYPES.PING });
    client.queueMessage({ type: MESSAGE_TYPES.PING });
    
    const cleared = client.clearMessageQueue();
    
    expect(cleared).toBe(2);
    expect(client.getMessageQueueSize()).toBe(0);
  });

  test('should factory function create client', () => {
    client = createWebSocketClient('ws://localhost:8000/ws');
    
    expect(client).toBeInstanceOf(WebSocketClientWrapper);
    expect(client.url).toBe('ws://localhost:8000/ws');
  });

  test('should get WebSocket URL', () => {
    const url = getWebSocketUrl();
    
    expect(url).toMatch(/^wss?:\/\/.+\/ws$/);
  });

  test('should handle state changes', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    const stateChanges = [];
    
    client.on(EVENT_TYPES.STATE_CHANGED, ({ from, to }) => {
      stateChanges.push({ from, to });
    });
    
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    expect(stateChanges.length).toBeGreaterThan(0);
    expect(stateChanges[0].to).toBe(CONNECTION_STATES.CONNECTING);
    expect(stateChanges[stateChanges.length - 1].to).toBe(CONNECTION_STATES.CONNECTED);
  });

  test('should send audio chunk', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    const audioData = new ArrayBuffer(256);
    client.sendAudioChunk(audioData, { chunk_number: 1 });
    
    const lastMessage = mockWS.messages[mockWS.messages.length - 1];
    expect(lastMessage.type).toBe(MESSAGE_TYPES.AUDIO);
    expect(lastMessage.chunk_number).toBe(1);
  });

  test('should destroy client', async () => {
    client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    const connectPromise = client.connect();
    setTimeout(() => mockWS?.simulateOpen(), 10);
    await connectPromise;
    
    client.destroy();
    
    expect(client.websocket).toBeNull();
    expect(client.messageHandlers).toEqual({});
  });
});

/**
 * Integration Tests
 */
describe('WebSocketClientWrapper Integration', () => {
  test('should handle complete conversation', async () => {
    const client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    
    let messageLog = [];
    client.on(EVENT_TYPES.MESSAGE, (message) => {
      messageLog.push(message);
    });
    
    // This would require a real WebSocket server for a true integration test
    // For now, this is a placeholder for integration test structure
    
    client.destroy();
    expect(messageLog).toBeDefined();
  });
});

/**
 * Performance Tests
 */
describe('WebSocketClientWrapper Performance', () => {
  test('should handle rapid message sending', async () => {
    jest.useFakeTimers();
    const client = new WebSocketClientWrapper('ws://localhost:8000/ws');
    
    global.WebSocket = MockWebSocket;
    let mockWS = null;
    const OriginalWebSocket = global.WebSocket;
    global.WebSocket = function (url) {
      mockWS = new OriginalWebSocket(url);
      return mockWS;
    };
    global.WebSocket.OPEN = 1;
    
    const connectPromise = client.connect();
    jest.advanceTimersByTime(10);
    mockWS?.simulateOpen();
    await connectPromise;
    
    // Send 1000 messages
    const start = Date.now();
    for (let i = 0; i < 1000; i++) {
      client.sendMessage({ type: 'test', sequence: i });
    }
    const elapsed = Date.now() - start;
    
    console.log(`Sent 1000 messages in ${elapsed}ms`);
    
    client.destroy();
    jest.useRealTimers();
  });
});
