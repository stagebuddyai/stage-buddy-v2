"""
Stage Buddy V2 - Chest Engine Module

The Chest Engine analyzes vocal technique in spoken word performances:
- Breath Control (35%) - Foundation of vocal technique
- Projection (35%) - Volume and energy to reach the audience
- Pause Technique (20%) - Strategic use of silence (beats, breaths, breaks)
- Vocal Health (10%) - Strain detection and consistency

Usage:
    from analysis_modules.chest_engine import ChestEngine, analyze_chest

    engine = ChestEngine()
    result = engine.analyze(audio_path="performance.wav")
    print(f"Chest Score: {result.overall_score}/5")

See docs/CHEST_ENGINE_DESIGN.md for full specification.
"""

# Module version
__version__ = "0.1.0"

# Imports will be added as modules are implemented
# from .chest_engine import ChestEngine, analyze_chest
# from .breath_analyzer import BreathAnalyzer
# from .projection_analyzer import ProjectionAnalyzer
# from .pause_detector import PauseDetector
# from .vocal_health_monitor import VocalHealthMonitor

__all__ = [
    # 'ChestEngine',
    # 'analyze_chest',
    # 'BreathAnalyzer',
    # 'ProjectionAnalyzer',
    # 'PauseDetector',
    # 'VocalHealthMonitor',
]
