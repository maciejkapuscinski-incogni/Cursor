"""Google Sheets integration module."""
import gspread
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials
import pandas as pd
import logging
from typing import List, Dict, Optional

from src.config import Config

logger = logging.getLogger(__name__)


class GoogleSheetsReader:
    """Read data from Google Sheets."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Sheets reader.
        
        Args:
            credentials_path: Path to Google service account credentials JSON file
        """
        if credentials_path is None:
            credentials_path = Config.GOOGLE_SHEETS_CREDENTIALS_PATH
        
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_file(
                credentials_path,
                scopes=scopes
            )
            self.client = gspread.authorize(creds)
            logger.info("Google Sheets client initialized successfully")
        except FileNotFoundError:
            logger.error(f"Credentials file not found: {credentials_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            raise
    
    def get_spreadsheet(self, spreadsheet_id: Optional[str] = None):
        """
        Get spreadsheet by ID.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            
        Returns:
            Spreadsheet object
        """
        if spreadsheet_id is None:
            spreadsheet_id = Config.GOOGLE_SHEETS_SPREADSHEET_ID
        
        if not spreadsheet_id:
            raise ValueError("Spreadsheet ID is required")
        
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            logger.info(f"Opened spreadsheet: {spreadsheet.title}")
            return spreadsheet
        except Exception as e:
            logger.error(f"Failed to open spreadsheet: {e}")
            raise
    
    def read_sheet(self, spreadsheet_id: Optional[str] = None, 
                   sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        Read data from a specific sheet.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the sheet to read (defaults to first sheet)
            
        Returns:
            DataFrame with sheet data
        """
        spreadsheet = self.get_spreadsheet(spreadsheet_id)
        
        if sheet_name:
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
            except Exception as e:
                logger.error(f"Sheet '{sheet_name}' not found: {e}")
                raise
        else:
            worksheet = spreadsheet.sheet1
        
        try:
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            logger.info(f"Read {len(df)} rows from sheet '{worksheet.title}'")
            return df
        except Exception as e:
            logger.error(f"Failed to read sheet data: {e}")
            raise
    
    def read_all_sheets(self, spreadsheet_id: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Read all sheets from a spreadsheet.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            
        Returns:
            Dictionary mapping sheet names to DataFrames
        """
        spreadsheet = self.get_spreadsheet(spreadsheet_id)
        sheets_data = {}
        
        for sheet in spreadsheet.worksheets():
            try:
                data = sheet.get_all_records()
                df = pd.DataFrame(data)
                sheets_data[sheet.title] = df
                logger.info(f"Read {len(df)} rows from sheet '{sheet.title}'")
            except Exception as e:
                logger.warning(f"Failed to read sheet '{sheet.title}': {e}")
                continue
        
        return sheets_data
    
    def get_sheet_urls(self, spreadsheet_id: Optional[str] = None,
                      url_column: str = "url") -> List[Dict]:
        """
        Extract URLs from a sheet column.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            url_column: Name of the column containing URLs
            
        Returns:
            List of dictionaries with row data and URLs
        """
        df = self.read_sheet(spreadsheet_id)
        
        if url_column not in df.columns:
            logger.warning(f"Column '{url_column}' not found in sheet")
            return []
        
        urls_data = []
        for idx, row in df.iterrows():
            url = row.get(url_column)
            if url and pd.notna(url) and str(url).startswith(('http://', 'https://')):
                urls_data.append({
                    'row_id': idx,
                    'url': str(url),
                    'row_data': row.to_dict()
                })
        
        logger.info(f"Extracted {len(urls_data)} URLs from sheet")
        return urls_data
    
    def write_dataframe_to_sheet(
        self,
        df: pd.DataFrame,
        spreadsheet_id: Optional[str] = None,
        sheet_name: str = "Results",
        clear_existing: bool = False
    ) -> bool:
        """
        Write DataFrame to a Google Sheet.
        
        Args:
            df: DataFrame to write
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the sheet to write to (will be created if doesn't exist)
            clear_existing: Whether to clear existing data first
            
        Returns:
            True if successful
        """
        try:
            spreadsheet = self.get_spreadsheet(spreadsheet_id)
            
            # Try to get existing sheet or create new one
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                if clear_existing:
                    worksheet.clear()
            except WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                logger.info(f"Created new sheet: {sheet_name}")
            
            # Convert DataFrame to list of lists
            # First row is headers
            values = [df.columns.tolist()]
            # Then data rows
            for _, row in df.iterrows():
                values.append(row.tolist())
            
            # Write to sheet
            worksheet.update(values, value_input_option='USER_ENTERED')
            logger.info(f"Wrote {len(df)} rows to sheet '{sheet_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error writing to sheet: {e}")
            raise
    
    def read_existing_results(
        self,
        spreadsheet_id: Optional[str] = None,
        sheet_name: str = "Results",
        keyword_column: str = "keyword",
        url_column: str = "url"
    ) -> pd.DataFrame:
        """
        Read existing analysis results from a sheet.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the results sheet
            keyword_column: Column name for keywords
            url_column: Column name for URLs
            
        Returns:
            DataFrame with existing results, or empty DataFrame if sheet doesn't exist
        """
        try:
            df = self.read_sheet(spreadsheet_id, sheet_name)
            logger.info(f"Read {len(df)} existing results from sheet '{sheet_name}'")
            return df
        except Exception as e:
            logger.info(f"No existing results found in sheet '{sheet_name}': {e}")
            return pd.DataFrame()
    
    def get_analyzed_pairs(
        self,
        spreadsheet_id: Optional[str] = None,
        sheet_name: str = "Results",
        keyword_column: str = "keyword",
        url_column: str = "url"
    ) -> set:
        """
        Get set of already analyzed keyword-URL pairs.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the results sheet
            keyword_column: Column name for keywords (in results sheet, typically "keyword")
            url_column: Column name for URLs (in results sheet, typically "url")
            
        Returns:
            Set of tuples (keyword, url) that have been analyzed
        """
        try:
            df = self.read_existing_results(spreadsheet_id, sheet_name, keyword_column, url_column)
            if df.empty:
                return set()
            
            # Results sheet uses standardized column names "keyword" and "url"
            # Try both the provided names and standard names
            result_keyword_col = "keyword" if "keyword" in df.columns else keyword_column
            result_url_col = "url" if "url" in df.columns else url_column
            
            # Create set of (keyword, url) pairs
            if result_keyword_col in df.columns and result_url_col in df.columns:
                pairs = set()
                for _, row in df.iterrows():
                    keyword = str(row[result_keyword_col]).strip() if pd.notna(row[result_keyword_col]) else ""
                    url = str(row[result_url_col]).strip() if pd.notna(row[result_url_col]) else ""
                    if keyword and url:
                        pairs.add((keyword.lower(), url.lower()))
                logger.info(f"Found {len(pairs)} previously analyzed keyword-URL pairs")
                return pairs
            else:
                available_cols = list(df.columns)
                logger.warning(f"Columns '{result_keyword_col}' or '{result_url_col}' not found in results sheet. Available columns: {available_cols}")
                return set()
        except Exception as e:
            logger.info(f"No existing analyzed pairs found: {e}")
            return set()

