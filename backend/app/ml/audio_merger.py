"""
Audio merging and concatenation utilities.
"""

import numpy as np
import torch
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from app.ml.embedding import preprocess_audio

logger = logging.getLogger(__name__)


class MergeMode(Enum):
    """Audio merging modes"""
    CONCATENATE = "concatenate"  # Direct concatenation
    OVERLAP = "overlap"  # With overlapping regions
    CROSSFADE = "crossfade"  # Smooth crossfading between segments
    MIX = "mix"  # Mix audio (weighted sum)


@dataclass
class AudioMergeConfig:
    """Configuration for audio merging operations"""
    mode: MergeMode = MergeMode.CONCATENATE
    sample_rate: int = 16000
    crossfade_duration_ms: float = 100.0  # Duration of crossfade in milliseconds
    overlap_duration_ms: float = 100.0  # Duration of overlap in milliseconds
    crossfade_shape: str = "linear"  # "linear", "exponential", "logarithmic"
    normalize_segments: bool = True  # Normalize each segment before merging
    silence_between_ms: float = 0.0  # Add silence between segments
    pad_missing_sample_rate: bool = True  # Try to resample if needed
    
    def __post_init__(self):
        """Validate configuration"""
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.crossfade_duration_ms < 0:
            raise ValueError("crossfade_duration_ms must be non-negative")
        if self.overlap_duration_ms < 0:
            raise ValueError("overlap_duration_ms must be non-negative")
        if self.crossfade_shape not in ["linear", "exponential", "logarithmic"]:
            raise ValueError(f"Unknown crossfade_shape: {self.crossfade_shape}")
        if self.silence_between_ms < 0:
            raise ValueError("silence_between_ms must be non-negative")


