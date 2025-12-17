"""NLP analysis module for sentiment and intent detection."""
import logging
from typing import Dict, List, Optional
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import re

logger = logging.getLogger(__name__)


class NLPAnalyzer:
    """NLP analyzer for sentiment and intent analysis."""
    
    def __init__(self, device: Optional[str] = None):
        """
        Initialize NLP analyzer.
        
        Args:
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.device = device
        logger.info(f"Initializing NLP analyzer on {device}")
        
        # Initialize sentiment analysis pipeline
        try:
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=0 if device == 'cuda' else -1,
                return_all_scores=True
            )
            logger.info("Sentiment analysis model loaded")
        except Exception as e:
            logger.warning(f"Failed to load sentiment model: {e}")
            self.sentiment_pipeline = None
        
        # Initialize intent classification (using a general model)
        # For intent, we'll use a zero-shot classification model
        try:
            self.intent_pipeline = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=0 if device == 'cuda' else -1
            )
            logger.info("Intent classification model loaded")
        except Exception as e:
            logger.warning(f"Failed to load intent model: {e}")
            self.intent_pipeline = None
        
        # Intent categories
        self.intent_categories = [
            "informational",
            "commercial",
            "navigational",
            "transactional",
            "entertainment",
            "educational",
            "news",
            "review",
            "comparison",
            "support"
        ]
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for analysis.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove URLs
        text = re.sub(r'http\S+|www\.\S+', '', text)
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:\-]', '', text)
        
        return text.strip()
    
    def analyze_sentiment(self, text: str) -> Dict[str, any]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment label and score
        """
        if not self.sentiment_pipeline:
            return {
                'label': 'neutral',
                'score': 0.5,
                'error': 'Sentiment model not available'
            }
        
        if not text or len(text.strip()) == 0:
            return {
                'label': 'neutral',
                'score': 0.5,
                'error': 'Empty text'
            }
        
        try:
            # Truncate text if too long (model limit)
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            results = self.sentiment_pipeline(text)
            
            # Get the highest scoring sentiment
            if isinstance(results, list) and len(results) > 0:
                scores = results[0] if isinstance(results[0], list) else results
                best = max(scores, key=lambda x: x['score'])
                
                # Map labels to standard format
                label = best['label'].lower()
                if 'positive' in label or 'pos' in label:
                    label = 'positive'
                elif 'negative' in label or 'neg' in label:
                    label = 'negative'
                else:
                    label = 'neutral'
                
                return {
                    'label': label,
                    'score': best['score'],
                    'all_scores': scores
                }
            else:
                return {
                    'label': 'neutral',
                    'score': 0.5,
                    'error': 'Unexpected result format'
                }
                
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                'label': 'neutral',
                'score': 0.5,
                'error': str(e)
            }
    
    def analyze_intent(self, text: str, categories: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Analyze intent of text.
        
        Args:
            text: Text to analyze
            categories: List of intent categories (defaults to predefined)
            
        Returns:
            Dictionary with intent label and confidence
        """
        if not self.intent_pipeline:
            return {
                'label': 'informational',
                'confidence': 0.5,
                'error': 'Intent model not available'
            }
        
        if not text or len(text.strip()) == 0:
            return {
                'label': 'informational',
                'confidence': 0.5,
                'error': 'Empty text'
            }
        
        if categories is None:
            categories = self.intent_categories
        
        try:
            # Truncate text if too long
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            result = self.intent_pipeline(text, categories)
            
            if result and 'labels' in result and 'scores' in result:
                best_idx = 0
                best_score = result['scores'][0]
                
                return {
                    'label': result['labels'][best_idx],
                    'confidence': best_score,
                    'all_scores': dict(zip(result['labels'], result['scores']))
                }
            else:
                return {
                    'label': 'informational',
                    'confidence': 0.5,
                    'error': 'Unexpected result format'
                }
                
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            return {
                'label': 'informational',
                'confidence': 0.5,
                'error': str(e)
            }
    
    def analyze_text(self, text: str, intent_categories: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Perform complete analysis on text (sentiment + intent).
        
        Args:
            text: Text to analyze
            intent_categories: Optional list of intent categories
            
        Returns:
            Dictionary with all analysis results
        """
        cleaned_text = self.preprocess_text(text)
        
        sentiment_result = self.analyze_sentiment(cleaned_text)
        intent_result = self.analyze_intent(cleaned_text, intent_categories)
        
        # Calculate text statistics
        word_count = len(cleaned_text.split())
        text_length = len(cleaned_text)
        
        return {
            'sentiment': sentiment_result,
            'intent': intent_result,
            'text_length': text_length,
            'word_count': word_count,
            'cleaned_text': cleaned_text[:500]  # Store first 500 chars
        }
    
    def analyze_batch(self, texts: List[str], intent_categories: Optional[List[str]] = None) -> List[Dict[str, any]]:
        """
        Analyze multiple texts in batch.
        
        Args:
            texts: List of texts to analyze
            intent_categories: Optional list of intent categories
            
        Returns:
            List of analysis results
        """
        results = []
        for text in texts:
            result = self.analyze_text(text, intent_categories)
            results.append(result)
        return results

