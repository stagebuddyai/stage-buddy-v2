"""
Stage Buddy V2 - Body Engine
Analyzes physical performance aspects for spoken word performances.

The Body Engine evaluates:
1. Gesture Intentionality (35%) - Purposeful vs nervous movements
2. Stage Presence (30%) - Use of space, stance, confidence
3. Eye Contact (20%) - Audience connection through gaze
4. Physical-Vocal Alignment (15%) - Gestures matching vocal emphasis
"""

from .body_engine import BodyEngine, analyze_body
from .gesture_analyzer import GestureAnalyzer, analyze_gestures
from .stage_presence_analyzer import StagePresenceAnalyzer, analyze_stage_presence
from .eye_contact_detector import EyeContactDetector, detect_eye_contact
from .alignment_scorer import AlignmentScorer, score_alignment

__all__ = [
    'BodyEngine',
    'analyze_body',
    'GestureAnalyzer',
    'analyze_gestures',
    'StagePresenceAnalyzer',
    'analyze_stage_presence',
    'EyeContactDetector',
    'detect_eye_contact',
    'AlignmentScorer',
    'score_alignment',
]
