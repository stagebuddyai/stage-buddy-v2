#!/usr/bin/env python3
"""
S.T.A.R.R. Orchestrator - Integration Test Suite

Tests the orchestrator, timeline builder, report generator, and coach feedback
using mock engine results (no real audio/video required).

Usage:
    python test_starr_orchestrator.py
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np

from python.analysis_modules.shared.data_structures import (
    WordSegment,
    EmotionCategory,
    EmotionSegment,
    PauseEvent,
    PauseType,
    ProsodyFeatures,
    SpiritAnalysisResult,
    ChestAnalysisResult,
    ChestSegment,
    BreathEvent,
    BodyAnalysisResult,
    BodySegment,
    GestureEvent,
    GestureType,
    AudienceAnalysisResult,
    AudienceSegment,
    EngagementEvent,
    PerformanceTimeline,
)
from python.orchestrator.starr_orchestrator import (
    STARROrchestrator,
    EngineResults,
    PreprocessingResult,
    ENGINE_WEIGHTS,
)
from python.orchestrator.timeline_builder import TimelineBuilder
from python.orchestrator.report_generator import (
    ReportGenerator,
    PerformanceReport,
    KeyMoment,
    _score_to_grade,
    _to_display_score,
)
from python.orchestrator.coach_feedback import CoachFeedbackGenerator


# =============================================================================
# Mock Data Generators
# =============================================================================

def create_mock_word_segments(transcript: str, duration: float) -> List[WordSegment]:
    """Create mock word segments with timing."""
    words = transcript.split()
    if not words:
        return []
    word_duration = duration / len(words)
    return [
        WordSegment(
            word=w,
            start_time=i * word_duration,
            end_time=(i + 0.9) * word_duration,
            confidence=0.95,
        )
        for i, w in enumerate(words)
    ]


def create_mock_spirit_result(score: float) -> SpiritAnalysisResult:
    """Create a mock Spirit Engine result."""
    # Map overall score to sub-scores
    base = score / 5.0  # normalize to 0-1
    return SpiritAnalysisResult(
        overall_score=score,
        emotion_alignment_score=base * 0.9,
        emotional_transition_score=base * 0.85,
        emotional_range_score=base * 1.1,
        settling_score=base * 0.95,
        vocal_emotions=[
            EmotionSegment(
                emotion=EmotionCategory.DETERMINED,
                intensity=0.8,
                valence=0.3,
                arousal=0.7,
                start_time=0.0,
                end_time=3.0,
                confidence=0.85,
                source="vocal",
            ),
            EmotionSegment(
                emotion=EmotionCategory.SAD,
                intensity=0.6,
                valence=-0.5,
                arousal=0.3,
                start_time=3.0,
                end_time=6.0,
                confidence=0.80,
                source="vocal",
            ),
        ],
        ideal_emotions=[
            EmotionSegment(
                emotion=EmotionCategory.DETERMINED,
                intensity=0.9,
                valence=0.4,
                arousal=0.8,
                start_time=0.0,
                end_time=3.0,
                confidence=0.90,
                source="text",
            ),
            EmotionSegment(
                emotion=EmotionCategory.SAD,
                intensity=0.7,
                valence=-0.6,
                arousal=0.2,
                start_time=3.0,
                end_time=6.0,
                confidence=0.85,
                source="text",
            ),
        ],
        alignment_timeline=[
            {"start": 0.0, "end": 3.0, "aligned": True, "score": 0.9},
            {"start": 3.0, "end": 6.0, "aligned": True, "score": 0.85},
        ],
        avg_pitch=180.0,
        pitch_range=80.0,
        avg_loudness=-20.0,
        loudness_range=15.0,
        speech_rate_avg=3.5,
        speech_rate_variance=0.8,
        misalignment_moments=[
            {"timestamp": 4.5, "description": "Slight emotional mismatch", "reason": "rushed delivery"},
        ],
        strength_moments=[
            {"timestamp": 1.5, "description": "Strong emotional alignment", "reason": "authentic delivery"},
            {"timestamp": 5.0, "description": "Powerful emotional peak", "reason": "full commitment"},
        ],
    )


def create_mock_chest_result(score: float) -> ChestAnalysisResult:
    """Create a mock Chest Engine result."""
    base = score / 5.0
    return ChestAnalysisResult(
        overall_score=score,
        breath_control_score=base * 0.9,
        projection_score=base * 1.05,
        pause_technique_score=base * 0.85,
        vocal_health_score=base * 0.95,
        segments=[
            ChestSegment(
                start_time=0.0, end_time=3.0,
                rms_energy=0.15, loudness_db=-18.0, energy_variance=0.02,
            ),
            ChestSegment(
                start_time=3.0, end_time=6.0,
                rms_energy=0.20, loudness_db=-15.0, energy_variance=0.03,
            ),
        ],
        breath_events=[
            BreathEvent(timestamp=2.8, duration=0.4, breath_quality="controlled", at_natural_break=True),
        ],
        pause_events=[
            PauseEvent(
                pause_type=PauseType.BEAT, start_time=2.5, duration=0.6,
                preceding_word="remember", following_word="when",
                at_punctuation=True,
            ),
        ],
        energy_curve=np.array([0.12, 0.15, 0.18, 0.20, 0.22, 0.19]),
        energy_timestamps=np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0]),
        strength_moments=[
            {"timestamp": 3.5, "description": "Strong projection", "reason": "full chest voice"},
        ],
        improvement_areas=[
            {"timestamp": 0.5, "description": "Weak start", "reason": "low energy opening"},
        ],
        processing_time_ms=150.0,
        audio_duration=6.0,
    )


def create_mock_body_result(score: float) -> BodyAnalysisResult:
    """Create a mock Body Engine result."""
    base = score / 5.0
    return BodyAnalysisResult(
        overall_score=score,
        gesture_score=base * 0.85,
        stage_presence_score=base * 1.0,
        eye_contact_score=base * 0.90,
        alignment_score=base * 0.80,
        segments=[
            BodySegment(
                start_time=0.0, end_time=3.0,
                gesture_count=2, intentional_ratio=0.7, gesture_diversity=0.5,
                movement_amount=0.3, position_stability=0.8, space_usage=0.4,
                eye_contact_ratio=0.6, gaze_stability=0.7, physical_energy=0.5,
            ),
            BodySegment(
                start_time=3.0, end_time=6.0,
                gesture_count=3, intentional_ratio=0.8, gesture_diversity=0.6,
                movement_amount=0.5, position_stability=0.7, space_usage=0.5,
                eye_contact_ratio=0.7, gaze_stability=0.8, physical_energy=0.7,
            ),
        ],
        gesture_events=[
            GestureEvent(
                timestamp=1.0, duration=0.5, gesture_type=GestureType.EMPHATIC,
                intentionality=0.8, body_region="hands", confidence=0.9,
            ),
            GestureEvent(
                timestamp=4.0, duration=0.8, gesture_type=GestureType.ILLUSTRATIVE,
                intentionality=0.7, body_region="arms", confidence=0.85,
            ),
        ],
        movement_heatmap=None,
        avg_movement=0.4,
        movement_variance=0.15,
        processing_time_ms=250.0,
        video_duration=6.0,
        frames_analyzed=30,
        weak_moments=[
            {"timestamp": 0.5, "description": "Static opening", "reason": "no physical engagement"},
        ],
        strong_moments=[
            {"timestamp": 4.0, "description": "Expressive gesture", "reason": "intentional movement"},
        ],
    )


def create_mock_audience_result(score: float) -> AudienceAnalysisResult:
    """Create a mock Audience Engine result."""
    base = score / 5.0
    return AudienceAnalysisResult(
        overall_score=score,
        direct_address_score=base * 1.05,
        pacing_score=base * 0.90,
        emotional_invitation_score=base * 0.95,
        engagement_pattern_score=base * 1.0,
        segments=[
            AudienceSegment(
                start_time=0.0, end_time=3.0,
                direct_address_ratio=0.6, pause_effectiveness=0.5,
                emotional_openness=0.5, pace_variation=0.4, engagement_score=0.5,
            ),
            AudienceSegment(
                start_time=3.0, end_time=6.0,
                direct_address_ratio=0.8, pause_effectiveness=0.7,
                emotional_openness=0.7, pace_variation=0.6, engagement_score=0.7,
            ),
        ],
        engagement_events=[
            EngagementEvent(
                timestamp=2.5, duration=1.0, event_type="strategic_pause",
                engagement_level=0.7, description="Effective pause after strong line",
            ),
            EngagementEvent(
                timestamp=5.0, duration=0.5, event_type="emotional_peak",
                engagement_level=0.9, description="Peak emotional moment with audience connection",
            ),
        ],
        engagement_curve=np.array([0.4, 0.5, 0.6, 0.65, 0.7, 0.8]),
        processing_time_ms=200.0,
        duration=6.0,
    )


def create_mock_preprocessing(
    video_path: str = "test_performance.mp4",
    duration: float = 6.0,
) -> PreprocessingResult:
    """Create mock preprocessing result."""
    transcript = "I remember when the world was quiet and the stars spoke to me in whispers"
    word_segments = create_mock_word_segments(transcript, duration)
    return PreprocessingResult(
        audio_path="test_audio.wav",
        transcript=transcript,
        word_segments=word_segments,
        duration_seconds=duration,
        video_path=video_path,
    )


# =============================================================================
# Test Functions
# =============================================================================

def test_engine_weights():
    """Test that engine weights sum to 1.0."""
    print("\n=== Testing Engine Weights ===")
    total = sum(ENGINE_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-10, f"Weights sum to {total}, expected 1.0"
    print(f"  Engine weights: {ENGINE_WEIGHTS}")
    print(f"  Total: {total}")
    print("PASS: Engine weights sum to 1.0")


def test_score_to_grade():
    """Test grade conversion."""
    print("\n=== Testing Score-to-Grade ===")
    test_cases = [
        (5.0, "A+"),
        (4.5, "A+"),
        (4.2, "A"),
        (4.0, "A-"),
        (3.7, "B+"),
        (3.3, "B"),
        (3.0, "B-"),
        (2.5, "C"),
        (2.0, "C-"),
        (1.5, "D"),
        (1.0, "D-"),
        (0.5, "F"),
    ]
    for score, expected_grade in test_cases:
        grade = _score_to_grade(score)
        assert grade == expected_grade, f"Score {score}: got {grade}, expected {expected_grade}"
        print(f"  {score}/5 -> {grade}")
    print("PASS: All grade conversions correct")


def test_display_score_conversion():
    """Test 0-1 to 1-5 score conversion."""
    print("\n=== Testing Display Score Conversion ===")
    assert _to_display_score(0.0) == 1.0
    assert _to_display_score(0.5) == 3.0
    assert _to_display_score(1.0) == 5.0
    # Already on 1-5 scale should pass through
    assert _to_display_score(3.5) == 3.5
    print("PASS: Score conversions correct")


def test_timeline_builder():
    """Test timeline building from engine results."""
    print("\n=== Testing Timeline Builder ===")

    preprocessing = create_mock_preprocessing()
    engine_results = EngineResults(
        spirit=create_mock_spirit_result(4.0),
        chest=create_mock_chest_result(3.5),
        body=create_mock_body_result(3.2),
        audience=create_mock_audience_result(3.8),
    )

    builder = TimelineBuilder()
    timeline = builder.build(preprocessing, engine_results)

    # Verify scores are set
    assert timeline.spirit_score == 4.0, f"Spirit: {timeline.spirit_score}"
    assert timeline.chest_score == 3.5, f"Chest: {timeline.chest_score}"
    assert timeline.body_score == 3.2, f"Body: {timeline.body_score}"
    assert timeline.audience_score == 3.8, f"Audience: {timeline.audience_score}"
    print(f"  Spirit: {timeline.spirit_score}/5")
    print(f"  Chest: {timeline.chest_score}/5")
    print(f"  Body: {timeline.body_score}/5")
    print(f"  Audience: {timeline.audience_score}/5")

    # Verify overall score calculation
    expected_overall = (4.0 * 0.30 + 3.5 * 0.25 + 3.2 * 0.25 + 3.8 * 0.20)
    assert abs(timeline.overall_score - expected_overall) < 0.01, (
        f"Overall: {timeline.overall_score}, expected: {expected_overall}"
    )
    print(f"  Overall: {timeline.overall_score:.2f}/5 (expected: {expected_overall:.2f})")

    # Verify data merged
    assert timeline.spirit_result is not None
    assert len(timeline.vocal_emotions) == 2
    assert len(timeline.pause_events) == 1
    assert len(timeline.gesture_events) == 2
    assert len(timeline.engagement_events) == 2
    assert timeline.loudness_curve is not None
    print("  All engine data merged into timeline")

    # Test performance curve
    curve = builder.build_performance_curve(timeline)
    assert len(curve) > 0
    assert all(0 <= v <= 1.0 for v in curve)
    print(f"  Performance curve: {len(curve)} data points")

    print("PASS: Timeline builder works correctly")


def test_timeline_builder_partial_results():
    """Test timeline building with missing engine results."""
    print("\n=== Testing Timeline Builder (Partial Results) ===")

    preprocessing = create_mock_preprocessing()
    # Only Spirit and Chest results available
    engine_results = EngineResults(
        spirit=create_mock_spirit_result(4.0),
        chest=create_mock_chest_result(3.5),
        body=None,
        audience=None,
    )

    builder = TimelineBuilder()
    timeline = builder.build(preprocessing, engine_results)

    # Overall should re-weight among available engines
    assert timeline.spirit_score == 4.0
    assert timeline.chest_score == 3.5
    assert timeline.body_score == 0.0
    assert timeline.audience_score == 0.0
    assert timeline.overall_score > 0, "Overall should be re-weighted, not zero"
    print(f"  Re-weighted overall: {timeline.overall_score:.2f}/5")
    print(f"  (Spirit 4.0 + Chest 3.5 only)")

    # Expected: proportional re-weight
    # spirit weight=0.30, chest weight=0.25 -> total=0.55
    # spirit: 4.0 * (0.30/0.55) = 2.18, chest: 3.5 * (0.25/0.55) = 1.59
    # overall = 3.77
    expected = 4.0 * (0.30 / 0.55) + 3.5 * (0.25 / 0.55)
    assert abs(timeline.overall_score - expected) < 0.01, (
        f"Got {timeline.overall_score}, expected {expected}"
    )
    print(f"  Proportional re-weight verified: {expected:.2f}")

    print("PASS: Partial results handled correctly")


def test_report_generator():
    """Test full report generation."""
    print("\n=== Testing Report Generator ===")

    preprocessing = create_mock_preprocessing()
    engine_results = EngineResults(
        spirit=create_mock_spirit_result(4.2),
        chest=create_mock_chest_result(3.5),
        body=create_mock_body_result(3.2),
        audience=create_mock_audience_result(4.0),
    )

    builder = TimelineBuilder()
    timeline = builder.build(preprocessing, engine_results)

    coach = CoachFeedbackGenerator(use_openai=False)
    generator = ReportGenerator()
    report = generator.generate(
        timeline=timeline,
        engine_results=engine_results,
        coach=coach,
        video_path="test_performance.mp4",
        processing_time_ms=1500.0,
    )

    # Verify overall score and grade
    assert 1.0 <= report.overall_score <= 5.0
    assert report.overall_grade in ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F"]
    print(f"  Overall: {report.overall_score:.2f}/5 ({report.overall_grade})")

    # Verify all engine scores present
    assert report.spirit_score == 4.2
    assert report.chest_score == 3.5
    assert report.body_score == 3.2
    assert report.audience_score == 4.0
    print(f"  Spirit: {report.spirit_score}/5")
    print(f"  Chest: {report.chest_score}/5")
    print(f"  Body: {report.body_score}/5")
    print(f"  Audience: {report.audience_score}/5")

    # Verify sub-scores exist for each engine
    assert len(report.spirit_subscores) == 4, f"Spirit subscores: {report.spirit_subscores}"
    assert len(report.chest_subscores) == 4, f"Chest subscores: {report.chest_subscores}"
    assert len(report.body_subscores) == 4, f"Body subscores: {report.body_subscores}"
    assert len(report.audience_subscores) == 4, f"Audience subscores: {report.audience_subscores}"
    print("  All 16 sub-scores present (4 per engine)")

    for name, subscores in [
        ("Spirit", report.spirit_subscores),
        ("Chest", report.chest_subscores),
        ("Body", report.body_subscores),
        ("Audience", report.audience_subscores),
    ]:
        for sub_name, sub_val in subscores.items():
            print(f"    {name}.{sub_name}: {sub_val:.2f}")

    # Verify feedback generated for all engines
    assert len(report.spirit_feedback) > 0, "Missing spirit feedback"
    assert len(report.chest_feedback) > 0, "Missing chest feedback"
    assert len(report.body_feedback) > 0, "Missing body feedback"
    assert len(report.audience_feedback) > 0, "Missing audience feedback"
    assert len(report.coach_summary) > 0, "Missing coach summary"
    print("\n  Feedback generated for all engines:")
    print(f"    Spirit: {report.spirit_feedback[:80]}...")
    print(f"    Chest: {report.chest_feedback[:80]}...")
    print(f"    Body: {report.body_feedback[:80]}...")
    print(f"    Audience: {report.audience_feedback[:80]}...")
    print(f"    Summary: {report.coach_summary[:80]}...")

    # Verify growth plan
    assert len(report.top_strengths) == 3
    assert len(report.growth_areas) == 3
    print(f"\n  Top Strengths:")
    for s in report.top_strengths:
        print(f"    - {s}")
    print(f"  Growth Areas:")
    for g in report.growth_areas:
        print(f"    - {g}")

    # Verify key moments
    print(f"\n  Key Moments: {len(report.key_moments)}")
    for m in report.key_moments[:3]:
        print(f"    [{m.moment_type}] {m.timestamp:.1f}s: {m.description[:60]}")

    # Verify metadata
    assert report.duration_seconds == 6.0
    assert report.processing_time_ms == 1500.0
    assert report.video_path == "test_performance.mp4"
    assert len(report.performance_id) > 0

    print("\nPASS: Report generator works correctly")


def test_json_output():
    """Test JSON output format for frontend rendering."""
    print("\n=== Testing JSON Output ===")

    preprocessing = create_mock_preprocessing()
    engine_results = EngineResults(
        spirit=create_mock_spirit_result(4.2),
        chest=create_mock_chest_result(3.5),
        body=create_mock_body_result(3.2),
        audience=create_mock_audience_result(4.0),
    )

    builder = TimelineBuilder()
    timeline = builder.build(preprocessing, engine_results)

    coach = CoachFeedbackGenerator(use_openai=False)
    generator = ReportGenerator()
    report = generator.generate(
        timeline=timeline,
        engine_results=engine_results,
        coach=coach,
        video_path="test_performance.mp4",
        processing_time_ms=1500.0,
    )

    # Generate JSON
    json_str = report.to_json()
    data = json.loads(json_str)

    # Verify top-level structure
    assert "performance_id" in data
    assert "overall" in data
    assert "pillars" in data
    assert "timeline" in data
    assert "growth_plan" in data
    assert "metadata" in data

    # Verify overall section
    assert "score" in data["overall"]
    assert "grade" in data["overall"]
    assert "summary" in data["overall"]

    # Verify pillars
    assert len(data["pillars"]) == 4
    pillar_names = [p["name"] for p in data["pillars"]]
    assert pillar_names == ["Spirit", "Chest", "Body", "Audience"]

    for pillar in data["pillars"]:
        assert "name" in pillar
        assert "weight" in pillar
        assert "score" in pillar
        assert "subscores" in pillar
        assert "feedback" in pillar
        assert "icon" in pillar
        assert len(pillar["subscores"]) == 4

    # Verify timeline
    assert "duration_seconds" in data["timeline"]
    assert "key_moments" in data["timeline"]
    assert "engagement_curve" in data["timeline"]

    # Verify growth plan
    assert len(data["growth_plan"]["top_strengths"]) == 3
    assert len(data["growth_plan"]["focus_areas"]) == 3

    # Pretty print a sample
    print(f"  JSON generated: {len(json_str)} bytes")
    print(f"  Performance ID: {data['performance_id']}")
    print(f"  Overall: {data['overall']['score']}/5 ({data['overall']['grade']})")
    for p in data["pillars"]:
        print(f"  {p['name']} ({p['weight']*100:.0f}%): {p['score']}/5 [{p['icon']}]")
    print(f"  Key Moments: {len(data['timeline']['key_moments'])}")
    print(f"  Engagement Curve: {len(data['timeline']['engagement_curve'])} points")

    print("\nPASS: JSON output is valid and complete")


def test_coach_feedback_tiers():
    """Test coach feedback for different score tiers."""
    print("\n=== Testing Coach Feedback Tiers ===")

    coach = CoachFeedbackGenerator(use_openai=False)

    # Test high score feedback
    preprocessing = create_mock_preprocessing()
    engine_results_high = EngineResults(
        spirit=create_mock_spirit_result(4.5),
        chest=create_mock_chest_result(4.2),
        body=create_mock_body_result(4.0),
        audience=create_mock_audience_result(4.3),
    )
    builder = TimelineBuilder()
    timeline_high = builder.build(preprocessing, engine_results_high)
    gen = ReportGenerator()
    report_high = gen.generate(timeline_high, engine_results_high, coach, "test.mp4", 1000)

    print(f"\n  HIGH TIER ({report_high.overall_score:.1f}/5 {report_high.overall_grade}):")
    print(f"    Spirit: {report_high.spirit_feedback[:100]}...")
    print(f"    Chest: {report_high.chest_feedback[:100]}...")
    print(f"    Summary: {report_high.coach_summary[:100]}...")

    # Test mid score feedback
    engine_results_mid = EngineResults(
        spirit=create_mock_spirit_result(3.2),
        chest=create_mock_chest_result(3.0),
        body=create_mock_body_result(2.8),
        audience=create_mock_audience_result(3.4),
    )
    timeline_mid = builder.build(preprocessing, engine_results_mid)
    report_mid = gen.generate(timeline_mid, engine_results_mid, coach, "test.mp4", 1000)

    print(f"\n  MID TIER ({report_mid.overall_score:.1f}/5 {report_mid.overall_grade}):")
    print(f"    Spirit: {report_mid.spirit_feedback[:100]}...")
    print(f"    Body: {report_mid.body_feedback[:100]}...")
    print(f"    Summary: {report_mid.coach_summary[:100]}...")

    # Test low score feedback
    engine_results_low = EngineResults(
        spirit=create_mock_spirit_result(2.0),
        chest=create_mock_chest_result(1.8),
        body=create_mock_body_result(1.5),
        audience=create_mock_audience_result(2.2),
    )
    timeline_low = builder.build(preprocessing, engine_results_low)
    report_low = gen.generate(timeline_low, engine_results_low, coach, "test.mp4", 1000)

    print(f"\n  LOW TIER ({report_low.overall_score:.1f}/5 {report_low.overall_grade}):")
    print(f"    Spirit: {report_low.spirit_feedback[:100]}...")
    print(f"    Body: {report_low.body_feedback[:100]}...")
    print(f"    Summary: {report_low.coach_summary[:100]}...")

    # Verify feedback is different for different tiers
    assert report_high.spirit_feedback != report_mid.spirit_feedback
    assert report_mid.spirit_feedback != report_low.spirit_feedback
    assert report_high.coach_summary != report_low.coach_summary

    # Verify POTS voice elements
    all_feedback = (
        report_high.spirit_feedback + report_mid.spirit_feedback + report_low.spirit_feedback +
        report_high.chest_feedback + report_mid.chest_feedback + report_low.chest_feedback +
        report_high.body_feedback + report_mid.body_feedback + report_low.body_feedback +
        report_high.coach_summary + report_mid.coach_summary + report_low.coach_summary
    )
    # Check for POTS-style emphasis and terminology
    has_caps_emphasis = any(
        word.isupper() and len(word) > 1
        for word in all_feedback.split()
    )
    assert has_caps_emphasis, "Feedback should use CAPS emphasis (POTS voice)"
    print("\n  POTS voice elements verified (CAPS emphasis present)")

    print("\nPASS: Coach feedback tiers work correctly")


def test_key_moment_detection():
    """Test key moment detection logic."""
    print("\n=== Testing Key Moment Detection ===")

    # Create engine results with clear strength/weakness patterns
    spirit = create_mock_spirit_result(4.0)
    spirit.strength_moments = [
        {"timestamp": 1.5, "description": "Strong alignment", "reason": "authentic"},
        {"timestamp": 4.0, "description": "Emotional peak", "reason": "committed"},
    ]
    spirit.misalignment_moments = [
        {"timestamp": 8.0, "description": "Lost emotion", "reason": "rushed"},
    ]

    chest = create_mock_chest_result(3.5)
    chest.strength_moments = [
        {"timestamp": 1.0, "description": "Great projection", "reason": "full voice"},
        {"timestamp": 4.5, "description": "Strategic pause", "reason": "effective"},
    ]
    chest.improvement_areas = [
        {"timestamp": 8.5, "description": "Ran out of breath", "reason": "no support"},
    ]

    body = create_mock_body_result(3.2)
    body.strong_moments = [
        {"timestamp": 4.2, "description": "Expressive gesture", "reason": "intentional"},
    ]
    body.weak_moments = [
        {"timestamp": 7.5, "description": "Frozen body", "reason": "disconnected"},
    ]

    audience = create_mock_audience_result(3.8)
    audience.strength_moments = [
        {"timestamp": 1.8, "description": "Direct address", "reason": "personal"},
    ]
    audience.weakness_moments = []

    engine_results = EngineResults(
        spirit=spirit,
        chest=chest,
        body=body,
        audience=audience,
    )

    preprocessing = create_mock_preprocessing(duration=12.0)
    builder = TimelineBuilder()
    timeline = builder.build(preprocessing, engine_results)

    generator = ReportGenerator()
    coach = CoachFeedbackGenerator(use_openai=False)
    report = generator.generate(timeline, engine_results, coach, "test.mp4", 1000)

    print(f"  Detected {len(report.key_moments)} key moments:")
    for m in report.key_moments:
        print(f"    [{m.moment_type:12s}] {m.timestamp:5.1f}s | {m.description[:60]}")
        print(f"                         Note: {m.coach_note[:60]}")

    # Verify moment types are valid
    valid_types = {"peak", "breakthrough", "opportunity", "stumble"}
    for m in report.key_moments:
        assert m.moment_type in valid_types, f"Invalid type: {m.moment_type}"

    print("\nPASS: Key moment detection works correctly")


def test_engine_results_dataclass():
    """Test EngineResults dataclass."""
    print("\n=== Testing EngineResults Dataclass ===")

    # Empty results
    results = EngineResults()
    assert results.spirit is None
    assert results.chest is None
    assert results.body is None
    assert results.audience is None
    assert results.errors == {}
    print("  Empty results: OK")

    # With data
    results = EngineResults(
        spirit=create_mock_spirit_result(4.0),
        errors={"body": "MediaPipe not available"},
    )
    assert results.spirit is not None
    assert results.spirit.overall_score == 4.0
    assert "body" in results.errors
    print("  Populated results: OK")

    print("PASS: EngineResults dataclass works correctly")


def test_full_pipeline_mock():
    """
    Test the full pipeline with mocked engine execution.

    This test bypasses actual engine analysis and tests the
    orchestrator's integration logic end-to-end.
    """
    print("\n=== Testing Full Pipeline (Mocked) ===")

    preprocessing = create_mock_preprocessing()
    engine_results = EngineResults(
        spirit=create_mock_spirit_result(3.8),
        chest=create_mock_chest_result(3.5),
        body=create_mock_body_result(3.0),
        audience=create_mock_audience_result(3.6),
    )

    # Build timeline
    builder = TimelineBuilder()
    timeline = builder.build(preprocessing, engine_results)

    # Generate report
    coach = CoachFeedbackGenerator(use_openai=False)
    generator = ReportGenerator()
    report = generator.generate(
        timeline=timeline,
        engine_results=engine_results,
        coach=coach,
        video_path="test_performance.mp4",
        processing_time_ms=2000.0,
    )

    # Generate JSON
    json_data = json.loads(report.to_json())

    # Full validation
    print(f"\n  === PERFORMANCE REPORT ===")
    print(f"  ID: {json_data['performance_id']}")
    print(f"  Overall: {json_data['overall']['score']}/5 ({json_data['overall']['grade']})")
    print()

    for pillar in json_data["pillars"]:
        print(f"  {pillar['name']} Engine ({pillar['weight']*100:.0f}%): {pillar['score']}/5")
        for sub_name, sub_val in pillar["subscores"].items():
            print(f"    {sub_name}: {sub_val}/5")
        print(f"    Feedback: {pillar['feedback'][:70]}...")
        print()

    print(f"  Key Moments: {len(json_data['timeline']['key_moments'])}")
    for m in json_data["timeline"]["key_moments"][:3]:
        print(f"    [{m['type']}] {m['timestamp']}s: {m['description'][:50]}")

    print(f"\n  Growth Plan:")
    print(f"    Strengths: {json_data['growth_plan']['top_strengths']}")
    print(f"    Focus: {json_data['growth_plan']['focus_areas']}")

    print(f"\n  Summary: {json_data['overall']['summary'][:100]}...")

    # Validate the report is complete
    assert json_data["overall"]["score"] > 0
    assert len(json_data["overall"]["grade"]) > 0
    assert len(json_data["overall"]["summary"]) > 0
    assert len(json_data["pillars"]) == 4
    assert all(p["score"] > 0 for p in json_data["pillars"])
    assert all(len(p["feedback"]) > 0 for p in json_data["pillars"])
    assert len(json_data["growth_plan"]["top_strengths"]) == 3
    assert len(json_data["growth_plan"]["focus_areas"]) == 3

    print("\nPASS: Full pipeline produces complete, valid report")


# =============================================================================
# Test Runner
# =============================================================================

def run_all_tests():
    """Run all orchestrator tests."""
    print("=" * 60)
    print("S.T.A.R.R. ORCHESTRATOR - INTEGRATION TEST SUITE")
    print("=" * 60)

    tests = [
        test_engine_weights,
        test_score_to_grade,
        test_display_score_conversion,
        test_engine_results_dataclass,
        test_timeline_builder,
        test_timeline_builder_partial_results,
        test_report_generator,
        test_json_output,
        test_coach_feedback_tiers,
        test_key_moment_detection,
        test_full_pipeline_mock,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\nFAIL: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
