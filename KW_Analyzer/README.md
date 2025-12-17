# KW Analyzer - Google Sheets and Web Content Analyzer

A comprehensive Python-based tool for analyzing Google Sheets data combined with web content analysis, featuring sentiment analysis, intent detection, and interactive visualizations.

## Features

- 📊 **Google Sheets Integration**: Read and process data from Google Sheets
- 🌐 **Web Scraping**: Extract content from websites using BeautifulSoup or Apify
- 💭 **Sentiment Analysis**: Analyze sentiment of web content using transformer models
- 🎯 **Intent Detection**: Classify content intent (informational, commercial, etc.)
- 📈 **Interactive Dashboard**: Streamlit-based dashboard with visualizations
- 💾 **Export Reports**: Generate CSV and PDF reports
- 🗄️ **Database Storage**: SQLite database for storing analysis results

## Tech Stack

- **Python 3.8+**
- **Data Processing**: pandas, numpy
- **Google Sheets**: gspread, google-auth
- **Web Scraping**: requests, beautifulsoup4, scrapy
- **NLP**: transformers (Hugging Face), torch
- **Dashboard**: Streamlit, Plotly
- **Database**: SQLAlchemy, SQLite
- **Reports**: reportlab, pandas

## Installation

1. **Clone the repository**:
   ```bash
   cd KW_Analyzer
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Download spaCy language model** (optional, for advanced text processing):
   ```bash
   python -m spacy download en_core_web_sm
   ```

5. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   - `GOOGLE_SHEETS_CREDENTIALS_PATH`: Path to your Google service account JSON file
   - `GOOGLE_SHEETS_SPREADSHEET_ID`: Your Google Sheets spreadsheet ID
   - `APIFY_API_TOKEN`: (Optional) Your Apify API token
   - `DATABASE_PATH`: Path to SQLite database (default: `./data/analyzer.db`)

## Google Sheets Setup

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Google Sheets API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Sheets API" and enable it
   - Search for "Google Drive API" and enable it

3. **Create Service Account**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Create a service account and download the JSON key file
   - Save the JSON file and update `GOOGLE_SHEETS_CREDENTIALS_PATH` in `.env`

4. **Share your Google Sheet**:
   - Open your Google Sheet
   - Click "Share" and add the service account email (found in the JSON file)
   - Give it "Viewer" permissions

## Usage

### Running the Dashboard

Start the Streamlit dashboard:

```bash
streamlit run dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Using the Dashboard

1. **Google Sheets Analysis**:
   - Select "Google Sheets" in the sidebar
   - Enter your Spreadsheet ID
   - (Optional) Specify sheet name and URL column name
   - Click "Process Google Sheets"
   - The tool will scrape URLs from the sheet and perform analysis

2. **Manual URL Analysis**:
   - Select "Manual URL Entry" in the sidebar
   - Enter URLs (one per line)
   - Click "Analyze URLs"
   - Results will be displayed with visualizations

3. **View Results**:
   - Summary statistics are shown at the top
   - Charts show sentiment and intent distributions
   - Detailed results table with filtering and search
   - Export results as CSV or PDF

### Programmatic Usage

You can also use the modules programmatically:

```python
from src.data_processor import DataProcessor
from src.report_generator import ReportGenerator

# Initialize processor
processor = DataProcessor(use_apify=False)

# Process Google Sheets
results_df = processor.process_sheet_data(
    spreadsheet_id="your_spreadsheet_id",
    sheet_name="Sheet1",
    url_column="url"
)

# Get summary
summary = processor.get_analysis_summary()

# Export reports
report_gen = ReportGenerator()
report_gen.export_csv(results_df, "results.csv")
report_gen.generate_pdf(results_df, summary, "report.pdf")
```

## Project Structure

```
KW_Analyzer/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── google_sheets.py       # Google Sheets integration
│   ├── web_scraper.py         # Web scraping module
│   ├── apify_integration.py   # Apify API integration
│   ├── nlp_analyzer.py        # Sentiment & intent analysis
│   ├── data_processor.py     # Data processing pipeline
│   ├── database.py            # Database operations
│   └── report_generator.py    # Report export functionality
├── dashboard/
│   └── app.py                 # Streamlit dashboard
├── data/                      # Database storage (created automatically)
├── exports/                   # Export files (created automatically)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Configuration

### Environment Variables

- `GOOGLE_SHEETS_CREDENTIALS_PATH`: Path to Google service account JSON file
- `GOOGLE_SHEETS_SPREADSHEET_ID`: Default Google Sheets spreadsheet ID
- `APIFY_API_TOKEN`: Apify API token (optional)
- `DATABASE_PATH`: Path to SQLite database file
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Database Schema

The tool uses SQLite with the following tables:

- **google_sheets_data**: Stores original Google Sheets data
- **web_content**: Stores scraped web content
- **analysis_results**: Stores NLP analysis results (sentiment, intent)

## Troubleshooting

### Google Sheets Authentication Issues

- Ensure the service account JSON file path is correct
- Verify the service account email has access to your Google Sheet
- Check that Google Sheets API and Drive API are enabled

### Web Scraping Issues

- Some websites may block scrapers - try using Apify instead
- Check network connectivity
- Verify URLs are accessible

### NLP Model Loading Issues

- Models are downloaded automatically on first use
- Ensure you have sufficient disk space (~2GB for models)
- For GPU acceleration, ensure CUDA is properly installed

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

