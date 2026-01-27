"""
Stage Buddy V2 - Chest Engine: Projection Analyzer
Analyzes volume, energy, and dynamic range in spoken word performances.

Projection is about filling the space with your voice (35% of Chest score).
This module measures:
- Baseline energy level (overall volume)
- Dynamic range (variety in loudness)
- Energy consistency (intentional vs. unintentional variation)
- Peak moments (intentional emphasis)

Excellence: Voice fills the room effortlessly, dynamic range serves the piece
Weakness: Too quiet, monotone, or inconsistent volume
"""

from typing import Dict, Any, List, Optional
import numpy as np
import logging

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProjectionAnalyzer:
    """
    Analyzes vocal projection by measuring energy and dynamic range.

    Analysis approach:
    1. Extract RMS energy over time
    2. Calculate baseline loudness (median)
    3. Measure dynamic range (peak to valley)
    4. Identify intentional peaks vs. dropouts
    5. Score based on appropriate projection
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        ideal_dynamic_range_db: tuple = (10, 25),
        window_seconds: float = 1.0
    ):
        """
        Initialize the Projection Analyzer.

        Args:
            sample_rate: Audio sample rate
            ideal_dynamic_range_db: Ideal dynamic range (min, max)
            window_seconds: Window size for energy analysis
        """
        self.sample_rate = sample_rate
        self.ideal_dynamic_range_min = ideal_dynamic_range_db[0]
        self.ideal_dynamic_range_max = ideal_dynamic_range_db[1]
        self.window_seconds = window_seconds

        # Frame parameters
        self.frame_length = int(window_seconds * sample_rate)
        self.hop_length = int(0.5 * sample_rate)  # 0.5s hop

    def analyze(self, audio: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze vocal projection in audio.

        Args:
            audio: Audio signal (mono)
            sr: Sample rate

        Returns:
            Dict with energy metrics and score
        """
        if not LIBROSA_AVAILABLE:
            return self._fallback_analysis(audio, sr)

        # Step 1: Extract RMS energy
        rms = librosa.feature.rms(
            y=audio,
            frame_length=self.frame_length,
            hop_length=self.hop_length
        )[0]

        # Convert to timestamps
        timestamps = librosa.frames_to_time(
            np.arange(len(rms)),
            sr=sr,
            hop_length=self.hop_length
        )

        # Step 2: Convert to dB
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)

        # Step 3: Calculate metrics
        baseline_db = float(np.median(rms_db))
        peak_db = float(np.max(rms_db))
        valley_db = float(np.percentile(rms_db, 10))  # Ignore complete silence
        dynamic_range_db = peak_db - valley_db

        # Step 4: Calculate consistency
        # High variance could be good (intentional) or bad (inconsistent)
        energy_std = float(np.std(rms_db))

        # Step 5: Find peaks (intentional loud moments)
        peak_threshold = baseline_db + 3  # 3dB above baseline
        peaks = self._find_peaks(rms_db, timestamps, peak_threshold)

        # Step 6: Find dropouts (unintentional quiet moments)
        dropout_threshold = baseline_db - 6  # 6dB below baseline
        dropouts = self._find_dropouts(rms_db, timestamps, dropout_threshold)

        # Step 7: Calculate score
        score = self._calculate_score(
            dynamic_range_db, baseline_db, energy_std,
            len(peaks), len(dropouts), len(rms)
        )

        logger.info(
            f"Projection analysis: dynamic_range={dynamic_range_db:.1f}dB, "
            f"baseline={baseline_db:.1f}dB, score={score:.2f}"
        )

        return {
            'score': score,
            'baseline_db': baseline_db,
            'peak_db': peak_db,
            'valley_db': valley_db,
            'dynamic_range_db': dynamic_range_db,
            'energy_std': energy_std,
            'peak_count': len(peaks),
            'dropout_count': len(dropouts),
            'peaks': peaks,
            'dropouts': dropouts,
            'energy_curve': rms_db.astype(np.float32),
            'timestamps': timestamps.astype(np.float32)
        }

    def _find_peaks(
        self,
        rms_db: np.ndarray,
        timestamps: np.ndarray,
        threshold: float
    ) -> List[Dict[str, float]]:
        """Find intentional loud moments (peaks above threshold)."""
        peaks = []
        in_peak = False
        peak_start = 0

        for i, db in enumerate(rms_db):
            if db > threshold and not in_peak:
                peak_start = i
                in_peak = True
            elif db <= threshold and in_peak:
                in_peak = False
                peak_db = float(np.max(rms_db[peak_start:i]))
                peaks.append({
                    'start_time': float(timestamps[peak_start]),
                    'end_time': float(timestamps[i]),
                    'peak_db': peak_db
                })

        return peaks

    def _find_dropouts(
        self,
        rms_db: np.ndarray,
        timestamps: np.ndarray,
        threshold: float
    ) -> List[Dict[str, float]]:
        """Find unintentional quiet moments (dropouts below threshold)."""
        dropouts = []
        in_dropout = False
        dropout_start = 0

        for i, db in enumerate(rms_db):
            if db < threshold and not in_dropout:
                dropout_start = i
                in_dropout = True
            elif db >= threshold and in_dropout:
                in_dropout = False
                # Only count longer dropouts as problems
                duration = timestamps[i] - timestamps[dropout_start]
                if duration > 0.5:  # > 0.5s dropout
                    dropouts.append({
                        'start_time': float(timestamps[dropout_start]),
                        'end_time': float(timestamps[i]),
                        'duration': float(duration)
                    })

        return dropouts

    def _calculate_score(
        self,
        dynamic_range_db: float,
        baseline_db: float,
        energy_std: float,
        peak_count: int,
        dropout_count: int,
        total_frames: int
    ) -> float:
        """
        Calculate projection score (0-1).

        Scoring:
        - Dynamic range in ideal zone (10-25dB): high score
        - Too narrow (<10dB): monotone penalty
        - Too wide (>30dB): uncontrolled penalty
        - Good baseline: bonus
        - Intentional peaks: bonus
        - Unintentional dropouts: penalty
        """
        score = 0.5  # Base score

        # Dynamic range scoring (most important)
        if self.ideal_dynamic_range_min <= dynamic_range_db <= self.ideal_dynamic_range_max:
            # Ideal range
            score += 0.3
        elif dynamic_range_db < self.ideal_dynamic_range_min:
            # Too narrow - monotone
            penalty = (self.ideal_dynamic_range_min - dynamic_range_db) / 20
            score -= min(0.3, penalty)
        else:
            # Too wide - might be uncontrolled
            if dynamic_range_db > 30:
                score -= 0.1
            else:
                score += 0.2  # Still decent

        # Baseline scoring
        # Very quiet baseline is problematic (< -30dB from peak)
        if baseline_db > -20:
            score += 0.1
        elif baseline_db < -30:
            score -= 0.1

        # Peak bonus (intentional emphasis is good)
        if 2 <= peak_count <= total_frames / 10:
            score += 0.1

        # Dropout penalty
        dropout_penalty = dropout_count * 0.05
        score -= min(0.2, dropout_penalty)

        return max(0.0, min(1.0, score))

    def _fallback_analysis(self, audio: np.ndarray, sr: int) -> Dict[str, Any]:
        """Fallback analysis when librosa is not available."""
        # Simple energy calculation
        frame_size = int(self.window_seconds * sr)
        hop_size = frame_size // 2

        energies = []
        timestamps = []

        for i in range(0, len(audio) - frame_size, hop_size):
            frame = audio[i:i + frame_size]
            rms = np.sqrt(np.mean(frame ** 2))
            energies.append(rms)
            timestamps.append(i / sr)

        if not energies:
            return {
                'score': 0.5,
                'baseline_db': -20,
                'dynamic_range_db': 0,
                'energy_curve': np.array([]),
                'timestamps': np.array([]),
                'peaks': [],
                'dropouts': []
            }

        energies = np.array(energies)
        timestamps = np.array(timestamps)

        # Convert to dB (avoid log of zero)
        ref = np.max(energies) if np.max(energies) > 0 else 1e-10
        rms_db = 20 * np.log10(energies / ref + 1e-10)

        dynamic_range = float(np.max(rms_db) - np.percentile(rms_db, 10))

        # Simple score based on dynamic range
        if 10 <= dynamic_range <= 25:
            score = 0.8
        elif 5 <= dynamic_range <= 30:
            score = 0.6
        else:
            score = 0.4

        return {
            'score': score,
            'baseline_db': float(np.median(rms_db)),
            'peak_db': float(np.max(rms_db)),
            'valley_db': float(np.min(rms_db)),
            'dynamic_range_db': dynamic_range,
            'energy_std': float(np.std(rms_db)),
            'peak_count': 0,
            'dropout_count': 0,
            'peaks': [],
            'dropouts': [],
            'energy_curve': rms_db.astype(np.float32),
            'timestamps': timestamps.astype(np.float32)
        }
