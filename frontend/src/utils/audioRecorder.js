/**
 * Browser-Side Audio Downsampling Utility
 * Forces microphone input to 16,000 Hz, mono channel
 * Exports as WAV blob for ECAPA-TDNN compatibility
 */

const TARGET_SAMPLE_RATE = 16000;
const NUM_CHANNELS = 1;

/**
 * Creates an audio recorder with downsampling to 16kHz mono
 * @returns {Object} Recorder controller with start, stop, and getBlob methods
 */
export function createAudioRecorder() {
  let mediaStream = null;
  let audioContext = null;
  let scriptProcessor = null;
  let recordedChunks = [];
  let isRecording = false;

  const start = async () => {
    try {
      // Request microphone access with high quality settings
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: { ideal: 48000 },
          channelCount: { exact: 1 },
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      // Create audio context
      audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: mediaStream.getAudioTracks()[0].getSettings().sampleRate || 48000,
      });

      const source = audioContext.createMediaStreamSource(mediaStream);
      
      // Use ScriptProcessorNode for raw PCM access
      // Buffer size of 4096 provides good balance between latency and performance
      scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
      
      recordedChunks = [];
      isRecording = true;

      scriptProcessor.onaudioprocess = (event) => {
        if (!isRecording) return;
        
        const inputData = event.inputBuffer.getChannelData(0);
        // Store a copy of the audio data
        recordedChunks.push(new Float32Array(inputData));
      };

      source.connect(scriptProcessor);
      scriptProcessor.connect(audioContext.destination);

      return true;
    } catch (error) {
      console.error('Failed to start recording:', error);
      throw error;
    }
  };

  const stop = async () => {
    isRecording = false;

    if (scriptProcessor) {
      scriptProcessor.disconnect();
      scriptProcessor = null;
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }

    if (recordedChunks.length === 0) {
      return null;
    }

    // Calculate total length
    const totalLength = recordedChunks.reduce((acc, chunk) => acc + chunk.length, 0);
    const mergedAudio = new Float32Array(totalLength);

    let offset = 0;
    for (const chunk of recordedChunks) {
      mergedAudio.set(chunk, offset);
      offset += chunk.length;
    }

    // Downsample to 16kHz
    const sourceSampleRate = audioContext.sampleRate;
    const downsampledAudio = downsample(mergedAudio, sourceSampleRate, TARGET_SAMPLE_RATE);

    // Close audio context
    if (audioContext) {
      await audioContext.close();
      audioContext = null;
    }

    // Convert to WAV blob
    const wavBlob = encodeWAV(downsampledAudio, TARGET_SAMPLE_RATE);
    
    recordedChunks = [];
    return wavBlob;
  };

  const getIsRecording = () => isRecording;

  return { start, stop, getIsRecording };
}

/**
 * Downsamples audio data from source rate to target rate
 * Uses linear interpolation for quality
 */
function downsample(audioData, sourceSampleRate, targetSampleRate) {
  if (sourceSampleRate === targetSampleRate) {
    return audioData;
  }

  const ratio = sourceSampleRate / targetSampleRate;
  const newLength = Math.round(audioData.length / ratio);
  const result = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const srcIndex = i * ratio;
    const srcIndexFloor = Math.floor(srcIndex);
    const srcIndexCeil = Math.min(srcIndexFloor + 1, audioData.length - 1);
    const fraction = srcIndex - srcIndexFloor;

    // Linear interpolation
    result[i] = audioData[srcIndexFloor] * (1 - fraction) + audioData[srcIndexCeil] * fraction;
  }

  return result;
}

/**
 * Encodes Float32Array audio data to WAV format
 * Standard 16-bit PCM WAV format
 */
function encodeWAV(samples, sampleRate) {
  const numChannels = NUM_CHANNELS;
  const bitsPerSample = 16;
  const blockAlign = numChannels * (bitsPerSample / 8);
  const byteRate = sampleRate * blockAlign;
  const dataLength = samples.length * (bitsPerSample / 8);
  
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);

  // RIFF chunk descriptor
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataLength, true);
  writeString(view, 8, 'WAVE');

  // fmt sub-chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
  view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);

  // data sub-chunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataLength, true);

  // Write audio data - convert float to 16-bit PCM
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    // Clamp to [-1, 1] and convert to 16-bit
    const sample = Math.max(-1, Math.min(1, samples[i]));
    const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    view.setInt16(offset, intSample, true);
    offset += 2;
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

/**
 * Writes a string to a DataView at the specified offset
 */
function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

/**
 * Calculates the duration of recorded audio in seconds
 */
export function calculateDuration(blob) {
  return new Promise((resolve) => {
    const audio = new Audio(URL.createObjectURL(blob));
    audio.addEventListener('loadedmetadata', () => {
      resolve(audio.duration);
    });
    audio.addEventListener('error', () => {
      resolve(0);
    });
  });
}
