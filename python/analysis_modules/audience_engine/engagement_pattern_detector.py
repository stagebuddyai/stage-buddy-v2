"""
Stage Buddy V2 - Engagement Pattern Detector
Analyzes delivery variation and room-reading signals.

Engagement Pattern Indicators:
- Energy variation over time (not monotonous)
- Strategic build-ups and releases
- Pace shifts that maintain interest
- Intensity modulation for impact

Poor Engagement Indicators:
- Monotonous delivery (flat energy)
- No variation in pace or intensity
- Constant high/low energy (exhausting or boring)
- Predictable patterns that lose audience attention
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging

from ..shared.data_structures import (
    WordSegment, EmotionSegment, ProsodyFeatures, SpiritAnalysisResult,
    EngagementEvent
)

logger = logging.getLogger(__name__)


# Optimal energy variation thresholds
MIN_ENERGY_VARIATION = 0.15     # Below this = monotonous
OPTIMAL_ENERGY_VARIATION = 0.3  # Ideal variation level
MAX_ENERGY_VARIATION = 0.6      # Above this = chaotic

# Pace shift detection thresholds
SIGNIFICANT_PACE_SHIFT = 0.25   # 25% change in pace


class EngagementPatternDetector:
    """
    Detects engagement patterns in performance delivery.

    A good performer varies their delivery to maintain audience
    attention through strategic energy shifts and pace modulation.
    """

    def __init__(
        self,
        segment_duration: float = 3.0,
        analysis_window: float = 5.0
    ):
        """
        Initialize the Engagement Pattern Detector.

        Args:
            segment_duration: Duration of analysis segments in seconds
            analysis_window: Window size for pattern detection
        """
        self.segment_duration = segment_duration
        self.analysis_window = analysis_window

        logger.info("EngagementPatternDetector initialized")

    def analyze(
        self,
        word_segments: List[WordSegment],
        spirit_result: Optional[SpiritAnalysisResult] = None,
        loudness_curve: Optional[np.ndarray] = None,
        prosody_features: Optional[List[ProsodyFeatures]] = None
    ) -> Dict[str, Any]:
        """
        Analyze engagement patterns in the performance.

        Args:
            word_segments: Word-level timing information
            spirit_result: Spirit Engine results (optional, enhances analysis)
            loudness_curve: Loudness over time (from Chest Engine)
            prosody_features: Prosody timeline (from Spirit Engine)

        Returns:
            Dictionary with:
            - overall_score: 0-1 engagement pattern score
            - segment_scores: Per-segment breakdown
            - engagement_events: Key pattern moments
            - metrics: Detailed metrics
        """
        if not word_segments:
            logger.warning("No word segments provided")
            return self._empty_result()

        logger.info(f"Analyzing engagement patterns in {len(word_segments)} words")

        # Extract energy curve from available data
        energy_curve = self._extract_energy_curve(
            word_segments, spirit_result, loudness_curve, prosody_features
        )

        # Analyze energy patterns
        energy_metrics = self._analyze_energy_patterns(energy_curve)

        # Analyze pace patterns
        pace_metrics = self._analyze_pace_patterns(word_segments)

        # Analyze by segments
        segment_results = self._analyze_by_segments(
            word_segments, energy_curve, spirit_result
        )

        # Find engagement events (significant shifts)
        engagement_events = self._find_pattern_shifts(
            word_segments, energy_curve, spirit_result
        )

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            energy_metrics, pace_metrics, segment_results
        )

        return {
            'overall_score': overall_score,
            'segment_scores': segment_results,
            'engagement_events': engagement_events,
            'energy_metrics': energy_metrics,
            'pace_metrics': pace_metrics,
            'energy_curve': energy_curve
        }

    def _extract_energy_curve(
        self,
        word_segments: List[WordSegment],
        spirit_result: Optional[SpiritAnalysisResult],
        loudness_curve: Optional[np.ndarray],
        prosody_features: Optional[List[ProsodyFeatures]]
    ) -> np.ndarray:
        """Extract an energy curve from available data sources."""
        if not word_segments:
            return np.array([])

        duration = word_segments[-1].end_time
        num_samples = max(1, int(duration * 10))  # 10 samples per second

        # Priority: loudness_curve > prosody_features > spirit emotions > word density

        if loudness_curve is not None and len(loudness_curve) > 0:
            # Resample loudness curve
            if len(loudness_curve) != num_samples:
                energy = np.interp(
                    np.linspace(0, 1, num_samples),
                    np.linspace(0, 1, len(loudness_curve)),
                    loudness_curve
                )
            else:
                energy = loudness_curve
            # Normalize
            if np.max(energy) > np.min(energy):
                energy = (energy - np.min(energy)) / (np.max(energy) - np.min(energy))
            return energy

        if prosody_features:
            # Use loudness from prosody features
            timestamps = np.array([p.timestamp for p in prosody_features])
            loudness = np.array([p.loudness_db for p in prosody_features])

            if len(timestamps) > 0 and np.max(timestamps) > 0:
                # Interpolate to regular grid
                sample_times = np.linspace(0, duration, num_samples)
                energy = np.interp(sample_times, timestamps, loudness, left=loudness[0], right=loudness[-1])
                # Normalize
                if np.max(energy) > np.min(energy):
                    energy = (energy - np.min(energy)) / (np.max(energy) - np.min(energy))
                return energy

        if spirit_result and spirit_result.vocal_emotions:
            # Use emotion intensity as proxy for energy
            emotions = spirit_result.vocal_emotions
            sample_times = np.linspace(0, duration, num_samples)
            energy = np.zeros(num_samples)

            for emotion in emotions:
                # Find samples within this emotion's timespan
                mask = (sample_times >= emotion.start_time) & (sample_times < emotion.end_time)
                # Weight by intensity and arousal
                emotion_energy = emotion.intensity * 0.6 + emotion.arousal * 0.4
                energy[mask] = np.maximum(energy[mask], emotion_energy)

            return energy

        # Fallback: use word density as energy proxy
        sample_times = np.linspace(0, duration, num_samples)
        energy = np.zeros(num_samples)
        window = 0.5  # seconds

        for i, t in enumerate(sample_times):
            # Count words near this time
            nearby_words = [
                ws for ws in word_segments
                if abs((ws.start_time + ws.end_time) / 2 - t) < window
            ]
            energy[i] = len(nearby_words) / (2 * window)  # Words per second

        # Normalize
        if np.max(energy) > np.min(energy):
            energy = (energy - np.min(energy)) / (np.max(energy) - np.min(energy))

        return energy

    def _analyze_energy_patterns(
        self,
        energy_curve: np.ndarray
    ) -> Dict[str, Any]:
        """Analyze patterns in the energy curve."""
        if len(energy_curve) == 0:
            return self._empty_energy_metrics()

        # Basic statistics
        mean_energy = np.mean(energy_curve)
        std_energy = np.std(energy_curve)
        energy_range = np.max(energy_curve) - np.min(energy_curve)

        # Coefficient of variation (normalized variability)
        cv = std_energy / mean_energy if mean_energy > 0 else 0

        # Count energy peaks and valleys
        peaks = self._find_peaks(energy_curve)
        valleys = self._find_valleys(energy_curve)

        # Analyze peak spacing (regular = monotonous, varied = good)
        if len(peaks) > 1:
            peak_spacing = np.diff(peaks)
            spacing_variance = np.std(peak_spacing) / np.mean(peak_spacing) if np.mean(peak_spacing) > 0 else 0
        else:
            spacing_variance = 0

        # Analyze build-ups (increasing energy runs)
        buildups = self._find_buildups(energy_curve)

        # Analyze releases (decreasing energy after peaks)
        releases = self._find_releases(energy_curve, peaks)

        return {
            'mean_energy': mean_energy,
            'std_energy': std_energy,
            'energy_range': energy_range,
            'coefficient_of_variation': cv,
            'peak_count': len(peaks),
            'valley_count': len(valleys),
            'peak_spacing_variance': spacing_variance,
            'buildup_count': len(buildups),
            'release_count': len(releases)
        }

    def _analyze_pace_patterns(
        self,
        word_segments: List[WordSegment]
    ) -> Dict[str, Any]:
        """Analyze speech pace patterns."""
        if len(word_segments) < 5:
            return self._empty_pace_metrics()

        # Calculate local speech rates
        window_duration = self.analysis_window
        rates = []
        times = []

        current_time = word_segments[0].start_time
        end_time = word_segments[-1].end_time

        while current_time < end_time:
            window_end = min(current_time + window_duration, end_time)

            # Count words in window
            window_words = [
                ws for ws in word_segments
                if ws.start_time >= current_time and ws.start_time < window_end
            ]

            if window_words:
                actual_duration = window_end - current_time
                rate = len(window_words) / actual_duration  # Words per second
                rates.append(rate)
                times.append(current_time + window_duration / 2)

            current_time += window_duration / 2  # 50% overlap

        if not rates:
            return self._empty_pace_metrics()

        rates = np.array(rates)

        # Basic pace statistics
        mean_pace = np.mean(rates)
        pace_variance = np.std(rates)
        pace_range = np.max(rates) - np.min(rates)

        # Coefficient of variation
        pace_cv = pace_variance / mean_pace if mean_pace > 0 else 0

        # Find significant pace shifts
        pace_shifts = []
        for i in range(1, len(rates)):
            change = abs(rates[i] - rates[i-1]) / rates[i-1] if rates[i-1] > 0 else 0
            if change >= SIGNIFICANT_PACE_SHIFT:
                pace_shifts.append({
                    'time': times[i],
                    'change_ratio': change,
                    'direction': 'faster' if rates[i] > rates[i-1] else 'slower'
                })

        return {
            'mean_pace': mean_pace,
            'pace_variance': pace_variance,
            'pace_range': pace_range,
            'pace_cv': pace_cv,
            'significant_shifts': len(pace_shifts),
            'pace_shifts': pace_shifts
        }

    def _analyze_by_segments(
        self,
        word_segments: List[WordSegment],
        energy_curve: np.ndarray,
        spirit_result: Optional[SpiritAnalysisResult]
    ) -> List[Dict[str, Any]]:
        """Analyze engagement patterns in time-based segments."""
        if not word_segments:
            return []

        duration = word_segments[-1].end_time
        segments = []
        samples_per_second = len(energy_curve) / duration if duration > 0 else 10

        current_time = 0.0
        while current_time < duration:
            segment_end = min(current_time + self.segment_duration, duration)

            # Get words in this segment
            segment_words = [
                ws for ws in word_segments
                if ws.start_time >= current_time and ws.start_time < segment_end
            ]

            # Get energy for this segment
            start_idx = int(current_time * samples_per_second)
            end_idx = int(segment_end * samples_per_second)
            segment_energy = energy_curve[start_idx:end_idx] if len(energy_curve) > 0 else np.array([])

            if segment_words:
                # Score this segment
                score = self._score_segment(segment_words, segment_energy)

                # Determine pattern type
                if len(segment_energy) > 0:
                    if np.std(segment_energy) < 0.1:
                        pattern = 'flat'
                    elif np.mean(np.diff(segment_energy)) > 0.02:
                        pattern = 'building'
                    elif np.mean(np.diff(segment_energy)) < -0.02:
                        pattern = 'releasing'
                    else:
                        pattern = 'dynamic'
                else:
                    pattern = 'unknown'

                segments.append({
                    'start_time': current_time,
                    'end_time': segment_end,
                    'score': score,
                    'word_count': len(segment_words),
                    'energy_mean': np.mean(segment_energy) if len(segment_energy) > 0 else 0.5,
                    'energy_std': np.std(segment_energy) if len(segment_energy) > 0 else 0.0,
                    'pattern': pattern
                })

            current_time = segment_end

        return segments

    def _score_segment(
        self,
        words: List[WordSegment],
        energy: np.ndarray
    ) -> float:
        """Score engagement patterns for a single segment."""
        score = 0.5  # Start neutral

        if len(energy) > 0:
            # Energy variation score
            energy_std = np.std(energy)
            if energy_std < MIN_ENERGY_VARIATION:
                variation_score = 0.3 + (energy_std / MIN_ENERGY_VARIATION) * 0.3  # Monotonous
            elif energy_std <= OPTIMAL_ENERGY_VARIATION:
                variation_score = 0.6 + (energy_std - MIN_ENERGY_VARIATION) / (OPTIMAL_ENERGY_VARIATION - MIN_ENERGY_VARIATION) * 0.4
            else:
                # Penalize excessive variation
                variation_score = max(0.4, 1.0 - (energy_std - OPTIMAL_ENERGY_VARIATION) / MAX_ENERGY_VARIATION)
        else:
            variation_score = 0.5

        # Pace score from word density
        if words:
            segment_duration = words[-1].end_time - words[0].start_time
            if segment_duration > 0:
                wps = len(words) / segment_duration
                # Optimal is 2-3 words per second
                if 2.0 <= wps <= 3.0:
                    pace_score = 1.0
                elif wps < 2.0:
                    pace_score = 0.5 + (wps / 2.0) * 0.5
                else:
                    pace_score = max(0.4, 1.0 - (wps - 3.0) / 2.0 * 0.6)
            else:
                pace_score = 0.5
        else:
            pace_score = 0.5

        # Combine
        score = variation_score * 0.6 + pace_score * 0.4

        return min(1.0, max(0.0, score))

    def _find_pattern_shifts(
        self,
        word_segments: List[WordSegment],
        energy_curve: np.ndarray,
        spirit_result: Optional[SpiritAnalysisResult]
    ) -> List[EngagementEvent]:
        """Find significant pattern shifts that engage the audience."""
        events = []

        if len(energy_curve) == 0:
            return events

        duration = word_segments[-1].end_time if word_segments else 0
        if duration == 0:
            return events

        samples_per_second = len(energy_curve) / duration

        # Find energy peaks
        peaks = self._find_peaks(energy_curve)
        for peak_idx in peaks:
            peak_time = peak_idx / samples_per_second
            events.append(EngagementEvent(
                timestamp=peak_time,
                duration=0.5,
                event_type='pace_shift',
                engagement_level=0.8,
                description="Energy peak - high engagement moment"
            ))

        # Find build-ups
        buildups = self._find_buildups(energy_curve)
        for start_idx, end_idx in buildups:
            start_time = start_idx / samples_per_second
            end_time = end_idx / samples_per_second
            events.append(EngagementEvent(
                timestamp=start_time,
                duration=end_time - start_time,
                event_type='pace_shift',
                engagement_level=0.7,
                description="Energy build-up - creating anticipation"
            ))

        # Find dramatic drops
        valleys = self._find_valleys(energy_curve)
        for valley_idx in valleys:
            # Check if preceded by peak
            recent_peaks = [p for p in peaks if valley_idx - 20 < p < valley_idx]
            if recent_peaks:
                valley_time = valley_idx / samples_per_second
                events.append(EngagementEvent(
                    timestamp=valley_time,
                    duration=0.5,
                    event_type='pace_shift',
                    engagement_level=0.75,
                    description="Energy drop after peak - letting moment land"
                ))

        return events

    def _find_peaks(self, curve: np.ndarray, threshold: float = 0.7) -> List[int]:
        """Find peaks in the energy curve."""
        if len(curve) < 3:
            return []

        peaks = []
        for i in range(1, len(curve) - 1):
            if curve[i] > curve[i-1] and curve[i] > curve[i+1] and curve[i] >= threshold:
                peaks.append(i)

        return peaks

    def _find_valleys(self, curve: np.ndarray, threshold: float = 0.3) -> List[int]:
        """Find valleys in the energy curve."""
        if len(curve) < 3:
            return []

        valleys = []
        for i in range(1, len(curve) - 1):
            if curve[i] < curve[i-1] and curve[i] < curve[i+1] and curve[i] <= threshold:
                valleys.append(i)

        return valleys

    def _find_buildups(self, curve: np.ndarray, min_length: int = 10) -> List[Tuple[int, int]]:
        """Find sustained energy increases (build-ups)."""
        if len(curve) < min_length:
            return []

        buildups = []
        in_buildup = False
        start_idx = 0

        for i in range(1, len(curve)):
            increasing = curve[i] > curve[i-1] + 0.01

            if increasing and not in_buildup:
                in_buildup = True
                start_idx = i - 1
            elif not increasing and in_buildup:
                if i - start_idx >= min_length:
                    buildups.append((start_idx, i))
                in_buildup = False

        # Handle end
        if in_buildup and len(curve) - start_idx >= min_length:
            buildups.append((start_idx, len(curve) - 1))

        return buildups

    def _find_releases(
        self,
        curve: np.ndarray,
        peaks: List[int],
        window: int = 20
    ) -> List[Tuple[int, int]]:
        """Find energy releases after peaks."""
        releases = []

        for peak_idx in peaks:
            end_idx = min(peak_idx + window, len(curve))
            segment = curve[peak_idx:end_idx]

            if len(segment) > 3:
                # Check for sustained decrease
                decreasing = np.all(np.diff(segment) < 0)
                if decreasing or (segment[-1] < segment[0] * 0.6):
                    releases.append((peak_idx, end_idx))

        return releases

    def _calculate_overall_score(
        self,
        energy_metrics: Dict[str, Any],
        pace_metrics: Dict[str, Any],
        segment_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall engagement pattern score."""
        # Energy variation score (optimal variation is best)
        cv = energy_metrics['coefficient_of_variation']
        if cv < MIN_ENERGY_VARIATION:
            energy_score = 0.3 + (cv / MIN_ENERGY_VARIATION) * 0.3
        elif cv <= OPTIMAL_ENERGY_VARIATION:
            energy_score = 0.6 + (cv - MIN_ENERGY_VARIATION) / (OPTIMAL_ENERGY_VARIATION - MIN_ENERGY_VARIATION) * 0.4
        else:
            energy_score = max(0.4, 1.0 - (cv - OPTIMAL_ENERGY_VARIATION) / 0.4 * 0.5)

        # Peak/buildup score (having peaks and buildups is good)
        peak_score = min(1.0, energy_metrics['peak_count'] / 5 * 0.5 +
                        energy_metrics['buildup_count'] / 3 * 0.5)

        # Pace variation score
        pace_cv = pace_metrics['pace_cv']
        if pace_cv < 0.1:
            pace_score = 0.4 + pace_cv * 3  # Low variation
        elif pace_cv <= 0.3:
            pace_score = 0.7 + (pace_cv - 0.1) * 1.5
        else:
            pace_score = max(0.5, 1.0 - (pace_cv - 0.3) * 1.5)

        # Segment consistency
        if segment_results:
            segment_scores = [s['score'] for s in segment_results]
            avg_segment = np.mean(segment_scores)

            # Check for pattern variety
            patterns = [s['pattern'] for s in segment_results]
            unique_patterns = len(set(patterns))
            variety_bonus = min(0.15, unique_patterns * 0.05)
        else:
            avg_segment = 0.5
            variety_bonus = 0

        # Combine scores
        overall = (
            energy_score * 0.30 +
            peak_score * 0.20 +
            pace_score * 0.25 +
            avg_segment * 0.25 +
            variety_bonus
        )

        return min(1.0, max(0.0, overall))

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result for invalid input."""
        return {
            'overall_score': 0.5,
            'segment_scores': [],
            'engagement_events': [],
            'energy_metrics': self._empty_energy_metrics(),
            'pace_metrics': self._empty_pace_metrics(),
            'energy_curve': np.array([])
        }

    def _empty_energy_metrics(self) -> Dict[str, Any]:
        """Return empty energy metrics."""
        return {
            'mean_energy': 0.5,
            'std_energy': 0.0,
            'energy_range': 0.0,
            'coefficient_of_variation': 0.0,
            'peak_count': 0,
            'valley_count': 0,
            'peak_spacing_variance': 0.0,
            'buildup_count': 0,
            'release_count': 0
        }

    def _empty_pace_metrics(self) -> Dict[str, Any]:
        """Return empty pace metrics."""
        return {
            'mean_pace': 0.0,
            'pace_variance': 0.0,
            'pace_range': 0.0,
            'pace_cv': 0.0,
            'significant_shifts': 0,
            'pace_shifts': []
        }


def analyze_engagement_patterns(
    word_segments: List[WordSegment],
    spirit_result: Optional[SpiritAnalysisResult] = None,
    loudness_curve: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Convenience function for engagement pattern analysis.

    Args:
        word_segments: Word-level timing information
        spirit_result: Spirit Engine results (optional)
        loudness_curve: Loudness over time (optional)

    Returns:
        Dictionary with engagement pattern analysis results
    """
    detector = EngagementPatternDetector()
    return detector.analyze(word_segments, spirit_result, loudness_curve)
