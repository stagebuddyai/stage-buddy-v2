# Audience Engine Design Document

## Overview

The Audience Engine is the fourth and final S.T.A.R.R. analysis module for Stage Buddy V2. It evaluates how effectively a performer engages their audience, measuring whether they perform **WITH** the audience rather than **AT** them.

**S.T.A.R.R. Framework Weight: 20%**

## Architecture

```
python/analysis_modules/audience_engine/
├── __init__.py                      # Module exports
├── audience_engine.py               # Main orchestrator
├── direct_address_analyzer.py       # Pronoun/question analysis
├── pacing_analyzer.py               # Strategic pause detection
├── emotional_invitation_scorer.py   # Shared emotional moment detection
└── engagement_pattern_detector.py   # Delivery variation analysis
```

## Scoring Components

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| **Direct Address** | 30% | Speaking TO the audience, not AT them |
| **Pacing** | 25% | Strategic pauses for audience absorption |
| **Emotional Invitation** | 25% | Inviting audience into the emotional journey |
| **Engagement Patterns** | 20% | Delivery variation for impact |

### Overall Score Formula

```python
overall_normalized = sum(score * weight for score, weight in components)
calibrated = apply_calibration(overall_normalized, component_scores)
overall_score = 1.0 + calibrated * 4.0  # Convert to 1-5 scale
```

## Component Details

### 1. Direct Address Analyzer

Analyzes whether the performer speaks TO the audience or AT them.

**Indicators Detected:**
- Second person pronouns ("you", "your", "yourself")
- Inclusive pronouns ("we", "us", "our", "let's")
- Rhetorical questions that engage the audience
- Imperative/command forms ("listen", "imagine", "feel")

**Scoring:**
- High direct address ratio = speaking WITH the audience
- High self-focused pronouns (I, me, my) = performing AT the audience
- Questions and imperatives boost engagement

### 2. Pacing Analyzer

Analyzes strategic pause usage for audience engagement.

**Pause Types:**
- MICRO (<0.5s): Natural speech rhythm
- BEAT (0.5-1.0s): Separates ideas
- BREATH (1.0-2.0s): Sentence boundary
- BREAK (2.0+s): Dramatic pause

**Scoring:**
- Optimal pause rate: 4-8 per minute
- Pauses at punctuation: Good alignment
- Strategic pauses after emotional moments: High engagement

### 3. Emotional Invitation Scorer

Measures whether the performer invites the audience into the emotional journey.

**Indicators:**
- Vulnerability language ("feel", "hurt", "hope", "remember")
- Shared experience phrases ("you know", "we all", "with me")
- Emotional peaks with "space" (pauses after intense moments)
- Dynamic intensity range (not flat or constant)

**Integration with Spirit Engine:**
When Spirit Engine results are available, uses:
- Vocal emotion intensity for peak detection
- Emotional arc for journey analysis
- Prosody features for space detection

### 4. Engagement Pattern Detector

Analyzes delivery variation for audience engagement.

**Patterns Detected:**
- Energy variation (coefficient of variation)
- Build-ups (sustained energy increases)
- Releases (energy drops after peaks)
- Pace shifts (significant rate changes)

**Scoring:**
- Optimal variation: 0.15-0.30 CV
- Below 0.15: Monotonous delivery
- Above 0.60: Erratic/chaotic

## Calibration

The Audience Engine applies calibration to match POTS scoring expectations:

### Floor Effect
Direct address is critical - no direct address = no audience connection:
- DA < 0.1: 0.2x multiplier (floor at ~1.0/5)
- DA < 0.2: 0.4x multiplier (floor at ~1.5/5)
- DA < 0.4: 0.7x multiplier (significant penalty)

### Ceiling Boost
High direct address + emotional invitation = true connection:
- DA > 0.7 AND EI > 0.5: Boost towards 5/5

### Synergy Bonus
All components above 0.6: 1.15x multiplier

### Anti-Monotony Penalty
High engagement patterns but low DA and EI: 0.8x multiplier
(Energy without connection is performing AT, not WITH)

## Benchmark Results

| Video | Category | Target | Achieved | Diff | Status |
|-------|----------|--------|----------|------|--------|
| x_king_city_winery_STRONG | STRONG | 5.0 | 4.82 | 0.18 | PASS |
| trap_ghost_MID | MID | 2.0 | 1.53 | 0.47 | PASS |
| did_you_smile_today_WEAK | WEAK | 1.0 | 1.36 | 0.36 | PASS |

**Average Difference: 0.33** (Success criteria: <1.0)

## Integration with Other Engines

The Audience Engine is unique because it can synthesize signals from all other engines:

