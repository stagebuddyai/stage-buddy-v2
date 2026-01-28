"""
Stage Buddy V2 - S.T.A.R.R. Orchestrator

The central system that brings all four analysis engines together:
- Spirit Engine (30%) - Emotional authenticity & alignment
- Chest Engine (25%) - Vocal technique & breath control
- Body Engine (25%) - Physical performance & gesture
- Audience Engine (20%) - Audience engagement & connection
"""

from .starr_orchestrator import STARROrchestrator
from .performance_analyzer import PerformanceAnalyzer
from .timeline_builder import TimelineBuilder
from .report_generator import ReportGenerator, PerformanceReport, KeyMoment
from .coach_feedback import CoachFeedbackGenerator

__all__ = [
    'STARROrchestrator',
    'PerformanceAnalyzer',
    'TimelineBuilder',
    'ReportGenerator',
    'PerformanceReport',
    'KeyMoment',
    'CoachFeedbackGenerator',
]
