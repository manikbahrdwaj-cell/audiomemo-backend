/**
 * WebSocket Client Usage Examples
 * Demonstrates how to use the WebSocket client wrapper in different scenarios
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  useWebSocket,
  useWebSocketMessage,
  useWebSocketEvent,
  useSendWebSocketMessage,
  useSendWebSocketRequest,
  useSendAudioChunk,
  useSendVerification,
  useSendEnrollment
} from '../services/useWebSocket';
import { MESSAGE_TYPES, EVENT_TYPES, CONNECTION_STATES } from '../services/webSocketConstants';

/**
 * Example 1: Basic WebSocket Connection
 * Simple component that connects and displays connection status
 */
export function BasicWebSocketExample() {
  const { client, isConnected, state, error } = useWebSocket();

  return (
    <div>
      <h2>WebSocket Connection Status</h2>
      <p>Connected: {isConnected ? 'Yes' : 'No'}</p>
      <p>State: {state}</p>
      {error && <p style={{ color: 'red' }}>Error: {error.message}</p>}
      <button onClick={() => client?.disconnect()}>Disconnect</button>
      <button onClick={() => client?.connect()}>Reconnect</button>
    </div>
  );
}

/**
 * Example 2: Sending Messages
 * Component that sends different types of messages
 */
export function SendMessagesExample() {
  const { client, isConnected } = useWebSocket();
  const sendMessage = useSendWebSocketMessage(client);
  const sendRequest = useSendWebSocketRequest(client);

  const handleSendMessage = () => {
    const message = {
      type: MESSAGE_TYPES.STATUS,
      timestamp: Date.now()
    };
    sendMessage(message);
  };

  const handleSendRequest = async () => {
    try {
      const response = await sendRequest({
        type: MESSAGE_TYPES.CONFIG,
        action: 'get'
      });
      console.log('Received response:', response);
    } catch (error) {
      console.error('Request failed:', error);
    }
  };

  return (
    <div>
      <h2>Send Messages</h2>
      <button onClick={handleSendMessage} disabled={!isConnected}>
        Send Message
      </button>
      <button onClick={handleSendRequest} disabled={!isConnected}>
        Send Request
      </button>
    </div>
  );
}

/**
 * Example 3: Audio Streaming
 * Component that handles audio streaming via WebSocket
 */
