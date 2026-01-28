"""
Stage Buddy V2 - Audience Engine
Main module that orchestrates audience engagement analysis.

The Audience Engine is the fourth S.T.A.R.R. module (20% weight).
It measures how effectively the performer engages their audience.

Core Scoring Components:
1. Direct Address (30%) - Speaking TO the audience, not AT them
2. Pacing for Engagement (25%) - Strategic pauses for absorption
3. Emotional Invitation (25%) - Inviting audience into the journey
4. Engagement Patterns (20%) - Delivery variation for impact

The Audience Engine is UNIQUE because it can synthesize signals from
Spirit, Chest, and Body engines when available, but also works standalone.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
import logging
import time

from ..shared.data_structures import (
    WordSegment, EmotionSegment, PauseEvent, ProsodyFeatures,
    SpiritAnalysisResult, EngagementEvent, AudienceSegment, AudienceAnalysisResult
)
from .direct_address_analyzer import DirectAddressAnalyzer
from .pacing_analyzer import PacingAnalyzer
from .emotional_invitation_scorer import EmotionalInvitationScorer
from .engagement_pattern_detector import EngagementPatternDetector

logger = logging.getLogger(__name__)


class AudienceEngine:
    """
    The Audience Engine analyzes audience engagement in spoken word performances.

    It answers the question: "Does the performer connect WITH the audience or
    perform AT them?"

    The engine:
    1. Analyzes direct address patterns (pronouns, rhetorical questions)
    2. Evaluates pacing effectiveness (strategic pauses)
    3. Measures emotional invitation (vulnerability, shared moments)
    4. Detects engagement patterns (energy variation, pace shifts)
    5. Produces an Audience score (1-5) with detailed feedback

    INTEGRATION: When Spirit/Chest/Body results are provided, the engine
    uses them to enhance accuracy. When not provided, it works standalone.
    """

    def __init__(
        self,
        segment_duration: float = 3.0
    ):
        """
        Initialize the Audience Engine.

        Args:
            segment_duration: Duration of analysis segments in seconds
        """
        logger.info("Initializing Audience Engine...")

        self.segment_duration = segment_duration

        # Initialize sub-analyzers
        self.direct_address_analyzer = DirectAddressAnalyzer(
            segment_duration=segment_duration
        )
        self.pacing_analyzer = PacingAnalyzer(
            segment_duration=segment_duration
        )
        self.emotional_invitation_scorer = EmotionalInvitationScorer(
            segment_duration=segment_duration
        )
        self.engagement_pattern_detector = EngagementPatternDetector(
            segment_duration=segment_duration
        )

        # Component weights (calibrated for audience engagement focus)
        # Direct address is most important for "speaking WITH" vs "speaking AT"
        self.weights = {
            'direct_address': 0.30,
            'pacing': 0.25,
            'emotional_invitation': 0.25,
            'engagement_patterns': 0.20
        }

        logger.info("Audience Engine initialized")

    def analyze(
        self,
        video_path: str,
        audio_path: str,
        transcript: Optional[str] = None,
        word_segments: Optional[List[WordSegment]] = None,
        spirit_result: Optional[SpiritAnalysisResult] = None,
        body_result: Optional[Any] = None,  # BodyAnalysisResult when implemented
        pause_events: Optional[List[PauseEvent]] = None,
        loudness_curve: Optional[np.ndarray] = None,
        prosody_features: Optional[List[ProsodyFeatures]] = None
    ) -> AudienceAnalysisResult:
        """
        Perform complete Audience analysis on a performance.

        Args:
            video_path: Path to video file
            audio_path: Path to audio file
            transcript: Full transcript text (required for full analysis)
            word_segments: Word-level timing (required for full analysis)
            spirit_result: Spirit Engine results (optional, enhances analysis)
            body_result: Body Engine results (optional, enhances analysis)
            pause_events: Pre-detected pauses from Chest Engine (optional)
            loudness_curve: Audio loudness over time (optional)
            prosody_features: Prosody timeline from Spirit Engine (optional)

        Returns:
            AudienceAnalysisResult with scores and detailed analysis
        """
        start_time = time.time()
        logger.info(f"Starting Audience analysis for: {video_path}")

        # Validate required inputs
        if not transcript or not word_segments:
            logger.warning("Missing transcript or word_segments - limited analysis available")
            return self._create_fallback_result(video_path, start_time)

        # Calculate duration
        duration = word_segments[-1].end_time if word_segments else 0.0

        # Step 1: Analyze direct address patterns
        logger.info("Analyzing direct address patterns...")
        direct_address_result = self.direct_address_analyzer.analyze(
            transcript, word_segments
        )

        # Step 2: Analyze pacing
        logger.info("Analyzing pacing for engagement...")
        pacing_result = self.pacing_analyzer.analyze(
            word_segments, pause_events, loudness_curve
        )

        # Step 3: Analyze emotional invitation
        logger.info("Analyzing emotional invitation...")
        emotional_result = self.emotional_invitation_scorer.analyze(
            transcript, word_segments, spirit_result, pause_events or pacing_result.get('pause_events', [])
        )

        # Step 4: Analyze engagement patterns
        logger.info("Analyzing engagement patterns...")
        # Use prosody features from Spirit result if available
        if spirit_result and hasattr(spirit_result, 'prosody_features'):
            prosody_features = spirit_result.prosody_features

        pattern_result = self.engagement_pattern_detector.analyze(
            word_segments, spirit_result, loudness_curve, prosody_features
        )

        # Step 5: Calculate component scores
        component_scores = {
            'direct_address': direct_address_result['overall_score'],
            'pacing': pacing_result['overall_score'],
            'emotional_invitation': emotional_result['overall_score'],
            'engagement_patterns': pattern_result['overall_score']
        }

        # Step 6: Calculate overall score with calibration
        overall_normalized = sum(
            score * self.weights[component]
            for component, score in component_scores.items()
        )

        # Apply calibration adjustments
        overall_normalized = self._apply_calibration(overall_normalized, component_scores)
        overall_score = self._normalize_to_5_scale(overall_normalized)

        # Step 7: Build segments
        segments = self._build_segments(
            word_segments,
            direct_address_result,
            pacing_result,
            emotional_result,
            pattern_result
        )

        # Step 8: Collect all engagement events
        all_events = (
            direct_address_result['engagement_events'] +
            pacing_result['engagement_events'] +
            emotional_result['engagement_events'] +
            pattern_result['engagement_events']
        )
        # Sort by timestamp
        all_events.sort(key=lambda e: e.timestamp)

        # Step 9: Build engagement curve
        engagement_curve = self._build_engagement_curve(
            duration, all_events, pattern_result.get('energy_curve')
        )

        # Step 10: Identify strength and weakness moments
        strength_moments, weakness_moments = self._identify_key_moments(
            segments, all_events, component_scores
        )

        processing_time_ms = (time.time() - start_time) * 1000
        logger.info(f"Audience analysis complete. Score: {overall_score:.2f}/5 ({processing_time_ms:.0f}ms)")

        return AudienceAnalysisResult(
            overall_score=overall_score,
            direct_address_score=component_scores['direct_address'],
            pacing_score=component_scores['pacing'],
            emotional_invitation_score=component_scores['emotional_invitation'],
            engagement_pattern_score=component_scores['engagement_patterns'],
            segments=segments,
            engagement_events=all_events,
            engagement_curve=engagement_curve,
            processing_time_ms=processing_time_ms,
            duration=duration,
            strength_moments=strength_moments,
            weakness_moments=weakness_moments
        )

    def _build_segments(
        self,
        word_segments: List[WordSegment],
        direct_address_result: Dict[str, Any],
        pacing_result: Dict[str, Any],
        emotional_result: Dict[str, Any],
        pattern_result: Dict[str, Any]
    ) -> List[AudienceSegment]:
        """Build unified audience segments from sub-analyzer results."""
        if not word_segments:
            return []

        duration = word_segments[-1].end_time
        segments = []

        # Get segment data from each analyzer
        da_segments = {s['start_time']: s for s in direct_address_result.get('segment_scores', [])}
        pacing_segments = {s['start_time']: s for s in pacing_result.get('segment_scores', [])}
        emotional_segments = {s['start_time']: s for s in emotional_result.get('segment_scores', [])}
        pattern_segments = {s['start_time']: s for s in pattern_result.get('segment_scores', [])}

        current_time = 0.0
        while current_time < duration:
            segment_end = min(current_time + self.segment_duration, duration)

            # Get scores from each analyzer (with fallbacks)
            da_score = da_segments.get(current_time, {}).get('score', 0.5)
            pacing_score = pacing_segments.get(current_time, {}).get('score', 0.5)
            emotional_score = emotional_segments.get(current_time, {}).get('score', 0.5)
            pattern_score = pattern_segments.get(current_time, {}).get('score', 0.5)

            # Calculate combined engagement score
            engagement_score = (
                da_score * self.weights['direct_address'] +
                pacing_score * self.weights['pacing'] +
                emotional_score * self.weights['emotional_invitation'] +
                pattern_score * self.weights['engagement_patterns']
            )

            segments.append(AudienceSegment(
                start_time=current_time,
                end_time=segment_end,
                direct_address_ratio=da_score,
                pause_effectiveness=pacing_score,
                emotional_openness=emotional_score,
                pace_variation=pattern_score,
                engagement_score=engagement_score
            ))

            current_time = segment_end

        return segments

    def _build_engagement_curve(
        self,
        duration: float,
        events: List[EngagementEvent],
        energy_curve: Optional[np.ndarray]
    ) -> np.ndarray:
        """Build engagement curve over time."""
        if duration <= 0:
            return np.array([])

        num_samples = max(1, int(duration * 10))  # 10 samples per second
        curve = np.zeros(num_samples)

        # Base curve from energy if available
        if energy_curve is not None and len(energy_curve) > 0:
            if len(energy_curve) != num_samples:
                curve = np.interp(
                    np.linspace(0, 1, num_samples),
                    np.linspace(0, 1, len(energy_curve)),
                    energy_curve
                ) * 0.5  # Weight energy at 50%
            else:
                curve = energy_curve * 0.5

        # Add engagement events
        for event in events:
            start_idx = int(event.timestamp / duration * num_samples)
            end_idx = int((event.timestamp + event.duration) / duration * num_samples)
            end_idx = min(end_idx, num_samples)

            if start_idx < num_samples:
                # Add event engagement level
                curve[start_idx:end_idx] += event.engagement_level * 0.5

        # Normalize to 0-1
        if np.max(curve) > 0:
            curve = curve / np.max(curve)

        return curve

    def _identify_key_moments(
        self,
        segments: List[AudienceSegment],
        events: List[EngagementEvent],
        component_scores: Dict[str, float]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Identify strength and weakness moments for feedback."""
        strengths = []
        weaknesses = []

        # Find strongest segments
        if segments:
            sorted_segments = sorted(segments, key=lambda s: s.engagement_score, reverse=True)

            # Top 3 strengths
            for seg in sorted_segments[:3]:
                if seg.engagement_score >= 0.6:
                    strengths.append({
                        'time': seg.start_time,
                        'score': seg.engagement_score,
                        'description': self._describe_strength(seg)
                    })

            # Bottom 3 weaknesses
            for seg in sorted_segments[-3:]:
                if seg.engagement_score < 0.5:
                    weaknesses.append({
                        'time': seg.start_time,
                        'score': seg.engagement_score,
                        'description': self._describe_weakness(seg)
                    })

        # Add high-engagement events as strengths
        for event in events:
            if event.engagement_level >= 0.8:
                strengths.append({
                    'time': event.timestamp,
                    'score': event.engagement_level,
                    'description': event.description
                })

        # Identify component weaknesses
        for component, score in component_scores.items():
            if score < 0.4:
                weaknesses.append({
                    'time': 0,
                    'score': score,
                    'description': self._describe_component_weakness(component)
                })

        return strengths[:5], weaknesses[:5]  # Limit to top 5 each

    def _describe_strength(self, segment: AudienceSegment) -> str:
        """Generate description for a strong segment."""
        # Find what made it strong
        best_component = max([
            ('direct_address_ratio', segment.direct_address_ratio, 'strong direct address'),
            ('pause_effectiveness', segment.pause_effectiveness, 'effective pacing'),
            ('emotional_openness', segment.emotional_openness, 'emotional openness'),
            ('pace_variation', segment.pace_variation, 'dynamic delivery')
        ], key=lambda x: x[1])

        return f"Strong engagement ({best_component[2]}) at {segment.start_time:.1f}s"

    def _describe_weakness(self, segment: AudienceSegment) -> str:
        """Generate description for a weak segment."""
        # Find what made it weak
        worst_component = min([
            ('direct_address_ratio', segment.direct_address_ratio, 'more direct address'),
            ('pause_effectiveness', segment.pause_effectiveness, 'better pausing'),
            ('emotional_openness', segment.emotional_openness, 'more emotional openness'),
            ('pace_variation', segment.pace_variation, 'more delivery variation')
        ], key=lambda x: x[1])

        return f"Needs {worst_component[2]} at {segment.start_time:.1f}s"

    def _describe_component_weakness(self, component: str) -> str:
        """Generate description for a weak component score."""
        descriptions = {
            'direct_address': "Speaking AT the audience rather than WITH them - try using 'you', 'we', rhetorical questions",
            'pacing': "Rushing through without letting moments land - add strategic pauses",
            'emotional_invitation': "Emotional walls up - invite the audience into your journey",
            'engagement_patterns': "Monotonous delivery - vary your energy and pace"
        }
        return descriptions.get(component, f"Low {component} score")

    def _apply_calibration(
        self,
        normalized_score: float,
        component_scores: Dict[str, float]
    ) -> float:
        """
        Apply calibration adjustments to better match POTS scoring.

        Key calibration insights:
        - Direct address is critical: no direct address = no audience connection
        - High scores require BOTH direct address AND emotional invitation
        - Energy/pacing alone doesn't create connection
        """
        calibrated = normalized_score

        # Floor effect: Very low direct address severely limits score
        # If performer doesn't speak TO audience, they're not connecting
        da_score = component_scores['direct_address']
        if da_score < 0.1:
            # Near-zero direct address = floor at ~1.0/5 (no connection)
            calibrated = calibrated * 0.2  # Very severe penalty
        elif da_score < 0.2:
            # Very low direct address = floor at ~1.5/5
            calibrated = calibrated * 0.4  # Severe penalty
        elif da_score < 0.4:
            # Low direct address = significant penalty
            calibrated = calibrated * 0.7

        # Ceiling boost: High direct address + emotional invitation = true connection
        ei_score = component_scores['emotional_invitation']
        if da_score > 0.7 and ei_score > 0.5:
            # Strong connection signals - boost towards 5/5
            boost = (da_score - 0.7) * 0.5 + (ei_score - 0.5) * 0.3
            calibrated = min(1.0, calibrated + boost)

        # Synergy bonus: All components above threshold = multiplicative boost
        all_above_threshold = all(score >= 0.6 for score in component_scores.values())
        if all_above_threshold:
            calibrated = min(1.0, calibrated * 1.15)

        # Anti-monotony: If only engagement patterns are high but others low, penalize
        ep_score = component_scores['engagement_patterns']
        pacing_score = component_scores['pacing']
        if ep_score > 0.7 and da_score < 0.3 and ei_score < 0.4:
            # Energy without connection - this is performing AT, not WITH
            calibrated = calibrated * 0.8

        return max(0.0, min(1.0, calibrated))

    def _normalize_to_5_scale(self, score: float) -> float:
        """Convert a 0-1 score to a 1-5 scale."""
        score = max(0.0, min(1.0, score))
        return 1.0 + score * 4.0

    def _create_fallback_result(
        self,
        video_path: str,
        start_time: float
    ) -> AudienceAnalysisResult:
        """Create a fallback result when full analysis isn't possible."""
        processing_time_ms = (time.time() - start_time) * 1000

        return AudienceAnalysisResult(
            overall_score=2.5,  # Neutral score
            direct_address_score=0.5,
            pacing_score=0.5,
            emotional_invitation_score=0.5,
            engagement_pattern_score=0.5,
            segments=[],
            engagement_events=[],
            engagement_curve=None,
            processing_time_ms=processing_time_ms,
            duration=0.0,
            strength_moments=[],
            weakness_moments=[{
                'time': 0,
                'score': 0,
                'description': 'Unable to perform full analysis - missing transcript/word segments'
            }]
        )

    def generate_feedback(self, result: AudienceAnalysisResult) -> str:
        """
        Generate coach-style feedback based on analysis results.

        Uses the POTS guidebook voice - direct, encouraging, focused on growth.
        """
        score = result.overall_score

        # Build feedback based on score range
        if score >= 4.5:
            opening = "You're speaking WITH the audience, not AT them! This is true connection."
        elif score >= 3.5:
            opening = "Good audience engagement - you're inviting them into your world."
        elif score >= 2.5:
            opening = "You're performing TO the audience, but not yet WITH them. Let them in."
        else:
            opening = "The audience feels like spectators, not participants. Break down that wall."

        feedback_parts = [opening]

        # Component-specific feedback
        if result.direct_address_score < 0.5:
            feedback_parts.append(
                "\nDirect Address: Speak TO the audience - use 'you', 'we', ask questions."
            )

        if result.pacing_score < 0.5:
            feedback_parts.append(
                "\nPacing: Let moments land. After something powerful, PAUSE. Let the audience absorb."
            )

        if result.emotional_invitation_score < 0.5:
            feedback_parts.append(
                "\nEmotional Invitation: You're guarding your emotions. Be vulnerable. Let them feel WITH you."
            )

        if result.engagement_pattern_score < 0.5:
            feedback_parts.append(
                "\nDelivery: Vary your energy. Monotony loses audiences. Build, release, build again."
            )

        # Highlight strengths
        if result.strength_moments:
            best = max(result.strength_moments, key=lambda x: x['score'])
            feedback_parts.append(f"\nStrong moment: {best['description']}")

        # Note: Audience score 2/5 for MID is intentional
        # Performers can have good energy but still not connect
        if 2.0 <= score <= 3.0:
            feedback_parts.append(
                "\nRemember: energy isn't connection. You can be dynamic but still distant."
            )

        return "\n".join(feedback_parts)


def analyze_audience(
    video_path: str,
    audio_path: str,
    transcript: str,
    word_segments: List[WordSegment],
    spirit_result: Optional[SpiritAnalysisResult] = None
) -> AudienceAnalysisResult:
    """
    Convenience function for Audience analysis.

    Args:
        video_path: Path to video file
        audio_path: Path to audio file
        transcript: Full transcript text
        word_segments: Word-level timing information
        spirit_result: Spirit Engine results (optional)

    Returns:
        AudienceAnalysisResult with complete analysis
    """
    engine = AudienceEngine()
    return engine.analyze(
        video_path=video_path,
        audio_path=audio_path,
        transcript=transcript,
        word_segments=word_segments,
        spirit_result=spirit_result
    )
