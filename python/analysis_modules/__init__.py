"""
Stage Buddy V2 - Analysis Modules
Performance analysis engines for spoken word performances.

S.T.A.R.R. Framework:
- Spirit Engine (30%) - Emotional authenticity analysis
- Chest Engine (25%) - Vocal technique analysis (pending)
- Body Engine (25%) - Physical performance analysis
- Audience Engine (20%) - Audience engagement analysis (pending)
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
    # Body Engine data structures
    GestureType,
    GestureEvent,
    BodySegment,
    BodyAnalysisResult,
)

from .spirit_engine import (
    SpiritEngine,
    analyze_spirit,
)

from .body_engine import (
    BodyEngine,
    analyze_body,
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
    # Body Engine data structures
    'GestureType',
    'GestureEvent',
    'BodySegment',
    'BodyAnalysisResult',
    # Spirit Engine
    'SpiritEngine',
    'analyze_spirit',
    # Body Engine
    'BodyEngine',
    'analyze_body',
]
