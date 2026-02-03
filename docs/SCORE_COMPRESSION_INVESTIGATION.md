# Score Compression Investigation Report

**Date:** 2026-02-03
**Branch:** claude/investigate-score-compression-gBLKo
**Issue:** Scores clustering between 3.1-3.9; Spirit 4.5 test result rendering as ~2.9 in production

---

## Executive Summary

**Primary Compression Source:** The Beta deterministic score generation in `run_analysis.py` generates all pillar scores in a **narrow range [2.5, 4.8]**, creating artificial clustering around 3.1-3.9 for overall scores.

**Spirit 4.5 → 2.9 Transformation:** Mathematically impossible within Beta constraints. Requires verification of actual test conditions.

**Scores are NOT transformed** - Spirit scores are real calculations from prosody/emotion analysis; other pillars are deterministic placeholders in Beta mode.

---

## 1. Where Compression Happens

### PRIMARY: Beta Pillar Generation
**Location:** `python/run_analysis.py:542-545`

```python
# Generate pillar scores (1-5 scale, consistent per file)
spirit_score = round(rng.uniform(2.5, 4.8), 1)   # ← COMPRESSED RANGE
chest_score = round(rng.uniform(2.5, 4.8), 1)    # ← COMPRESSED RANGE
body_score = round(rng.uniform(2.5, 4.8), 1)     # ← COMPRESSED RANGE
audience_score = round(rng.uniform(2.5, 4.8), 1) # ← COMPRESSED RANGE
```

**Impact:**
- Artificial floor at 2.5 (prevents scores below "Emerging")
- Artificial ceiling at 4.8 (prevents "Strong" 5.0 scores)
- Mean: 3.65 (mid-range bias)
- Effective range: 2.3 points (should be 4.0 for full scale)

### SECONDARY: Weighted Averaging Dampening
**Location:** `python/run_analysis.py:548-554`

```python
overall_score = round(
    spirit_score * 0.30 +
    chest_score * 0.25 +
    body_score * 0.25 +
    audience_score * 0.20,
    1
)
```

**Impact:**
- Weighted averaging dampens variance by 74% (σ: 0.66 → 0.33)
- Even strong individual pillar (4.5) contributes only 1.35 to overall
- Three weak pillars (2.5 each) contribute 1.75, overwhelming strong pillar
- Result: Regression to mean around 3.5

---

## 2. Raw vs Rendered Score Comparison

### Spirit Engine (REAL - Production Ready)

**Component Calculation (0-1 normalized):**
- Emotion-Word Alignment (25%): `spirit_engine.py:195-289`
- Emotional Transition Quality (20%): `spirit_engine.py:291-344`
- Emotional Range (45%): `spirit_engine.py:346-397`
- Settling Indicator (10%): `spirit_engine.py:399-449`

**Transformation to 1-5 scale:**
```python
def _normalize_to_5_scale(self, score: float) -> float:
    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
    return 1.0 + score * 4.0           # Map to [1, 5]
```

**Examples:**
- Raw 0.0 → Rendered 1.0 ("Early")
- Raw 0.5 → Rendered 3.0 ("Emerging")
- Raw 0.875 → Rendered 4.5 ("Strong")
- Raw 1.0 → Rendered 5.0 ("Strong")

### Chest, Body, Audience (BETA Placeholders)

**Generation:** Direct random in [2.5, 4.8] - no component calculations or transformations.

---

## 3. Normalization & Transformation Steps

### Spirit Engine Pipeline

| Step | File:Line | Operation | Input → Output |
|------|-----------|-----------|----------------|
| Component calculation | `spirit_engine.py:195-449` | Various algorithms | Raw features → [0, 1] |
| Weighted aggregation | `spirit_engine.py:165-168` | Weighted sum | [0, 1] × 4 → [0, 1] |
| Clamping | `spirit_engine.py:479` | `max(0, min(1, x))` | Any → [0, 1] |
| Scale transform | `spirit_engine.py:481` | `1 + x * 4` | [0, 1] → [1, 5] |

### Beta Engine Pipeline

| Step | File:Line | Operation | Input → Output |
|------|-----------|-----------|----------------|
| Random generation | `run_analysis.py:542-545` | `rng.uniform(2.5, 4.8)` | N/A → [2.5, 4.8] |
| Rounding | `run_analysis.py:542-545` | `round(x, 1)` | Float → 0.1 precision |

### Subscore Pipeline

| Step | File:Line | Operation | Input → Output |
|------|-----------|-----------|----------------|
| Gaussian generation | `run_analysis.py:560` | `rng.gauss(base, 0.5)` | N/A → Gaussian |
| Clamping | `run_analysis.py:561` | `max(1, min(5, x))` | Any → [1, 5] |
| Rounding | `run_analysis.py:562` | `round(x, 1)` | Float → 0.1 precision |

