"""
Stage Buddy V2 - Shared Data Structures
Common data types used across all analysis modules.
"""

from .data_structures import (
    EmotionCategory,
    PauseType,
    WordSegment,
    EmotionSegment,
    PauseEvent,
    ProsodyFeatures,
    SpiritAnalysisResult,
    PerformanceTimeline,
    EMOTION_ADJACENCY,
    EMOTION_VA_MAP,
    emotions_are_aligned,
    # Body Engine data structures
    GestureType,
    GestureEvent,
    BodySegment,
    BodyAnalysisResult,
)

__all__ = [
    'EmotionCategory',
    'PauseType',
    'WordSegment',
    'EmotionSegment',
    'PauseEvent',
    'ProsodyFeatures',
    'SpiritAnalysisResult',
    'PerformanceTimeline',
    'EMOTION_ADJACENCY',
    'EMOTION_VA_MAP',
    'emotions_are_aligned',
    # Body Engine data structures
    'GestureType',
    'GestureEvent',
    'BodySegment',
    'BodyAnalysisResult',
]