class AudioMerger:
    """
    Advanced audio merging and concatenation with multiple strategies
    
    Features:
    - Multiple merge modes (concatenate, overlap, crossfade, mix)
    - Sample rate handling and resampling
    - Crossfading with different shapes
    - Silence insertion
    - Normalization
    - Quality preservation
    """
    
    def __init__(self, config: Optional[AudioMergeConfig] = None):
        """
        Initialize AudioMerger
        
        Args:
            config: AudioMergeConfig object with merge parameters
        """
        self.config = config or AudioMergeConfig()
        logger.info(f"Initialized AudioMerger with mode={self.config.mode.value}")
    
    @staticmethod
    def _get_sample_rate_from_bytes(audio_bytes: bytes) -> Optional[int]:
        """
        Extract sample rate from audio bytes
        
        Args:
            audio_bytes: Audio file bytes
            
        Returns:
            Sample rate in Hz or None if unable to determine
        """
        try:
            audio_tensor, sample_rate = preprocess_audio(audio_bytes)
            return sample_rate
        except Exception as e:
            logger.warning(f"Could not determine sample rate from audio bytes: {e}")
            return None
    
    @staticmethod
    def _resample_audio(
        audio: np.ndarray,
        orig_sample_rate: int,
        target_sample_rate: int
    ) -> np.ndarray:
        """
        Resample audio to target sample rate
        
        Args:
            audio: Audio waveform
            orig_sample_rate: Original sample rate
            target_sample_rate: Target sample rate
            
        Returns:
            Resampled audio
        """
        if orig_sample_rate == target_sample_rate:
            return audio
        
        # Calculate resampling ratio
        ratio = target_sample_rate / orig_sample_rate
        new_length = int(len(audio) * ratio)
        
        # Simple linear interpolation for resampling
        old_indices = np.arange(len(audio))
        new_indices = np.linspace(0, len(audio) - 1, new_length)
        resampled = np.interp(new_indices, old_indices, audio)
        
        logger.debug(
            f"Resampled audio from {orig_sample_rate}Hz to {target_sample_rate}Hz "
            f"({len(audio)} -> {len(resampled)} samples)"
        )
        
        return resampled
    
    @staticmethod
    def _create_crossfade_envelope(
        length: int,
        shape: str = "linear"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create crossfade envelopes (fade out, fade in)
        
        Args:
            length: Length of fade in samples
            shape: Fade shape ('linear', 'exponential', 'logarithmic')
            
        Returns:
            Tuple of (fade_out, fade_in) arrays
        """
        if shape == "linear":
            fade_out = np.linspace(1.0, 0.0, length)
            fade_in = np.linspace(0.0, 1.0, length)
        
        elif shape == "exponential":
            # Exponential curve (e^(-x) style)
            x = np.linspace(0, 5, length)
            fade_out = np.exp(-x) * np.exp(-0)  # Normalize
            fade_in = 1.0 - fade_out
        
        elif shape == "logarithmic":
            # Logarithmic curve
            fade_out = np.log(np.linspace(np.e, 1, length))
            fade_in = 1.0 - fade_out
        
        else:
            logger.warning(f"Unknown shape '{shape}', using linear")
            fade_out = np.linspace(1.0, 0.0, length)
            fade_in = np.linspace(0.0, 1.0, length)
        
        # Normalize to [0, 1]
        fade_out = np.clip(fade_out, 0, 1)
        fade_in = np.clip(fade_in, 0, 1)
        
        return fade_out, fade_in
    
    def merge_audio_segments(
        self,
        audio_segments: List[Union[np.ndarray, bytes]],
        sample_rates: Optional[List[int]] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Merge multiple audio segments according to configured mode
        
        Args:
            audio_segments: List of audio arrays or bytes
            sample_rates: List of sample rates (auto-detected if None)
            
        Returns:
            Tuple of (merged_audio, sample_rate)
            
        Raises:
            ValueError: If segments list is empty or invalid
        """
        if not audio_segments:
            raise ValueError("audio_segments cannot be empty")
        
        if len(audio_segments) == 1:
            if isinstance(audio_segments[0], bytes):
                audio, sr = preprocess_audio(audio_segments[0])
                return audio.numpy(), sr
            return audio_segments[0], self.config.sample_rate
        
        logger.info(
            f"Merging {len(audio_segments)} audio segments "
            f"(mode={self.config.mode.value}, sample_rate={self.config.sample_rate})"
        )
        
        # Convert all segments to numpy arrays and handle sample rates
        audio_arrays = []
        segment_sample_rates = []
        
        for idx, segment in enumerate(audio_segments):
            if isinstance(segment, bytes):
                audio_tensor, sr = preprocess_audio(segment)
                audio = audio_tensor.numpy()
                segment_sr = sr
            else:
                audio = segment
                segment_sr = sample_rates[idx] if sample_rates else self.config.sample_rate
            
            # Resample if needed
            if segment_sr != self.config.sample_rate:
                if self.config.pad_missing_sample_rate:
                    audio = self._resample_audio(audio, segment_sr, self.config.sample_rate)
                    segment_sr = self.config.sample_rate
                else:
                    logger.warning(
                        f"Segment {idx} has sample rate {segment_sr}, "
                        f"expected {self.config.sample_rate}"
                    )
            
            # Normalize segment if configured
            if self.config.normalize_segments:
                max_val = np.max(np.abs(audio))
                if max_val > 0:
                    audio = audio / max_val
            
            audio_arrays.append(audio)
            segment_sample_rates.append(segment_sr)
        
        # Merge based on mode
        if self.config.mode == MergeMode.CONCATENATE:
            merged = self._concatenate(audio_arrays)
        
        elif self.config.mode == MergeMode.OVERLAP:
            merged = self._merge_with_overlap(audio_arrays)
        
        elif self.config.mode == MergeMode.CROSSFADE:
            merged = self._merge_with_crossfade(audio_arrays)
        
        elif self.config.mode == MergeMode.MIX:
            merged = self._merge_with_mix(audio_arrays)
        
        else:
            raise ValueError(f"Unknown merge mode: {self.config.mode}")
        
        # Normalize final output
        max_val = np.max(np.abs(merged))
        if max_val > 1.0:
            merged = merged / (max_val * 1.05)  # 5% safety margin
        
        logger.info(
            f"✓ Merged {len(audio_arrays)} segments into {len(merged)} samples "
            f"(duration: {len(merged) / self.config.sample_rate:.2f}s)"
        )
        
        return merged, self.config.sample_rate
    
    def _concatenate(self, audio_arrays: List[np.ndarray]) -> np.ndarray:
        """
        Simple concatenation of audio segments
        
        Args:
            audio_arrays: List of audio arrays
            
        Returns:
            Concatenated audio
        """
        parts = []
        
        for idx, audio in enumerate(audio_arrays):
            parts.append(audio)
            
            # Add silence between segments if configured
            if self.config.silence_between_ms > 0 and idx < len(audio_arrays) - 1:
                silence_samples = int(
                    self.config.silence_between_ms * self.config.sample_rate / 1000
                )
                silence = np.zeros(silence_samples)
                parts.append(silence)
        
        merged = np.concatenate(parts)
        logger.debug(f"Concatenated {len(audio_arrays)} segments")
        
        return merged
    
    def _merge_with_overlap(self, audio_arrays: List[np.ndarray]) -> np.ndarray:
        """
        Merge audio segments with overlap (simple averaging in overlap region)
        
        Args:
            audio_arrays: List of audio arrays
            
        Returns:
            Merged audio with overlapping regions
        """
        overlap_samples = int(
            self.config.overlap_duration_ms * self.config.sample_rate / 1000
        )
        
        if overlap_samples == 0:
            return self._concatenate(audio_arrays)
        
        # Calculate output length
        output_length = len(audio_arrays[0])
        for audio in audio_arrays[1:]:
            output_length += len(audio) - overlap_samples
        
        merged = np.zeros(output_length)
        position = 0
        
        for idx, audio in enumerate(audio_arrays):
            if idx == 0:
                # First segment - copy as is
                merged[position:position + len(audio)] = audio
                position += len(audio)
            else:
                # Overlapping regions - average
                overlap_start = position - overlap_samples
                
                # Average in overlap region
                for i in range(overlap_samples):
                    if overlap_start + i < len(merged):
                        merged[overlap_start + i] = (
                            merged[overlap_start + i] + audio[i]
                        ) / 2.0
                
                # Copy rest of segment
                remaining = len(audio) - overlap_samples
                if remaining > 0:
                    start_pos = overlap_start + overlap_samples
                    merged[start_pos:start_pos + remaining] = audio[overlap_samples:]
                    position = start_pos + remaining
        
        logger.debug(f"Merged {len(audio_arrays)} segments with {overlap_samples} sample overlap")
        
        return merged
    
    def _merge_with_crossfade(self, audio_arrays: List[np.ndarray]) -> np.ndarray:
        """
        Merge audio segments with smooth crossfading
        
        Args:
            audio_arrays: List of audio arrays
            
        Returns:
            Merged audio with crossfades between segments
        """
        crossfade_samples = int(
            self.config.crossfade_duration_ms * self.config.sample_rate / 1000
        )
        
        if crossfade_samples == 0:
            return self._concatenate(audio_arrays)
        
        # Build output
        parts = []
        
        for idx, audio in enumerate(audio_arrays):
            if idx == 0:
                # First segment - include full segment
                parts.append(audio)
            else:
                # Get previous segment
                prev_audio = audio_arrays[idx - 1]
                
                # Get crossfade envelopes
                fade_out, fade_in = self._create_crossfade_envelope(
                    crossfade_samples,
                    self.config.crossfade_shape
                )
                
                # Extract regions to crossfade
                prev_end_start = max(0, len(prev_audio) - crossfade_samples)
                prev_fade_region = prev_audio[prev_end_start:]
                
                # Pad if needed
                if len(prev_fade_region) < crossfade_samples:
                    prev_fade_region = np.pad(
                        prev_fade_region,
                        (crossfade_samples - len(prev_fade_region), 0),
                        mode='edge'
                    )
                
                curr_fade_region = audio[:min(len(audio), crossfade_samples)]
                
                # Pad if needed
                if len(curr_fade_region) < crossfade_samples:
                    curr_fade_region = np.pad(
                        curr_fade_region,
                        (0, crossfade_samples - len(curr_fade_region)),
                        mode='edge'
                    )
                
                # Apply crossfade
                crossfaded = (
                    prev_fade_region[:crossfade_samples] * fade_out +
                    curr_fade_region[:crossfade_samples] * fade_in
                )
                
                # Remove the fade region from previous segment
                prev_without_fade = prev_audio[:prev_end_start]
                if len(prev_without_fade) > 0:
                    parts[-1] = prev_without_fade
                
                # Add crossfaded region
                parts.append(crossfaded)
                
                # Add remainder of current segment
                if len(audio) > crossfade_samples:
                    parts.append(audio[crossfade_samples:])
        
        merged = np.concatenate(parts)
        logger.debug(
            f"Merged {len(audio_arrays)} segments with {crossfade_samples} sample crossfade "
            f"({self.config.crossfade_shape})"
        )
        
        return merged
    
    def _merge_with_mix(self, audio_arrays: List[np.ndarray]) -> np.ndarray:
        """
        Merge audio segments by mixing (weighted sum)
        
        Args:
            audio_arrays: List of audio arrays
            
        Returns:
            Mixed audio
        """
        # Use maximum length for output
        max_length = max(len(audio) for audio in audio_arrays)
        mixed = np.zeros(max_length)
        
        # Equal weighting for all segments
        weight = 1.0 / len(audio_arrays)
        
        for audio in audio_arrays:
            # Pad audio to max length if needed
            if len(audio) < max_length:
                audio = np.pad(audio, (0, max_length - len(audio)), mode='constant')
            
            mixed += audio * weight
        
        logger.debug(f"Mixed {len(audio_arrays)} segments with equal weight ({weight:.3f})")
        
        return mixed
    
    def merge_from_files(
        self,
        file_paths: List[str]
    ) -> Tuple[np.ndarray, int]:
        """
        Merge audio from multiple files
        
        Args:
            file_paths: List of paths to audio files
            
        Returns:
            Tuple of (merged_audio, sample_rate)
        """
        audio_segments = []
        
        for file_path in file_paths:
            try:
                with open(file_path, 'rb') as f:
                    audio_bytes = f.read()
                audio_segments.append(audio_bytes)
                logger.debug(f"Loaded audio from {file_path}")
            except Exception as e:
                logger.error(f"Failed to load audio from {file_path}: {e}")
                raise
        
        return self.merge_audio_segments(audio_segments)
    
    def save_merged_audio(
        self,
        audio: np.ndarray,
        sample_rate: int,
        output_path: str,
        format: str = "wav"
    ) -> None:
        """
        Save merged audio to file
        
        Args:
            audio: Audio waveform
            sample_rate: Sample rate
            output_path: Path to save file
            format: Audio format ('wav', 'mp3', 'flac')
        """
        try:
            import torchaudio
            
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio).float()
            if audio_tensor.ndim == 1:
                audio_tensor = audio_tensor.unsqueeze(0)
            
            # Save
            torchaudio.save(output_path, audio_tensor, sample_rate)
            logger.info(f"✓ Saved merged audio to {output_path} ({format})")
            
        except Exception as e:
            logger.error(f"Failed to save audio to {output_path}: {e}")
            raise
    
    def get_merge_stats(self, audio_arrays: List[np.ndarray]) -> Dict[str, any]:
        """
        Get statistics about audio segments before merging
        
        Args:
            audio_arrays: List of audio arrays
            
        Returns:
            Dictionary with statistics
        """
        total_samples = sum(len(audio) for audio in audio_arrays)
        duration_s = total_samples / self.config.sample_rate
        
        return {
            "num_segments": len(audio_arrays),
            "total_samples": total_samples,
            "duration_seconds": duration_s,
            "sample_rate": self.config.sample_rate,
            "merge_mode": self.config.mode.value,
            "segment_lengths": [len(audio) for audio in audio_arrays],
            "segment_durations_s": [len(audio) / self.config.sample_rate for audio in audio_arrays]
        }