---

## 4. Why Scores Cluster 3.1-3.9

### Mathematical Analysis

**Given:** Four pillars from `uniform(2.5, 4.8)`
- **Mean:** (2.5 + 4.8) / 2 = **3.65**
- **Std Dev:** (4.8 - 2.5) / √12 ≈ **0.66**

**Overall Score Statistics:**
```
E[Overall] = 3.65 × (0.30 + 0.25 + 0.25 + 0.20) = 3.65
σ[Overall] = √((0.30² + 0.25² + 0.25² + 0.20²) × 0.66²) ≈ 0.33
```

**Expected Distribution:**
- **68% of scores:** 3.65 ± 0.33 = **[3.3, 4.0]**
- **95% of scores:** 3.65 ± 0.66 = **[3.0, 4.3]**

**Observed clustering (3.1-3.9) perfectly matches the 68% confidence interval.**

### Root Causes

1. Artificial floor at 2.5 prevents low scores
2. Artificial ceiling at 4.8 prevents high scores
3. Weighted averaging dampens variance by 74%
4. Rounding to 0.1 quantizes distribution
5. Central Limit Theorem: Averaging 4 variables creates normal distribution

---

## 5. Spirit 4.5 → 2.9 Investigation

### Mathematical Feasibility

**For Overall = 2.9 with Spirit = 4.5:**
```
4.5 × 0.30 + X × 0.70 = 2.9
1.35 + 0.70X = 2.9
X = 2.214
```

**Conclusion:** Requires other three pillars to average 2.214, which is **BELOW the Beta floor of 2.5**.

**Verdict:** **MATHEMATICALLY IMPOSSIBLE** within Beta constraints.

### Possible Explanations

1. **Real Spirit engine run** with other engines producing scores < 2.5 (old code version?)
2. **Database contains pre-Beta scores** before [2.5, 4.8] range was implemented
3. **User confusion:** 4.5 was a **subscore** (e.g., emotion_alignment), not Spirit pillar score
4. **Display bug:** Rounding or formatting artifact
5. **Test environment:** Different scoring logic than production

### Verification Needed

- Was this a real Spirit engine run or Beta deterministic generation?
- Was 4.5 a pillar score or subscore?
- What were the actual Chest/Body/Audience scores?
- Check database record for that performance

---

## 6. Recommended Calibration Changes

### Option A: Expand Beta Range (IMMEDIATE FIX)

**File:** `python/run_analysis.py:542-545`

**Current:**
```python
spirit_score = round(rng.uniform(2.5, 4.8), 1)
chest_score = round(rng.uniform(2.5, 4.8), 1)
body_score = round(rng.uniform(2.5, 4.8), 1)
audience_score = round(rng.uniform(2.5, 4.8), 1)
```

**Recommended:**
```python
# Expand range with triangular distribution (mode=3.5)
spirit_score = round(rng.triangular(1.5, 5.0, 3.5), 1)
chest_score = round(rng.triangular(1.5, 5.0, 3.5), 1)
body_score = round(rng.triangular(1.5, 5.0, 3.5), 1)
audience_score = round(rng.triangular(1.5, 5.0, 3.5), 1)
```

**Impact:**
- Range: [1.5, 5.0] (3.5 point spread vs 2.3 currently)
- Mode: 3.5 (maintains realistic distribution)
- Mean: ≈3.5 (similar to current)
- Overall spread: [2.0, 4.5] expected (68% CI: [2.8, 4.2])

**Alternative (Beta distribution for more control):**
```python
def beta_score(rng, low=1.0, high=5.0, alpha=2.5, beta=2.5):
    """Generate score using Beta distribution (bell curve)."""
    raw = rng.betavariate(alpha, beta)
    return round(low + raw * (high - low), 1)

spirit_score = beta_score(rng, 1.5, 5.0, alpha=2.5, beta=2.5)
# ... repeat for other pillars
```

---

### Option B: Rebalance Spirit Component Weights

**File:** `python/analysis_modules/spirit_engine/spirit_engine.py:84-89`

**Current:**
```python
self.weights = {
    'emotion_alignment': 0.25,
    'transition_quality': 0.20,
    'emotional_range': 0.45,    # Dominates
    'settling': 0.10
}
```

**Recommended:**
```python
self.weights = {
    'emotion_alignment': 0.30,     # Increase (core metric)
    'transition_quality': 0.25,    # Increase (skill differentiator)
    'emotional_range': 0.35,       # Decrease (reduce dominance)
    'settling': 0.10               # Keep (consistency indicator)
}
```

**Rationale:**
- Alignment and transitions are more technically measurable
- Range still important but less dominant (45% → 35%)
- Better balance across components

---

### Option C: Add Score Stretch Transform (ADVANCED)

