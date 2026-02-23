/**
 * WAV File Encoder
 * Encodes raw PCM audio samples into proper WAV format with RIFF headers
 */

/**
 * Encode raw audio samples to WAV format
 * @param {Float32Array|Int16Array|number[]} samples - Audio samples
 * @param {number} sampleRate - Sample rate (e.g., 16000)
 * @returns {Blob} WAV file as Blob
 */
export function encodeWAV(samples, sampleRate = 16000) {
  // Convert Float32Array to Int16Array if needed
  let int16Samples;
  if (samples instanceof Float32Array) {
    int16Samples = new Int16Array(samples.length);
    for (let i = 0; i < samples.length; i++) {
      // Convert float [-1, 1] to int16 [-32768, 32767]
      const sample = Math.max(-1, Math.min(1, samples[i]));
      int16Samples[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    }
  } else if (samples instanceof Int16Array) {
    int16Samples = samples;
  } else {
    int16Samples = new Int16Array(samples);
  }

  const numChannels = 1; // mono
  const sampleBits = 16;
  const byteRate = (sampleRate * numChannels * sampleBits) / 8;
  const blockAlign = (numChannels * sampleBits) / 8;

  // Calculate sizes
  const dataLength = int16Samples.byteLength;
  const fileLength = 36 + dataLength;

  // Create buffer for WAV file
  const wavBuffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(wavBuffer);

  // Write RIFF header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, fileLength, true); // file length
  writeString(view, 8, 'WAVE');

  // Write fmt subchunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // subchunk size
  view.setUint16(20, 1, true); // audio format (PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, sampleBits, true);

  // Write data subchunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataLength, true);

  // Copy PCM data
  const pcmView = new Int16Array(wavBuffer, 44);
  pcmView.set(int16Samples);

  // Create Blob
  return new Blob([wavBuffer], { type: 'audio/wav' });
}

/**
 * Helper to write ASCII string to DataView
 */
function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

/**
 * Create WAV Blob from audio samples
 * @param {Float32Array} samples - Audio samples as float
 * @param {number} sampleRate - Sample rate
 * @returns {Promise<Blob>} WAV file as blob
 */
export async function createWAVBlob(samples, sampleRate = 16000) {
  return new Promise((resolve) => {
    const wavBlob = encodeWAV(samples, sampleRate);
    resolve(wavBlob);
  });
}
