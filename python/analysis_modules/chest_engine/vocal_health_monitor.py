"""
Stage Buddy V2 - Chest Engine: Vocal Health Monitor
Detects vocal strain and fatigue in spoken word performances.

Vocal health is about maintaining voice quality throughout (10% of Chest score).
This module monitors:
- Jitter/shimmer trends (voice stability)
- Pitch decline over time (fatigue indicator)
- Spectral changes (strain indicators)
- Consistency between early and late performance

Excellence: Voice sounds as fresh at the end as at the beginning
Weakness: Noticeable strain, voice cracks, fatigue in final third
"""

from typing import List, Dict, Any, Optional
import numpy as np
import logging

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

from ..shared.data_structures import ProsodyFeatures

logger = logging.getLogger(__name__)


class VocalHealthMonitor:
    """
    Monitors vocal health by detecting strain and fatigue.

    Analysis approach:
    1. Divide performance into thirds (early, middle, late)
    2. Compare voice quality metrics across sections
    3. Detect pitch decline (fatigue indicator)
    4. Monitor jitter/shimmer trends (strain indicators)
    5. Score based on consistency
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        jitter_increase_threshold: float = 0.35,  # Increased: only flag significant jitter
        pitch_drop_threshold: float = 0.15,  # Increased: only flag significant pitch drop
        energy_decline_threshold: float = 0.30  # Only flag significant energy decline
    ):
        """
        Initialize the Vocal Health Monitor.

        Args:
            sample_rate: Audio sample rate
            jitter_increase_threshold: Threshold for significant jitter increase
            pitch_drop_threshold: Threshold for significant pitch drop
            energy_decline_threshold: Threshold for significant energy decline
        """
        self.sample_rate = sample_rate
        self.jitter_increase_threshold = jitter_increase_threshold
        self.pitch_drop_threshold = pitch_drop_threshold
        self.energy_decline_threshold = energy_decline_threshold

    def analyze(
        self,
        audio: np.ndarray,
        sr: int,
        prosody_features: Optional[List[ProsodyFeatures]] = None
    ) -> Dict[str, Any]:
        """
        Analyze vocal health in audio.

        Args:
            audio: Audio signal (mono)
            sr: Sample rate
            prosody_features: Optional pre-extracted prosody from Spirit Engine

        Returns:
            Dict with health metrics and score
        """
        duration = len(audio) / sr

        # Divide into thirds
        third_samples = len(audio) // 3
        early_audio = audio[:third_samples]
        middle_audio = audio[third_samples:2*third_samples]
        late_audio = audio[2*third_samples:]

        # Extract metrics for each section
        early_metrics = self._extract_section_metrics(early_audio, sr, "early")
        middle_metrics = self._extract_section_metrics(middle_audio, sr, "middle")
        late_metrics = self._extract_section_metrics(late_audio, sr, "late")

        # Calculate trends
        pitch_drop = self._calculate_pitch_drop(early_metrics, late_metrics)
        jitter_increase = self._calculate_jitter_increase(early_metrics, late_metrics)
        energy_decline = self._calculate_energy_decline(early_metrics, late_metrics)

        # Detect fatigue - be conservative to avoid false positives
        # Dynamic performances may have natural energy variation that isn't fatigue
        # Only flag fatigue when multiple indicators are present or one is severe
        fatigue_indicators = 0
        if jitter_increase > self.jitter_increase_threshold:
            fatigue_indicators += 1
        if pitch_drop > self.pitch_drop_threshold:
            fatigue_indicators += 1
        if energy_decline > self.energy_decline_threshold:
            fatigue_indicators += 1

        # Require at least 2 indicators for fatigue, OR one severe indicator
        severe_jitter = jitter_increase > 0.5
        severe_pitch_drop = pitch_drop > 0.25
        fatigue_detected = fatigue_indicators >= 2 or severe_jitter or severe_pitch_drop

        # Estimate fatigue onset time
        fatigue_onset_time = None
        if fatigue_detected:
            # Check if middle section shows fatigue
            middle_pitch_drop = self._calculate_pitch_drop(early_metrics, middle_metrics)
            if middle_pitch_drop > self.pitch_drop_threshold / 2:
                fatigue_onset_time = duration / 3  # Started in first third
            else:
                fatigue_onset_time = 2 * duration / 3  # Started in second third

        # Calculate strain level
        strain_level = self._calculate_strain_level(
            early_metrics, middle_metrics, late_metrics
        )

        # Calculate overall score
        score = self._calculate_score(
            fatigue_detected, jitter_increase, pitch_drop,
            energy_decline, strain_level
        )

        logger.info(
            f"Vocal health: fatigue={'YES' if fatigue_detected else 'NO'}, "
            f"pitch_drop={pitch_drop:.1%}, jitter_increase={jitter_increase:.1%}, "
            f"score={score:.2f}"
        )

        return {
            'score': score,
            'fatigue_detected': fatigue_detected,
            'fatigue_onset_time': fatigue_onset_time,
            'pitch_drop': pitch_drop,
            'jitter_increase': jitter_increase,
            'energy_decline': energy_decline,
            'strain_level': strain_level,
            'early_metrics': early_metrics,
            'middle_metrics': middle_metrics,
            'late_metrics': late_metrics
        }

    def _extract_section_metrics(
        self,
        audio: np.ndarray,
        sr: int,
        section_name: str
    ) -> Dict[str, float]:
        """Extract voice quality metrics for a section of audio."""
        metrics = {
            'pitch_mean': 0.0,
            'pitch_std': 0.0,
            'energy_mean': 0.0,
            'spectral_centroid': 0.0,
            'zcr': 0.0  # Zero crossing rate
        }

        if len(audio) < sr * 0.5:
            return metrics

        if LIBROSA_AVAILABLE:
            try:
                # Pitch (F0) estimation
                f0, voiced_flag, voiced_prob = librosa.pyin(
                    audio,
                    fmin=librosa.note_to_hz('C2'),
                    fmax=librosa.note_to_hz('C7'),
                    sr=sr
                )
                f0_clean = f0[~np.isnan(f0)]

                if len(f0_clean) > 0:
                    metrics['pitch_mean'] = float(np.mean(f0_clean))
                    metrics['pitch_std'] = float(np.std(f0_clean))

                # Energy
                rms = librosa.feature.rms(y=audio)[0]
                metrics['energy_mean'] = float(np.mean(rms))

                # Spectral centroid (voice brightness)
                spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
                metrics['spectral_centroid'] = float(np.mean(spectral_centroid))

                # Zero crossing rate (voice quality indicator)
                zcr = librosa.feature.zero_crossing_rate(audio)[0]
                metrics['zcr'] = float(np.mean(zcr))

            except Exception as e:
                logger.warning(f"Error extracting metrics for {section_name}: {e}")
        else:
            # Fallback: simple energy calculation
            metrics['energy_mean'] = float(np.sqrt(np.mean(audio ** 2)))

            # Simple zero crossing rate
            zero_crossings = np.sum(np.abs(np.diff(np.signbit(audio))))
            metrics['zcr'] = float(zero_crossings / len(audio))

        return metrics

    def _calculate_pitch_drop(
        self,
        early_metrics: Dict[str, float],
        late_metrics: Dict[str, float]
    ) -> float:
        """Calculate pitch drop from early to late performance."""
        early_pitch = early_metrics.get('pitch_mean', 0)
        late_pitch = late_metrics.get('pitch_mean', 0)

        if early_pitch > 0:
            return (early_pitch - late_pitch) / early_pitch
        return 0.0

    def _calculate_jitter_increase(
        self,
        early_metrics: Dict[str, float],
        late_metrics: Dict[str, float]
    ) -> float:
        """
        Estimate jitter increase using pitch standard deviation as proxy.
        True jitter requires specialized tools like Praat.
        """
        early_std = early_metrics.get('pitch_std', 0)
        late_std = late_metrics.get('pitch_std', 0)

        if early_std > 0:
            return (late_std - early_std) / early_std
        return 0.0

    def _calculate_energy_decline(
        self,
        early_metrics: Dict[str, float],
        late_metrics: Dict[str, float]
    ) -> float:
        """Calculate energy decline from early to late performance."""
        early_energy = early_metrics.get('energy_mean', 0)
        late_energy = late_metrics.get('energy_mean', 0)

        if early_energy > 0:
            return (early_energy - late_energy) / early_energy
        return 0.0

    def _calculate_strain_level(
        self,
        early_metrics: Dict[str, float],
        middle_metrics: Dict[str, float],
        late_metrics: Dict[str, float]
    ) -> float:
        """
        Calculate overall strain level (0-1).

        Indicators of strain:
        - Increasing spectral centroid (brighter/tighter voice)
        - Increasing zero crossing rate (noise in voice)
        - Decreasing pitch stability
        """
        strain_indicators = []

        # Spectral centroid increase (strain makes voice brighter/tighter)
        early_sc = early_metrics.get('spectral_centroid', 0)
        late_sc = late_metrics.get('spectral_centroid', 0)
        if early_sc > 0:
            sc_increase = (late_sc - early_sc) / early_sc
            strain_indicators.append(max(0, sc_increase))

        # Zero crossing rate increase (more noise in voice)
        early_zcr = early_metrics.get('zcr', 0)
        late_zcr = late_metrics.get('zcr', 0)
        if early_zcr > 0:
            zcr_increase = (late_zcr - early_zcr) / early_zcr
            strain_indicators.append(max(0, zcr_increase))

        # Pitch instability
        pitch_drop = self._calculate_pitch_drop(early_metrics, late_metrics)
        strain_indicators.append(abs(pitch_drop))

        if strain_indicators:
            return min(1.0, np.mean(strain_indicators))
        return 0.0

    def _calculate_score(
        self,
        fatigue_detected: bool,
        jitter_increase: float,
        pitch_drop: float,
        energy_decline: float,
        strain_level: float
    ) -> float:
        """
        Calculate vocal health score (0-1).

        Scoring:
        - No fatigue or strain: high score
        - Minor fatigue (late only): moderate penalty
        - Significant fatigue: larger penalty
        - Noticeable strain throughout: penalty

        Note: Very high consistency (low strain) in short performances
        may indicate monotone delivery rather than vocal excellence.
        """
        score = 0.85  # Start slightly lower (more conservative baseline)

        if fatigue_detected:
            score -= 0.25

        # Additional penalties for severity (with higher thresholds)
        if jitter_increase > 0.4:
            score -= 0.1
        if pitch_drop > 0.2:
            score -= 0.1
        if energy_decline > 0.35:
            score -= 0.05  # Reduced penalty - energy decline isn't always bad

        # Strain penalty (only for significant strain)
        if strain_level > 0.15:
            score -= (strain_level - 0.15) * 0.3

        # Bonus for genuine consistency (not just monotone)
        # Only award bonus if there's some variation (not monotone)
        if not fatigue_detected and 0.05 < strain_level < 0.15:
            score += 0.1  # Some variation but controlled = good

        return max(0.0, min(1.0, score))
