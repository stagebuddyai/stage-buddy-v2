"""
Report Generator - Structured Performance Report Output

Generates PerformanceReport with:
- Overall and per-engine scores with sub-components
- Key moments timeline
- Performance curve
- Coach feedback (template or OpenAI)
- JSON output for frontend rendering
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, TYPE_CHECKING

import numpy as np

from python.analysis_modules.shared.data_structures import (
    PerformanceTimeline,
)

if TYPE_CHECKING:
    from .starr_orchestrator import EngineResults
    from .coach_feedback import CoachFeedbackGenerator

logger = logging.getLogger(__name__)

# Grade thresholds (1-5 scale)
GRADE_THRESHOLDS = [
    (4.5, "A+"),
    (4.2, "A"),
    (4.0, "A-"),
    (3.7, "B+"),
    (3.3, "B"),
    (3.0, "B-"),
    (2.7, "C+"),
    (2.3, "C"),
    (2.0, "C-"),
    (1.7, "D+"),
    (1.3, "D"),
    (1.0, "D-"),
    (0.0, "F"),
]


@dataclass
class KeyMoment:
    """A significant moment during the performance."""
    timestamp: float
    duration: float
    moment_type: str            # "peak", "opportunity", "breakthrough", "stumble"
    engines_involved: List[str]
    score_at_moment: float
    description: str
    coach_note: str


@dataclass
class PerformanceReport:
    """Complete S.T.A.R.R. performance analysis report."""

    # Overall
    overall_score: float
    overall_grade: str

    # Spirit Engine (30%)
    spirit_score: float
    spirit_subscores: Dict[str, float]
    spirit_feedback: str

    # Chest Engine (25%)
    chest_score: float
    chest_subscores: Dict[str, float]
    chest_feedback: str

    # Body Engine (25%)
    body_score: float
    body_subscores: Dict[str, float]
    body_feedback: str

    # Audience Engine (20%)
    audience_score: float
    audience_subscores: Dict[str, float]
    audience_feedback: str

    # Timeline & Moments
    key_moments: List[KeyMoment]
    performance_curve: Optional[np.ndarray]

    # Coach Summary
    coach_summary: str
    top_strengths: List[str]
    growth_areas: List[str]

    # Metadata
    duration_seconds: float
    processing_time_ms: float
    video_path: str
    performance_id: str = ""

    # Engine errors (if any engine failed gracefully)
    engine_errors: Dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        """Generate JSON report suitable for frontend rendering."""
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "performance_id": self.performance_id,
            "overall": {
                "score": round(self.overall_score, 2),
                "grade": self.overall_grade,
                "summary": self.coach_summary,
            },
            "pillars": [
                {
                    "name": "Spirit",
                    "weight": 0.30,
                    "score": round(self.spirit_score, 2),
                    "subscores": {
                        k: round(v, 2)
                        for k, v in self.spirit_subscores.items()
                    },
                    "feedback": self.spirit_feedback,
                    "icon": "flame",
                },
                {
                    "name": "Chest",
                    "weight": 0.25,
                    "score": round(self.chest_score, 2),
                    "subscores": {
                        k: round(v, 2)
                        for k, v in self.chest_subscores.items()
                    },
                    "feedback": self.chest_feedback,
                    "icon": "lungs",
                },
                {
                    "name": "Body",
                    "weight": 0.25,
                    "score": round(self.body_score, 2),
                    "subscores": {
                        k: round(v, 2)
                        for k, v in self.body_subscores.items()
                    },
                    "feedback": self.body_feedback,
                    "icon": "person",
                },
                {
                    "name": "Audience",
                    "weight": 0.20,
                    "score": round(self.audience_score, 2),
                    "subscores": {
                        k: round(v, 2)
                        for k, v in self.audience_subscores.items()
                    },
                    "feedback": self.audience_feedback,
                    "icon": "users",
                },
            ],
            "timeline": {
                "duration_seconds": round(self.duration_seconds, 1),
                "key_moments": [
                    {
                        "timestamp": round(m.timestamp, 1),
                        "duration": round(m.duration, 1),
                        "type": m.moment_type,
                        "engines_involved": m.engines_involved,
                        "score_at_moment": round(m.score_at_moment, 2),
                        "description": m.description,
                        "coach_note": m.coach_note,
                    }
                    for m in self.key_moments
                ],
                "engagement_curve": (
                    self.performance_curve.tolist()
                    if self.performance_curve is not None
                    else []
                ),
            },
            "growth_plan": {
                "top_strengths": self.top_strengths,
                "focus_areas": self.growth_areas,
            },
            "metadata": {
                "duration_seconds": round(self.duration_seconds, 1),
                "processing_time_ms": round(self.processing_time_ms, 1),
                "video_path": self.video_path,
                "engine_errors": self.engine_errors,
            },
        }


def _score_to_grade(score: float) -> str:
    """Convert a 1-5 score to a letter grade."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _to_display_score(raw: float) -> float:
    """
    Convert a raw 0-1 score to 1-5 display scale.
    If the score is already on 1-5 scale (> 1.0), return as-is.
    """
    if raw > 1.0:
        return min(raw, 5.0)
    return 1.0 + raw * 4.0


