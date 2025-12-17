"""Report generation module for CSV and PDF exports."""
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate CSV and PDF reports."""
    
    def __init__(self):
        """Initialize report generator."""
        logger.info("Report generator initialized")
    
    def export_csv(self, df: pd.DataFrame, filepath: str) -> bool:
        """
        Export DataFrame to CSV.
        
        Args:
            df: DataFrame to export
            filepath: Output file path
            
        Returns:
            True if successful
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(filepath, index=False)
            logger.info(f"Exported CSV to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            return False
    
    def generate_pdf(self, df: pd.DataFrame, summary: dict, filepath: str) -> bool:
        """
        Generate PDF report.
        
        Args:
            df: DataFrame with analysis results
            summary: Summary statistics dictionary
            filepath: Output file path
            
        Returns:
            True if successful
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=30,
                alignment=1  # Center
            )
            title = Paragraph("Analysis Report", title_style)
            story.append(title)
            story.append(Spacer(1, 0.2*inch))
            
            # Date
            date_style = ParagraphStyle(
                'DateStyle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey,
                alignment=1
            )
            date_text = Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
            story.append(date_text)
            story.append(Spacer(1, 0.3*inch))
            
            # Summary Section
            story.append(Paragraph("Summary Statistics", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            summary_data = [
                ['Metric', 'Value'],
                ['Total Records', summary.get('total_analyses', 0)],
                ['Total Web Content', summary.get('total_web_content', 0)],
                ['Average Sentiment Score', f"{summary.get('average_sentiment_score', 0):.3f}"],
                ['Average Intent Confidence', f"{summary.get('average_intent_confidence', 0):.3f}"]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Sentiment Distribution
            if 'sentiment_distribution' in summary:
                story.append(Paragraph("Sentiment Distribution", styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                
                sentiment_data = [['Sentiment', 'Count']]
                for label, count in summary['sentiment_distribution'].items():
                    sentiment_data.append([label.title(), str(count)])
                
                sentiment_table = Table(sentiment_data, colWidths=[2*inch, 1*inch])
                sentiment_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(sentiment_table)
                story.append(Spacer(1, 0.2*inch))
            
            # Intent Distribution
            if 'intent_distribution' in summary:
                story.append(Paragraph("Intent Distribution", styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                
                intent_data = [['Intent', 'Count']]
                for label, count in summary['intent_distribution'].items():
                    intent_data.append([label.title(), str(count)])
                
                intent_table = Table(intent_data, colWidths=[2*inch, 1*inch])
                intent_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(intent_table)
                story.append(PageBreak())
            
            # Detailed Results Table (first 50 rows)
            story.append(Paragraph("Detailed Results", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            # Prepare data for table
            display_df = df.head(50)  # Limit to 50 rows for PDF
            table_data = [df.columns.tolist()]
            
            for _, row in display_df.iterrows():
                table_data.append([str(val)[:50] for val in row.values])  # Truncate long values
            
            # Create table
            results_table = Table(table_data, colWidths=[1.5*inch] * len(df.columns))
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            story.append(results_table)
            
            if len(df) > 50:
                story.append(Spacer(1, 0.1*inch))
                note = Paragraph(f"<i>Note: Showing first 50 of {len(df)} total records. Full data available in CSV export.</i>", styles['Normal'])
                story.append(note)
            
            # Build PDF
            doc.build(story)
            logger.info(f"Generated PDF report: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            return False