export function AudioStreamingExample() {
  const { client, isConnected } = useWebSocket();
  const sendAudioChunk = useSendAudioChunk(client);
  const [isStreaming, setIsStreaming] = useState(false);

  const simulateAudioStream = useCallback(async () => {
    setIsStreaming(true);
    try {
      // Simulate audio chunks
      for (let i = 0; i < 5; i++) {
        const audioData = new ArrayBuffer(4096);
        sendAudioChunk(audioData, {
          chunk_number: i,
          final: i === 4
        });
        // Wait between chunks
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    } finally {
      setIsStreaming(false);
    }
  }, [sendAudioChunk]);

  return (
    <div>
      <h2>Audio Streaming</h2>
      <button
        onClick={simulateAudioStream}
        disabled={!isConnected || isStreaming}
      >
        {isStreaming ? 'Streaming...' : 'Start Stream'}
      </button>
    </div>
  );
}

/**
 * Example 4: Voice Verification
 * Component for voice verification flow
 */
export function VoiceVerificationExample() {
  const { client, isConnected } = useWebSocket();
  const [phoneNumber, setPhoneNumber] = useState('');
  const [verificationResult, setVerificationResult] = useState(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const sendVerification = useSendVerification(client);

  // Listen for verification responses
  useWebSocketMessage(client, MESSAGE_TYPES.RESPONSE, (message) => {
    if (message.action === 'verify') {
      setVerificationResult(message);
    }
  });

  const handleVerify = async () => {
    setIsVerifying(true);
    try {
      const result = await sendVerification(phoneNumber);
      setVerificationResult(result);
    } catch (error) {
      setVerificationResult({ error: error.message });
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div>
      <h2>Voice Verification</h2>
      <input
        type="text"
        placeholder="Phone number"
        value={phoneNumber}
        onChange={(e) => setPhoneNumber(e.target.value)}
      />
      <button
        onClick={handleVerify}
        disabled={!isConnected || isVerifying || !phoneNumber}
      >
        {isVerifying ? 'Verifying...' : 'Verify'}
      </button>
      {verificationResult && (
        <pre>{JSON.stringify(verificationResult, null, 2)}</pre>
      )}
    </div>
  );
}

/**
 * Example 5: Voice Enrollment
 * Component for voice enrollment flow
 */
export function VoiceEnrollmentExample() {
  const { client, isConnected } = useWebSocket();
  const [phoneNumber, setPhoneNumber] = useState('');
  const [enrollmentStatus, setEnrollmentStatus] = useState(null);
  const [isEnrolling, setIsEnrolling] = useState(false);
  const sendEnrollment = useSendEnrollment(client);

  // Listen for enrollment status updates
  useWebSocketMessage(client, MESSAGE_TYPES.ENROLLMENT_STATUS, (message) => {
    setEnrollmentStatus(message);
  });

  const handleEnroll = async () => {
    setIsEnrolling(true);
    try {
      const result = await sendEnrollment(phoneNumber);
      setEnrollmentStatus(result);
    } catch (error) {
      setEnrollmentStatus({ error: error.message });
    } finally {
      setIsEnrolling(false);
    }
  };

  return (
    <div>
      <h2>Voice Enrollment</h2>
      <input
        type="text"
        placeholder="Phone number"
        value={phoneNumber}
        onChange={(e) => setPhoneNumber(e.target.value)}
      />
      <button
        onClick={handleEnroll}
        disabled={!isConnected || isEnrolling || !phoneNumber}
      >
        {isEnrolling ? 'Enrolling...' : 'Enroll'}
      </button>
      {enrollmentStatus && (
        <pre>{JSON.stringify(enrollmentStatus, null, 2)}</pre>
      )}
    </div>
  );
}

/**
 * Example 6: Event Monitoring
 * Component that monitors various WebSocket events
 */
export function EventMonitoringExample() {
  const { client, isConnected, state, messageQueueSize } = useWebSocket();
  const [events, setEvents] = useState([]);

  useWebSocketEvent(client, EVENT_TYPES.CONNECTED, () => {
    setEvents(e => [...e, { type: 'CONNECTED', time: new Date() }]);
  });

  useWebSocketEvent(client, EVENT_TYPES.DISCONNECTED, () => {
    setEvents(e => [...e, { type: 'DISCONNECTED', time: new Date() }]);
  });

  useWebSocketEvent(client, EVENT_TYPES.ERROR, (error) => {
    setEvents(e => [...e, { type: 'ERROR', error: error.message, time: new Date() }]);
  });

  useWebSocketEvent(client, EVENT_TYPES.MESSAGE_SENT, (message) => {
    setEvents(e => [...e, { type: 'MESSAGE_SENT', messageType: message.type, time: new Date() }]);
  });

  useWebSocketEvent(client, EVENT_TYPES.RECONNECT_ATTEMPT, (data) => {
    setEvents(e => [...e, { type: 'RECONNECT_ATTEMPT', attempt: data.attempt, time: new Date() }]);
  });

  return (
    <div>
      <h2>Event Monitor</h2>
      <div style={{ marginBottom: '10px' }}>
        <p>Connected: {isConnected ? 'Yes' : 'No'}</p>
        <p>State: {state}</p>
        <p>Queued Messages: {messageQueueSize}</p>
      </div>
      <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #ccc', padding: '10px' }}>
        {events.map((event, i) => (
          <div key={i} style={{ fontSize: '12px', marginBottom: '5px' }}>
            [{event.time.toLocaleTimeString()}] {event.type}
            {event.error && ` - ${event.error}`}
            {event.attempt && ` (attempt ${event.attempt})`}
            {event.messageType && ` (${event.messageType})`}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Example 7: Complete Application
 * Full-featured component combining multiple examples
 */
export function CompleteWebSocketApplication() {
  const { client, isConnected, state, error, messageQueueSize } = useWebSocket();
  const [activeTab, setActiveTab] = useState('status');

  const tabs = {
    status: <BasicWebSocketExample />,
    send: <SendMessagesExample />,
    audio: <AudioStreamingExample />,
    verify: <VoiceVerificationExample />,
    enroll: <VoiceEnrollmentExample />,
    events: <EventMonitoringExample />
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>WebSocket Client Demo</h1>

      <div style={{ marginBottom: '20px', padding: '10px', backgroundColor: '#f0f0f0', borderRadius: '5px' }}>
        <h3>Connection Status</h3>
        <p>Connected: {isConnected ? '✓' : '✗'}</p>
        <p>State: {state}</p>
        <p>Queued: {messageQueueSize}</p>
        {error && <p style={{ color: 'red' }}>Error: {error.message}</p>}
      </div>

      <div style={{ marginBottom: '20px' }}>
        {Object.keys(tabs).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              marginRight: '10px',
              padding: '8px 16px',
              backgroundColor: activeTab === tab ? '#007bff' : '#ddd',
              color: activeTab === tab ? 'white' : 'black',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '5px' }}>
        {tabs[activeTab]}
      </div>
    </div>
  );
}

export default CompleteWebSocketApplication;