def merge_audio(
    audio_segments: List[Union[np.ndarray, bytes]],
    mode: str = "concatenate",
    sample_rate: int = 16000,
    crossfade_ms: float = 100.0
) -> Tuple[np.ndarray, int]:
    """
    Convenience function to merge multiple audio segments
    
    Args:
        audio_segments: List of audio arrays or bytes
        mode: Merge mode ('concatenate', 'overlap', 'crossfade', 'mix')
        sample_rate: Sample rate in Hz
        crossfade_ms: Crossfade duration in milliseconds (for crossfade mode)
        
    Returns:
        Tuple of (merged_audio, sample_rate)
        
    Example:
        >>> audio1 = np.random.randn(16000)
        >>> audio2 = np.random.randn(16000)
        >>> merged, sr = merge_audio([audio1, audio2], mode='crossfade')
        >>> print(f"Merged audio duration: {len(merged) / sr:.2f}s")
    """
    try:
        merge_mode = MergeMode(mode)
    except ValueError:
        raise ValueError(
            f"Invalid mode '{mode}'. Must be one of: "
            f"{', '.join([m.value for m in MergeMode])}"
        )
    
    config = AudioMergeConfig(
        mode=merge_mode,
        sample_rate=sample_rate,
        crossfade_duration_ms=crossfade_ms
    )
    
    merger = AudioMerger(config)
    return merger.merge_audio_segments(audio_segments)


