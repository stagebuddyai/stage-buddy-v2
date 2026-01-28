"""
Stage Buddy V2 - Pacing Analyzer
Analyzes strategic pause usage for audience engagement.

Good Pacing Indicators:
- Strategic pauses after emotional moments (letting them land)
- Breath pauses at natural sentence boundaries
- Variation in pace (not monotonously fast or slow)
- Landing pauses before key reveals

Poor Pacing Indicators:
- Rushing through without pauses
- Pausing at awkward moments (mid-phrase)
- Monotonous pace throughout
- No variation in delivery speed
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging

from ..shared.data_structures import (
    WordSegment, PauseEvent, PauseType, EngagementEvent
)

logger = logging.getLogger(__name__)


# Pause duration thresholds (in seconds)
MICRO_PAUSE_MAX = 0.5       # Natural speech rhythm
BEAT_PAUSE_MIN = 0.5        # Separates ideas
BEAT_PAUSE_MAX = 1.0
BREATH_PAUSE_MIN = 1.0      # Sentence boundary
BREATH_PAUSE_MAX = 2.0
BREAK_PAUSE_MIN = 2.0       # Dramatic pause

# Optimal pauses per minute for spoken word (typically 4-8)
OPTIMAL_PAUSE_RATE_MIN = 4.0
OPTIMAL_PAUSE_RATE_MAX = 8.0

# Speech rate thresholds (words per minute)
SLOW_SPEECH_WPM = 100
NORMAL_SPEECH_WPM = 150
FAST_SPEECH_WPM = 180


class PacingAnalyzer:
    """
    Analyzes pacing patterns for audience engagement.

    Good pacing creates space for the audience to absorb content,
    while maintaining engagement through variation.
    """

    def __init__(
        self,
        segment_duration: float = 3.0,
        min_pause_duration: float = 0.3
    ):
        """
        Initialize the Pacing Analyzer.

        Args:
            segment_duration: Duration of analysis segments in seconds
            min_pause_duration: Minimum gap to consider a pause
        """
        self.segment_duration = segment_duration
        self.min_pause_duration = min_pause_duration

        logger.info("PacingAnalyzer initialized")

    def analyze(
        self,
        word_segments: List[WordSegment],
        pause_events: Optional[List[PauseEvent]] = None,
        loudness_curve: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Analyze pacing patterns in the performance.

        Args:
            word_segments: Word-level timing information
            pause_events: Pre-detected pauses (from Chest Engine if available)
            loudness_curve: Audio loudness over time (from Chest Engine if available)

        Returns:
            Dictionary with:
            - overall_score: 0-1 pacing score
            - segment_scores: Per-segment breakdown
            - engagement_events: Key pacing moments
            - metrics: Detailed metrics
        """
        if not word_segments:
            logger.warning("No word segments provided")
            return self._empty_result()

        logger.info(f"Analyzing pacing in {len(word_segments)} words")

        # Extract pauses from word segments if not provided
        if not pause_events:
            pause_events = self._detect_pauses(word_segments)

        # Calculate overall metrics
        overall_metrics = self._calculate_metrics(word_segments, pause_events)

        # Analyze by segments
        segment_results = self._analyze_by_segments(word_segments, pause_events)

        # Find engagement events (strategic pauses)
        engagement_events = self._find_strategic_pauses(word_segments, pause_events)

        # Calculate overall score
        overall_score = self._calculate_overall_score(overall_metrics, segment_results)

        return {
            'overall_score': overall_score,
            'segment_scores': segment_results,
            'engagement_events': engagement_events,
            'metrics': overall_metrics,
            'pause_events': pause_events
        }

    def _detect_pauses(
        self,
        word_segments: List[WordSegment]
    ) -> List[PauseEvent]:
        """Detect pauses from gaps between words."""
        pauses = []

        for i in range(1, len(word_segments)):
            prev_word = word_segments[i - 1]
            curr_word = word_segments[i]

            gap = curr_word.start_time - prev_word.end_time

            if gap >= self.min_pause_duration:
                # Classify pause type
                if gap < BEAT_PAUSE_MIN:
                    pause_type = PauseType.MICRO
                elif gap < BREATH_PAUSE_MIN:
                    pause_type = PauseType.BEAT
                elif gap < BREAK_PAUSE_MIN:
                    pause_type = PauseType.BREATH
                else:
                    pause_type = PauseType.BREAK

                # Check for punctuation context
                at_punctuation = self._has_punctuation(prev_word.word)

                pauses.append(PauseEvent(
                    pause_type=pause_type,
                    start_time=prev_word.end_time,
                    duration=gap,
                    preceding_word=prev_word.word,
                    following_word=curr_word.word,
                    at_punctuation=at_punctuation,
                    at_line_break=gap >= BREATH_PAUSE_MIN
                ))

        return pauses

    def _calculate_metrics(
        self,
        word_segments: List[WordSegment],
        pause_events: List[PauseEvent]
    ) -> Dict[str, Any]:
        """Calculate overall pacing metrics."""
        if not word_segments:
            return self._empty_metrics()

        # Duration
        duration = word_segments[-1].end_time - word_segments[0].start_time
        duration_minutes = duration / 60.0

        if duration_minutes == 0:
            return self._empty_metrics()

        # Word count and speech rate
        word_count = len(word_segments)
        words_per_minute = word_count / duration_minutes

        # Pause statistics
        pause_count = len(pause_events)
        pauses_per_minute = pause_count / duration_minutes

        # Pause type breakdown
        beat_pauses = sum(1 for p in pause_events if p.pause_type == PauseType.BEAT)
        breath_pauses = sum(1 for p in pause_events if p.pause_type == PauseType.BREATH)
        break_pauses = sum(1 for p in pause_events if p.pause_type == PauseType.BREAK)

        # Average pause duration
        avg_pause_duration = np.mean([p.duration for p in pause_events]) if pause_events else 0.0

        # Punctuation pause ratio (good pauses at natural breaks)
        punctuation_pauses = sum(1 for p in pause_events if p.at_punctuation)
        punctuation_ratio = punctuation_pauses / pause_count if pause_count > 0 else 0.0

        # Speech rate variation (good = varied, bad = monotonous)
        speech_rate_variation = self._calculate_rate_variation(word_segments)

        return {
            'duration_seconds': duration,
            'word_count': word_count,
            'words_per_minute': words_per_minute,
            'pause_count': pause_count,
            'pauses_per_minute': pauses_per_minute,
            'beat_pauses': beat_pauses,
            'breath_pauses': breath_pauses,
            'break_pauses': break_pauses,
            'avg_pause_duration': avg_pause_duration,
            'punctuation_ratio': punctuation_ratio,
            'speech_rate_variation': speech_rate_variation
        }

    def _calculate_rate_variation(
        self,
        word_segments: List[WordSegment]
    ) -> float:
        """Calculate speech rate variation across the performance."""
        if len(word_segments) < 10:
            return 0.5  # Not enough data

        # Calculate local speech rates in 5-second windows
        window_size = 5.0
        rates = []

        start_time = word_segments[0].start_time
        end_time = word_segments[-1].end_time

        current_time = start_time
        while current_time < end_time:
            window_end = min(current_time + window_size, end_time)

            # Count words in window
            window_words = [
                ws for ws in word_segments
                if ws.start_time >= current_time and ws.start_time < window_end
            ]

            if window_words:
                window_duration = window_end - current_time
                rate = len(window_words) / (window_duration / 60.0)  # WPM
                rates.append(rate)

            current_time = window_end

        if len(rates) < 2:
            return 0.5

        # Calculate coefficient of variation
        mean_rate = np.mean(rates)
        std_rate = np.std(rates)

        if mean_rate > 0:
            cv = std_rate / mean_rate
            # Normalize: 0.1-0.3 CV is good variation, <0.1 is monotonous, >0.5 is erratic
            if cv < 0.1:
                return cv / 0.1 * 0.5  # Low variation
            elif cv <= 0.3:
                return 0.5 + (cv - 0.1) / 0.2 * 0.5  # Ideal variation
            else:
                return max(0.3, 1.0 - (cv - 0.3) / 0.3 * 0.7)  # Too erratic
        else:
            return 0.5

    def _analyze_by_segments(
        self,
        word_segments: List[WordSegment],
        pause_events: List[PauseEvent]
    ) -> List[Dict[str, Any]]:
        """Analyze pacing in time-based segments."""
        if not word_segments:
            return []

        end_time = word_segments[-1].end_time
        segments = []

        current_time = 0.0
        while current_time < end_time:
            segment_end = min(current_time + self.segment_duration, end_time)

            # Get words in this segment
            segment_words = [
                ws for ws in word_segments
                if ws.start_time >= current_time and ws.start_time < segment_end
            ]

            # Get pauses in this segment
            segment_pauses = [
                p for p in pause_events
                if p.start_time >= current_time and p.start_time < segment_end
            ]

            if segment_words:
                # Calculate segment metrics
                segment_duration = segment_end - current_time
                wpm = len(segment_words) / (segment_duration / 60.0) if segment_duration > 0 else 0

                # Pause effectiveness
                has_strategic_pause = any(
                    p.pause_type in (PauseType.BEAT, PauseType.BREATH, PauseType.BREAK)
                    for p in segment_pauses
                )

                # Score this segment
                score = self._score_segment_pacing(wpm, segment_pauses, segment_duration)

                segments.append({
                    'start_time': current_time,
                    'end_time': segment_end,
                    'score': score,
                    'word_count': len(segment_words),
                    'pause_count': len(segment_pauses),
                    'words_per_minute': wpm,
                    'has_strategic_pause': has_strategic_pause
                })

            current_time = segment_end

        return segments

    def _score_segment_pacing(
        self,
        wpm: float,
        pauses: List[PauseEvent],
        duration: float
    ) -> float:
        """Score the pacing of a single segment."""
        score = 0.5  # Start neutral

        # Score based on speech rate
        if SLOW_SPEECH_WPM < wpm < FAST_SPEECH_WPM:
            rate_score = 1.0  # Ideal range
        elif wpm <= SLOW_SPEECH_WPM:
            rate_score = 0.6 + (wpm / SLOW_SPEECH_WPM) * 0.4
        else:
            rate_score = max(0.3, 1.0 - (wpm - FAST_SPEECH_WPM) / 100)

        # Score based on pause presence
        strategic_pauses = [p for p in pauses if p.pause_type in (PauseType.BEAT, PauseType.BREATH, PauseType.BREAK)]
        if strategic_pauses:
            # Has strategic pauses - good
            pause_score = min(1.0, len(strategic_pauses) * 0.3 + 0.4)

            # Bonus for punctuation alignment
            at_punctuation = [p for p in strategic_pauses if p.at_punctuation]
            if at_punctuation:
                pause_score = min(1.0, pause_score + 0.1)
        else:
            # No strategic pauses in this segment
            pause_score = 0.3

        # Combine scores
        score = rate_score * 0.4 + pause_score * 0.6

        return min(1.0, max(0.0, score))

    def _find_strategic_pauses(
        self,
        word_segments: List[WordSegment],
        pause_events: List[PauseEvent]
    ) -> List[EngagementEvent]:
        """Find pauses that are strategically effective for engagement."""
        events = []

        for pause in pause_events:
            # Strategic pauses are BEAT, BREATH, or BREAK at natural points
            if pause.pause_type == PauseType.BREAK:
                # Dramatic pause - high engagement
                events.append(EngagementEvent(
                    timestamp=pause.start_time,
                    duration=pause.duration,
                    event_type='strategic_pause',
                    engagement_level=0.9,
                    description=f"Dramatic pause ({pause.duration:.1f}s) - letting moment land"
                ))

            elif pause.pause_type == PauseType.BREATH and pause.at_punctuation:
                # Well-placed breath pause
                events.append(EngagementEvent(
                    timestamp=pause.start_time,
                    duration=pause.duration,
                    event_type='strategic_pause',
                    engagement_level=0.7,
                    description="Breath pause at natural break"
                ))

            elif pause.pause_type == PauseType.BEAT and pause.at_punctuation:
                # Beat pause at punctuation
                events.append(EngagementEvent(
                    timestamp=pause.start_time,
                    duration=pause.duration,
                    event_type='strategic_pause',
                    engagement_level=0.6,
                    description="Beat pause between ideas"
                ))

        return events

    def _calculate_overall_score(
        self,
        metrics: Dict[str, Any],
        segment_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall pacing score."""
        score = 0.5  # Start neutral

        # Pause rate score (optimal is 4-8 per minute)
        ppm = metrics['pauses_per_minute']
        if OPTIMAL_PAUSE_RATE_MIN <= ppm <= OPTIMAL_PAUSE_RATE_MAX:
            pause_rate_score = 1.0
        elif ppm < OPTIMAL_PAUSE_RATE_MIN:
            pause_rate_score = 0.4 + (ppm / OPTIMAL_PAUSE_RATE_MIN) * 0.6
        else:
            pause_rate_score = max(0.5, 1.0 - (ppm - OPTIMAL_PAUSE_RATE_MAX) / 10.0)

        # Speech rate score
        wpm = metrics['words_per_minute']
        if SLOW_SPEECH_WPM < wpm < FAST_SPEECH_WPM:
            rate_score = 1.0
        elif wpm <= SLOW_SPEECH_WPM:
            rate_score = 0.5 + (wpm / SLOW_SPEECH_WPM) * 0.5
        else:
            rate_score = max(0.3, 1.0 - (wpm - FAST_SPEECH_WPM) / 100)

        # Variation score
        variation_score = metrics['speech_rate_variation']

        # Punctuation alignment score
        punctuation_score = metrics['punctuation_ratio']

        # Segment consistency
        if segment_results:
            segment_scores = [s['score'] for s in segment_results]
            avg_segment = np.mean(segment_scores)
        else:
            avg_segment = 0.5

        # Combine scores
        overall = (
            pause_rate_score * 0.25 +
            rate_score * 0.20 +
            variation_score * 0.20 +
            punctuation_score * 0.15 +
            avg_segment * 0.20
        )

        return min(1.0, max(0.0, overall))

    def _has_punctuation(self, word: str) -> bool:
        """Check if word ends with punctuation."""
        return word.rstrip().endswith(('.', ',', '!', '?', ';', ':', '-', '...'))

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result for invalid input."""
        return {
            'overall_score': 0.5,
            'segment_scores': [],
            'engagement_events': [],
            'metrics': self._empty_metrics(),
            'pause_events': []
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics."""
        return {
            'duration_seconds': 0.0,
            'word_count': 0,
            'words_per_minute': 0.0,
            'pause_count': 0,
            'pauses_per_minute': 0.0,
            'beat_pauses': 0,
            'breath_pauses': 0,
            'break_pauses': 0,
            'avg_pause_duration': 0.0,
            'punctuation_ratio': 0.0,
            'speech_rate_variation': 0.5
        }


def analyze_pacing(
    word_segments: List[WordSegment],
    pause_events: Optional[List[PauseEvent]] = None
) -> Dict[str, Any]:
    """
    Convenience function for pacing analysis.

    Args:
        word_segments: Word-level timing information
        pause_events: Pre-detected pauses (optional)

    Returns:
        Dictionary with pacing analysis results
    """
    analyzer = PacingAnalyzer()
    return analyzer.analyze(word_segments, pause_events)
