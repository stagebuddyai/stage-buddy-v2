"""
Stage Buddy V2 - Spirit Engine: Text Emotion Analyzer
Predicts the "ideal" emotional arc from transcript text.

This module answers: "What emotions SHOULD be expressed for these words?"
By comparing this ideal arc to the actually detected vocal emotions,
we can measure emotion-word alignment - the core Spirit metric.
"""

import re
import os
import warnings
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

def _resolve_hf_token() -> str | None:
    """Resolve HuggingFace token from environment with validation."""
    token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')
    if not token:
        return None
    token = token.strip()
    if not token.startswith('hf_'):
        logging.warning(
            "HF_TOKEN does not start with 'hf_' — may not be a valid HuggingFace token."
        )
    os.environ['HF_TOKEN'] = token
    return token

HF_TOKEN = _resolve_hf_token()

try:
    # Suppress the position_ids warning from transformers during model loading
    # This happens because roberta-base-go_emotions was saved with position_ids
    # as a buffer, but newer transformers don't expect it. It's harmless.
    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")  # Avoid tokenizer warnings

    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    from transformers import logging as transformers_logging

    # Set transformers logging to only show errors (suppress position_ids INFO/WARNING)
    transformers_logging.set_verbosity_error()

    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("transformers not installed. Install with: pip install transformers torch")

from ..shared.data_structures import EmotionCategory, EmotionSegment, WordSegment

logger = logging.getLogger(__name__)


# Mapping from various emotion model outputs to our EmotionCategory
EMOTION_LABEL_MAP = {
    # Standard emotion labels
    'joy': EmotionCategory.HAPPY,
    'happiness': EmotionCategory.HAPPY,
    'happy': EmotionCategory.HAPPY,
    'love': EmotionCategory.HAPPY,
    'optimism': EmotionCategory.HAPPY,
    
    'sadness': EmotionCategory.SAD,
    'sad': EmotionCategory.SAD,
    'grief': EmotionCategory.SAD,
    'disappointment': EmotionCategory.SAD,
    
    'anger': EmotionCategory.ANGRY,
    'angry': EmotionCategory.ANGRY,
    'annoyance': EmotionCategory.ANGRY,
    'frustration': EmotionCategory.ANGRY,
    
    'fear': EmotionCategory.FEARFUL,
    'fearful': EmotionCategory.FEARFUL,
    'nervousness': EmotionCategory.FEARFUL,
    'anxiety': EmotionCategory.FEARFUL,
    
    'surprise': EmotionCategory.SURPRISED,
    'surprised': EmotionCategory.SURPRISED,
    'realization': EmotionCategory.SURPRISED,
    
    'disgust': EmotionCategory.DISGUSTED,
    'disgusted': EmotionCategory.DISGUSTED,
    
    'neutral': EmotionCategory.NEUTRAL,
    
    # Extended emotions
    'calm': EmotionCategory.CALM,
    'caring': EmotionCategory.TENDER,
    'admiration': EmotionCategory.TENDER,
    'gratitude': EmotionCategory.TENDER,
    'desire': EmotionCategory.EXCITED,
    'excitement': EmotionCategory.EXCITED,
    'pride': EmotionCategory.DETERMINED,
    'determination': EmotionCategory.DETERMINED,
    'curiosity': EmotionCategory.SURPRISED,
    'confusion': EmotionCategory.NEUTRAL,
    'embarrassment': EmotionCategory.FEARFUL,
    'remorse': EmotionCategory.SAD,
    'amusement': EmotionCategory.HAPPY,
    'approval': EmotionCategory.HAPPY,
    'disapproval': EmotionCategory.ANGRY,
}

