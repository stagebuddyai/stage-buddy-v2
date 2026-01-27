"""
Stage Buddy V2 - Chest Engine: Breath Analyzer
Detects and evaluates breath control in spoken word performances.

Breath control is the foundation of vocal technique (35% of Chest score).
This module detects breath events and classifies them as:
- Controlled: Invisible to audience, properly timed
- Gasping: Audible, rushed intake
- Shallow: Insufficient breath support

Excellence: Breathing is invisible - audience never hears intake
Weakness: Frequent gasping, running out of breath mid-line
"""

from typing import List, Dict, Any, Optional
import numpy as np
import logging

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

from ..shared.data_structures import BreathEvent

logger = logging.getLogger(__name__)


class BreathAnalyzer:
    """
    Analyzes breath control by detecting breath events in audio.

    Detection approach:
    1. Find energy dips (potential breath locations)
    2. Analyze spectral characteristics at dip points
    3. Classify each breath event by quality
    4. Score based on breath quality distribution
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        energy_threshold_percentile: float = 15.0,
        min_breath_duration: float = 0.1,
        max_breath_duration: float = 1.5
    ):
        """
        Initialize the Breath Analyzer.

        Args:
            sample_rate: Audio sample rate
            energy_threshold_percentile: Percentile for energy dip detection
            min_breath_duration: Minimum duration for breath event (seconds)
            max_breath_duration: Maximum duration for breath event (seconds)
        """
        self.sample_rate = sample_rate
        self.energy_threshold_percentile = energy_threshold_percentile
        self.min_breath_duration = min_breath_duration
        self.max_breath_duration = max_breath_duration

        # Frame parameters for energy analysis
        self.frame_length = int(0.025 * sample_rate)  # 25ms frames
        self.hop_length = int(0.010 * sample_rate)    # 10ms hop

    def analyze(self, audio: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze breath control in audio.

        Args:
            audio: Audio signal (mono)
            sr: Sample rate

        Returns:
            Dict with 'events' (List[BreathEvent]) and 'score' (float 0-1)
        """
        if not LIBROSA_AVAILABLE:
            logger.warning("librosa not available, using fallback breath detection")
            return self._fallback_analysis(audio, sr)

        # Step 1: Extract RMS energy
        rms = librosa.feature.rms(
            y=audio,
            frame_length=self.frame_length,
            hop_length=self.hop_length
        )[0]

        # Convert frames to timestamps
        times = librosa.frames_to_time(
            np.arange(len(rms)),
            sr=sr,
            hop_length=self.hop_length
        )

        # Step 2: Find energy dips (potential breath locations)
        threshold = np.percentile(rms, self.energy_threshold_percentile)
        dip_mask = rms < threshold

        # Step 3: Cluster consecutive dips into breath events
        breath_events = self._cluster_breath_events(
            dip_mask, times, rms, audio, sr
        )

        # Step 4: Calculate score based on breath quality
        score = self._calculate_score(breath_events)

        logger.info(f"Detected {len(breath_events)} breath events, score: {score:.2f}")

        return {
            'events': breath_events,
            'score': score,
            'controlled_count': len([e for e in breath_events if e.breath_quality == 'controlled']),
            'gasping_count': len([e for e in breath_events if e.breath_quality == 'gasping']),
            'shallow_count': len([e for e in breath_events if e.breath_quality == 'shallow'])
        }

    def _cluster_breath_events(
        self,
        dip_mask: np.ndarray,
        times: np.ndarray,
        rms: np.ndarray,
        audio: np.ndarray,
        sr: int
    ) -> List[BreathEvent]:
        """Cluster energy dips into breath events."""
        breath_events = []

        # Find contiguous regions of low energy
        in_dip = False
        dip_start = 0

        for i, is_dip in enumerate(dip_mask):
            if is_dip and not in_dip:
                # Start of dip
                dip_start = i
                in_dip = True
            elif not is_dip and in_dip:
                # End of dip
                dip_end = i
                in_dip = False

                # Calculate duration
                start_time = times[dip_start]
                end_time = times[min(dip_end, len(times) - 1)]
                duration = end_time - start_time

                # Filter by duration
                if self.min_breath_duration <= duration <= self.max_breath_duration:
                    # Calculate energy dip magnitude
                    segment_rms = rms[dip_start:dip_end]
                    surrounding_rms = np.concatenate([
                        rms[max(0, dip_start-10):dip_start],
                        rms[dip_end:min(len(rms), dip_end+10)]
                    ])

                    if len(surrounding_rms) > 0:
                        energy_dip = float(np.mean(surrounding_rms) - np.mean(segment_rms))
                    else:
                        energy_dip = 0.0

                    # Classify breath quality
                    breath_quality = self._classify_breath(
                        duration, energy_dip, audio, sr, start_time, end_time
                    )

                    breath_events.append(BreathEvent(
                        timestamp=start_time,
                        duration=duration,
                        breath_quality=breath_quality,
                        energy_dip=energy_dip,
                        spectral_change=0.0,  # Could add spectral analysis
                        at_natural_break=False  # Will be set by pause_detector
                    ))

        return breath_events

    def _classify_breath(
        self,
        duration: float,
        energy_dip: float,
        audio: np.ndarray,
        sr: int,
        start_time: float,
        end_time: float
    ) -> str:
        """
        Classify breath quality based on acoustic characteristics.

        - Controlled: Moderate duration (0.3-0.8s), gradual energy change
        - Gasping: Short duration (<0.3s), sharp energy spike after
        - Shallow: Very short (<0.2s), minimal energy change
        - Held: Long duration (>1.0s), potential dramatic pause
        """
        # Extract breath segment audio
        start_sample = int(start_time * sr)
        end_sample = int(end_time * sr)
        breath_audio = audio[start_sample:end_sample]

        if len(breath_audio) == 0:
            return 'shallow'

        # Calculate spectral centroid (breathiness indicator)
        if LIBROSA_AVAILABLE:
            try:
                spectral_centroid = np.mean(librosa.feature.spectral_centroid(
                    y=breath_audio, sr=sr
                ))
            except Exception:
                spectral_centroid = 0
        else:
            spectral_centroid = 0

        # Classification logic
        if duration < 0.15:
            return 'shallow'
        elif duration < 0.3:
            # Short breath - could be gasping or controlled quick breath
            if energy_dip > 0.02:  # Sharp dip suggests gasping
                return 'gasping'
            return 'controlled'
        elif duration < 0.8:
            # Moderate duration - ideal for controlled breathing
            if energy_dip > 0.03 and spectral_centroid > 2000:
                # High spectral centroid + sharp dip = audible breath
                return 'gasping'
            return 'controlled'
        elif duration < 1.2:
            # Longer breath - could be held breath or slow inhale
            return 'controlled'
        else:
            # Very long - this is a pause, not a breath
            return 'held'

    def _calculate_score(self, breath_events: List[BreathEvent]) -> float:
        """
        Calculate breath control score (0-1).

        Scoring:
        - Base score: 0.7 (everyone breathes)
        - Controlled breaths: +0.05 each (max +0.3)
        - Gasping breaths: -0.1 each
        - No gasping + multiple controlled: bonus +0.1
        """
        if not breath_events:
            # No detected breaths could mean very short audio or quiet delivery
            return 0.5

        controlled = [e for e in breath_events if e.breath_quality == 'controlled']
        gasping = [e for e in breath_events if e.breath_quality == 'gasping']

        # Base score
        score = 0.7

        # Add for controlled breaths (up to 0.3 bonus)
        controlled_bonus = min(0.3, len(controlled) * 0.05)
        score += controlled_bonus

        # Subtract for gasping
        gasping_penalty = len(gasping) * 0.1
        score -= gasping_penalty

        # Bonus for no gasping
        if len(gasping) == 0 and len(controlled) >= 3:
            score += 0.1

        # Clamp to 0-1
        return max(0.0, min(1.0, score))

    def _fallback_analysis(self, audio: np.ndarray, sr: int) -> Dict[str, Any]:
        """Fallback analysis when librosa is not available."""
        # Simple energy-based detection
        frame_size = int(0.025 * sr)
        hop_size = int(0.010 * sr)

        energies = []
        for i in range(0, len(audio) - frame_size, hop_size):
            frame = audio[i:i + frame_size]
            energies.append(np.sqrt(np.mean(frame ** 2)))

        energies = np.array(energies)
        threshold = np.percentile(energies, 15)

        # Count low-energy frames as potential breaths
        low_energy_count = np.sum(energies < threshold)
        total_frames = len(energies)

        # Estimate score based on ratio
        breath_ratio = low_energy_count / total_frames if total_frames > 0 else 0

        # Good breath control = moderate pauses (10-20%)
        if 0.1 <= breath_ratio <= 0.2:
            score = 0.8
        elif 0.05 <= breath_ratio <= 0.25:
            score = 0.6
        else:
            score = 0.4

        return {
            'events': [],
            'score': score,
            'controlled_count': 0,
            'gasping_count': 0,
            'shallow_count': 0
        }
