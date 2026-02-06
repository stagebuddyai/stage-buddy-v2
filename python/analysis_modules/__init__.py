"""
Stage Buddy V2 - Analysis Modules
Performance analysis engines for spoken word performances.
"""

from .shared import (
    EmotionCategory,
    PauseType,
    WordSegment,
    EmotionSegment,
    PauseEvent,
    ProsodyFeatures,
    SpiritAnalysisResult,
    PerformanceTimeline,
)

from .spirit_engine import (
    SpiritEngine,
    analyze_spirit,
)

from .chest_engine import (
    ChestEngine,
    analyze_chest,
)

__all__ = [
    # Data structures
    'EmotionCategory',
    'PauseType',
    'WordSegment',
    'EmotionSegment',
    'PauseEvent',
    'ProsodyFeatures',
    'SpiritAnalysisResult',
    'PerformanceTimeline',
    # Spirit Engine
    'SpiritEngine',
    'analyze_spirit',
    # Chest Engine
    'ChestEngine',
    'analyze_chest',
]
