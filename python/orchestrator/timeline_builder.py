"""
Timeline Builder - Unified PerformanceTimeline Construction

Merges results from all four engines into a single PerformanceTimeline
with proper time alignment and overall score calculation.
"""

import logging
from typing import TYPE_CHECKING

import numpy as np

from python.analysis_modules.shared.data_structures import (
    PerformanceTimeline,
)

if TYPE_CHECKING:
    from .starr_orchestrator import PreprocessingResult, EngineResults

logger = logging.getLogger(__name__)

# Engine weights per POTS methodology
SPIRIT_WEIGHT = 0.30
CHEST_WEIGHT = 0.25
BODY_WEIGHT = 0.25
AUDIENCE_WEIGHT = 0.20


class TimelineBuilder:
    """
    Builds a unified PerformanceTimeline from all engine results.

    The timeline is the central data structure that:
    - Contains all word segments with timing
    - Holds results from each engine
    - Stores derived data (gesture events, engagement curve, etc.)
    - Calculates the weighted overall score
    """

    def build(
        self,
        preprocessing: "PreprocessingResult",
        engine_results: "EngineResults",
    ) -> PerformanceTimeline:
        """
        Build a unified PerformanceTimeline from preprocessing and engine results.

        Args:
            preprocessing: Audio, transcript, word segments
            engine_results: Results from all four engines

        Returns:
            PerformanceTimeline with all data merged
        """
        timeline = PerformanceTimeline(
            video_path=preprocessing.video_path,
            audio_path=preprocessing.audio_path,
            duration_seconds=preprocessing.duration_seconds,
            words=preprocessing.word_segments,
            transcript_text=preprocessing.transcript,
        )

        # Merge Spirit Engine results
        self._merge_spirit(timeline, engine_results)

        # Merge Chest Engine results
        self._merge_chest(timeline, engine_results)

        # Merge Body Engine results
        self._merge_body(timeline, engine_results)

        # Merge Audience Engine results
        self._merge_audience(timeline, engine_results)

        # Calculate weighted overall score
        self._calculate_overall(timeline)

        logger.info(
            f"Timeline built: {timeline.duration_seconds:.1f}s, "
            f"spirit={timeline.spirit_score:.2f}, "
            f"chest={timeline.chest_score:.2f}, "
            f"body={timeline.body_score:.2f}, "
            f"audience={timeline.audience_score:.2f}, "
            f"overall={timeline.overall_score:.2f}"
        )

        return timeline

    def _merge_spirit(
        self,
        timeline: PerformanceTimeline,
        engine_results: "EngineResults",
    ) -> None:
        """Merge Spirit Engine results into the timeline."""
        if engine_results.spirit is None:
            logger.warning("No Spirit Engine results to merge")
            return

        result = engine_results.spirit
        timeline.spirit_result = result
        timeline.spirit_score = result.overall_score
        timeline.vocal_emotions = result.vocal_emotions
        timeline.ideal_emotions = result.ideal_emotions

    def _merge_chest(
        self,
        timeline: PerformanceTimeline,
        engine_results: "EngineResults",
    ) -> None:
        """Merge Chest Engine results into the timeline."""
        if engine_results.chest is None:
            logger.warning("No Chest Engine results to merge")
            return

        result = engine_results.chest
        timeline.chest_score = result.overall_score
        timeline.pause_events = result.pause_events

        if result.energy_curve is not None:
            timeline.loudness_curve = result.energy_curve

    def _merge_body(
        self,
        timeline: PerformanceTimeline,
        engine_results: "EngineResults",
    ) -> None:
        """Merge Body Engine results into the timeline."""
        if engine_results.body is None:
            logger.warning("No Body Engine results to merge")
            return

        result = engine_results.body
        timeline.body_result = result
        timeline.body_score = result.overall_score
        timeline.gesture_events = result.gesture_events
        timeline.body_segments = result.segments

    def _merge_audience(
        self,
        timeline: PerformanceTimeline,
        engine_results: "EngineResults",
    ) -> None:
        """Merge Audience Engine results into the timeline."""
        if engine_results.audience is None:
            logger.warning("No Audience Engine results to merge")
            return

        result = engine_results.audience
        timeline.audience_result = result
        timeline.audience_score = result.overall_score
        timeline.engagement_events = result.engagement_events

        if result.engagement_curve is not None:
            timeline.engagement_curve = result.engagement_curve

    def _calculate_overall(self, timeline: PerformanceTimeline) -> None:
        """
        Calculate the weighted overall S.T.A.R.R. score.

        If some engines failed, re-weights among available engines
        proportionally to maintain a meaningful overall score.
        """
        scores = {
            "spirit": (timeline.spirit_score, SPIRIT_WEIGHT),
            "chest": (timeline.chest_score, CHEST_WEIGHT),
            "body": (timeline.body_score, BODY_WEIGHT),
            "audience": (timeline.audience_score, AUDIENCE_WEIGHT),
        }

        # Check which engines produced results (score > 0)
        active_scores = {
            k: v for k, v in scores.items() if v[0] > 0
        }

        if not active_scores:
            timeline.overall_score = 0.0
            return

        # If all engines active, use standard weights
        if len(active_scores) == 4:
            timeline.calculate_overall_score()
            return

        # Re-weight proportionally among active engines
        total_weight = sum(w for _, w in active_scores.values())
        weighted_sum = sum(
            score * (weight / total_weight)
            for score, weight in active_scores.values()
        )
        timeline.overall_score = weighted_sum

        missing = set(scores.keys()) - set(active_scores.keys())
        logger.warning(
            f"Re-weighted overall score excluding: {missing}. "
            f"Overall: {timeline.overall_score:.2f}/5"
        )

    def build_performance_curve(
        self,
        timeline: PerformanceTimeline,
        window_seconds: float = 5.0,
    ) -> np.ndarray:
        """
        Build an overall performance curve over time.

        Combines available time-series data from engines into
        a single engagement/performance curve for visualization.

        Args:
            timeline: Complete performance timeline
            window_seconds: Time window for smoothing

        Returns:
            1D numpy array of performance scores over time
        """
        duration = timeline.duration_seconds
        if duration <= 0:
            return np.array([])

        # Create time bins
        num_bins = max(1, int(duration / window_seconds))
        curve = np.zeros(num_bins)
        counts = np.zeros(num_bins)

        # Incorporate engagement curve from Audience Engine
        if timeline.engagement_curve is not None and len(timeline.engagement_curve) > 0:
            eng = timeline.engagement_curve
            eng_bins = np.linspace(0, num_bins - 1, len(eng)).astype(int)
            for i, val in zip(eng_bins, eng):
                if 0 <= i < num_bins:
                    curve[i] += val
                    counts[i] += 1

        # Incorporate body segment energy
        for seg in timeline.body_segments:
            mid = (seg.start_time + seg.end_time) / 2.0
            bin_idx = min(int(mid / window_seconds), num_bins - 1)
            if 0 <= bin_idx < num_bins:
                curve[bin_idx] += seg.physical_energy
                counts[bin_idx] += 1

        # Incorporate engagement events
        for event in timeline.engagement_events:
            bin_idx = min(int(event.timestamp / window_seconds), num_bins - 1)
            if 0 <= bin_idx < num_bins:
                curve[bin_idx] += event.engagement_level
                counts[bin_idx] += 1

        # Average where we have data, fill gaps with interpolation
        mask = counts > 0
        if mask.any():
            curve[mask] /= counts[mask]
            # Fill gaps with linear interpolation
            if not mask.all():
                indices = np.arange(num_bins)
                curve[~mask] = np.interp(
                    indices[~mask],
                    indices[mask],
                    curve[mask],
                )
        else:
            # No time-series data available, use overall score as flat line
            curve[:] = timeline.overall_score / 5.0

        return np.clip(curve, 0.0, 1.0)