**File:** `python/run_analysis.py` after line 554

**Add function:**
```python
def stretch_score(score, center=3.5, stretch_factor=1.3, min_score=1.0, max_score=5.0):
    """
    Non-linear stretch to expand score range.
    Scores far from center are amplified.
    """
    deviation = score - center
    stretched_deviation = deviation * stretch_factor
    stretched = center + stretched_deviation
    return max(min_score, min(max_score, stretched))
```

**Apply to overall:**
```python
raw_overall = (
    spirit_score * 0.30 +
    chest_score * 0.25 +
    body_score * 0.25 +
    audience_score * 0.20
)
overall_score = round(stretch_score(raw_overall, stretch_factor=1.3), 1)
```

**Effect:**
- 2.5 → 2.2 (floor moves down)
- 3.0 → 2.85
- 3.5 → 3.5 (center unchanged)
- 4.0 → 4.15
- 4.5 → 4.8 (ceiling moves up)

---

### Option D: Add Standout Bonus/Weakness Penalty

**File:** `python/run_analysis.py:548-554`

**Current:** Simple weighted average

**Recommended:**
```python
# Base weighted average
base_overall = (
    spirit_score * 0.30 +
    chest_score * 0.25 +
    body_score * 0.25 +
    audience_score * 0.20
)

# Standout bonus: reward exceptional pillars
max_pillar = max(spirit_score, chest_score, body_score, audience_score)
standout_bonus = max(0, (max_pillar - 4.0) * 0.15)  # Up to +0.15

# Weakness penalty: penalize very weak pillars
min_pillar = min(spirit_score, chest_score, body_score, audience_score)
weakness_penalty = max(0, (2.5 - min_pillar) * 0.15)  # Up to -0.225

overall_score = round(
    base_overall + standout_bonus - weakness_penalty,
    1
)
overall_score = max(1.0, min(5.0, overall_score))
```

**Impact:**
- Excellent pillar (5.0) adds +0.15 to overall
- Very weak pillar (1.0) subtracts -0.225 from overall
- Increases variance without inflating all scores
- Philosophically aligned: rewards excellence, penalizes weaknesses

---

## Implementation Order

1. **IMMEDIATE:** Option A - Expand Beta range to `triangular(1.5, 5.0, 3.5)`
   - One-line change per pillar
   - Instant score spread improvement
   - No side effects

2. **SHORT-TERM:** Option B - Rebalance Spirit weights (30/25/35/10)
   - Test with benchmark performances
   - Validate against POTS expert ratings
   - Deploy after 2-week validation

3. **MEDIUM-TERM:** Option D - Add standout bonus/weakness penalty
   - More POTS-aligned philosophy
   - Rewards excellence naturally
   - Deploy after real engines implemented

4. **OPTIONAL:** Option C - Score stretch transform
   - Only if A+B+D insufficient
   - Requires careful parameter tuning
   - Risk of over-correction

---

## Exact Levers Summary

| Lever | File | Line | Current | Recommended |
|-------|------|------|---------|-------------|
| Beta floor | `run_analysis.py` | 542-545 | `2.5` | `1.5` |
| Beta ceiling | `run_analysis.py` | 542-545 | `4.8` | `5.0` |
| Beta distribution | `run_analysis.py` | 542-545 | `uniform` | `triangular(mode=3.5)` |
| Spirit alignment wt | `spirit_engine.py` | 85 | `0.25` | `0.30` |
| Spirit transition wt | `spirit_engine.py` | 86 | `0.20` | `0.25` |
| Spirit range wt | `spirit_engine.py` | 87 | `0.45` | `0.35` |
| Subscore std dev | `run_analysis.py` | 560 | `0.5` | Keep |
| Overall weights | `run_analysis.py` | 549-552 | 30/25/25/20 | Keep (POTS-aligned) |

---

## Key Findings

### Where Compression Happens
1. **PRIMARY:** Beta pillar generation - narrow range [2.5, 4.8]
2. **SECONDARY:** Weighted averaging - dampens variance by 74%
3. **TERTIARY:** Subscore Gaussian clustering around pillar

### Scores: Real or Transformed?
- **Spirit:** REAL (calculated from audio analysis) → transformed [0,1] to [1,5]
- **Chest/Body/Audience (Beta):** ARTIFICIAL (deterministic random)
- **Overall:** CALCULATED (weighted average)
- **All deterministic:** Same video → same scores (hash-seeded)

### Exact Adjustment Levers
- **Immediate impact:** Change `uniform(2.5, 4.8)` → `triangular(1.5, 5.0, 3.5)`
- **Medium impact:** Rebalance Spirit weights: 25/20/45/10 → 30/25/35/10
- **Advanced impact:** Add standout bonus/weakness penalty to overall
