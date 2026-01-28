"""
Stage Buddy V2 - Direct Address Analyzer
Analyzes whether the performer speaks TO the audience or AT them.

Direct Address Indicators:
- Second person pronouns ("you", "your", "yourself")
- Inclusive pronouns ("we", "us", "our", "let's")
- Rhetorical questions that engage the audience
- Imperative/command forms that invite participation
- Conversational patterns vs formal recitation

Scoring:
- High direct address = speaking WITH the audience (intimacy)
- Low direct address = performing AT the audience (distance)
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import logging

from ..shared.data_structures import WordSegment, EngagementEvent

logger = logging.getLogger(__name__)


# Direct address pronouns (speaking TO the audience)
DIRECT_ADDRESS_PRONOUNS = {
    'you', 'your', 'yours', 'yourself', 'yourselves',
    'we', 'us', 'our', 'ours', 'ourselves',
    "let's", "lets"  # Inclusive invitation
}

# Self-focused pronouns (speaking ABOUT self, not TO audience)
SELF_FOCUSED_PRONOUNS = {
    'i', 'me', 'my', 'mine', 'myself'
}

# Third-person pronouns (distance from audience)
THIRD_PERSON_PRONOUNS = {
    'he', 'she', 'they', 'them', 'his', 'her', 'their',
    'him', 'hers', 'theirs', 'it', 'its'
}

# Rhetorical question indicators
QUESTION_WORDS = {'who', 'what', 'when', 'where', 'why', 'how', 'which', 'whose', 'whom'}

# Command/imperative indicators (engagement invitation)
IMPERATIVE_STARTERS = {
    'listen', 'look', 'see', 'hear', 'feel', 'imagine', 'think', 'remember',
    'come', 'follow', 'join', 'be', 'take', 'give', 'hold', 'let', 'know',
    'watch', 'notice', 'consider', 'understand'
}


class DirectAddressAnalyzer:
    """
    Analyzes direct address patterns in spoken word performances.

    A strong performer speaks WITH their audience, creating intimacy through:
    - Direct pronouns (you, we)
    - Rhetorical questions
    - Inclusive language
    - Imperative invitations
    """

    def __init__(
        self,
        segment_duration: float = 3.0,
        min_words_per_segment: int = 5
    ):
        """
        Initialize the Direct Address Analyzer.

        Args:
            segment_duration: Duration of analysis segments in seconds
            min_words_per_segment: Minimum words needed for valid analysis
        """
        self.segment_duration = segment_duration
        self.min_words_per_segment = min_words_per_segment

        logger.info("DirectAddressAnalyzer initialized")

    def analyze(
        self,
        transcript: str,
        word_segments: List[WordSegment]
    ) -> Dict[str, Any]:
        """
        Analyze direct address patterns in the transcript.

        Args:
            transcript: Full transcript text
            word_segments: Word-level timing information

        Returns:
            Dictionary with:
            - overall_score: 0-1 direct address score
            - segment_scores: Per-segment breakdown
            - engagement_events: Key direct address moments
            - metrics: Detailed metrics
        """
        if not transcript or not word_segments:
            logger.warning("No transcript or word segments provided")
            return self._empty_result()

        logger.info(f"Analyzing direct address in {len(word_segments)} words")

        # Analyze overall transcript
        overall_metrics = self._analyze_text(transcript)

        # Analyze by time segments
        segment_results = self._analyze_by_segments(word_segments)

        # Find engagement events (strong direct address moments)
        engagement_events = self._find_engagement_events(word_segments, transcript)

        # Calculate overall score
        overall_score = self._calculate_overall_score(overall_metrics, segment_results)

        return {
            'overall_score': overall_score,
            'segment_scores': segment_results,
            'engagement_events': engagement_events,
            'metrics': overall_metrics
        }

    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze pronoun distribution and direct address patterns in text."""
        words = text.lower().split()
        total_words = len(words)

        if total_words == 0:
            return self._empty_metrics()

        # Count pronoun types
        direct_count = sum(1 for w in words if self._clean_word(w) in DIRECT_ADDRESS_PRONOUNS)
        self_count = sum(1 for w in words if self._clean_word(w) in SELF_FOCUSED_PRONOUNS)
        third_count = sum(1 for w in words if self._clean_word(w) in THIRD_PERSON_PRONOUNS)

        # Count rhetorical questions
        sentences = re.split(r'[.!?]+', text)
        question_count = sum(1 for s in sentences if '?' in s or self._is_rhetorical_question(s))

        # Count imperative forms
        imperative_count = self._count_imperatives(text)

        # Calculate ratios
        pronoun_total = direct_count + self_count + third_count

        if pronoun_total > 0:
            direct_ratio = direct_count / pronoun_total
            self_ratio = self_count / pronoun_total
        else:
            # No pronouns - neutral
            direct_ratio = 0.5
            self_ratio = 0.5

        # Question density (per 100 words)
        question_density = (question_count / total_words) * 100 if total_words > 0 else 0

        # Imperative density (per 100 words)
        imperative_density = (imperative_count / total_words) * 100 if total_words > 0 else 0

        return {
            'total_words': total_words,
            'direct_pronouns': direct_count,
            'self_pronouns': self_count,
            'third_person_pronouns': third_count,
            'direct_ratio': direct_ratio,
            'self_ratio': self_ratio,
            'question_count': question_count,
            'question_density': question_density,
            'imperative_count': imperative_count,
            'imperative_density': imperative_density
        }

    def _analyze_by_segments(
        self,
        word_segments: List[WordSegment]
    ) -> List[Dict[str, Any]]:
        """Analyze direct address in time-based segments."""
        if not word_segments:
            return []

        # Get total duration
        end_time = word_segments[-1].end_time
        segments = []

        current_time = 0.0
        while current_time < end_time:
            segment_end = min(current_time + self.segment_duration, end_time)

            # Get words in this segment
            segment_words = [
                ws for ws in word_segments
                if ws.start_time >= current_time and ws.start_time < segment_end
            ]

            if len(segment_words) >= self.min_words_per_segment:
                # Analyze this segment
                segment_text = ' '.join(ws.word for ws in segment_words)
                metrics = self._analyze_text(segment_text)

                # Calculate segment score
                segment_score = self._calculate_segment_score(metrics)

                segments.append({
                    'start_time': current_time,
                    'end_time': segment_end,
                    'score': segment_score,
                    'word_count': len(segment_words),
                    'direct_pronouns': metrics['direct_pronouns'],
                    'has_question': metrics['question_count'] > 0
                })

            current_time = segment_end

        return segments

    def _find_engagement_events(
        self,
        word_segments: List[WordSegment],
        transcript: str
    ) -> List[EngagementEvent]:
        """Find specific moments of strong direct address."""
        events = []

        # Find rhetorical questions
        sentences = self._split_into_sentences(transcript, word_segments)
        for sentence in sentences:
            if self._is_rhetorical_question(sentence['text']):
                events.append(EngagementEvent(
                    timestamp=sentence['start_time'],
                    duration=sentence['end_time'] - sentence['start_time'],
                    event_type='direct_address',
                    engagement_level=0.8,
                    description=f"Rhetorical question: '{sentence['text'][:50]}...'"
                ))

        # Find "you" clusters (multiple direct addresses in short span)
        you_positions = []
        for ws in word_segments:
            if self._clean_word(ws.word.lower()) in {'you', 'your', 'we', 'us'}:
                you_positions.append(ws.start_time)

        # Find clusters (3+ direct pronouns in 5 seconds)
        for i, pos in enumerate(you_positions):
            cluster_count = sum(1 for p in you_positions if pos <= p < pos + 5.0)
            if cluster_count >= 3:
                events.append(EngagementEvent(
                    timestamp=pos,
                    duration=5.0,
                    event_type='direct_address',
                    engagement_level=0.9,
                    description="Strong direct address cluster"
                ))

        # Find imperative moments
        for ws in word_segments:
            if self._clean_word(ws.word.lower()) in IMPERATIVE_STARTERS:
                events.append(EngagementEvent(
                    timestamp=ws.start_time,
                    duration=ws.duration,
                    event_type='direct_address',
                    engagement_level=0.7,
                    description=f"Imperative invitation: '{ws.word}'"
                ))

        return events

    def _calculate_segment_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate direct address score for a segment."""
        # Base score from direct pronoun ratio
        # High direct ratio = good, high self ratio = less good
        pronoun_score = metrics['direct_ratio'] * 0.7 + (1.0 - metrics['self_ratio']) * 0.3

        # Boost for questions (engagement)
        question_boost = min(0.2, metrics['question_density'] * 0.05)

        # Boost for imperatives
        imperative_boost = min(0.1, metrics['imperative_density'] * 0.02)

        score = pronoun_score + question_boost + imperative_boost
        return min(1.0, max(0.0, score))

    def _calculate_overall_score(
        self,
        overall_metrics: Dict[str, Any],
        segment_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall direct address score."""
        # Base score from overall metrics
        base_score = self._calculate_segment_score(overall_metrics)

        # Consider segment variance (consistent engagement is better)
        if segment_results:
            segment_scores = [s['score'] for s in segment_results]
            avg_segment_score = sum(segment_scores) / len(segment_scores)

            # Variance penalty (inconsistent = slightly lower score)
            if len(segment_scores) > 1:
                variance = sum((s - avg_segment_score) ** 2 for s in segment_scores) / len(segment_scores)
                variance_penalty = min(0.1, variance)
            else:
                variance_penalty = 0

            # Combine base and segment scores
            score = base_score * 0.5 + avg_segment_score * 0.5 - variance_penalty
        else:
            score = base_score

        return min(1.0, max(0.0, score))

    def _is_rhetorical_question(self, text: str) -> bool:
        """Check if a sentence appears to be a rhetorical question."""
        text_lower = text.lower().strip()

        # Check for question mark
        if '?' in text:
            return True

        # Check for question word at start
        words = text_lower.split()
        if words and words[0] in QUESTION_WORDS:
            return True

        # Check for inverted question structure ("do you", "can you", "have you")
        if len(words) >= 2:
            auxiliaries = {'do', 'does', 'did', 'can', 'could', 'will', 'would', 'have', 'has', 'are', 'is', 'was', 'were'}
            if words[0] in auxiliaries and words[1] in {'you', 'we', 'i'}:
                return True

        return False

    def _count_imperatives(self, text: str) -> int:
        """Count imperative/command forms in text."""
        sentences = re.split(r'[.!?]+', text)
        count = 0

        for sentence in sentences:
            words = sentence.lower().split()
            if words:
                first_word = self._clean_word(words[0])
                if first_word in IMPERATIVE_STARTERS:
                    count += 1

        return count

    def _split_into_sentences(
        self,
        transcript: str,
        word_segments: List[WordSegment]
    ) -> List[Dict[str, Any]]:
        """Split transcript into sentences with timing."""
        sentences = []

        # Simple sentence splitting
        sentence_texts = re.split(r'(?<=[.!?])\s+', transcript)

        current_word_idx = 0
        for sentence_text in sentence_texts:
            if not sentence_text.strip():
                continue

            sentence_words = sentence_text.split()
            if not sentence_words:
                continue

            # Find start time
            start_time = 0.0
            end_time = 0.0

            for i in range(current_word_idx, min(current_word_idx + len(sentence_words) + 5, len(word_segments))):
                if i < len(word_segments):
                    if self._words_match(word_segments[i].word, sentence_words[0]):
                        start_time = word_segments[i].start_time
                        # Find end
                        for j in range(i, min(i + len(sentence_words) + 5, len(word_segments))):
                            if self._words_match(word_segments[j].word, sentence_words[-1]):
                                end_time = word_segments[j].end_time
                                current_word_idx = j + 1
                                break
                        break

            if end_time == 0.0:
                end_time = start_time + 3.0  # Default duration

            sentences.append({
                'text': sentence_text,
                'start_time': start_time,
                'end_time': end_time
            })

        return sentences

    def _words_match(self, word1: str, word2: str) -> bool:
        """Check if two words match (ignoring punctuation)."""
        return self._clean_word(word1.lower()) == self._clean_word(word2.lower())

    def _clean_word(self, word: str) -> str:
        """Remove punctuation from word."""
        return re.sub(r'[^\w]', '', word.lower())

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result for invalid input."""
        return {
            'overall_score': 0.5,  # Neutral score
            'segment_scores': [],
            'engagement_events': [],
            'metrics': self._empty_metrics()
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics."""
        return {
            'total_words': 0,
            'direct_pronouns': 0,
            'self_pronouns': 0,
            'third_person_pronouns': 0,
            'direct_ratio': 0.5,
            'self_ratio': 0.5,
            'question_count': 0,
            'question_density': 0.0,
            'imperative_count': 0,
            'imperative_density': 0.0
        }


def analyze_direct_address(
    transcript: str,
    word_segments: List[WordSegment]
) -> Dict[str, Any]:
    """
    Convenience function for direct address analysis.

    Args:
        transcript: Full transcript text
        word_segments: Word-level timing information

    Returns:
        Dictionary with direct address analysis results
    """
    analyzer = DirectAddressAnalyzer()
    return analyzer.analyze(transcript, word_segments)
