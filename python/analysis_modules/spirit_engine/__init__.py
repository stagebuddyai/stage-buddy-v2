"""
Stage Buddy V2 - Spirit Engine
Analyzes emotion-word alignment for spoken word performances.
"""

from .spirit_engine import SpiritEngine, analyze_spirit
from .opensmile_extractor import OpenSMILEExtractor, extract_prosody
from .text_emotion_analyzer import TextEmotionAnalyzer, predict_ideal_emotions
from .vocal_emotion_detector import VocalEmotionDetector, detect_vocal_emotions

__all__ = [
    'SpiritEngine',
    'analyze_spirit',
    'OpenSMILEExtractor',
    'extract_prosody',
    'TextEmotionAnalyzer',
    'predict_ideal_emotions',
    'VocalEmotionDetector',
    'detect_vocal_emotions',
]
