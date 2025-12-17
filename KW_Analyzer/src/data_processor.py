"""Data processing pipeline to combine Google Sheets and web analysis."""
import pandas as pd
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import func

from src.database import Database, GoogleSheetsData, WebContent, AnalysisResult
from src.google_sheets import GoogleSheetsReader
from src.web_scraper import WebScraper
from src.apify_integration import ApifyScraper
from src.nlp_analyzer import NLPAnalyzer

logger = logging.getLogger(__name__)


class DataProcessor:
    """Main data processing pipeline."""
    
    def __init__(self, db_path: Optional[str] = None, use_apify: bool = False):
        """
        Initialize data processor.
        
        Args:
            db_path: Path to database file
            use_apify: Whether to use Apify for scraping (default: BeautifulSoup)
        """
        self.db = Database(db_path)
        self.sheets_reader = GoogleSheetsReader()
        self.web_scraper = WebScraper() if not use_apify else ApifyScraper()
        self.nlp_analyzer = NLPAnalyzer()
        self.use_apify = use_apify
        logger.info("Data processor initialized")
    
    def process_sheet_data(self, spreadsheet_id: Optional[str] = None,
                          sheet_name: Optional[str] = None,
                          url_column: str = "url") -> pd.DataFrame:
        """
        Process Google Sheets data: scrape URLs and perform analysis.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of sheet to process
            url_column: Column name containing URLs
            
        Returns:
            DataFrame with combined results
        """
        session = self.db.get_session()
        
        try:
            # Read Google Sheets data
            df = self.sheets_reader.read_sheet(spreadsheet_id, sheet_name)
            logger.info(f"Read {len(df)} rows from Google Sheets")
            
            # Store sheet data in database
            sheet_records = []
            for idx, row in df.iterrows():
                sheet_record = GoogleSheetsData(
                    row_id=idx,
                    sheet_name=sheet_name or "Sheet1",
                    data=row.to_json()
                )
                session.add(sheet_record)
                sheet_records.append((idx, sheet_record))
            
            session.commit()
            logger.info(f"Stored {len(sheet_records)} rows in database")
            
            # Extract URLs
            urls_data = self.sheets_reader.get_sheet_urls(spreadsheet_id, url_column)
            
            # Process each URL
            results = []
            for url_info in urls_data:
                row_id = url_info['row_id']
                url = url_info['url']
                row_data = url_info['row_data']
                
                # Find corresponding sheet record
                sheet_record = next((r[1] for r in sheet_records if r[0] == row_id), None)
                
                # Scrape web content
                logger.info(f"Scraping URL: {url}")
                scraped_data = self.web_scraper.scrape_url(url)
                
                if scraped_data:
                    # Store web content
                    web_content = WebContent(
                        sheet_data_id=sheet_record.id if sheet_record else None,
                        url=url,
                        title=scraped_data.get('title', ''),
                        content=scraped_data.get('content', ''),
                        scraping_method='apify' if self.use_apify else 'beautifulsoup'
                    )
                    session.add(web_content)
                    session.flush()
                    
                    # Perform NLP analysis
                    analysis = self.nlp_analyzer.analyze_text(scraped_data.get('content', ''))
                    
                    # Store analysis results
                    analysis_result = AnalysisResult(
                        sheet_data_id=sheet_record.id if sheet_record else None,
                        web_content_id=web_content.id,
                        sentiment_label=analysis['sentiment']['label'],
                        sentiment_score=analysis['sentiment']['score'],
                        intent_label=analysis['intent']['label'],
                        intent_confidence=analysis['intent']['confidence'],
                        text_length=analysis['text_length'],
                        word_count=analysis['word_count']
                    )
                    session.add(analysis_result)
                    session.commit()
                    
                    # Combine results
                    result_row = {
                        **row_data,
                        'url': url,
                        'web_title': scraped_data.get('title', ''),
                        'web_content_length': len(scraped_data.get('content', '')),
                        'sentiment': analysis['sentiment']['label'],
                        'sentiment_score': analysis['sentiment']['score'],
                        'intent': analysis['intent']['label'],
                        'intent_confidence': analysis['intent']['confidence'],
                        'word_count': analysis['word_count']
                    }
                    results.append(result_row)
                else:
                    logger.warning(f"Failed to scrape URL: {url}")
            
            return pd.DataFrame(results)
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error processing sheet data: {e}")
            raise
        finally:
            session.close()
    
    def get_analysis_summary(self) -> Dict:
        """
        Get summary statistics from database.
        
        Returns:
            Dictionary with summary statistics
        """
        session = self.db.get_session()
        
        try:
            # Count records
            total_sheets = session.query(GoogleSheetsData).count()
            total_web_content = session.query(WebContent).count()
            total_analyses = session.query(AnalysisResult).count()
            
            # Sentiment distribution
            sentiment_counts = {}
            for result in session.query(AnalysisResult.sentiment_label).all():
                label = result[0]
                sentiment_counts[label] = sentiment_counts.get(label, 0) + 1
            
            # Intent distribution
            intent_counts = {}
            for result in session.query(AnalysisResult.intent_label).all():
                label = result[0]
                intent_counts[label] = intent_counts.get(label, 0) + 1
            
            # Average scores
            avg_sentiment = session.query(
                func.avg(AnalysisResult.sentiment_score)
            ).scalar() or 0
            
            avg_intent_confidence = session.query(
                func.avg(AnalysisResult.intent_confidence)
            ).scalar() or 0
            
            return {
                'total_sheets_records': total_sheets,
                'total_web_content': total_web_content,
                'total_analyses': total_analyses,
                'sentiment_distribution': sentiment_counts,
                'intent_distribution': intent_counts,
                'average_sentiment_score': float(avg_sentiment),
                'average_intent_confidence': float(avg_intent_confidence)
            }
            
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return {}
        finally:
            session.close()
    
    def get_all_results(self) -> pd.DataFrame:
        """
        Get all analysis results as DataFrame.
        
        Returns:
            DataFrame with all results
        """
        session = self.db.get_session()
        
        try:
            results = session.query(
                AnalysisResult,
                GoogleSheetsData,
                WebContent
            ).join(
                GoogleSheetsData, AnalysisResult.sheet_data_id == GoogleSheetsData.id, isouter=True
            ).join(
                WebContent, AnalysisResult.web_content_id == WebContent.id, isouter=True
            ).all()
            
            data = []
            for analysis, sheet_data, web_content in results:
                row = {
                    'analysis_id': analysis.id,
                    'sentiment_label': analysis.sentiment_label,
                    'sentiment_score': analysis.sentiment_score,
                    'intent_label': analysis.intent_label,
                    'intent_confidence': analysis.intent_confidence,
                    'text_length': analysis.text_length,
                    'word_count': analysis.word_count,
                    'analyzed_at': analysis.analyzed_at
                }
                
                if web_content:
                    row['url'] = web_content.url
                    row['web_title'] = web_content.title
                
                if sheet_data:
                    import json
                    try:
                        sheet_row_data = json.loads(sheet_data.data)
                        row.update(sheet_row_data)
                    except:
                        pass
                
                data.append(row)
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error getting results: {e}")
            return pd.DataFrame()
        finally:
            session.close()

