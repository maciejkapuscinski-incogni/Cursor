"""Advanced data processor for keyword analysis with conversion data and landing page alignment."""
import pandas as pd
import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.database import Database
from src.google_sheets import GoogleSheetsReader
from src.keyword_analyzer import KeywordAnalyzer

logger = logging.getLogger(__name__)


class AdvancedDataProcessor:
    """Advanced processor for keyword analysis workflow."""
    
    def __init__(self, db_path: Optional[str] = None, use_apify: bool = False, use_openai: Optional[bool] = None):
        """
        Initialize advanced data processor.
        
        Args:
            db_path: Path to database file
            use_apify: Whether to use Apify for scraping
            use_openai: Whether to use OpenAI for NLP (defaults to config)
        """
        self.db = Database(db_path)
        self.sheets_reader = GoogleSheetsReader()
        self.keyword_analyzer = KeywordAnalyzer(use_apify=use_apify, use_openai=use_openai)
        self.use_apify = use_apify
        logger.info("Advanced data processor initialized")
    
    def get_initial_info(
        self,
        spreadsheet_id: Optional[str] = None,
        sheet_name: Optional[str] = None,
        keyword_column: str = 'keyword',
        url_column: str = 'url'
    ) -> Dict:
        """
        Get initial information about the spreadsheet before processing.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of sheet to process
            keyword_column: Column name containing keywords/search terms
            url_column: Column name containing landing page URLs
            
        Returns:
            Dictionary with initial info (keywords count, spreadsheet name, unique URLs count)
        """
        # Read Google Sheets data
        df = self.sheets_reader.read_sheet(spreadsheet_id, sheet_name)
        
        # Get spreadsheet name
        spreadsheet = self.sheets_reader.get_spreadsheet(spreadsheet_id)
        spreadsheet_name = spreadsheet.title
        
        # Get sheet name
        if sheet_name:
            actual_sheet_name = sheet_name
        else:
            actual_sheet_name = spreadsheet.sheet1.title
        
        # Count keywords
        keywords = df[keyword_column].dropna()
        keyword_count = len(keywords[keywords.astype(str).str.strip() != ''])
        
        # Count unique URLs
        urls = df[url_column].dropna()
        unique_urls = urls.unique()
        unique_url_count = len([u for u in unique_urls if str(u).strip()])
        
        return {
            'spreadsheet_name': spreadsheet_name,
            'sheet_name': actual_sheet_name,
            'keyword_count': keyword_count,
            'unique_url_count': unique_url_count,
            'total_rows': len(df)
        }
    
    def process_keyword_analysis(
        self,
        spreadsheet_id: Optional[str] = None,
        sheet_name: Optional[str] = None,
        keyword_column: str = 'keyword',
        url_column: str = 'url',
        conversion_columns: Optional[Dict[str, str]] = None,
        results_sheet_name: Optional[str] = None,
        force_rerun: bool = False
    ) -> pd.DataFrame:
        """
        Complete workflow: Analyze keywords -> Compare with conversions -> Analyze landing pages.
        Skips previously analyzed pairs unless force_rerun is True.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of sheet to process
            keyword_column: Column name containing keywords/search terms
            url_column: Column name containing landing page URLs
            conversion_columns: Optional dict mapping conversion metrics
                Example: {'conversions': 'conversions', 'clicks': 'clicks', 'cost': 'cost'}
            results_sheet_name: Name of sheet to save results to (default: 'Analysis_Results')
            force_rerun: If True, re-analyze all pairs even if already analyzed
            
        Returns:
            DataFrame with complete analysis including recommendations
        """
        # Read Google Sheets data
        df = self.sheets_reader.read_sheet(spreadsheet_id, sheet_name)
        logger.info(f"Read {len(df)} rows from Google Sheets")
        
        # Validate required columns
        if keyword_column not in df.columns:
            raise ValueError(f"Column '{keyword_column}' not found in sheet. Available columns: {list(df.columns)}")
        if url_column not in df.columns:
            raise ValueError(f"Column '{url_column}' not found in sheet. Available columns: {list(df.columns)}")
        
        # Check for existing results if not forcing rerun
        existing_results_df = pd.DataFrame()
        analyzed_pairs = set()
        
        if results_sheet_name and not force_rerun:
            # Results sheet always uses standardized column names "keyword" and "url"
            existing_results_df = self.sheets_reader.read_existing_results(
                spreadsheet_id=spreadsheet_id,
                sheet_name=results_sheet_name,
                keyword_column="keyword",  # Results sheet uses standardized names
                url_column="url"  # Results sheet uses standardized names
            )
            analyzed_pairs = self.sheets_reader.get_analyzed_pairs(
                spreadsheet_id=spreadsheet_id,
                sheet_name=results_sheet_name,
                keyword_column="keyword",  # Results sheet uses standardized names
                url_column="url"  # Results sheet uses standardized names
            )
            logger.info(f"Found {len(analyzed_pairs)} previously analyzed pairs")
        
        # Filter out already analyzed pairs
        if analyzed_pairs and not force_rerun:
            df_to_analyze = df.copy()
            df_to_analyze['_pair_key'] = df_to_analyze.apply(
                lambda row: (
                    str(row[keyword_column]).strip().lower() if pd.notna(row[keyword_column]) else "",
                    str(row[url_column]).strip().lower() if pd.notna(row[url_column]) else ""
                ),
                axis=1
            )
            df_to_analyze = df_to_analyze[~df_to_analyze['_pair_key'].isin(analyzed_pairs)]
            df_to_analyze = df_to_analyze.drop(columns=['_pair_key'])
            logger.info(f"Filtered to {len(df_to_analyze)} new pairs to analyze (skipped {len(df) - len(df_to_analyze)} existing)")
        else:
            df_to_analyze = df
            if force_rerun:
                logger.info("Force rerun enabled - analyzing all pairs")
        
        # Perform batch analysis on new pairs
        new_results_df = pd.DataFrame()
        if len(df_to_analyze) > 0:
            logger.info("Starting keyword-landing page analysis...")
            new_results_df = self.keyword_analyzer.batch_analyze_keywords_landing_pages(
                df_to_analyze,
                keyword_column=keyword_column,
                url_column=url_column,
                conversion_columns=conversion_columns
            )
            logger.info(f"Completed analysis for {len(new_results_df)} new keywords")
        else:
            logger.info("No new pairs to analyze")
        
        # Combine with existing results
        if not existing_results_df.empty:
            # Merge new results with existing
            # Results DataFrames use standardized column names "keyword" and "url"
            # Use keyword+url as unique identifier
            all_results = pd.concat([existing_results_df, new_results_df], ignore_index=True)
            # Remove duplicates based on keyword+url (keep latest)
            # Use standardized column names that exist in results
            merge_columns = []
            if 'keyword' in all_results.columns:
                merge_columns.append('keyword')
            elif keyword_column in all_results.columns:
                merge_columns.append(keyword_column)
            
            if 'url' in all_results.columns:
                merge_columns.append('url')
            elif url_column in all_results.columns:
                merge_columns.append(url_column)
            
            if len(merge_columns) == 2:
                all_results = all_results.drop_duplicates(
                    subset=merge_columns,
                    keep='last'
                )
            else:
                logger.warning(f"Could not find merge columns. Using all results without deduplication.")
            logger.info(f"Combined results: {len(existing_results_df)} existing + {len(new_results_df)} new = {len(all_results)} total")
        else:
            all_results = new_results_df
        
        # Save results back to sheet if results_sheet_name is provided
        if results_sheet_name and len(all_results) > 0:
            try:
                self.sheets_reader.write_dataframe_to_sheet(
                    all_results,
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=results_sheet_name,
                    clear_existing=force_rerun
                )
                logger.info(f"Saved {len(all_results)} results to sheet '{results_sheet_name}'")
            except Exception as e:
                logger.warning(f"Failed to save results to sheet: {e}")
        
        return all_results
    
    def get_analysis_summary(self, results_df: pd.DataFrame) -> Dict:
        """
        Get summary statistics from analysis results.
        
        Args:
            results_df: DataFrame from process_keyword_analysis
            
        Returns:
            Dictionary with summary statistics
        """
        if results_df.empty:
            return {}
        
        summary = {
            'total_keywords': len(results_df),
            'good_landing_pages': len(results_df[results_df['recommendation'] == 'GOOD_LANDING_PAGE']),
            'needs_optimization': len(results_df[results_df['recommendation'] == 'NEEDS_OPTIMIZATION']),
            'poor_alignment': len(results_df[results_df['recommendation'] == 'POOR_ALIGNMENT']),
            'average_alignment_score': results_df['alignment_score'].mean() if 'alignment_score' in results_df.columns else 0,
            'intent_match_rate': results_df['intent_match'].mean() if 'intent_match' in results_df.columns else 0,
        }
        
        # Conversion statistics if available
        if 'conversions' in results_df.columns and 'clicks' in results_df.columns:
            total_conversions = results_df['conversions'].sum()
            total_clicks = results_df['clicks'].sum()
            summary['total_conversions'] = total_conversions
            summary['total_clicks'] = total_clicks
            summary['overall_conversion_rate'] = total_conversions / total_clicks if total_clicks > 0 else 0
        
        # Recommendation distribution
        if 'recommendation' in results_df.columns:
            summary['recommendation_distribution'] = results_df['recommendation'].value_counts().to_dict()
        
        return summary
    
    def get_optimization_recommendations(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get prioritized list of keywords that need optimization.
        
        Args:
            results_df: DataFrame from process_keyword_analysis
            
        Returns:
            DataFrame sorted by priority with optimization recommendations
        """
        if results_df.empty:
            return pd.DataFrame()
        
        # Filter keywords that need attention
        needs_attention = results_df[
            results_df['recommendation'].isin(['NEEDS_OPTIMIZATION', 'POOR_ALIGNMENT'])
        ].copy()
        
        if needs_attention.empty:
            return pd.DataFrame()
        
        # Sort by priority and alignment score
        needs_attention['priority_score'] = needs_attention.apply(
            lambda row: (
                3 if row['recommendation'] == 'POOR_ALIGNMENT' else 2,
                1 - row['alignment_score']  # Lower alignment = higher priority
            ),
            axis=1
        )
        
        # Add conversion impact if available
        if 'conversions' in needs_attention.columns and 'clicks' in needs_attention.columns:
            needs_attention['conversion_rate'] = (
                needs_attention['conversions'] / needs_attention['clicks']
            ).fillna(0)
            needs_attention = needs_attention.sort_values(
                by=['priority_score', 'conversion_rate'],
                ascending=[False, False]
            )
        else:
            needs_attention = needs_attention.sort_values(
                by=['priority_score', 'alignment_score'],
                ascending=[False, True]
            )
        
        return needs_attention[[
            'keyword', 'url', 'recommendation', 'action', 'reasoning',
            'alignment_score', 'intent_match', 'keyword_presence', 'priority'
        ] + [col for col in needs_attention.columns if col not in [
            'keyword', 'url', 'recommendation', 'action', 'reasoning',
            'alignment_score', 'intent_match', 'keyword_presence', 'priority', 'priority_score'
        ]]]

