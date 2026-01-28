"""
Stage Buddy V2 - Emotional Invitation Scorer
Analyzes whether the performer invites the audience into the emotional journey.

Emotional Invitation Indicators:
- Vulnerability moments (intensity drops, voice softening)
- Emotional peaks with "space" (pauses after intense moments)
- Shared emotional language ("we feel", "you know that moment when")
- Build-up patterns that create anticipation
- Emotional variety that takes audience on a journey

Poor Emotional Invitation Indicators:
- Emotional walls up (constant high intensity, no vulnerability)
- Performing emotions AT audience rather than WITH them
- No space for audience to absorb emotional moments
- Flat emotional delivery (no peaks to share)
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging

from ..shared.data_structures import (
    EmotionSegment, WordSegment, PauseEvent, SpiritAnalysisResult,
    EngagementEvent, EMOTION_VA_MAP
)

logger = logging.getLogger(__name__)


# Vulnerability indicators in language
VULNERABILITY_WORDS = {
    'feel', 'felt', 'feeling', 'afraid', 'scared', 'fear',
    'love', 'loved', 'heart', 'hurt', 'pain', 'cry', 'tears',
    'hope', 'dream', 'wish', 'wonder', 'maybe', 'lost',
    'alone', 'lonely', 'broken', 'healing', 'remember',
    'miss', 'sorry', 'forgive', 'truth', 'honest', 'real',
    'young', 'world', 'together', 'carry', 'think', 'listen',
    'soul', 'spirit', 'life', 'death', 'mother', 'father',
    'child', 'home', 'believe', 'trust', 'need', 'want'
}

# Shared experience indicators
SHARED_EXPERIENCE_PHRASES = [
    "you know", "we all", "we feel", "don't we", "haven't we",
    "remember when", "that moment when", "you ever", "ever felt",
    "like when", "you understand", "we understand",
    "let me tell", "tell you", "you and me", "all of us",
    "think about", "feel it", "with me", "do you remember",
    "we carry", "we were", "what i mean", "felt it"
]


class EmotionalInvitationScorer:
    """
    Scores how well the performer invites the audience into the emotional journey.

    A high score means the performer creates shared emotional moments,
    shows vulnerability, and gives space for audience connection.
    """

    def __init__(
        self,
        segment_duration: float = 3.0,
        emotional_peak_threshold: float = 0.7
    ):
        """
        Initialize the Emotional Invitation Scorer.

        Args:
            segment_duration: Duration of analysis segments in seconds
            emotional_peak_threshold: Intensity threshold for emotional peaks
        """
        self.segment_duration = segment_duration
        self.emotional_peak_threshold = emotional_peak_threshold

        logger.info("EmotionalInvitationScorer initialized")

    def analyze(
        self,
        transcript: str,
        word_segments: List[WordSegment],
        spirit_result: Optional[SpiritAnalysisResult] = None,
        pause_events: Optional[List[PauseEvent]] = None
    ) -> Dict[str, Any]:
        """
        Analyze emotional invitation in the performance.

        Args:
            transcript: Full transcript text
            word_segments: Word-level timing information
            spirit_result: Spirit Engine results (optional, enhances analysis)
            pause_events: Detected pauses (optional, for space analysis)

        Returns:
            Dictionary with:
            - overall_score: 0-1 emotional invitation score
            - segment_scores: Per-segment breakdown
            - engagement_events: Key emotional invitation moments
            - metrics: Detailed metrics
        """
        if not transcript or not word_segments:
            logger.warning("No transcript or word segments provided")
            return self._empty_result()

        logger.info(f"Analyzing emotional invitation in {len(word_segments)} words")

        # Analyze language patterns
        language_metrics = self._analyze_language(transcript)

        # Analyze emotional dynamics
        if spirit_result:
            emotional_metrics = self._analyze_emotional_dynamics(
                spirit_result.vocal_emotions,
                pause_events or []
            )
        else:
            emotional_metrics = self._analyze_from_text(transcript, word_segments)

        # Analyze by segments
        segment_results = self._analyze_by_segments(
            word_segments, transcript, spirit_result, pause_events
        )

        # Find engagement events
        engagement_events = self._find_invitation_moments(
            word_segments, transcript, spirit_result, pause_events
        )

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            language_metrics, emotional_metrics, segment_results
        )

        return {
            'overall_score': overall_score,
            'segment_scores': segment_results,
            'engagement_events': engagement_events,
            'language_metrics': language_metrics,
            'emotional_metrics': emotional_metrics
        }

    def _analyze_language(self, transcript: str) -> Dict[str, Any]:
        """Analyze language patterns for emotional invitation."""
        words = transcript.lower().split()
        total_words = len(words)

        if total_words == 0:
            return self._empty_language_metrics()

        # Count vulnerability words
        vulnerability_count = sum(
            1 for w in words
            if w.strip('.,!?;:') in VULNERABILITY_WORDS
        )
        vulnerability_density = vulnerability_count / total_words

        # Count shared experience phrases
        text_lower = transcript.lower()
        shared_experience_count = sum(
            1 for phrase in SHARED_EXPERIENCE_PHRASES
            if phrase in text_lower
        )
        shared_experience_density = shared_experience_count / (total_words / 50)  # Per 50 words

        # Emotional language richness (unique emotional words)
        emotional_words_found = set(
            w.strip('.,!?;:') for w in words
            if w.strip('.,!?;:') in VULNERABILITY_WORDS
        )
        emotional_richness = min(1.0, len(emotional_words_found) / 10)  # 10+ unique = full score

        return {
            'total_words': total_words,
            'vulnerability_count': vulnerability_count,
            'vulnerability_density': vulnerability_density,
            'shared_experience_count': shared_experience_count,
            'shared_experience_density': shared_experience_density,
            'emotional_richness': emotional_richness
        }

    def _analyze_emotional_dynamics(
        self,
        vocal_emotions: List[EmotionSegment],
        pause_events: List[PauseEvent]
    ) -> Dict[str, Any]:
        """Analyze emotional dynamics using Spirit Engine data."""
        if not vocal_emotions:
            return self._empty_emotional_metrics()

        # Find emotional peaks
        intensities = [e.intensity for e in vocal_emotions]
        peaks = [
            e for e in vocal_emotions
            if e.intensity >= self.emotional_peak_threshold
        ]
        peak_count = len(peaks)

        # Find vulnerability moments (low intensity in emotional context)
        vulnerability_moments = [
            e for e in vocal_emotions
            if e.intensity < 0.5 and abs(e.valence) > 0.3  # Low intensity but emotional
        ]
        vulnerability_count = len(vulnerability_moments)

        # Analyze if peaks have "space" (pauses nearby)
        peaks_with_space = 0
        for peak in peaks:
            # Check for pause within 2 seconds after peak
            nearby_pauses = [
                p for p in pause_events
                if peak.end_time <= p.start_time <= peak.end_time + 2.0
            ]
            if nearby_pauses:
                peaks_with_space += 1

        space_after_peaks = peaks_with_space / peak_count if peak_count > 0 else 0.0

        # Intensity variation (shows emotional journey)
        if len(intensities) > 1:
            intensity_range = max(intensities) - min(intensities)
            intensity_std = np.std(intensities)
        else:
            intensity_range = 0.0
            intensity_std = 0.0

        # Emotional journey score (variety of emotions)
        unique_emotions = len(set(e.emotion for e in vocal_emotions))
        emotional_variety = min(1.0, unique_emotions / 4)  # 4+ emotions = full score

        return {
            'peak_count': peak_count,
            'vulnerability_count': vulnerability_count,
            'space_after_peaks': space_after_peaks,
            'intensity_range': intensity_range,
            'intensity_std': intensity_std,
            'emotional_variety': emotional_variety
        }

    def _analyze_from_text(
        self,
        transcript: str,
        word_segments: List[WordSegment]
    ) -> Dict[str, Any]:
        """Fallback analysis when Spirit Engine data not available."""
        # Simple heuristic: estimate emotional dynamics from text patterns
        words = transcript.lower().split()

        # Count intensity markers
        high_intensity_words = {
            'never', 'always', 'must', 'need', 'now', 'stop', 'help',
            'please', 'god', 'damn', 'hell', 'love', 'hate', 'kill'
        }

        low_intensity_words = {
            'maybe', 'perhaps', 'sometimes', 'quietly', 'softly',
            'gently', 'slowly', 'whisper', 'wonder', 'dream'
        }

        high_count = sum(1 for w in words if w.strip('.,!?;:') in high_intensity_words)
        low_count = sum(1 for w in words if w.strip('.,!?;:') in low_intensity_words)

        # Estimate dynamics
        total = len(words)
        if total > 0:
            intensity_range = abs(high_count - low_count) / (total / 20)  # Normalized
            has_variation = high_count > 0 and low_count > 0
        else:
            intensity_range = 0.0
            has_variation = False

        return {
            'peak_count': high_count,
            'vulnerability_count': low_count,
            'space_after_peaks': 0.5,  # Unknown without pause data
            'intensity_range': min(1.0, intensity_range),
            'intensity_std': intensity_range * 0.5,
            'emotional_variety': 0.5 if has_variation else 0.3
        }

    def _analyze_by_segments(
        self,
        word_segments: List[WordSegment],
        transcript: str,
        spirit_result: Optional[SpiritAnalysisResult],
        pause_events: Optional[List[PauseEvent]]
    ) -> List[Dict[str, Any]]:
        """Analyze emotional invitation in time-based segments."""
        if not word_segments:
            return []

        end_time = word_segments[-1].end_time
        segments = []

        # Get emotional timeline if available
        vocal_emotions = spirit_result.vocal_emotions if spirit_result else []

        current_time = 0.0
        while current_time < end_time:
            segment_end = min(current_time + self.segment_duration, end_time)

            # Get words in this segment
            segment_words = [
                ws for ws in word_segments
                if ws.start_time >= current_time and ws.start_time < segment_end
            ]

            if segment_words:
                segment_text = ' '.join(ws.word for ws in segment_words)

                # Get emotions in this segment
                segment_emotions = [
                    e for e in vocal_emotions
                    if e.start_time >= current_time and e.start_time < segment_end
                ]

                # Get pauses in this segment
                segment_pauses = [
                    p for p in (pause_events or [])
                    if p.start_time >= current_time and p.start_time < segment_end
                ]

                # Score this segment
                score = self._score_segment(
                    segment_text, segment_emotions, segment_pauses
                )

                segments.append({
                    'start_time': current_time,
                    'end_time': segment_end,
                    'score': score,
                    'word_count': len(segment_words),
                    'has_vulnerability': self._has_vulnerability_language(segment_text),
                    'has_emotional_peak': any(
                        e.intensity >= self.emotional_peak_threshold
                        for e in segment_emotions
                    )
                })

            current_time = segment_end

        return segments

    def _score_segment(
        self,
        text: str,
        emotions: List[EmotionSegment],
        pauses: List[PauseEvent]
    ) -> float:
        """Score emotional invitation for a single segment."""
        score = 0.5  # Start neutral

        # Language score
        words = text.lower().split()
        vuln_count = sum(
            1 for w in words
            if w.strip('.,!?;:') in VULNERABILITY_WORDS
        )
        if vuln_count > 0:
            language_score = min(1.0, 0.5 + vuln_count * 0.15)
        else:
            language_score = 0.4

        # Check for shared experience language
        text_lower = text.lower()
        has_shared = any(phrase in text_lower for phrase in SHARED_EXPERIENCE_PHRASES)
        if has_shared:
            language_score = min(1.0, language_score + 0.2)

        # Emotional dynamics score
        if emotions:
            intensities = [e.intensity for e in emotions]
            intensity_range = max(intensities) - min(intensities) if len(intensities) > 1 else 0
            has_peak = any(e.intensity >= self.emotional_peak_threshold for e in emotions)
            has_low = any(e.intensity < 0.4 for e in emotions)

            if has_peak and has_low:
                dynamics_score = 0.9  # Great dynamic range
            elif has_peak:
                dynamics_score = 0.7
            elif has_low:
                dynamics_score = 0.6  # Vulnerability without peaks
            else:
                dynamics_score = 0.5
        else:
            dynamics_score = 0.5

        # Space score (pauses after intensity)
        if pauses:
            space_score = min(1.0, 0.5 + len(pauses) * 0.1)
        else:
            space_score = 0.4

        # Combine scores
        score = language_score * 0.4 + dynamics_score * 0.4 + space_score * 0.2

        return min(1.0, max(0.0, score))

    def _has_vulnerability_language(self, text: str) -> bool:
        """Check if text contains vulnerability language."""
        words = text.lower().split()
        return any(
            w.strip('.,!?;:') in VULNERABILITY_WORDS
            for w in words
        )

    def _find_invitation_moments(
        self,
        word_segments: List[WordSegment],
        transcript: str,
        spirit_result: Optional[SpiritAnalysisResult],
        pause_events: Optional[List[PauseEvent]]
    ) -> List[EngagementEvent]:
        """Find specific moments of emotional invitation."""
        events = []

        # Find vulnerability word moments
        for ws in word_segments:
            if ws.word.lower().strip('.,!?;:') in VULNERABILITY_WORDS:
                events.append(EngagementEvent(
                    timestamp=ws.start_time,
                    duration=ws.duration,
                    event_type='emotional_peak',
                    engagement_level=0.7,
                    description=f"Vulnerability moment: '{ws.word}'"
                ))

        # Find shared experience phrases
        text_lower = transcript.lower()
        for phrase in SHARED_EXPERIENCE_PHRASES:
            if phrase in text_lower:
                # Find approximate timing
                idx = text_lower.find(phrase)
                words_before = text_lower[:idx].split()
                if words_before and len(word_segments) > len(words_before):
                    ws = word_segments[min(len(words_before), len(word_segments) - 1)]
                    events.append(EngagementEvent(
                        timestamp=ws.start_time,
                        duration=2.0,
                        event_type='emotional_peak',
                        engagement_level=0.8,
                        description=f"Shared experience: '{phrase}'"
                    ))

        # Find emotional peaks with space
        if spirit_result and pause_events:
            for emotion in spirit_result.vocal_emotions:
                if emotion.intensity >= self.emotional_peak_threshold:
                    # Check for pause after
                    nearby_pauses = [
                        p for p in pause_events
                        if emotion.end_time <= p.start_time <= emotion.end_time + 2.0
                    ]
                    if nearby_pauses:
                        events.append(EngagementEvent(
                            timestamp=emotion.start_time,
                            duration=emotion.duration + nearby_pauses[0].duration,
                            event_type='emotional_peak',
                            engagement_level=0.9,
                            description=f"Emotional peak with space: {emotion.emotion.value}"
                        ))

        return events

    def _calculate_overall_score(
        self,
        language_metrics: Dict[str, Any],
        emotional_metrics: Dict[str, Any],
        segment_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall emotional invitation score."""
        # Language component (shared experience, vulnerability)
        language_score = (
            min(1.0, language_metrics['vulnerability_density'] * 20) * 0.4 +
            min(1.0, language_metrics['shared_experience_density']) * 0.3 +
            language_metrics['emotional_richness'] * 0.3
        )

        # Emotional dynamics component
        emotional_score = (
            emotional_metrics['emotional_variety'] * 0.3 +
            min(1.0, emotional_metrics['intensity_range']) * 0.3 +
            emotional_metrics['space_after_peaks'] * 0.2 +
            min(1.0, emotional_metrics['vulnerability_count'] / 3) * 0.2
        )

        # Segment consistency
        if segment_results:
            segment_scores = [s['score'] for s in segment_results]
            avg_segment = np.mean(segment_scores)
        else:
            avg_segment = 0.5

        # Combine
        overall = (
            language_score * 0.35 +
            emotional_score * 0.40 +
            avg_segment * 0.25
        )

        return min(1.0, max(0.0, overall))

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result for invalid input."""
        return {
            'overall_score': 0.5,
            'segment_scores': [],
            'engagement_events': [],
            'language_metrics': self._empty_language_metrics(),
            'emotional_metrics': self._empty_emotional_metrics()
        }

    def _empty_language_metrics(self) -> Dict[str, Any]:
        """Return empty language metrics."""
        return {
            'total_words': 0,
            'vulnerability_count': 0,
            'vulnerability_density': 0.0,
            'shared_experience_count': 0,
            'shared_experience_density': 0.0,
            'emotional_richness': 0.0
        }

    def _empty_emotional_metrics(self) -> Dict[str, Any]:
        """Return empty emotional metrics."""
        return {
            'peak_count': 0,
            'vulnerability_count': 0,
            'space_after_peaks': 0.0,
            'intensity_range': 0.0,
            'intensity_std': 0.0,
            'emotional_variety': 0.0
        }


def analyze_emotional_invitation(
    transcript: str,
    word_segments: List[WordSegment],
    spirit_result: Optional[SpiritAnalysisResult] = None
) -> Dict[str, Any]:
    """
    Convenience function for emotional invitation analysis.

    Args:
        transcript: Full transcript text
        word_segments: Word-level timing information
        spirit_result: Spirit Engine results (optional)

    Returns:
        Dictionary with emotional invitation analysis results
    """
    analyzer = EmotionalInvitationScorer()
    return analyzer.analyze(transcript, word_segments, spirit_result)
