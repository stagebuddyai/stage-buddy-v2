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

        # Step 7: Analyze pitch variation (expressiveness indicator)
        # Monotone = low pitch variation, expressive = high pitch variation
        pitch_variation = self._analyze_pitch_variation(audio, sr)

        # Step 8: Calculate score
        score = self._calculate_score(
            dynamic_range_db, baseline_db, energy_std,
            len(peaks), len(dropouts), len(rms), pitch_variation
        )

        logger.info(
            f"Projection analysis: dynamic_range={dynamic_range_db:.1f}dB, "
            f"baseline={baseline_db:.1f}dB, pitch_var={pitch_variation:.2f}, score={score:.2f}"
        )

        return {
            'score': score,
            'baseline_db': baseline_db,
            'peak_db': peak_db,
            'valley_db': valley_db,
            'dynamic_range_db': dynamic_range_db,
            'energy_std': energy_std,
            'pitch_variation': pitch_variation,
            'peak_count': len(peaks),
            'dropout_count': len(dropouts),
            'peaks': peaks,
            'dropouts': dropouts,
            'energy_curve': rms_db.astype(np.float32),
            'timestamps': timestamps.astype(np.float32)
        }

    def _analyze_pitch_variation(self, audio: np.ndarray, sr: int) -> float:
        """
        Analyze pitch variation as an expressiveness indicator.

        Returns a normalized score (0-1) where:
        - 0: Monotone delivery (low pitch variation)
        - 1: Highly expressive (high pitch variation, multiple characters)

        Calibrated thresholds:
        - CV < 0.20: monotone (score 0-0.4)
        - CV 0.20-0.35: normal (score 0.4-0.7)
        - CV > 0.35: expressive (score 0.7-1.0)

        - Range < 12 semitones: narrow (score 0-0.4)
        - Range 12-20 semitones: normal (score 0.4-0.7)
        - Range > 20 semitones: wide (score 0.7-1.0)
        """
        try:
            # Extract pitch using pyin
            f0, voiced_flag, voiced_prob = librosa.pyin(
                audio,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'),
                sr=sr
            )

            # Remove unvoiced segments
            f0_clean = f0[~np.isnan(f0)]

            if len(f0_clean) < 10:
                return 0.5  # Not enough data

            # Calculate coefficient of variation (std/mean)
            pitch_mean = np.mean(f0_clean)
            pitch_std = np.std(f0_clean)

            if pitch_mean > 0:
                cv = pitch_std / pitch_mean
            else:
                return 0.5

            # Calculate the pitch range in semitones
            pitch_range_hz = np.percentile(f0_clean, 95) - np.percentile(f0_clean, 5)
            pitch_range_semitones = 12 * np.log2((pitch_mean + pitch_range_hz/2) /
                                                   (pitch_mean - pitch_range_hz/2 + 1))

            # CV scoring with calibrated thresholds
            # Based on benchmark data: STRONG=0.454, MID=0.300, WEAK=0.313
            if cv < 0.20:
                cv_score = cv / 0.20 * 0.4  # 0-0.4 for monotone
            elif cv < 0.35:
                cv_score = 0.4 + (cv - 0.20) / 0.15 * 0.3  # 0.4-0.7 for normal
            else:
                cv_score = 0.7 + min(0.3, (cv - 0.35) / 0.15 * 0.3)  # 0.7-1.0 for expressive

            # Range scoring with calibrated thresholds
            # Based on benchmark data: STRONG=26.6, MID=12.8, WEAK=18.8
            if pitch_range_semitones < 12:
                range_score = pitch_range_semitones / 12 * 0.4  # 0-0.4 for narrow
            elif pitch_range_semitones < 20:
                range_score = 0.4 + (pitch_range_semitones - 12) / 8 * 0.3  # 0.4-0.7 for normal
            else:
                range_score = 0.7 + min(0.3, (pitch_range_semitones - 20) / 10 * 0.3)  # 0.7-1.0 for wide

            # Combine both metrics
            variation_score = 0.6 * cv_score + 0.4 * range_score

            logger.debug(f"Pitch variation: CV={cv:.3f} (score {cv_score:.2f}), range={pitch_range_semitones:.1f}st (score {range_score:.2f}), combined={variation_score:.2f}")

            return float(max(0.0, min(1.0, variation_score)))

        except Exception as e:
            logger.warning(f"Error analyzing pitch variation: {e}")
            return 0.5  # Default neutral score

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
        total_frames: int,
        pitch_variation: float = 0.5
    ) -> float:
        """
        Calculate projection score (0-1).

        Scoring priority:
        1. Pitch variation (35%) - differentiates expressive from monotone
        2. Dynamic range (25%) - ideal zone is 10-25dB
        3. Baseline energy (10%) - can fill the space
        4. Peak ratio (15%) - intentional emphasis
        5. Dropout penalty (15%) - avoiding unintentional drops
        """
        score = 0.3  # Base score

        # Pitch variation scoring (most important - 35%)
        # This differentiates monotone from expressive performances
        score += pitch_variation * 0.35

        # Dynamic range scoring (25%)
        if self.ideal_dynamic_range_min <= dynamic_range_db <= self.ideal_dynamic_range_max:
            # Ideal range
            score += 0.20
        elif dynamic_range_db < self.ideal_dynamic_range_min:
            # Too narrow - monotone in volume
            penalty = (self.ideal_dynamic_range_min - dynamic_range_db) / 15
            score -= min(0.15, penalty)
        else:
            # Too wide - might be uncontrolled
            if dynamic_range_db > 30:
                score -= 0.05
            else:
                score += 0.15  # Still decent

        # Baseline scoring (10%)
        # Very quiet baseline is problematic (< -30dB from peak)
        if baseline_db > -20:
            score += 0.05
        elif baseline_db < -30:
            score -= 0.1

        # Peak ratio bonus (15%) - more peaks relative to duration = more intentional emphasis
        if total_frames > 0:
            peak_ratio = peak_count / total_frames
            # Ideal peak ratio is 5-15% of frames
            if 0.05 <= peak_ratio <= 0.15:
                score += 0.10
            elif 0.02 <= peak_ratio <= 0.20:
                score += 0.05
            # Very few peaks in a long performance is monotone
            elif peak_ratio < 0.02 and total_frames > 20:
                score -= 0.05

        # Dropout penalty
        dropout_penalty = dropout_count * 0.03
        score -= min(0.1, dropout_penalty)

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