```python
def analyze(
    self,
    video_path: str,
    audio_path: str,
    transcript: Optional[str] = None,
    word_segments: Optional[List[WordSegment]] = None,
    spirit_result: Optional[SpiritAnalysisResult] = None,  # Emotion data
    body_result: Optional[Any] = None,                      # Physical engagement
    pause_events: Optional[List[PauseEvent]] = None,        # From Chest
    loudness_curve: Optional[np.ndarray] = None             # From Chest
) -> AudienceAnalysisResult:
```

### Standalone Operation
When other engine results are NOT available:
- Extracts pauses from word segment gaps
- Analyzes transcript independently for direct address
- Uses word density as energy proxy
- Produces valid scores (graceful degradation)

### Enhanced Operation
When other engine results ARE available:
- Uses Spirit Engine's emotional arc for invitation scoring
- Uses Spirit Engine's prosody for energy curve
- Uses Chest Engine's pause events for pacing analysis
- Uses Chest Engine's loudness curve for engagement patterns

## Data Structures

### EngagementEvent
```python
@dataclass
class EngagementEvent:
    timestamp: float           # When this event occurred
    duration: float            # How long the event lasted
    event_type: str            # "direct_address", "strategic_pause", etc.
    engagement_level: float    # 0-1, how engaging this moment is
    description: str           # Human-readable description
```

### AudienceSegment
```python
@dataclass
class AudienceSegment:
    start_time: float
    end_time: float
    direct_address_ratio: float    # 0-1
    pause_effectiveness: float     # 0-1
    emotional_openness: float      # 0-1
    pace_variation: float          # 0-1
    engagement_score: float        # Combined segment score
```

### AudienceAnalysisResult
```python
@dataclass
class AudienceAnalysisResult:
    overall_score: float                    # 1-5 scale
    direct_address_score: float             # 0-1 normalized
    pacing_score: float                     # 0-1 normalized
    emotional_invitation_score: float       # 0-1 normalized
    engagement_pattern_score: float         # 0-1 normalized
    segments: List[AudienceSegment]
    engagement_events: List[EngagementEvent]
    engagement_curve: Optional[np.ndarray]  # Engagement over time
    processing_time_ms: float
    duration: float
    strength_moments: List[Dict]
    weakness_moments: List[Dict]
```

## Usage Example

```python
from python.analysis_modules.audience_engine import AudienceEngine

# Initialize
engine = AudienceEngine()

# Analyze (standalone)
result = engine.analyze(
    video_path="performance.mp4",
    audio_path="performance.wav",
    transcript="Do you remember when we were young?",
    word_segments=word_segments
)

# With Spirit Engine integration
result = engine.analyze(
    video_path="performance.mp4",
    audio_path="performance.wav",
    transcript=transcript,
    word_segments=word_segments,
    spirit_result=spirit_result  # From Spirit Engine
)

print(f"Audience Score: {result.overall_score:.2f}/5")
print(f"Direct Address: {result.direct_address_score:.2f}")
print(f"Pacing: {result.pacing_score:.2f}")
print(f"Emotional Invitation: {result.emotional_invitation_score:.2f}")
print(f"Engagement Patterns: {result.engagement_pattern_score:.2f}")

# Generate coach feedback
feedback = engine.generate_feedback(result)
print(feedback)
```

## Coach Feedback Examples

### High Score (4.5+)
> "You're speaking WITH the audience, not AT them! This is true connection."

### Mid Score (2.5-3.5)
> "You're performing TO the audience, but not yet WITH them. Let them in."

### Low Score (<2.5)
> "The audience feels like spectators, not participants. Break down that wall."

### Component-Specific Feedback
- **Direct Address:** "Speak TO the audience - use 'you', 'we', ask questions."
- **Pacing:** "Let moments land. After something powerful, PAUSE."
- **Emotional Invitation:** "You're guarding your emotions. Be vulnerable."
- **Engagement Patterns:** "Vary your energy. Monotony loses audiences."

## Key Design Decisions

### MID Video Scores LOW (2/5)
The MID video scores 2/5 for Audience (not 3/5) because:
- Performer has good energy but performs AT the audience
- Doesn't create shared emotional moments
- This is a key differentiator from other engines

### Focus on ENGAGEMENT not QUALITY
Audience Engine measures CONNECTION with audience, not technical quality.
A technically flawed but emotionally open performance can score high.

### Direct Address is Critical
Without direct address, there's no audience connection. The floor effect
ensures that no-direct-address performances can't score above ~1.5/5.

## Dependencies

No new heavy dependencies required. Uses:
- numpy (already installed)
- re (standard library)
- logging (standard library)

## Future Enhancements

1. **Body Engine Integration:** Use physical gestures for engagement signals
2. **Audience Detection:** Analyze audience audio/reactions if available
3. **Temporal Patterns:** Detect "golden moments" where all signals align
4. **Personalized Feedback:** Tailored suggestions based on weakness patterns