class ReportGenerator:
    """
    Generates PerformanceReport from engine results and timeline.
    """

    def generate(
        self,
        timeline: PerformanceTimeline,
        engine_results: "EngineResults",
        coach: "CoachFeedbackGenerator",
        video_path: str,
        processing_time_ms: float,
    ) -> PerformanceReport:
        """
        Generate a complete PerformanceReport.

        Args:
            timeline: Unified performance timeline
            engine_results: Results from all engines
            coach: Coach feedback generator
            video_path: Original video path
            processing_time_ms: Total processing time

        Returns:
            PerformanceReport with all scores, feedback, and moments
        """
        # Extract sub-scores from each engine
        spirit_subscores = self._extract_spirit_subscores(engine_results)
        chest_subscores = self._extract_chest_subscores(engine_results)
        body_subscores = self._extract_body_subscores(engine_results)
        audience_subscores = self._extract_audience_subscores(engine_results)

        # Detect key moments
        key_moments = self._detect_key_moments(timeline, engine_results)

        # Build performance curve
        from .timeline_builder import TimelineBuilder
        tb = TimelineBuilder()
        performance_curve = tb.build_performance_curve(timeline)

        # Build partial report for feedback generation
        report = PerformanceReport(
            overall_score=timeline.overall_score,
            overall_grade=_score_to_grade(timeline.overall_score),
            spirit_score=timeline.spirit_score,
            spirit_subscores=spirit_subscores,
            spirit_feedback="",
            chest_score=timeline.chest_score,
            chest_subscores=chest_subscores,
            chest_feedback="",
            body_score=timeline.body_score,
            body_subscores=body_subscores,
            body_feedback="",
            audience_score=timeline.audience_score,
            audience_subscores=audience_subscores,
            audience_feedback="",
            key_moments=key_moments,
            performance_curve=performance_curve,
            coach_summary="",
            top_strengths=[],
            growth_areas=[],
            duration_seconds=timeline.duration_seconds,
            processing_time_ms=processing_time_ms,
            video_path=video_path,
            performance_id=str(uuid.uuid4())[:8],
            engine_errors=engine_results.errors,
        )

        # Generate coach feedback for each engine
        report.spirit_feedback = coach.generate_feedback(report, "spirit")
        report.chest_feedback = coach.generate_feedback(report, "chest")
        report.body_feedback = coach.generate_feedback(report, "body")
        report.audience_feedback = coach.generate_feedback(report, "audience")
        report.coach_summary = coach.generate_feedback(report, "overall")

        # Generate growth plan
        report.top_strengths = self._identify_strengths(report, engine_results)
        report.growth_areas = self._identify_growth_areas(report, engine_results)

        return report

    def _extract_spirit_subscores(
        self, engine_results: "EngineResults"
    ) -> Dict[str, float]:
        """Extract Spirit Engine sub-component scores."""
        if engine_results.spirit is None:
            return {
                "emotion_alignment": 0.0,
                "transitions": 0.0,
                "range": 0.0,
                "settling": 0.0,
            }

        r = engine_results.spirit
        return {
            "emotion_alignment": _to_display_score(r.emotion_alignment_score),
            "transitions": _to_display_score(r.emotional_transition_score),
            "range": _to_display_score(r.emotional_range_score),
            "settling": _to_display_score(r.settling_score),
        }

    def _extract_chest_subscores(
        self, engine_results: "EngineResults"
    ) -> Dict[str, float]:
        """Extract Chest Engine sub-component scores."""
        if engine_results.chest is None:
            return {
                "breath_control": 0.0,
                "projection": 0.0,
                "pause_technique": 0.0,
                "vocal_health": 0.0,
            }

        r = engine_results.chest
        return {
            "breath_control": _to_display_score(r.breath_control_score),
            "projection": _to_display_score(r.projection_score),
            "pause_technique": _to_display_score(r.pause_technique_score),
            "vocal_health": _to_display_score(r.vocal_health_score),
        }

    def _extract_body_subscores(
        self, engine_results: "EngineResults"
    ) -> Dict[str, float]:
        """Extract Body Engine sub-component scores."""
        if engine_results.body is None:
            return {
                "gesture_intentionality": 0.0,
                "stage_presence": 0.0,
                "eye_contact": 0.0,
                "physical_vocal_sync": 0.0,
            }

        r = engine_results.body
        return {
            "gesture_intentionality": _to_display_score(r.gesture_score),
            "stage_presence": _to_display_score(r.stage_presence_score),
            "eye_contact": _to_display_score(r.eye_contact_score),
            "physical_vocal_sync": _to_display_score(r.alignment_score),
        }

    def _extract_audience_subscores(
        self, engine_results: "EngineResults"
    ) -> Dict[str, float]:
        """Extract Audience Engine sub-component scores."""
        if engine_results.audience is None:
            return {
                "direct_address": 0.0,
                "pacing": 0.0,
                "emotional_invitation": 0.0,
                "engagement_patterns": 0.0,
            }

        r = engine_results.audience
        return {
            "direct_address": _to_display_score(r.direct_address_score),
            "pacing": _to_display_score(r.pacing_score),
            "emotional_invitation": _to_display_score(r.emotional_invitation_score),
            "engagement_patterns": _to_display_score(r.engagement_pattern_score),
        }

    def _detect_key_moments(
        self,
        timeline: PerformanceTimeline,
        engine_results: "EngineResults",
    ) -> List[KeyMoment]:
        """
        Detect significant moments in the performance.

        Moment types:
        - peak: All engines aligned, high scores
        - breakthrough: Sudden improvement from previous section
        - opportunity: Good foundation but one engine lagging
        - stumble: Multiple engines flagged issues
        """
        moments = []

        # Collect strength and weakness moments from all engines
        strength_moments = []
        weakness_moments = []

        if engine_results.spirit:
            for m in engine_results.spirit.strength_moments:
                strength_moments.append(("spirit", m))
            for m in engine_results.spirit.misalignment_moments:
                weakness_moments.append(("spirit", m))

        if engine_results.chest:
            for m in engine_results.chest.strength_moments:
                strength_moments.append(("chest", m))
            for m in engine_results.chest.improvement_areas:
                weakness_moments.append(("chest", m))

        if engine_results.body:
            for m in engine_results.body.strong_moments:
                strength_moments.append(("body", m))
            for m in engine_results.body.weak_moments:
                weakness_moments.append(("body", m))

        if engine_results.audience:
            for m in engine_results.audience.strength_moments:
                strength_moments.append(("audience", m))
            for m in engine_results.audience.weakness_moments:
                weakness_moments.append(("audience", m))

        # Group moments by time window (5 second windows)
        window = 5.0
        duration = timeline.duration_seconds

        if duration <= 0:
            return moments

        num_windows = max(1, int(duration / window))

        for w in range(num_windows):
            t_start = w * window
            t_end = t_start + window

            # Find strength/weakness moments in this window
            window_strengths = []
            window_weaknesses = []

            for engine, m in strength_moments:
                ts = m.get("timestamp", m.get("start_time", -1))
                if t_start <= ts < t_end:
                    window_strengths.append((engine, m))

            for engine, m in weakness_moments:
                ts = m.get("timestamp", m.get("start_time", -1))
                if t_start <= ts < t_end:
                    window_weaknesses.append((engine, m))

            # Classify the window
            if len(window_strengths) >= 2 and len(window_weaknesses) == 0:
                # Peak: multiple engines report strength, no weaknesses
                engines = list(set(e for e, _ in window_strengths))
                desc_parts = [
                    m.get("description", m.get("reason", "strong moment"))
                    for _, m in window_strengths[:2]
                ]
                moments.append(KeyMoment(
                    timestamp=t_start,
                    duration=window,
                    moment_type="peak",
                    engines_involved=engines,
                    score_at_moment=self._estimate_score_at_time(
                        timeline, t_start, t_end
                    ),
                    description=f"Everything aligned - {', '.join(desc_parts)}",
                    coach_note="THIS is the performer you're becoming. Bottle this energy.",
                ))

            elif (
                len(window_strengths) >= 1
                and len(window_weaknesses) >= 1
                and len(window_strengths) > len(window_weaknesses)
            ):
                # Opportunity: good foundation but something lagging
                strong_engines = list(set(e for e, _ in window_strengths))
                weak_engines = list(set(e for e, _ in window_weaknesses))
                weak_desc = window_weaknesses[0][1].get(
                    "description", window_weaknesses[0][1].get("reason", "needs attention")
                )
                moments.append(KeyMoment(
                    timestamp=t_start,
                    duration=window,
                    moment_type="opportunity",
                    engines_involved=strong_engines + weak_engines,
                    score_at_moment=self._estimate_score_at_time(
                        timeline, t_start, t_end
                    ),
                    description=f"Strong foundation but {weak_desc}",
                    coach_note=(
                        f"The {', '.join(strong_engines)} is working. "
                        f"Now let the {', '.join(weak_engines)} catch up."
                    ),
                ))

            elif len(window_weaknesses) >= 2:
                # Stumble: multiple engines flagged issues
                engines = list(set(e for e, _ in window_weaknesses))
                desc_parts = [
                    m.get("description", m.get("reason", "needs work"))
                    for _, m in window_weaknesses[:2]
                ]
                moments.append(KeyMoment(
                    timestamp=t_start,
                    duration=window,
                    moment_type="stumble",
                    engines_involved=engines,
                    score_at_moment=self._estimate_score_at_time(
                        timeline, t_start, t_end
                    ),
                    description=f"Multiple areas need attention - {', '.join(desc_parts)}",
                    coach_note=(
                        "This section needs some love. Take it slow, "
                        "breathe into it, and let each line land."
                    ),
                ))

        # Detect breakthroughs by looking for score jumps between windows
        if len(moments) >= 2:
            for i in range(1, len(moments)):
                prev = moments[i - 1]
                curr = moments[i]
                if (
                    prev.moment_type in ("stumble", "opportunity")
                    and curr.moment_type == "peak"
                ):
                    curr.moment_type = "breakthrough"
                    curr.coach_note = (
                        "You found your way through. That recovery? That's GROWTH. "
                        "Remember this feeling."
                    )

        # Limit to most impactful moments (max 10)
        moments.sort(key=lambda m: (
            {"peak": 4, "breakthrough": 3, "opportunity": 2, "stumble": 1}.get(
                m.moment_type, 0
            ),
            m.score_at_moment,
        ), reverse=True)

        return moments[:10]

    def _estimate_score_at_time(
        self,
        timeline: PerformanceTimeline,
        t_start: float,
        t_end: float,
    ) -> float:
        """Estimate the combined performance score at a specific time window."""
        scores = []

        # Check engagement events in this window
        for event in timeline.engagement_events:
            if t_start <= event.timestamp < t_end:
                scores.append(event.engagement_level)

        # Check body segments
        for seg in timeline.body_segments:
            if seg.start_time < t_end and seg.end_time > t_start:
                scores.append(seg.physical_energy)

        if scores:
            return sum(scores) / len(scores) * 5.0  # Scale to 1-5

        # Fallback to overall score
        return timeline.overall_score

    def _identify_strengths(
        self,
        report: PerformanceReport,
        engine_results: "EngineResults",
    ) -> List[str]:
        """Identify top 3 strengths from the analysis."""
        candidates = []

        # Check each engine's sub-scores for standouts
        all_subscores = [
            ("spirit", report.spirit_subscores, report.spirit_score),
            ("chest", report.chest_subscores, report.chest_score),
            ("body", report.body_subscores, report.body_score),
            ("audience", report.audience_subscores, report.audience_score),
        ]

        # Engine-level strengths
        for engine_name, subscores, overall in all_subscores:
            if overall >= 3.5:
                candidates.append((overall, self._strength_phrase(engine_name, overall)))
            # Sub-score level strengths
            for sub_name, sub_val in subscores.items():
                if sub_val >= 4.0:
                    candidates.append(
                        (sub_val, self._subscore_strength_phrase(engine_name, sub_name, sub_val))
                    )

        # Sort by score descending, take top 3
        candidates.sort(key=lambda x: x[0], reverse=True)
        strengths = [phrase for _, phrase in candidates[:3]]

        # Ensure we always have 3 strengths
        if len(strengths) < 3:
            defaults = [
                "Willingness to perform and share your work",
                "Commitment to growth as a performer",
                "Authenticity in your artistic expression",
            ]
            for d in defaults:
                if len(strengths) >= 3:
                    break
                if d not in strengths:
                    strengths.append(d)

        return strengths[:3]

    def _identify_growth_areas(
        self,
        report: PerformanceReport,
        engine_results: "EngineResults",
    ) -> List[str]:
        """Identify top 3 areas for improvement."""
        candidates = []

        all_subscores = [
            ("spirit", report.spirit_subscores, report.spirit_score),
            ("chest", report.chest_subscores, report.chest_score),
            ("body", report.body_subscores, report.body_score),
            ("audience", report.audience_subscores, report.audience_score),
        ]

        for engine_name, subscores, overall in all_subscores:
            if 0 < overall < 3.0:
                candidates.append(
                    (overall, self._growth_phrase(engine_name, overall))
                )
            for sub_name, sub_val in subscores.items():
                if 0 < sub_val < 3.0:
                    candidates.append(
                        (sub_val, self._subscore_growth_phrase(engine_name, sub_name, sub_val))
                    )

        # Sort by score ascending (weakest first)
        candidates.sort(key=lambda x: x[0])
        areas = [phrase for _, phrase in candidates[:3]]

        if len(areas) < 3:
            defaults = [
                "Let big moments land - add strategic pauses after emotional peaks",
                "Engage your body more - let the truth move through you",
                "Speak WITH the audience, not just AT them",
            ]
            for d in defaults:
                if len(areas) >= 3:
                    break
                if d not in areas:
                    areas.append(d)

        return areas[:3]

    def _strength_phrase(self, engine: str, score: float) -> str:
        """Generate a strength phrase for an engine."""
        phrases = {
            "spirit": "Authentic emotional connection that resonates",
            "chest": "Strong vocal technique and projection",
            "body": "Expressive physical presence on stage",
            "audience": "Natural ability to connect with the audience",
        }
        return phrases.get(engine, f"Strong {engine} performance")

    def _subscore_strength_phrase(self, engine: str, sub: str, score: float) -> str:
        """Generate a strength phrase for a specific sub-score."""
        phrases = {
            ("spirit", "emotion_alignment"): "Words and emotions are deeply aligned",
            ("spirit", "transitions"): "Smooth, intentional emotional transitions",
            ("spirit", "range"): "Rich emotional range that moves the audience",
            ("spirit", "settling"): "The piece is settled and lived-in",
            ("chest", "breath_control"): "Excellent breath control as your foundation",
            ("chest", "projection"): "Powerful vocal projection that fills the room",
            ("chest", "pause_technique"): "Strategic use of silence for impact",
            ("chest", "vocal_health"): "Healthy, sustainable vocal technique",
            ("body", "gesture_intentionality"): "Purposeful, intentional gestures",
            ("body", "stage_presence"): "Commanding stage presence",
            ("body", "eye_contact"): "Strong audience connection through eye contact",
            ("body", "physical_vocal_sync"): "Body and voice working in harmony",
            ("audience", "direct_address"): "Speaking directly TO the audience",
            ("audience", "pacing"): "Excellent pacing for audience absorption",
            ("audience", "emotional_invitation"): "Inviting the audience into your journey",
            ("audience", "engagement_patterns"): "Dynamic delivery that keeps attention",
        }
        return phrases.get(
            (engine, sub),
            f"Strong {sub.replace('_', ' ')} in {engine}",
        )

    def _growth_phrase(self, engine: str, score: float) -> str:
        """Generate a growth area phrase for an engine."""
        phrases = {
            "spirit": "Wake up the spirit - let the emotions fully land",
            "chest": "Build your breath foundation - breath is life on stage",
            "body": "Let your body join the performance - it's watching from the sidelines",
            "audience": "Speak WITH the audience, not just to the room",
        }
        return phrases.get(engine, f"Develop your {engine} presence")

    def _subscore_growth_phrase(self, engine: str, sub: str, score: float) -> str:
        """Generate a growth phrase for a specific sub-score."""
        phrases = {
            ("spirit", "emotion_alignment"): "Bridge the gap between your words and your emotions",
            ("spirit", "transitions"): "Smooth out the emotional transitions between sections",
            ("spirit", "range"): "Explore more of your emotional range - don't play it safe",
            ("spirit", "settling"): "Live with the piece more - let it settle into your bones",
            ("chest", "breath_control"): "Master your breath - it's the foundation of everything",
            ("chest", "projection"): "Project with confidence - the back row wants to hear you too",
            ("chest", "pause_technique"): "Use silence strategically - pauses are powerful",
            ("chest", "vocal_health"): "Watch for vocal strain - protect your instrument",
            ("body", "gesture_intentionality"): "Make every gesture count - purposeful movement",
            ("body", "stage_presence"): "Own the stage - use the space you're given",
            ("body", "eye_contact"): "Connect with the audience through your gaze",
            ("body", "physical_vocal_sync"): "Let your body match your voice - they should dance together",
            ("audience", "direct_address"): "Talk TO people, not past them",
            ("audience", "pacing"): "Let big moments breathe - your audience needs time to feel",
            ("audience", "emotional_invitation"): "Open the door wider - invite the audience in",
            ("audience", "engagement_patterns"): "Vary your delivery to keep the audience locked in",
        }
        return phrases.get(
            (engine, sub),
            f"Develop your {sub.replace('_', ' ')}",
        )
