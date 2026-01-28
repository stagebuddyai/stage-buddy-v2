"""
Stage Buddy V2 - Audience Engine Module
Analyzes audience engagement in spoken word performances.

The Audience Engine is the fourth S.T.A.R.R. module (20% weight).
It evaluates how effectively the performer connects with their audience through:
- Direct address (30%) - Speaking TO the audience, not AT them
- Pacing for engagement (25%) - Strategic pauses for absorption
- Emotional invitation (25%) - Inviting audience into the journey
- Room reading signals (20%) - Delivery variation for impact
"""

from .audience_engine import AudienceEngine, analyze_audience
from .direct_address_analyzer import DirectAddressAnalyzer
from .pacing_analyzer import PacingAnalyzer
from .emotional_invitation_scorer import EmotionalInvitationScorer
from .engagement_pattern_detector import EngagementPatternDetector

__all__ = [
    'AudienceEngine',
    'analyze_audience',
    'DirectAddressAnalyzer',
    'PacingAnalyzer',
    'EmotionalInvitationScorer',
    'EngagementPatternDetector',
]
