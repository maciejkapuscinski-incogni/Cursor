"""OpenAI-based NLP analysis module for sentiment and intent detection."""
import logging
from typing import Dict, List, Optional
import re
from openai import OpenAI

from src.config import Config

logger = logging.getLogger(__name__)


class OpenAINLPAnalyzer:
    """OpenAI-based NLP analyzer for sentiment and intent analysis."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI NLP analyzer.
        
        Args:
            api_key: OpenAI API key (defaults to config)
            model: OpenAI model to use (defaults to config)
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model or Config.OPENAI_MODEL
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env file.")
        
        # Verify API key format
        if not self.api_key.startswith('sk-'):
            logger.warning(f"OpenAI API key doesn't start with 'sk-'. Key length: {len(self.api_key)}")
        
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"✅ Initialized OpenAI NLP analyzer with model: {self.model}, API key length: {len(self.api_key)}")
        
        # Test API connection with a simple call (optional, can be disabled for faster startup)
        # Uncomment to test on initialization
        # try:
        #     test_response = self.client.chat.completions.create(
        #         model=self.model,
        #         messages=[{"role": "user", "content": "test"}],
        #         max_tokens=5
        #     )
        #     logger.info("✅ OpenAI API connection test successful")
        # except Exception as e:
        #     logger.error(f"❌ OpenAI API connection test failed: {e}")
        #     raise
        
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
        Analyze sentiment of text using OpenAI.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment label and score
        """
        if not text or len(text.strip()) == 0:
            return {
                'label': 'neutral',
                'score': 0.5,
                'error': 'Empty text'
            }
        
        try:
            # Truncate text if too long (OpenAI has token limits)
            max_length = 8000  # Conservative limit for gpt-4o-mini
            if len(text) > max_length:
                text = text[:max_length]
            
            cleaned_text = self.preprocess_text(text)
            
            prompt = f"""Analyze the sentiment of the following text and respond with ONLY a JSON object in this exact format:
{{"sentiment": "positive", "negative", or "neutral", "confidence": 0.0-1.0}}

Text: {cleaned_text}"""
            
            logger.debug(f"Calling OpenAI API for sentiment analysis (text length: {len(cleaned_text)})")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a sentiment analysis expert. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )
            logger.debug(f"OpenAI API response received (usage: {response.usage})")
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            return {
                'label': result.get('sentiment', 'neutral').lower(),
                'score': float(result.get('confidence', 0.5)),
                'all_scores': None  # OpenAI doesn't provide all scores
            }
            
        except Exception as e:
            error_msg = str(e)
            # Check for specific error types
            if '429' in error_msg or 'quota' in error_msg.lower() or 'insufficient_quota' in error_msg.lower():
                logger.error(f"❌ OpenAI API quota exceeded. Please check your billing: {e}")
            elif '401' in error_msg or 'unauthorized' in error_msg.lower():
                logger.error(f"❌ OpenAI API key invalid or unauthorized: {e}")
            else:
                logger.error(f"❌ Error analyzing sentiment with OpenAI: {e}")
            return {
                'label': 'neutral',
                'score': 0.5,
                'error': error_msg
            }
    
    def analyze_intent(self, text: str, categories: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Analyze intent of text using OpenAI.
        
        Args:
            text: Text to analyze
            categories: List of intent categories (defaults to predefined)
            
        Returns:
            Dictionary with intent label and confidence
        """
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
            max_length = 8000
            if len(text) > max_length:
                text = text[:max_length]
            
            cleaned_text = self.preprocess_text(text)
            categories_str = ", ".join(categories)
            
            prompt = f"""Analyze the intent of the following text and classify it into one of these categories: {categories_str}

Respond with ONLY a JSON object in this exact format:
{{"intent": "category_name", "confidence": 0.0-1.0}}

Text: {cleaned_text}"""
            
            logger.debug(f"Calling OpenAI API for intent analysis (text length: {len(cleaned_text)})")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an intent classification expert. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            logger.debug(f"OpenAI API response received (usage: {response.usage})")
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            intent_label = result.get('intent', 'informational').lower()
            # Validate intent is in categories
            if intent_label not in [c.lower() for c in categories]:
                intent_label = 'informational'
            
            return {
                'label': intent_label,
                'confidence': float(result.get('confidence', 0.5)),
                'all_scores': None
            }
            
        except Exception as e:
            error_msg = str(e)
            # Check for specific error types
            if '429' in error_msg or 'quota' in error_msg.lower() or 'insufficient_quota' in error_msg.lower():
                logger.error(f"❌ OpenAI API quota exceeded. Please check your billing: {e}")
            elif '401' in error_msg or 'unauthorized' in error_msg.lower():
                logger.error(f"❌ OpenAI API key invalid or unauthorized: {e}")
            else:
                logger.error(f"❌ Error analyzing intent with OpenAI: {e}")
            return {
                'label': 'informational',
                'confidence': 0.5,
                'error': error_msg
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
        Analyze multiple texts in batch (parallel processing).
        
        Args:
            texts: List of texts to analyze
            intent_categories: Optional list of intent categories
            
        Returns:
            List of analysis results
        """
        import concurrent.futures
        import threading
        
        results = [None] * len(texts)
        
        def analyze_single(idx, text):
            try:
                results[idx] = self.analyze_text(text, intent_categories)
            except Exception as e:
                logger.error(f"Error analyzing text at index {idx}: {e}")
                results[idx] = {
                    'sentiment': {'label': 'neutral', 'score': 0.5, 'error': str(e)},
                    'intent': {'label': 'informational', 'confidence': 0.5, 'error': str(e)},
                    'text_length': len(text),
                    'word_count': len(text.split()),
                    'cleaned_text': text[:500]
                }
        
        # Process in parallel with thread pool (OpenAI API is I/O bound)
        max_workers = min(10, len(texts))  # Limit concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(analyze_single, idx, text) for idx, text in enumerate(texts)]
            concurrent.futures.wait(futures)
        
        return results
    
    def analyze_batch_combined(self, keyword_text_pairs: List[Dict[str, str]], intent_categories: Optional[List[str]] = None, batch_size: int = 20) -> List[Dict[str, any]]:
        """
        Analyze multiple keyword-text pairs in optimized batch requests.
        Processes in smaller batches to avoid token limits.
        
        Args:
            keyword_text_pairs: List of dicts with 'keyword' and 'text' keys
            intent_categories: Optional list of intent categories
            batch_size: Number of pairs to process per API call (default: 20)
            
        Returns:
            List of analysis results
        """
        if not keyword_text_pairs:
            return []
        
        # Process in batches to avoid token limits
        all_results = []
        for i in range(0, len(keyword_text_pairs), batch_size):
            batch = keyword_text_pairs[i:i + batch_size]
            batch_results = self._analyze_single_batch(batch, intent_categories)
            all_results.extend(batch_results)
        
        return all_results
    
    def _analyze_single_batch(self, keyword_text_pairs: List[Dict[str, str]], intent_categories: Optional[List[str]] = None) -> List[Dict[str, any]]:
        """
        Analyze a single batch of keyword-text pairs in one API call.
        
        Args:
            keyword_text_pairs: List of dicts with 'keyword' and 'text' keys (max ~20 pairs)
            intent_categories: Optional list of intent categories
            
        Returns:
            List of analysis results
        """
        if not keyword_text_pairs:
            return []
        
        try:
            # Prepare batch data
            batch_items = []
            for pair in keyword_text_pairs:
                keyword = pair.get('keyword', '')
                text = pair.get('text', '')
                cleaned_text = self.preprocess_text(text)
                # Truncate if needed
                if len(cleaned_text) > 4000:  # Leave room for prompt
                    cleaned_text = cleaned_text[:4000]
                batch_items.append({
                    'keyword': keyword,
                    'text': cleaned_text
                })
            
            if not batch_items:
                return []
            
            # Create batch prompt
            categories_str = ", ".join(intent_categories or self.intent_categories)
            
            batch_prompt = f"""Analyze the following keyword-text pairs. For each pair, determine:
1. Sentiment of the keyword (positive, negative, or neutral)
2. Intent of the keyword (from: {categories_str})
3. Intent of the text content (from: {categories_str})
4. Whether the keyword intent matches the text intent (true/false)

Respond with a JSON array where each object has this structure:
{{
  "keyword": "the keyword",
  "keyword_sentiment": "positive|negative|neutral",
  "keyword_sentiment_confidence": 0.0-1.0,
  "keyword_intent": "intent_category",
  "keyword_intent_confidence": 0.0-1.0,
  "text_intent": "intent_category",
  "text_intent_confidence": 0.0-1.0,
  "intent_match": true/false
}}

Keyword-Text Pairs:
"""
            
            for idx, item in enumerate(batch_items, 1):
                batch_prompt += f"\n{idx}. Keyword: {item['keyword']}\n   Text: {item['text'][:2000]}...\n"
            
            logger.info(f"Calling OpenAI API for batch analysis ({len(batch_items)} pairs)")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert NLP analyst. Always respond with valid JSON arrays only."},
                    {"role": "user", "content": batch_prompt}
                ],
                temperature=0.3,
                max_tokens=4000  # Enough for multiple results
            )
            logger.info(f"OpenAI API batch response received (usage: {response.usage}, prompt_tokens: {response.usage.prompt_tokens}, completion_tokens: {response.usage.completion_tokens})")
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            batch_results = json.loads(result_text)
            
            # Convert to standard format
            results = []
            for i, batch_result in enumerate(batch_results):
                keyword = batch_result.get('keyword', keyword_text_pairs[i].get('keyword', ''))
                text = keyword_text_pairs[i].get('text', '')
                
                results.append({
                    'sentiment': {
                        'label': batch_result.get('keyword_sentiment', 'neutral').lower(),
                        'score': float(batch_result.get('keyword_sentiment_confidence', 0.5))
                    },
                    'intent': {
                        'label': batch_result.get('keyword_intent', 'informational').lower(),
                        'confidence': float(batch_result.get('keyword_intent_confidence', 0.5))
                    },
                    'text_length': len(text),
                    'word_count': len(text.split()),
                    'cleaned_text': text[:500],
                    'text_intent': batch_result.get('text_intent', 'informational').lower(),
                    'text_intent_confidence': float(batch_result.get('text_intent_confidence', 0.5)),
                    'intent_match': batch_result.get('intent_match', False)
                })
            
            return results
            
        except Exception as e:
            error_msg = str(e)
            # Check for specific error types
            if '429' in error_msg or 'quota' in error_msg.lower() or 'insufficient_quota' in error_msg.lower():
                logger.error(f"❌ OpenAI API quota exceeded in batch analysis. Please check your billing: {e}")
            elif '401' in error_msg or 'unauthorized' in error_msg.lower():
                logger.error(f"❌ OpenAI API key invalid in batch analysis: {e}")
            else:
                logger.error(f"❌ Error in batch analysis: {e}. Falling back to individual analysis.")
            # Fallback to individual analysis
            results = []
            for pair in keyword_text_pairs:
                text = pair.get('text', '')
                result = self.analyze_text(text, intent_categories)
                results.append(result)
            return results

