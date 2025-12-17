"""Streamlit dashboard for the analyzer."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_processor import DataProcessor
from src.advanced_processor import AdvancedDataProcessor
from src.report_generator import ReportGenerator
from src.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="KW Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'processor' not in st.session_state:
    st.session_state.processor = None
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'summary' not in st.session_state:
    st.session_state.summary = {}
if 'analysis_mode' not in st.session_state:
    st.session_state.analysis_mode = 'basic'

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f4788;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f4788;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">📊 KW Analyzer</h1>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    use_apify = st.checkbox("Use Apify for scraping", value=False)
    
    use_openai = st.checkbox(
        "Use OpenAI for NLP (faster, requires API key)",
        value=Config.USE_OPENAI_NLP,
        help="Use OpenAI API for sentiment and intent analysis. Much faster than local models. Requires OPENAI_API_KEY in .env"
    )
    
    # Show OpenAI status
    if use_openai:
        if Config.OPENAI_API_KEY:
            st.success(f"✅ OpenAI API key configured (Model: {Config.OPENAI_MODEL})")
        else:
            st.error("❌ OpenAI API key not found in .env file. Please set OPENAI_API_KEY.")
    else:
        st.info("ℹ️ Using local models for NLP analysis")
    
    st.markdown("---")
    st.header("🔧 Analysis Mode")
    
    analysis_mode = st.radio(
        "Select analysis mode:",
        ["Basic Analysis", "Advanced Keyword Analysis"],
        help="Basic: Analyze URLs only. Advanced: Analyze keywords, compare with conversions, and evaluate landing page alignment."
    )
    st.session_state.analysis_mode = 'advanced' if analysis_mode == "Advanced Keyword Analysis" else 'basic'
    
    st.markdown("---")
    st.header("📥 Data Input")
    
    input_method = st.radio(
        "Select input method:",
        ["Google Sheets", "Manual URL Entry"]
    )
    
    if input_method == "Google Sheets":
        spreadsheet_id = st.text_input(
            "Spreadsheet ID",
            value=Config.GOOGLE_SHEETS_SPREADSHEET_ID,
            help="Enter your Google Sheets spreadsheet ID"
        )
        sheet_name = st.text_input(
            "Sheet Name (optional)",
            help="Leave empty for first sheet"
        )
        
        if st.session_state.analysis_mode == 'advanced':
            keyword_column = st.text_input(
                "Keyword Column Name",
                value="keyword",
                help="Column name containing keywords/search terms"
            )
            url_column = st.text_input(
                "URL Column Name",
                value="url",
                help="Column name containing landing page URLs"
            )
            st.markdown("**Conversion Columns (Optional):**")
            conversions_col = st.text_input(
                "Conversions Column",
                value="",
                help="Column name for conversion count (optional)"
            )
            clicks_col = st.text_input(
                "Clicks Column",
                value="",
                help="Column name for click count (optional)"
            )
            
            conversion_columns = None
            if conversions_col and clicks_col:
                conversion_columns = {
                    'conversions': conversions_col,
                    'clicks': clicks_col
                }
            
            st.markdown("---")
            st.markdown("**Results Sheet Configuration:**")
            results_sheet_name = st.text_input(
                "Results Sheet Name",
                value="Analysis_Results",
                help="Name of sheet to save results to (will be created if doesn't exist)"
            )
            
            force_rerun = st.checkbox(
                "Force Rerun All Analysis",
                value=False,
                help="If checked, re-analyze all keyword-URL pairs even if already analyzed. If unchecked, skip previously analyzed pairs."
            )
        else:
            url_column = st.text_input(
                "URL Column Name",
                value="url",
                help="Column name containing URLs"
            )
        
        button_text = "🚀 Process Google Sheets" if st.session_state.analysis_mode == 'basic' else "🚀 Analyze Keywords & Landing Pages"
        
        # Show initial info button for advanced mode
        if st.session_state.analysis_mode == 'advanced':
            if st.button("📊 Preview Spreadsheet Info", help="Load spreadsheet info without processing"):
                try:
                    processor = AdvancedDataProcessor(use_apify=use_apify, use_openai=use_openai)
                    initial_info = processor.get_initial_info(
                        spreadsheet_id=spreadsheet_id if spreadsheet_id else None,
                        sheet_name=sheet_name if sheet_name else None,
                        keyword_column=keyword_column,
                        url_column=url_column
                    )
                    st.session_state.initial_info = initial_info
                    st.info(f"""
                    **Spreadsheet:** {initial_info['spreadsheet_name']}  
                    **Sheet:** {initial_info['sheet_name']}  
                    **Keywords Found:** {initial_info['keyword_count']}  
                    **Unique URLs:** {initial_info['unique_url_count']}  
                    **Total Rows:** {initial_info['total_rows']}
                    """)
                except Exception as e:
                    st.error(f"❌ Error loading spreadsheet info: {str(e)}")
                    logger.error(f"Error loading spreadsheet info: {e}")
        
        if st.button(button_text, type="primary"):
            with st.spinner("Processing data..."):
                try:
                    if st.session_state.analysis_mode == 'advanced':
                        processor = AdvancedDataProcessor(use_apify=use_apify, use_openai=use_openai)
                        
                        # Show initial info first
                        initial_info = processor.get_initial_info(
                            spreadsheet_id=spreadsheet_id if spreadsheet_id else None,
                            sheet_name=sheet_name if sheet_name else None,
                            keyword_column=keyword_column,
                            url_column=url_column
                        )
                        st.session_state.initial_info = initial_info
                        
                        # Check for existing results
                        existing_count = 0
                        if results_sheet_name and not force_rerun:
                            existing_results = processor.sheets_reader.read_existing_results(
                                spreadsheet_id=spreadsheet_id if spreadsheet_id else None,
                                sheet_name=results_sheet_name,
                                keyword_column=keyword_column,
                                url_column=url_column
                            )
                            existing_count = len(existing_results)
                        
                        # Display initial info
                        info_text = f"""
                        **📊 Spreadsheet Information:**
                        - **Spreadsheet:** {initial_info['spreadsheet_name']}
                        - **Sheet:** {initial_info['sheet_name']}
                        - **Keywords Found:** {initial_info['keyword_count']}
                        - **Unique URLs:** {initial_info['unique_url_count']}
                        - **Total Rows:** {initial_info['total_rows']}
                        """
                        
                        if existing_count > 0 and not force_rerun:
                            info_text += f"\n- **Previously Analyzed:** {existing_count} pairs (will be skipped)"
                            new_to_analyze = initial_info['keyword_count'] - existing_count
                            info_text += f"\n- **New to Analyze:** {new_to_analyze} pairs"
                        elif force_rerun:
                            info_text += f"\n- **⚠️ Force Rerun:** All {initial_info['keyword_count']} pairs will be re-analyzed"
                        else:
                            info_text += f"\n\n*Processing will scrape {initial_info['unique_url_count']} unique URLs and analyze {initial_info['keyword_count']} keywords...*"
                        
                        st.info(info_text)
                        
                        results_df = processor.process_keyword_analysis(
                            spreadsheet_id=spreadsheet_id if spreadsheet_id else None,
                            sheet_name=sheet_name if sheet_name else None,
                            keyword_column=keyword_column,
                            url_column=url_column,
                            conversion_columns=conversion_columns,
                            results_sheet_name=results_sheet_name if results_sheet_name else None,
                            force_rerun=force_rerun
                        )
                        summary = processor.get_analysis_summary(results_df)
                        
                        # Show save confirmation
                        if results_sheet_name and len(results_df) > 0:
                            st.success(f"✅ Results saved to sheet '{results_sheet_name}' in the spreadsheet!")
                    else:
                        processor = DataProcessor(use_apify=use_apify)
                        results_df = processor.process_sheet_data(
                            spreadsheet_id=spreadsheet_id if spreadsheet_id else None,
                            sheet_name=sheet_name if sheet_name else None,
                            url_column=url_column
                        )
                        summary = processor.get_analysis_summary()
                    
                    st.session_state.processor = processor
                    st.session_state.results_df = results_df
                    st.session_state.summary = summary
                    
                    st.success(f"✅ Processed {len(results_df)} records!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    logger.error(f"Error processing sheets: {e}")
    
    else:  # Manual URL Entry
        urls_text = st.text_area(
            "Enter URLs (one per line)",
            height=200,
            help="Enter URLs to analyze, one per line"
        )
        
        if st.button("🚀 Analyze URLs", type="primary"):
            if urls_text:
                urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
                with st.spinner(f"Analyzing {len(urls)} URLs..."):
                    try:
                        processor = DataProcessor(use_apify=use_apify)
                        # For manual URLs, we'll create a simple DataFrame
                        results = []
                        for url in urls:
                            scraped = processor.web_scraper.scrape_url(url)
                            if scraped:
                                analysis = processor.nlp_analyzer.analyze_text(scraped.get('content', ''))
                                results.append({
                                    'url': url,
                                    'title': scraped.get('title', ''),
                                    'sentiment': analysis['sentiment']['label'],
                                    'sentiment_score': analysis['sentiment']['score'],
                                    'intent': analysis['intent']['label'],
                                    'intent_confidence': analysis['intent']['confidence'],
                                    'word_count': analysis['word_count']
                                })
                        
                        results_df = pd.DataFrame(results)
                        summary = {
                            'total_analyses': len(results),
                            'total_web_content': len(results),
                            'sentiment_distribution': results_df['sentiment'].value_counts().to_dict(),
                            'intent_distribution': results_df['intent'].value_counts().to_dict(),
                            'average_sentiment_score': results_df['sentiment_score'].mean(),
                            'average_intent_confidence': results_df['intent_confidence'].mean()
                        }
                        
                        st.session_state.processor = processor
                        st.session_state.results_df = results_df
                        st.session_state.summary = summary
                        
                        st.success(f"✅ Analyzed {len(results)} URLs!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        logger.error(f"Error analyzing URLs: {e}")
            else:
                st.warning("Please enter at least one URL")

# Main content
if st.session_state.results_df is not None and len(st.session_state.results_df) > 0:
    df = st.session_state.results_df
    summary = st.session_state.summary
    
    # Summary Metrics
    st.header("📈 Summary Statistics")
    
    if st.session_state.analysis_mode == 'advanced':
        # Advanced analysis metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Keywords", summary.get('total_keywords', len(df)))
        with col2:
            good_pages = summary.get('good_landing_pages', 0)
            st.metric("✅ Good Landing Pages", good_pages, 
                     delta=f"{good_pages/len(df)*100:.1f}%" if len(df) > 0 else "0%")
        with col3:
            needs_opt = summary.get('needs_optimization', 0)
            st.metric("⚠️ Needs Optimization", needs_opt,
                     delta=f"{needs_opt/len(df)*100:.1f}%" if len(df) > 0 else "0%")
        with col4:
            poor = summary.get('poor_alignment', 0)
            st.metric("❌ Poor Alignment", poor,
                     delta=f"{poor/len(df)*100:.1f}%" if len(df) > 0 else "0%")
        with col5:
            avg_score = summary.get('average_alignment_score', df['alignment_score'].mean() if 'alignment_score' in df.columns else 0)
            st.metric("Avg Alignment Score", f"{avg_score:.2f}")
        
        # Conversion metrics if available
        if 'overall_conversion_rate' in summary:
            st.markdown("---")
            st.subheader("📊 Conversion Metrics")
            conv_col1, conv_col2, conv_col3 = st.columns(3)
            with conv_col1:
                st.metric("Total Conversions", summary.get('total_conversions', 0))
            with conv_col2:
                st.metric("Total Clicks", summary.get('total_clicks', 0))
            with conv_col3:
                conv_rate = summary.get('overall_conversion_rate', 0)
                st.metric("Overall Conversion Rate", f"{conv_rate:.2%}")
    else:
        # Basic analysis metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Records", summary.get('total_analyses', len(df)))
        with col2:
            st.metric("Average Sentiment", f"{summary.get('average_sentiment_score', df['sentiment_score'].mean() if 'sentiment_score' in df.columns else 0):.3f}")
        with col3:
            st.metric("Average Intent Confidence", f"{summary.get('average_intent_confidence', df['intent_confidence'].mean() if 'intent_confidence' in df.columns else 0):.3f}")
        with col4:
            st.metric("Total URLs", len(df))
    
    st.markdown("---")
    
    # Visualizations
    if st.session_state.analysis_mode == 'advanced':
        # Advanced analysis visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Recommendation Distribution")
            if 'recommendation' in df.columns:
                rec_counts = df['recommendation'].value_counts()
                colors_map = {
                    'GOOD_LANDING_PAGE': '#2ecc71',
                    'NEEDS_OPTIMIZATION': '#f39c12',
                    'POOR_ALIGNMENT': '#e74c3c'
                }
                fig_rec = px.pie(
                    values=rec_counts.values,
                    names=rec_counts.index,
                    color=rec_counts.index,
                    color_discrete_map=colors_map
                )
                fig_rec.update_layout(showlegend=True)
                st.plotly_chart(fig_rec, use_container_width=True)
        
        with col2:
            st.subheader("Alignment Score Distribution")
            if 'alignment_score' in df.columns:
                fig_align = px.histogram(
                    df,
                    x='alignment_score',
                    nbins=20,
                    labels={'alignment_score': 'Alignment Score', 'count': 'Frequency'},
                    color_discrete_sequence=['#1f4788']
                )
                st.plotly_chart(fig_align, use_container_width=True)
        
        # Optimization recommendations section
        st.markdown("---")
        st.header("🎯 Optimization Recommendations")
        
        if isinstance(st.session_state.processor, AdvancedDataProcessor):
            optimization_df = st.session_state.processor.get_optimization_recommendations(df)
            if not optimization_df.empty:
                st.subheader("Keywords Requiring Attention (Priority Order)")
                st.dataframe(
                    optimization_df,
                    use_container_width=True,
                    height=400
                )
            else:
                st.success("🎉 All keywords have good landing page alignment!")
        
    else:
        # Basic analysis visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Sentiment Distribution")
            if 'sentiment' in df.columns:
                sentiment_counts = df['sentiment'].value_counts()
                fig_sentiment = px.pie(
                    values=sentiment_counts.values,
                    names=sentiment_counts.index,
                    color_discrete_map={
                        'positive': '#2ecc71',
                        'negative': '#e74c3c',
                        'neutral': '#95a5a6'
                    }
                )
                fig_sentiment.update_layout(showlegend=True)
                st.plotly_chart(fig_sentiment, use_container_width=True)
        
        with col2:
            st.subheader("Intent Distribution")
            if 'intent' in df.columns:
                intent_counts = df['intent'].value_counts().head(10)
                fig_intent = px.bar(
                    x=intent_counts.index,
                    y=intent_counts.values,
                    labels={'x': 'Intent', 'y': 'Count'},
                    color=intent_counts.values,
                    color_continuous_scale='Blues'
                )
                fig_intent.update_layout(showlegend=False)
                st.plotly_chart(fig_intent, use_container_width=True)
    
    # Sentiment Score Distribution
    if 'sentiment_score' in df.columns:
        st.subheader("Sentiment Score Distribution")
        fig_dist = px.histogram(
            df,
            x='sentiment_score',
            nbins=20,
            labels={'sentiment_score': 'Sentiment Score', 'count': 'Frequency'},
            color_discrete_sequence=['#1f4788']
        )
        st.plotly_chart(fig_dist, use_container_width=True)
    
    st.markdown("---")
    
    # Data Table
    st.header("📋 Detailed Results")
    
    # Filters
    if st.session_state.analysis_mode == 'advanced':
        col1, col2, col3 = st.columns(3)
        with col1:
            if 'recommendation' in df.columns:
                selected_recs = st.multiselect(
                    "Filter by Recommendation",
                    options=df['recommendation'].unique(),
                    default=df['recommendation'].unique()
                )
                df_filtered = df[df['recommendation'].isin(selected_recs)]
            else:
                df_filtered = df
        with col2:
            if 'keyword_intent' in df.columns:
                selected_intents = st.multiselect(
                    "Filter by Keyword Intent",
                    options=df['keyword_intent'].unique(),
                    default=df['keyword_intent'].unique()
                )
                df_filtered = df_filtered[df_filtered['keyword_intent'].isin(selected_intents)]
        with col3:
            if 'priority' in df.columns:
                selected_priorities = st.multiselect(
                    "Filter by Priority",
                    options=df['priority'].unique(),
                    default=df['priority'].unique()
                )
                df_filtered = df_filtered[df_filtered['priority'].isin(selected_priorities)]
    else:
        col1, col2 = st.columns(2)
        with col1:
            if 'sentiment' in df.columns:
                selected_sentiments = st.multiselect(
                    "Filter by Sentiment",
                    options=df['sentiment'].unique(),
                    default=df['sentiment'].unique()
                )
                df_filtered = df[df['sentiment'].isin(selected_sentiments)]
            else:
                df_filtered = df
        
        with col2:
            if 'intent' in df.columns:
                selected_intents = st.multiselect(
                    "Filter by Intent",
                    options=df['intent'].unique(),
                    default=df['intent'].unique()
                )
                df_filtered = df_filtered[df_filtered['intent'].isin(selected_intents)]
    
    # Search
    search_term = st.text_input("🔍 Search", placeholder="Search in results...")
    if search_term:
        mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask]
    
    # Display table
    st.dataframe(df_filtered, use_container_width=True, height=400)
    
    st.markdown("---")
    
    # Export Section
    st.header("💾 Export Results")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 Export CSV", use_container_width=True):
            report_gen = ReportGenerator()
            csv_path = "./exports/results.csv"
            if report_gen.export_csv(df_filtered, csv_path):
                with open(csv_path, 'rb') as f:
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=f.read(),
                        file_name="analysis_results.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
    
    with col2:
        if st.button("📑 Generate PDF Report", use_container_width=True):
            report_gen = ReportGenerator()
            pdf_path = "./exports/report.pdf"
            if report_gen.generate_pdf(df_filtered, summary, pdf_path):
                with open(pdf_path, 'rb') as f:
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=f.read(),
                        file_name="analysis_report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

else:
    # Welcome screen
    st.info("👈 Use the sidebar to start analyzing data. Connect to Google Sheets or enter URLs manually.")
    
    st.markdown("""
    ### Features:
    - 📊 **Google Sheets Integration**: Connect and analyze data from Google Sheets
    - 🌐 **Web Scraping**: Extract content from websites using BeautifulSoup or Apify
    - 💭 **Sentiment Analysis**: Analyze sentiment of web content
    - 🎯 **Intent Detection**: Classify content intent
    - 📈 **Interactive Dashboard**: Visualize results with charts and filters
    - 💾 **Export Reports**: Generate CSV and PDF reports
    """)

