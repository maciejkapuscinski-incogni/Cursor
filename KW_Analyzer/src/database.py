"""Database operations for storing analysis data."""
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from pathlib import Path
import logging

from src.config import Config

Base = declarative_base()
logger = logging.getLogger(__name__)


class GoogleSheetsData(Base):
    """Table for storing Google Sheets data."""
    __tablename__ = "google_sheets_data"
    
    id = Column(Integer, primary_key=True)
    row_id = Column(Integer)  # Original row ID from sheet
    sheet_name = Column(String(255))
    data = Column(Text)  # JSON string of row data
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    web_content = relationship("WebContent", back_populates="sheet_data", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="sheet_data", cascade="all, delete-orphan")


class WebContent(Base):
    """Table for storing scraped web content."""
    __tablename__ = "web_content"
    
    id = Column(Integer, primary_key=True)
    sheet_data_id = Column(Integer, ForeignKey("google_sheets_data.id"), nullable=True)
    url = Column(String(1000), nullable=False)
    title = Column(String(500))
    content = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    scraping_method = Column(String(50))  # 'beautifulsoup' or 'apify'
    
    # Relationships
    sheet_data = relationship("GoogleSheetsData", back_populates="web_content")
    analysis_results = relationship("AnalysisResult", back_populates="web_content", cascade="all, delete-orphan")


class AnalysisResult(Base):
    """Table for storing NLP analysis results."""
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True)
    sheet_data_id = Column(Integer, ForeignKey("google_sheets_data.id"), nullable=True)
    web_content_id = Column(Integer, ForeignKey("web_content.id"), nullable=True)
    
    # Sentiment Analysis
    sentiment_label = Column(String(50))  # 'positive', 'negative', 'neutral'
    sentiment_score = Column(Float)
    
    # Intent Analysis
    intent_label = Column(String(100))
    intent_confidence = Column(Float)
    
    # Text Analysis
    text_length = Column(Integer)
    word_count = Column(Integer)
    
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sheet_data = relationship("GoogleSheetsData", back_populates="analysis_results")
    web_content = relationship("WebContent", back_populates="analysis_results")


class Database:
    """Database manager."""
    
    def __init__(self, db_path=None):
        """Initialize database connection."""
        if db_path is None:
            db_path = Config.ensure_data_dir()
        
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialized at {db_path}")
    
    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()

