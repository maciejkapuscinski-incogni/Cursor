"""Advanced keyword analysis module for search terms, conversions, and landing page alignment."""
import pandas as pd
import logging
from typing import List, Dict, Optional
import re

from src.nlp_analyzer import NLPAnalyzer
from src.openai_nlp_analyzer import OpenAINLPAnalyzer
from src.web_scraper import WebScraper
from src.apify_integration import ApifyScraper
from src.config import Config

logger = logging.getLogger(__name__)


class KeywordAnalyzer:
    """Advanced keyword and landing page analysis."""
    
    def __init__(self, use_apify: bool = False, use_openai: Optional[bool] = None):
        """
        Initialize keyword analyzer.
        
        Args:
            use_apify: Whether to use Apify for scraping
            use_openai: Whether to use OpenAI for NLP (defaults to config, falls back to local models)
        """
        # Determine which NLP analyzer to use
        if use_openai is None:
            use_openai = Config.USE_OPENAI_NLP
        
        logger.info(f"OpenAI NLP requested: {use_openai}, Config.USE_OPENAI_NLP: {Config.USE_OPENAI_NLP}, Config.OPENAI_API_KEY set: {bool(Config.OPENAI_API_KEY)}")
        
        if use_openai:
            try:
                self.nlp_analyzer = OpenAINLPAnalyzer()
                logger.info(f"✅ Successfully initialized OpenAI NLP analyzer with model: {Config.OPENAI_MODEL}")
                self.using_openai = True
            except Exception as e:
                logger.warning(f"❌ Failed to initialize OpenAI analyzer: {e}. Falling back to local models.")
                self.nlp_analyzer = NLPAnalyzer()
                self.using_openai = False
        else:
            self.nlp_analyzer = NLPAnalyzer()
            self.using_openai = False
            logger.info("Using local models for NLP analysis")
        
        self.web_scraper = WebScraper() if not use_apify else ApifyScraper()
        self.use_apify = use_apify
        logger.info("Keyword analyzer initialized")
    
    def analyze_keyword(self, keyword: str) -> Dict:
        """
        Analyze a single keyword for sentiment and intent.
        
        Args:
            keyword: Search term/keyword to analyze
            
        Returns:
            Dictionary with sentiment and intent analysis
        """
        analysis = self.nlp_analyzer.analyze_text(keyword)
        
        return {
            'keyword': keyword,
            'sentiment': analysis['sentiment']['label'],
            'sentiment_score': analysis['sentiment']['score'],
            'intent': analysis['intent']['label'],
            'intent_confidence': analysis['intent']['confidence']
        }
    
    def analyze_keywords(self, keywords: List[str]) -> pd.DataFrame:
        """
        Analyze multiple keywords.
        
        Args:
            keywords: List of keywords to analyze
            
        Returns:
            DataFrame with analysis results
        """
        results = []
        for keyword in keywords:
            if keyword and pd.notna(keyword) and str(keyword).strip():
                result = self.analyze_keyword(str(keyword).strip())
                results.append(result)
        
        return pd.DataFrame(results)
    
    def calculate_content_alignment(self, keyword_text: str, page_content: str, page_intent: Optional[str] = None) -> Dict:
        """
        Calculate how well page content aligns with keyword intent.
        
        Args:
            keyword_text: The search term/keyword
            page_content: Content scraped from the landing page
            page_intent: Optional pre-analyzed page intent (to avoid re-analyzing)
            
        Returns:
            Dictionary with alignment metrics and analysis
        """
        # Analyze keyword (sentiment and intent)
        keyword_analysis = self.nlp_analyzer.analyze_text(keyword_text)
        
        # Analyze page content for intent only (if not provided)
        if page_intent is None:
            page_analysis = self.nlp_analyzer.analyze_text(page_content)
            page_intent = page_analysis['intent']['label']
        else:
            page_analysis = None  # We don't need full analysis if intent is provided
        
        # Calculate alignment scores
        intent_match = 1.0 if keyword_analysis['intent']['label'] == page_intent else 0.0
        
        # Keyword presence in content (case-insensitive)
        keyword_lower = keyword_text.lower()
        content_lower = page_content.lower()
        keyword_presence = 1.0 if keyword_lower in content_lower else 0.0
        
        # Calculate keyword density
        words = content_lower.split()
        keyword_words = keyword_lower.split()
        keyword_count = sum(1 for word in words if word in keyword_words)
        keyword_density = keyword_count / len(words) if words else 0.0
        
        # Overall alignment score (weighted average - removed sentiment alignment)
        alignment_score = (
            intent_match * 0.5 +
            keyword_presence * 0.3 +
            min(keyword_density * 10, 1.0) * 0.2  # Cap density contribution
        )
        
        return {
            'keyword_intent': keyword_analysis['intent']['label'],
            'page_intent': page_intent,
            'intent_match': intent_match,
            'keyword_sentiment': keyword_analysis['sentiment']['label'],
            'keyword_presence': keyword_presence,
            'keyword_density': keyword_density,
            'alignment_score': alignment_score,
            'keyword_analysis': keyword_analysis
        }
    
    def generate_recommendation(self, alignment_data: Dict, conversion_data: Optional[Dict] = None) -> Dict:
        """
        Generate recommendation based on alignment and conversion data.
        
        Args:
            alignment_data: Results from calculate_content_alignment
            conversion_data: Optional dict with conversion metrics (e.g., {'conversions': 10, 'clicks': 100})
            
        Returns:
            Dictionary with recommendation and reasoning
        """
        alignment_score = alignment_data['alignment_score']
        intent_match = alignment_data['intent_match']
        keyword_presence = alignment_data['keyword_presence']
        
        # Determine recommendation
        if alignment_score >= 0.7 and intent_match == 1.0:
            recommendation = "GOOD_LANDING_PAGE"
            action = "Keep and optimize"
            reasoning = "Strong alignment between keyword intent and page content. The landing page effectively matches user search intent."
        elif alignment_score >= 0.5:
            recommendation = "NEEDS_OPTIMIZATION"
            action = "Optimize website content"
            reasoning = f"Moderate alignment (score: {alignment_score:.2f}). Consider better matching keyword intent ({alignment_data['keyword_intent']}) and ensuring keyword appears in content."
        else:
            recommendation = "POOR_ALIGNMENT"
            action = "Exclude from campaign or create new landing page"
            reasoning = f"Poor alignment (score: {alignment_score:.2f}). Keyword intent ({alignment_data['keyword_intent']}) doesn't match page intent ({alignment_data['page_intent']})."
        
        # Factor in conversion data if available
        if conversion_data:
            conversions = conversion_data.get('conversions', 0)
            clicks = conversion_data.get('clicks', 0)
            conversion_rate = conversions / clicks if clicks > 0 else 0
            
            if recommendation == "GOOD_LANDING_PAGE" and conversion_rate < 0.02:
                recommendation = "NEEDS_OPTIMIZATION"
                action = "Optimize for conversions"
                reasoning += f" Despite good alignment, conversion rate is low ({conversion_rate:.2%}). Focus on conversion optimization."
            elif recommendation in ["NEEDS_OPTIMIZATION", "POOR_ALIGNMENT"] and conversion_rate > 0.05:
                # If conversions are good despite poor alignment, might be brand/awareness
                reasoning += f" However, conversion rate is strong ({conversion_rate:.2%}), suggesting the keyword may work despite alignment issues."
        
        return {
            'recommendation': recommendation,
            'action': action,
            'reasoning': reasoning,
            'alignment_score': alignment_score,
            'priority': 'HIGH' if alignment_score < 0.5 else 'MEDIUM' if alignment_score < 0.7 else 'LOW'
        }
    
    def analyze_keyword_landing_page(
        self,
        keyword: str,
        url: str,
        conversion_data: Optional[Dict] = None
    ) -> Dict:
        """
        Complete analysis: keyword -> landing page alignment -> recommendation.
        
        Args:
            keyword: Search term/keyword
            url: Landing page URL
            conversion_data: Optional conversion metrics
            
        Returns:
            Complete analysis dictionary
        """
        # Scrape landing page
        logger.info(f"Analyzing keyword '{keyword}' with landing page: {url}")
        scraped_data = self.web_scraper.scrape_url(url)
        
        if not scraped_data:
            return {
                'keyword': keyword,
                'url': url,
                'error': 'Failed to scrape landing page',
                'recommendation': 'ERROR',
                'action': 'Check URL accessibility'
            }
        
        # Calculate alignment
        alignment = self.calculate_content_alignment(keyword, scraped_data.get('content', ''))
        
        # Generate recommendation
        recommendation = self.generate_recommendation(alignment, conversion_data)
        
        # Combine results
        result = {
            'keyword': keyword,
            'url': url,
            'page_title': scraped_data.get('title', ''),
            **alignment,
            **recommendation
        }
        
        return result
    
    def batch_analyze_keywords_landing_pages(
        self,
        data: pd.DataFrame,
        keyword_column: str = 'keyword',
        url_column: str = 'url',
        conversion_columns: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Analyze multiple keyword-landing page pairs from a DataFrame.
        Optimized to scrape each unique URL only once.
        
        Args:
            data: DataFrame with keywords and URLs
            keyword_column: Column name containing keywords
            url_column: Column name containing URLs
            conversion_columns: Optional dict mapping {'conversions': 'col_name', 'clicks': 'col_name'}
            
        Returns:
            DataFrame with complete analysis results
        """
        # Step 1: Get unique URLs and scrape them once
        unique_urls = data[url_column].dropna().unique()
        url_content_cache = {}
        url_analysis_cache = {}
        
        logger.info(f"Scraping {len(unique_urls)} unique URLs...")
        url_texts_for_batch = []
        url_mapping = []
        
        for url in unique_urls:
            if url and str(url).strip():
                url_str = str(url).strip()
                logger.info(f"Scraping URL: {url_str}")
                scraped_data = self.web_scraper.scrape_url(url_str)
                if scraped_data:
                    content = scraped_data.get('content', '')
                    url_content_cache[url_str] = {
                        'content': content,
                        'title': scraped_data.get('title', '')
                    }
                    url_texts_for_batch.append(content)
                    url_mapping.append(url_str)
        
        logger.info(f"Successfully scraped {len(url_content_cache)} URLs")
        
        # Batch analyze all URL contents at once if using OpenAI
        if hasattr(self, 'using_openai') and self.using_openai and url_texts_for_batch:
            try:
                logger.info(f"🔄 Batch analyzing {len(url_texts_for_batch)} URL contents with OpenAI API...")
                url_analyses = self.nlp_analyzer.analyze_batch(url_texts_for_batch)
                
                # Cache the analyses
                for url_str, analysis in zip(url_mapping, url_analyses):
                    url_analysis_cache[url_str] = {
                        'intent': analysis['intent']['label'],
                        'intent_confidence': analysis['intent']['confidence'],
                        'word_count': analysis['word_count'],
                        'text_length': analysis['text_length'],
                        'full_analysis': analysis
                    }
                logger.info("Completed batch analysis of URL contents")
            except Exception as e:
                logger.warning(f"Batch URL analysis failed: {e}. Analyzing individually...")
                # Fall back to individual analysis
                for url_str in url_mapping:
                    if url_str in url_content_cache:
                        content = url_content_cache[url_str]['content']
                        page_analysis = self.nlp_analyzer.analyze_text(content)
                        url_analysis_cache[url_str] = {
                            'intent': page_analysis['intent']['label'],
                            'intent_confidence': page_analysis['intent']['confidence'],
                            'word_count': page_analysis['word_count'],
                            'text_length': page_analysis['text_length'],
                            'full_analysis': page_analysis
                        }
        else:
            # Individual analysis for non-OpenAI or fallback
            for url_str in url_mapping:
                if url_str in url_content_cache:
                    content = url_content_cache[url_str]['content']
                    page_analysis = self.nlp_analyzer.analyze_text(content)
                    url_analysis_cache[url_str] = {
                        'intent': page_analysis['intent']['label'],
                        'intent_confidence': page_analysis['intent']['confidence'],
                        'word_count': page_analysis['word_count'],
                        'text_length': page_analysis['text_length'],
                        'full_analysis': page_analysis
                    }
        
        # Step 2: Batch analyze all keyword-URL pairs if using OpenAI
        results = []
        logger.info(f"Analyzing {len(data)} keyword-URL pairs...")
        
        # Prepare batch data for OpenAI if available
        if hasattr(self, 'using_openai') and self.using_openai and hasattr(self.nlp_analyzer, 'analyze_batch_combined'):
            try:
                # Prepare all keyword-text pairs
                batch_pairs = []
                row_indices = []
                
                for idx, row in data.iterrows():
                    keyword = row.get(keyword_column, '')
                    url = row.get(url_column, '')
                    
                    if not keyword or not url:
                        continue
                    
                    url_str = str(url).strip()
                    if url_str not in url_content_cache:
                        continue
                    
                    page_content = url_content_cache[url_str]['content']
                    batch_pairs.append({
                        'keyword': str(keyword).strip(),
                        'text': page_content
                    })
                    row_indices.append((idx, row, url_str))
                
                if batch_pairs:
                    logger.info(f"🔄 Batch processing {len(batch_pairs)} keyword-URL pairs with OpenAI API...")
                    batch_results = self.nlp_analyzer.analyze_batch_combined(batch_pairs)
                    
                    # Process batch results
                    for batch_idx, (idx, row, url_str) in enumerate(row_indices):
                        if batch_idx >= len(batch_results):
                            continue
                        
                        batch_result = batch_results[batch_idx]
                        keyword = str(row.get(keyword_column, '')).strip()
                        cached_content = url_content_cache[url_str]
                        page_content = cached_content['content']
                        page_title = cached_content['title']
                        
                        # Extract conversion data if available
                        conversion_data = None
                        if conversion_columns:
                            conversion_data = {
                                'conversions': row.get(conversion_columns.get('conversions'), 0),
                                'clicks': row.get(conversion_columns.get('clicks'), 0)
                            }
                        
                        # Use batch results
                        keyword_intent = batch_result['intent']['label']
                        keyword_sentiment = batch_result['sentiment']['label']
                        page_intent = batch_result.get('text_intent', 'informational')
                        intent_match = 1.0 if batch_result.get('intent_match', False) else 0.0
                        
                        # Calculate other alignment metrics
                        keyword_lower = keyword.lower()
                        content_lower = page_content.lower()
                        keyword_presence = 1.0 if keyword_lower in content_lower else 0.0
                        
                        words = content_lower.split()
                        keyword_words = keyword_lower.split()
                        keyword_count = sum(1 for word in words if word in keyword_words)
                        keyword_density = keyword_count / len(words) if words else 0.0
                        
                        alignment_score = (
                            intent_match * 0.5 +
                            keyword_presence * 0.3 +
                            min(keyword_density * 10, 1.0) * 0.2
                        )
                        
                        alignment = {
                            'keyword_intent': keyword_intent,
                            'page_intent': page_intent,
                            'intent_match': intent_match,
                            'keyword_sentiment': keyword_sentiment,
                            'keyword_presence': keyword_presence,
                            'keyword_density': keyword_density,
                            'alignment_score': alignment_score
                        }
                        
                        recommendation = self.generate_recommendation(alignment, conversion_data)
                        
                        content_preview = page_content[:500] + "..." if len(page_content) > 500 else page_content
                        
                        analysis = {
                            'keyword': keyword,
                            'url': url_str,
                            'page_title': page_title,
                            'scraped_content': page_content,
                            'scraped_content_preview': content_preview,
                            'keyword_intent': keyword_intent,
                            'keyword_sentiment': keyword_sentiment,
                            'keyword_sentiment_score': batch_result['sentiment']['score'],
                            'keyword_intent_confidence': batch_result['intent']['confidence'],
                            'landing_page_intent': page_intent,
                            'landing_page_intent_confidence': batch_result.get('text_intent_confidence', 0.5),
                            'landing_page_word_count': batch_result['word_count'],
                            'landing_page_text_length': batch_result['text_length'],
                            'page_intent': page_intent,
                            'intent_match': intent_match,
                            'keyword_presence': keyword_presence,
                            'keyword_density': keyword_density,
                            'alignment_score': alignment_score,
                            **recommendation
                        }
                        
                        analysis.update({col: row[col] for col in data.columns if col not in [keyword_column, url_column]})
                        results.append(analysis)
                    
                    logger.info(f"Completed batch analysis for {len(results)} keywords")
                    return pd.DataFrame(results)
                    
            except Exception as e:
                logger.warning(f"Batch processing failed: {e}. Falling back to individual analysis.")
                # Fall back to individual processing below
        
        # Fallback: Individual analysis (original method)
        for idx, row in data.iterrows():
            keyword = row.get(keyword_column, '')
            url = row.get(url_column, '')
            
            if not keyword or not url:
                continue
            
            url_str = str(url).strip()
            
            # Get cached content
            if url_str not in url_content_cache:
                logger.warning(f"URL not found in cache: {url_str}")
                continue
            
            cached_content = url_content_cache[url_str]
            page_content = cached_content['content']
            page_title = cached_content['title']
            page_analysis_data = url_analysis_cache.get(url_str, {})
            page_intent = page_analysis_data.get('intent')
            
            # Extract conversion data if available
            conversion_data = None
            if conversion_columns:
                conversion_data = {
                    'conversions': row.get(conversion_columns.get('conversions'), 0),
                    'clicks': row.get(conversion_columns.get('clicks'), 0)
                }
            
            # Analyze keyword
            keyword_analysis = self.analyze_keyword(str(keyword).strip())
            
            # Calculate alignment (using cached page intent)
            alignment = self.calculate_content_alignment(
                str(keyword).strip(),
                page_content,
                page_intent=page_intent
            )
            
            # Generate recommendation
            recommendation = self.generate_recommendation(alignment, conversion_data)
            
            # Combine results with landing page analysis details
            # Note: alignment already contains keyword_intent and keyword_sentiment
            # Truncate content for preview (first 500 characters)
            content_preview = page_content[:500] + "..." if len(page_content) > 500 else page_content
            
            analysis = {
                'keyword': str(keyword).strip(),
                'url': url_str,
                'page_title': page_title,
                # Full scraped data
                'scraped_content': page_content,  # Full content
                'scraped_content_preview': content_preview,  # Truncated preview for quick viewing
                # Keyword analysis (from alignment dict, but add confidence scores from keyword_analysis)
                'keyword_intent': alignment['keyword_intent'],
                'keyword_sentiment': alignment['keyword_sentiment'],
                'keyword_sentiment_score': keyword_analysis['sentiment_score'],
                'keyword_intent_confidence': keyword_analysis['intent_confidence'],
                # Landing page analysis
                'landing_page_intent': page_analysis_data.get('intent', ''),
                'landing_page_intent_confidence': page_analysis_data.get('intent_confidence', 0),
                'landing_page_word_count': page_analysis_data.get('word_count', 0),
                'landing_page_text_length': page_analysis_data.get('text_length', 0),
                # Alignment metrics
                'page_intent': alignment['page_intent'],
                'intent_match': alignment['intent_match'],
                'keyword_presence': alignment['keyword_presence'],
                'keyword_density': alignment['keyword_density'],
                'alignment_score': alignment['alignment_score'],
                # Recommendations
                **recommendation
            }
            
            # Add original row data
            analysis.update({col: row[col] for col in data.columns if col not in [keyword_column, url_column]})
            
            results.append(analysis)
        
        logger.info(f"Completed analysis for {len(results)} keywords")
        return pd.DataFrame(results)