def merge_audio_files(
    file_paths: List[str],
    mode: str = "concatenate",
    sample_rate: int = 16000,
    crossfade_ms: float = 100.0,
    output_path: Optional[str] = None
) -> Tuple[np.ndarray, int]:
    """
    Merge audio from multiple files
    
    Args:
        file_paths: List of paths to audio files
        mode: Merge mode ('concatenate', 'overlap', 'crossfade', 'mix')
        sample_rate: Target sample rate
        crossfade_ms: Crossfade duration in milliseconds
        output_path: Optional path to save merged audio
        
    Returns:
        Tuple of (merged_audio, sample_rate)
        
    Example:
        >>> merged, sr = merge_audio_files(
        ...     ['audio1.wav', 'audio2.wav'],
        ...     mode='crossfade',
        ...     output_path='merged.wav'
        ... )
    """
    try:
        merge_mode = MergeMode(mode)
    except ValueError:
        raise ValueError(
            f"Invalid mode '{mode}'. Must be one of: "
            f"{', '.join([m.value for m in MergeMode])}"
        )
    
    config = AudioMergeConfig(
        mode=merge_mode,
        sample_rate=sample_rate,
        crossfade_duration_ms=crossfade_ms
    )
    
    merger = AudioMerger(config)
    merged_audio, sr = merger.merge_from_files(file_paths)
    
    if output_path:
        merger.save_merged_audio(merged_audio, sr, output_path)
    
    return merged_audio, sr


