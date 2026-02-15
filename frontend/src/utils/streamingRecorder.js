/**
 * Audio Streaming Integration
 * Combines audio recording and WebSocket streaming for real-time voice processing
 */

import { createAudioRecorder } from './audioRecorder';
import { createWebSocketClient, getWebSocketUrl } from '../services/websocketClient';

/**
 * Create an integrated streaming recorder with WebSocket support
 * @param {Object} options - Configuration options
 * @returns {Object} Streaming recorder controller
 */
export function createStreamingRecorder(options = {}) {
  let recorder = null;
  let wsClient = null;
  let intentionalStop = false;

  const initialize = async () => {
    try {
      // Create WebSocket client
      const wsUrl = options.websocketUrl || getWebSocketUrl();
      wsClient = createWebSocketClient(wsUrl, {
        onOpen: () => {
          console.log('WebSocket connected for audio streaming');
          if (options.onWSOpen) options.onWSOpen();
        },
        onClose: () => {
          console.log('WebSocket disconnected');
          if (options.onWSClose) options.onWSClose();
        },
        onError: (error) => {
          console.error('WebSocket error:', error);
          if (options.onWSError) options.onWSError(error);
        },
        onMessage: (message) => {
          handleWSMessage(message);
        }
      });

      // Setup message handlers
      wsClient.on('verification_result', (msg) => {
        console.log('Verification result:', msg);
        if (options.onVerificationResult) {
          options.onVerificationResult(msg.data);
        }
      });

      wsClient.on('enrollment_result', (msg) => {
        console.log('Enrollment result:', msg);
        if (options.onEnrollmentResult) {
          options.onEnrollmentResult(msg.data);
        }
      });

      wsClient.on('error', (msg) => {
        console.error('Server error:', msg);
        if (options.onServerError) {
          options.onServerError(msg);
        }
      });

      // Connect WebSocket
      await wsClient.connect();

      // Create audio recorder with WebSocket streaming
      recorder = createAudioRecorder({
        websocket: wsClient.websocket,
        onChunkSent: (info) => {
          if (options.onChunkStreamed) {
            options.onChunkStreamed(info);
          }
        },
        onError: (error) => {
          console.error('Audio recording error:', error);
          if (options.onAudioError) {
            options.onAudioError(error);
          }
        }
      });

      console.log('Streaming recorder initialized');
      return true;
    } catch (error) {
      console.error('Failed to initialize streaming recorder:', error);
      throw error;
    }
  };

  const handleWSMessage = (message) => {
    const { type } = message;
    console.log('WebSocket message received:', type);

    // Message type handlers are registered via wsClient.on()
  };

  const startRecording = async () => {
    try {
      intentionalStop = false;
      await recorder.start();
      console.log('Recording started');
      return true;
    } catch (error) {
      console.error('Failed to start recording:', error);
      throw error;
    }
  };

  const stopRecording = async () => {
    try {
      intentionalStop = true;

      // Get the final audio blob
      const audioBlob = await recorder.stop();

      // Notify server that streaming is complete
      recorder.notifyStreamComplete();

      console.log('Recording stopped');
      return audioBlob;
    } catch (error) {
      console.error('Failed to stop recording:', error);
      throw error;
    }
  };

  const verifyVoice = (phoneNumber) => {
    try {
      if (!wsClient.isConnected()) {
        throw new Error('WebSocket not connected');
      }
      wsClient.sendVerification(phoneNumber);
      console.log('Verification request sent for:', phoneNumber);
    } catch (error) {
      console.error('Failed to send verification:', error);
      throw error;
    }
  };

  const enrollVoice = (phoneNumber) => {
    try {
      if (!wsClient.isConnected()) {
        throw new Error('WebSocket not connected');
      }
      wsClient.sendEnrollment(phoneNumber);
      console.log('Enrollment request sent for:', phoneNumber);
    } catch (error) {
      console.error('Failed to send enrollment:', error);
      throw error;
    }
  };

  const resetBuffer = () => {
    try {
      if (!wsClient.isConnected()) {
        throw new Error('WebSocket not connected');
      }
      wsClient.sendReset();
      console.log('Audio buffer reset sent');
    } catch (error) {
      console.error('Failed to reset buffer:', error);
      throw error;
    }
  };

  const getStats = () => {
    if (!recorder) {
      return null;
    }

    const recorderStats = recorder.getStreamStats();
    return {
      ...recorderStats,
      websocketState: wsClient.getState(),
      websocketConnected: wsClient.isConnected()
    };
  };

  const disconnect = () => {
    try {
      if (recorder && recorder.getIsRecording()) {
        recorder.stop();
      }

      if (wsClient) {
        wsClient.disconnect();
      }

      console.log('Streaming recorder disconnected');
    } catch (error) {
      console.error('Error during disconnect:', error);
    }
  };

  const isRecording = () => {
    return recorder && recorder.getIsRecording();
  };

  const isConnected = () => {
    return wsClient && wsClient.isConnected();
  };

  return {
    initialize,
    startRecording,
    stopRecording,
    verifyVoice,
    enrollVoice,
    resetBuffer,
    getStats,
    disconnect,
    isRecording,
    isConnected,
    // Direct access to underlying objects for advanced use
    get recorder() {
      return recorder;
    },
    get wsClient() {
      return wsClient;
    }
  };
}

export default createStreamingRecorder;
