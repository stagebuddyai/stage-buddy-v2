"""
Stage Buddy V2 - Alignment Scorer
Scores physical-vocal synchronization (body movement matching vocal emphasis).

This module evaluates:
1. Do gestures coincide with vocal emphasis?
2. Does physical energy match vocal energy?
3. Are movements supporting the words or disconnected?
"""

from typing import List, Dict, Any, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class AlignmentScorer:
    """
    Scores alignment between physical movement and vocal delivery.

    Good alignment (POTS criteria):
    - Gestures land with emphatic words
    - Physical energy rises and falls with vocal energy
    - Movement supports meaning, not random

    Poor alignment:
    - Movement disconnected from words
    - High energy movement during quiet moments
    - Static during powerful vocal moments
    """

    def __init__(
        self,
        segment_duration: float = 3.0,
        alignment_window: float = 0.5  # Window for correlation
    ):
        """
        Initialize the alignment scorer.

        Args:
            segment_duration: Duration for segment analysis
            alignment_window: Time window for correlation calculation
        """
        self.segment_duration = segment_duration
        self.alignment_window = alignment_window

        logger.info("AlignmentScorer initialized")

    def analyze(
        self,
        pose_data: Dict[str, Any],
        timestamps: List[float],
        audio_energy_curve: Optional[np.ndarray] = None,
        audio_timestamps: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Analyze physical-vocal alignment.

        Args:
            pose_data: Pose estimation results from GestureAnalyzer
            timestamps: Frame timestamps
            audio_energy_curve: Energy/loudness curve from audio analysis
            audio_timestamps: Timestamps for audio curve

        Returns:
            Alignment analysis results
        """
        poses = pose_data.get('poses', [])

        if not poses:
            return self._create_empty_analysis()

        # Calculate physical energy curve from pose data
        physical_energy = self._calculate_physical_energy(poses, timestamps)

        if audio_energy_curve is not None and audio_timestamps is not None:
            # Full alignment analysis with audio data
            return self._analyze_with_audio(
                physical_energy, timestamps,
                audio_energy_curve, audio_timestamps
            )
        else:
            # Limited analysis without audio data
            return self._analyze_physical_only(physical_energy, timestamps)

    def _calculate_physical_energy(
        self,
        poses: List[Dict],
        timestamps: List[float]
    ) -> np.ndarray:
        """
        Calculate physical energy (movement intensity) over time.

        Returns an array of energy values corresponding to timestamps.
        """
        if len(poses) < 2:
            return np.zeros(len(timestamps))

        method = poses[0].get('method', poses[0].get('landmarks') and 'mediapipe' or 'motion')

        if method == 'motion' or 'motion_ratio' in poses[0]:
            # Use motion ratio directly
            energy = np.array([
                p.get('motion_ratio', 0.0) for p in poses
            ])
        else:
            # Calculate from pose landmarks
            energy = []
            for i in range(len(poses)):
                if i == 0:
                    energy.append(0.0)
                    continue

                prev = poses[i - 1]
                curr = poses[i]

                if not prev.get('detected') or not curr.get('detected'):
                    energy.append(0.0)
                    continue

                # Calculate total movement
                total_movement = 0.0
                prev_lm = prev.get('landmarks', {})
                curr_lm = curr.get('landmarks', {})

                for key in ['left_wrist', 'right_wrist', 'left_elbow', 'right_elbow']:
                    if key in prev_lm and key in curr_lm:
                        p1 = prev_lm[key]
                        p2 = curr_lm[key]
                        dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                        total_movement += dist

                energy.append(total_movement)

            energy = np.array(energy)

        # Normalize energy to 0-1 range
        if energy.max() > 0:
            energy = energy / energy.max()

        return energy

    def _analyze_with_audio(
        self,
        physical_energy: np.ndarray,
        physical_timestamps: List[float],
        audio_energy: np.ndarray,
        audio_timestamps: np.ndarray
    ) -> Dict[str, Any]:
        """Analyze alignment when audio energy data is available."""
        # Resample audio energy to match physical timestamps
        resampled_audio = self._resample_to_timestamps(
            audio_energy, audio_timestamps, physical_timestamps
        )

        # Calculate correlation
        if len(physical_energy) > 1 and len(resampled_audio) > 1:
            # Normalize both signals
            phys_norm = (physical_energy - physical_energy.mean()) / (physical_energy.std() + 1e-6)
            audio_norm = (resampled_audio - resampled_audio.mean()) / (resampled_audio.std() + 1e-6)

            # Calculate correlation coefficient
            correlation = np.corrcoef(phys_norm, audio_norm)[0, 1]

            # Handle NaN
            if np.isnan(correlation):
                correlation = 0.0
        else:
            correlation = 0.0

        # Calculate per-segment alignment
        segment_data = self._calculate_segment_alignment(
            physical_energy, physical_timestamps,
            resampled_audio
        )

        # Overall alignment score
        # Correlation > 0.3 is good, < 0 is bad (inverse correlation)
        # But also consider energy levels

        avg_physical = np.mean(physical_energy)
        avg_audio = np.mean(resampled_audio) if len(resampled_audio) > 0 else 0

        # Score components
        correlation_score = max(0, (correlation + 1) / 2)  # Map [-1, 1] to [0, 1]

        # Energy match score
        if avg_audio > 0:
            energy_ratio = avg_physical / (avg_audio + 0.1)
            # Ideal ratio is around 1.0
            energy_match = 1.0 - min(1.0, abs(energy_ratio - 1.0))
        else:
            energy_match = 0.5  # Neutral if no audio

        overall_score = correlation_score * 0.6 + energy_match * 0.4

        return {
            'overall_score': overall_score,
            'segments': segment_data,
            'correlation': correlation,
            'avg_physical_energy': avg_physical,
            'avg_audio_energy': avg_audio,
            'method': 'audio_alignment'
        }

    def _analyze_physical_only(
        self,
        physical_energy: np.ndarray,
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """Analyze physical movement patterns without audio reference."""
        # Without audio, we can only analyze physical consistency
        # and make assumptions about good movement patterns

        avg_energy = np.mean(physical_energy)
        energy_variance = np.var(physical_energy)

        # Good patterns:
        # - Not too static (some movement)
        # - Not constant high energy (variation)
        # - Smooth transitions (low high-frequency variance)

        if avg_energy < 0.05:
            # Very static - low score
            consistency_score = 0.3
        elif avg_energy > 0.8:
            # Constant high movement - suspicious
            consistency_score = 0.5
        else:
            # Moderate movement is good
            consistency_score = 0.7

        # Variation is good (dynamic performance)
        if energy_variance > 0.01:
            variation_score = min(1.0, energy_variance * 10)
        else:
            variation_score = 0.3

        overall_score = consistency_score * 0.5 + variation_score * 0.5

        # Create segment data
        segment_data = self._create_physical_only_segments(
            physical_energy, timestamps
        )

        return {
            'overall_score': overall_score,
            'segments': segment_data,
            'correlation': 0.0,  # No audio correlation available
            'avg_physical_energy': avg_energy,
            'avg_audio_energy': 0.0,
            'method': 'physical_only'
        }

    def _resample_to_timestamps(
        self,
        signal: np.ndarray,
        original_timestamps: np.ndarray,
        target_timestamps: List[float]
    ) -> np.ndarray:
        """Resample a signal to match target timestamps."""
        if len(signal) == 0 or len(original_timestamps) == 0:
            return np.zeros(len(target_timestamps))

        resampled = np.interp(
            target_timestamps,
            original_timestamps,
            signal
        )

        return resampled

    def _calculate_segment_alignment(
        self,
        physical_energy: np.ndarray,
        timestamps: List[float],
        audio_energy: np.ndarray
    ) -> Dict[int, Dict[str, Any]]:
        """Calculate per-segment alignment metrics."""
        segment_data = {}

        if not timestamps:
            return segment_data

        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        segment_count = max(1, int(duration / self.segment_duration))

        for i in range(segment_count):
            seg_start = i * self.segment_duration
            seg_end = (i + 1) * self.segment_duration

            # Get indices for this segment
            seg_indices = [
                j for j, t in enumerate(timestamps)
                if seg_start <= t < seg_end
            ]

            if seg_indices and len(seg_indices) > 1:
                seg_physical = physical_energy[seg_indices]
                seg_audio = audio_energy[seg_indices] if len(audio_energy) > max(seg_indices) else np.zeros(len(seg_indices))

                # Segment correlation
                if seg_physical.std() > 0 and seg_audio.std() > 0:
                    seg_corr = np.corrcoef(seg_physical, seg_audio)[0, 1]
                    if np.isnan(seg_corr):
                        seg_corr = 0.0
                else:
                    seg_corr = 0.0

                seg_phys_energy = float(np.mean(seg_physical))
            else:
                seg_corr = 0.0
                seg_phys_energy = 0.0

            segment_data[i] = {
                'correlation': seg_corr,
                'physical_energy': seg_phys_energy
            }

        return segment_data

    def _create_physical_only_segments(
        self,
        physical_energy: np.ndarray,
        timestamps: List[float]
    ) -> Dict[int, Dict[str, Any]]:
        """Create segment data when only physical energy is available."""
        segment_data = {}

        if not timestamps:
            return segment_data

        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        segment_count = max(1, int(duration / self.segment_duration))

        for i in range(segment_count):
            seg_start = i * self.segment_duration
            seg_end = (i + 1) * self.segment_duration

            seg_indices = [
                j for j, t in enumerate(timestamps)
                if seg_start <= t < seg_end
            ]

            if seg_indices:
                seg_physical = physical_energy[seg_indices]
                seg_phys_energy = float(np.mean(seg_physical))
            else:
                seg_phys_energy = 0.0

            segment_data[i] = {
                'correlation': 0.0,
                'physical_energy': seg_phys_energy
            }

        return segment_data

    def _create_empty_analysis(self) -> Dict[str, Any]:
        """Create empty analysis result."""
        return {
            'overall_score': 0.5,  # Neutral when no data
            'segments': {},
            'correlation': 0.0,
            'avg_physical_energy': 0.0,
            'avg_audio_energy': 0.0,
            'method': 'none'
        }


def score_alignment(
    pose_data: Dict[str, Any],
    timestamps: List[float],
    audio_energy_curve: Optional[np.ndarray] = None,
    audio_timestamps: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Convenience function for alignment scoring.

    Args:
        pose_data: Pose estimation results
        timestamps: Frame timestamps
        audio_energy_curve: Optional audio energy curve
        audio_timestamps: Optional audio timestamps

    Returns:
        Alignment analysis results
    """
    scorer = AlignmentScorer()
    return scorer.analyze(pose_data, timestamps, audio_energy_curve, audio_timestamps)
