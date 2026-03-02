import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

/**
 * Enroll a new voice identity
 * @param {string} phoneNumber - Unique identifier (phone number)
 * @param {Blob} audioBlob - WAV audio blob for voice enrollment
 * @returns {Promise<Object>} Enrollment result
 */
export async function enrollVoice(phoneNumber, audioBlob) {
  const formData = new FormData();
  formData.append('phone_number', phoneNumber);
  formData.append('file', audioBlob, 'voice.wav');

  const response = await api.post('/enroll', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Verify a voice against enrolled identity
 * @param {string} phoneNumber - Phone number to verify against
 * @param {Blob} audioBlob - WAV audio blob for voice verification
 * @returns {Promise<Object>} Verification result with similarity score
 */
export async function verifyVoice(phoneNumber, audioBlob) {
  const formData = new FormData();
  formData.append('phone_number', phoneNumber);
  formData.append('file', audioBlob, 'voice.wav');

  const response = await api.post('/verify', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Check if a phone number is enrolled
 * @param {string} phoneNumber - Phone number to check
 * @returns {Promise<Object>} Enrollment status
 */
export async function checkEnrollment(phoneNumber) {
  const response = await api.get(`/check/${phoneNumber}`);
  return response.data;
}

/**
 * Validate a recorded enrollment sample via Whisper STT.
 * Sends audio to backend, gets transcription, and receives fuzzy-match result.
 *
 * @param {Blob}   audioBlob    - Recorded audio blob (WAV/webm)
 * @param {string} expectedText - The phrase the user was shown
 * @param {number} sampleNumber - 1-based sample index (1–5)
 * @returns {Promise<{matched: boolean, transcription: string, similarity: number, sample_number: number}>}
 */
export async function validateEnrollmentSample(audioBlob, expectedText, sampleNumber) {
  const formData = new FormData();
  formData.append('file', audioBlob, 'sample.wav');
  formData.append('expected_text', expectedText);
  formData.append('sample_number', String(sampleNumber));

  const response = await api.post('/enrollment/validate-sample', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  });
  return response.data;
}

export default api;
