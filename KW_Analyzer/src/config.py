"""Configuration management for the analyzer."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Get project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

# Load environment variables from project root
env_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration."""
    
    # Google Sheets Configuration
    _credentials_path = os.getenv(
        "GOOGLE_SHEETS_CREDENTIALS_PATH",
        "./credentials/google-sheets-credentials.json"
    )
    # Resolve relative paths to absolute paths based on project root
    GOOGLE_SHEETS_CREDENTIALS_PATH = str(
        (PROJECT_ROOT / _credentials_path).resolve()
        if not os.path.isabs(_credentials_path)
        else Path(_credentials_path)
    )
    GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    
    # Apify Configuration
    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    USE_OPENAI_NLP = os.getenv("USE_OPENAI_NLP", "false").lower() == "true"
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Fast and cost-effective
    
    # Database Configuration
    _db_path = os.getenv("DATABASE_PATH", "./data/analyzer.db")
    DATABASE_PATH = str(
        (PROJECT_ROOT / _db_path).resolve()
        if not os.path.isabs(_db_path)
        else Path(_db_path)
    )
    
    # Application Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Ensure data directory exists
    @staticmethod
    def ensure_data_dir():
        """Ensure the data directory exists."""
        db_path = Path(Config.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