def get_audio_merger(
    mode: str = "concatenate",
    sample_rate: int = 16000,
    crossfade_ms: float = 100.0,
    overlap_ms: float = 100.0,
    crossfade_shape: str = "linear",
    normalize: bool = True,
    silence_between_ms: float = 0.0
) -> AudioMerger:
    """
    Get a configured AudioMerger instance
    
    Args:
        mode: Merge mode ('concatenate', 'overlap', 'crossfade', 'mix')
        sample_rate: Sample rate in Hz
        crossfade_ms: Crossfade duration in milliseconds
        overlap_ms: Overlap duration in milliseconds
        crossfade_shape: Shape of crossfade ('linear', 'exponential', 'logarithmic')
        normalize: Whether to normalize segments
        silence_between_ms: Silence duration between segments
        
    Returns:
        Configured AudioMerger instance
        
    Example:
        >>> merger = get_audio_merger(mode='crossfade', crossfade_ms=200)
        >>> merged_audio, sr = merger.merge_audio_segments([audio1, audio2])
    """
    try:
        merge_mode = MergeMode(mode)
    except ValueError:
        raise ValueError(
            f"Invalid mode '{mode}'. Must be one of: "
            f"{', '.join([m.value for m in MergeMode])}"
        )
    
    config = AudioMergeConfig(
        mode=merge_mode,
        sample_rate=sample_rate,
        crossfade_duration_ms=crossfade_ms,
        overlap_duration_ms=overlap_ms,
        crossfade_shape=crossfade_shape,
        normalize_segments=normalize,
        silence_between_ms=silence_between_ms
    )
    
    return AudioMerger(config)