# Valence-Arousal mappings for emotions
EMOTION_VA_MAP = {
    EmotionCategory.HAPPY: (0.8, 0.6),      # Positive, moderately aroused
    EmotionCategory.SAD: (-0.7, 0.3),        # Negative, low arousal
    EmotionCategory.ANGRY: (-0.6, 0.9),      # Negative, high arousal
    EmotionCategory.FEARFUL: (-0.7, 0.8),    # Negative, high arousal
    EmotionCategory.SURPRISED: (0.1, 0.8),   # Neutral-positive, high arousal
    EmotionCategory.DISGUSTED: (-0.8, 0.5),  # Very negative, moderate arousal
    EmotionCategory.NEUTRAL: (0.0, 0.3),     # Neutral, low arousal
    EmotionCategory.CALM: (0.4, 0.1),        # Positive, very low arousal
    EmotionCategory.EXCITED: (0.7, 0.9),     # Positive, very high arousal
    EmotionCategory.TENDER: (0.6, 0.2),      # Positive, low arousal
    EmotionCategory.DETERMINED: (0.3, 0.7),  # Slightly positive, high arousal
}


class TextEmotionAnalyzer:
    """
    Analyzes text to predict what emotions should be expressed.
    
    Uses transformer-based emotion classification to generate an
    "ideal emotional arc" from the transcript. This represents what
    the Spirit of the piece demands, regardless of how the performer
    might be feeling at the moment.
    """
    
    def __init__(
        self,
        model_name: str = "SamLowe/roberta-base-go_emotions",
        device: str = "auto"
    ):
        """
        Initialize the text emotion analyzer.
        
        Args:
            model_name: HuggingFace model for emotion classification.
                Options:
                - "SamLowe/roberta-base-go_emotions" (27 emotions, recommended)
                - "j-hartmann/emotion-english-distilroberta-base" (7 emotions)
                - "bhadresh-savani/bert-base-uncased-emotion" (6 emotions)
            device: "auto", "cpu", or "cuda"
        """
        self.model_name = model_name
        
        if TRANSFORMERS_AVAILABLE:
            if device == "auto":
                device = 0 if torch.cuda.is_available() else -1
            elif device == "cpu":
                device = -1
            elif device == "cuda":
                device = 0

            try:
                # Suppress warnings during model loading (position_ids mismatch is harmless)
                # The UNEXPECTED status for roberta.embeddings.position_ids is expected
                # when loading models saved with older transformers versions
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=".*position_ids.*")
                    warnings.filterwarnings("ignore", message=".*UNEXPECTED.*")
                    warnings.filterwarnings("ignore", category=UserWarning)
                    warnings.filterwarnings("ignore", category=FutureWarning)

                    # Build pipeline kwargs
                    pipeline_kwargs = {
                        "task": "text-classification",
                        "model": model_name,
                        "top_k": None,  # Return all emotions with scores
                        "device": device,
                    }

                    # Add HF token if available for authenticated downloads
                    if HF_TOKEN:
                        pipeline_kwargs["token"] = HF_TOKEN

                    self.classifier = pipeline(**pipeline_kwargs)
                logger.info(f"Loaded emotion model: {model_name}")
            except Exception as e:
                err_str = str(e)
                if '403' in err_str or 'Forbidden' in err_str:
                    logger.error(
                        f"Model download returned 403 Forbidden for {model_name}. "
                        "Your HF_TOKEN may be invalid or lack 'read' permissions. "
                        "Verify at https://huggingface.co/settings/tokens"
                    )
                elif '401' in err_str or 'Unauthorized' in err_str:
                    logger.error(
                        f"Model download returned 401 for {model_name}. "
                        "Set a valid HF_TOKEN in .env.local."
                    )
                else:
                    logger.error(f"Failed to load emotion model: {e}")
                self.classifier = None
        else:
            self.classifier = None
            logger.warning("Transformers not available - using rule-based fallback")
    
    def analyze_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze a piece of text for emotional content.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of emotion predictions with scores
        """
        if self.classifier is not None:
            try:
                results = self.classifier(text)
                if isinstance(results, list) and len(results) > 0:
                    if isinstance(results[0], list):
                        # Multiple inputs case
                        return results[0]
                    return results
            except Exception as e:
                logger.error(f"Emotion classification failed: {e}")
        
        # Fallback to rule-based
        return self._rule_based_analysis(text)
    
    def _rule_based_analysis(self, text: str) -> List[Dict[str, Any]]:
        """Simple keyword-based emotion detection as fallback."""
        text_lower = text.lower()
        
        scores = {
            'joy': 0.0,
            'sadness': 0.0,
            'anger': 0.0,
            'fear': 0.0,
            'surprise': 0.0,
            'disgust': 0.0,
            'neutral': 0.3  # Base neutral score
        }
        
        # Keyword patterns
        joy_words = ['happy', 'joy', 'love', 'wonderful', 'beautiful', 'amazing', 'blessed', 'smile']
        sad_words = ['sad', 'cry', 'tears', 'lost', 'miss', 'gone', 'pain', 'hurt', 'broken']
        anger_words = ['angry', 'hate', 'rage', 'fury', 'damn', 'fight', 'fire', 'burn']
        fear_words = ['afraid', 'fear', 'scared', 'terror', 'nightmare', 'dark', 'shadow']
        surprise_words = ['wow', 'amazing', 'suddenly', 'unexpected', 'shock']
        
        for word in joy_words:
            if word in text_lower:
                scores['joy'] += 0.2
        for word in sad_words:
            if word in text_lower:
                scores['sadness'] += 0.2
        for word in anger_words:
            if word in text_lower:
                scores['anger'] += 0.2
        for word in fear_words:
            if word in text_lower:
                scores['fear'] += 0.2
        for word in surprise_words:
            if word in text_lower:
                scores['surprise'] += 0.2
        
        # Normalize and convert to expected format
        total = sum(scores.values())
        return [{'label': k, 'score': v / total} for k, v in scores.items() if v > 0]
    
    def generate_ideal_arc(
        self,
        words: List[WordSegment],
        segment_duration: float = 3.0,
        overlap: float = 1.0
    ) -> List[EmotionSegment]:
        """
        Generate the ideal emotional arc for a performance.
        
        This is the core function for Spirit scoring - it predicts what
        emotions SHOULD be expressed at each point in the performance
        based on the text content.
        
        Args:
            words: List of transcribed words with timestamps
            segment_duration: Duration of each analysis segment in seconds
            overlap: Overlap between segments for smooth transitions
            
        Returns:
            List of EmotionSegment representing the ideal emotional arc
        """
        if not words:
            return []
        
        ideal_arc = []
        
        # Get full duration
        start_time = words[0].start_time
        end_time = words[-1].end_time
        
        # Create overlapping segments
        current_time = start_time
        step = segment_duration - overlap
        
        while current_time < end_time:
            segment_end = min(current_time + segment_duration, end_time)
            
            # Get words in this segment
            segment_words = [
                w for w in words
                if w.start_time < segment_end and w.end_time > current_time
            ]
            
            if segment_words:
                # Combine words into text
                segment_text = ' '.join([w.word for w in segment_words])
                
                # Analyze emotion
                emotion_result = self._analyze_segment(segment_text)
                
                ideal_arc.append(EmotionSegment(
                    emotion=emotion_result['emotion'],
                    intensity=emotion_result['intensity'],
                    valence=emotion_result['valence'],
                    arousal=emotion_result['arousal'],
                    start_time=current_time,
                    end_time=segment_end,
                    confidence=emotion_result['confidence'],
                    source="text"
                ))
            
            current_time += step
        
        return ideal_arc
    
    def _analyze_segment(self, text: str) -> Dict[str, Any]:
        """Analyze a single text segment and return standardized emotion info."""
        results = self.analyze_text(text)
        
        if not results:
            return {
                'emotion': EmotionCategory.NEUTRAL,
                'intensity': 0.3,
                'valence': 0.0,
                'arousal': 0.3,
                'confidence': 0.5
            }
        
        # Get top emotion
        top_result = max(results, key=lambda x: x['score'])
        label = top_result['label'].lower()
        score = top_result['score']
        
        # Map to our emotion category
        emotion = EMOTION_LABEL_MAP.get(label, EmotionCategory.NEUTRAL)
        
        # Get valence-arousal values
        valence, arousal = EMOTION_VA_MAP.get(emotion, (0.0, 0.3))
        
        # Intensity based on confidence score
        intensity = min(1.0, score * 1.2)  # Slight boost
        
        return {
            'emotion': emotion,
            'intensity': intensity,
            'valence': valence,
            'arousal': arousal,
            'confidence': score
        }
    
    def analyze_line_by_line(
        self,
        transcript: str,
        word_segments: List[WordSegment]
    ) -> List[EmotionSegment]:
        """
        Analyze the transcript line by line (for poems/lyrics).
        
        This respects the natural structure of the piece, analyzing
        each line/sentence as its own emotional unit.
        
        Args:
            transcript: Full transcript text
            word_segments: Word-level timing information
            
        Returns:
            List of EmotionSegment, one per line
        """
        # Split into lines/sentences
        lines = self._split_into_lines(transcript)
        
        if not lines or not word_segments:
            return self.generate_ideal_arc(word_segments)
        
        ideal_arc = []
        word_idx = 0
        
        for line in lines:
            if not line.strip():
                continue
            
            # Find words that belong to this line
            line_words_text = line.lower().split()
            line_word_segments = []
            
            temp_idx = word_idx
            for word_text in line_words_text:
                # Find matching word in segments
                while temp_idx < len(word_segments):
                    segment_word = word_segments[temp_idx].word.lower()
                    # Fuzzy match (remove punctuation)
                    segment_clean = re.sub(r'[^\w]', '', segment_word)
                    word_clean = re.sub(r'[^\w]', '', word_text)
                    
                    if segment_clean == word_clean or segment_clean.startswith(word_clean):
                        line_word_segments.append(word_segments[temp_idx])
                        temp_idx += 1
                        break
                    temp_idx += 1
            
            if line_word_segments:
                word_idx = temp_idx
                
                # Analyze the line
                emotion_result = self._analyze_segment(line)
                
                ideal_arc.append(EmotionSegment(
                    emotion=emotion_result['emotion'],
                    intensity=emotion_result['intensity'],
                    valence=emotion_result['valence'],
                    arousal=emotion_result['arousal'],
                    start_time=line_word_segments[0].start_time,
                    end_time=line_word_segments[-1].end_time,
                    confidence=emotion_result['confidence'],
                    source="text"
                ))
        
        return ideal_arc
    
    def _split_into_lines(self, text: str) -> List[str]:
        """Split text into lines, respecting both newlines and sentence boundaries."""
        # First split by newlines
        lines = text.split('\n')
        
        # Then split long lines by sentence boundaries
        result = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # If line is long, try to split by sentence
            if len(line) > 100:
                sentences = re.split(r'(?<=[.!?])\s+', line)
                result.extend([s.strip() for s in sentences if s.strip()])
            else:
                result.append(line)
        
        return result


def predict_ideal_emotions(
    transcript: str,
    word_segments: List[WordSegment],
    line_based: bool = True
) -> List[EmotionSegment]:
    """
    Convenience function to predict ideal emotional arc.
    
    Args:
        transcript: Full transcript text
        word_segments: Word-level timing from transcription
        line_based: If True, analyze line-by-line (better for poetry)
        
    Returns:
        List of EmotionSegment representing ideal emotional arc
    """
    analyzer = TextEmotionAnalyzer()
    
    if line_based:
        return analyzer.analyze_line_by_line(transcript, word_segments)
    else:
        return analyzer.generate_ideal_arc(word_segments)
