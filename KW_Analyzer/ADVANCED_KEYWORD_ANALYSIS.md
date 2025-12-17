# Advanced Keyword Analysis Guide

This guide explains how to use the Advanced Keyword Analysis feature to analyze search terms, compare with conversion data, and evaluate landing page alignment.

## Overview

The Advanced Keyword Analysis workflow performs:

1. **Keyword Analysis**: Analyzes search terms/keywords for sentiment and intent
2. **Conversion Comparison**: Compares keyword performance with conversion data
3. **Landing Page Alignment**: Evaluates if keywords/intents are reflected on the website
4. **Recommendations**: Provides actionable insights:
   - ✅ **GOOD_LANDING_PAGE**: Keep and optimize
   - ⚠️ **NEEDS_OPTIMIZATION**: Optimize website content
   - ❌ **POOR_ALIGNMENT**: Exclude from campaign or create new landing page

## Google Sheets Format

Your Google Sheet should have the following columns:

### Required Columns:
- **keyword** (or custom name): Search terms/keywords to analyze
- **url** (or custom name): Landing page URLs

### Optional Columns (for conversion analysis):
- **conversions**: Number of conversions for each keyword
- **clicks**: Number of clicks for each keyword
- **cost**: Cost per keyword (for future analysis)

### Example Sheet Structure:

| keyword | url | conversions | clicks |
|---------|-----|-------------|--------|
| buy running shoes | https://example.com/shoes | 15 | 200 |
| best running shoes | https://example.com/shoes | 8 | 150 |
| running shoe reviews | https://example.com/reviews | 2 | 80 |

## Using the Dashboard

### Step 1: Select Analysis Mode
1. Open the dashboard: `streamlit run dashboard/app.py`
2. In the sidebar, select **"Advanced Keyword Analysis"** mode

### Step 2: Configure Google Sheets
1. Enter your **Spreadsheet ID**
2. (Optional) Enter **Sheet Name** if not using the first sheet
3. Specify column names:
   - **Keyword Column Name**: Column containing keywords (default: `keyword`)
   - **URL Column Name**: Column containing URLs (default: `url`)
   - **Conversions Column**: (Optional) Column with conversion counts
   - **Clicks Column**: (Optional) Column with click counts

### Step 3: Run Analysis
1. Click **"🚀 Analyze Keywords & Landing Pages"**
2. Wait for analysis to complete (this may take a few minutes depending on the number of keywords)

## Understanding Results

### Summary Statistics

- **Total Keywords**: Number of keywords analyzed
- **✅ Good Landing Pages**: Keywords with strong alignment (score ≥ 0.7)
- **⚠️ Needs Optimization**: Keywords with moderate alignment (score 0.5-0.7)
- **❌ Poor Alignment**: Keywords with poor alignment (score < 0.5)
- **Avg Alignment Score**: Average alignment score across all keywords

### Alignment Score Components

The alignment score (0-1) is calculated from:

1. **Intent Match** (40%): Does page intent match keyword intent?
2. **Sentiment Alignment** (30%): Do sentiments align?
3. **Keyword Presence** (20%): Is the keyword present in page content?
4. **Keyword Density** (10%): How frequently does the keyword appear?

### Recommendations

#### ✅ GOOD_LANDING_PAGE
- **Action**: Keep and optimize
- **When**: Alignment score ≥ 0.7 AND intent matches
- **Meaning**: Landing page effectively matches user search intent

#### ⚠️ NEEDS_OPTIMIZATION
- **Action**: Optimize website content
- **When**: Alignment score 0.5-0.7
- **Meaning**: Moderate alignment - improve content to better match keyword intent

#### ❌ POOR_ALIGNMENT
- **Action**: Exclude from campaign or create new landing page
- **When**: Alignment score < 0.5
- **Meaning**: Keyword intent doesn't match page content

### Conversion Data Integration

If you provide conversion data:
- **High conversion rate + poor alignment**: May indicate brand/awareness keywords
- **Low conversion rate + good alignment**: Focus on conversion optimization
- **High conversion rate + good alignment**: Optimal - keep and scale

## Optimization Recommendations Section

The dashboard shows a prioritized list of keywords requiring attention:

1. **Priority**: HIGH, MEDIUM, or LOW
2. **Alignment Score**: Current alignment (lower = higher priority)
3. **Intent Match**: Whether intents match (1.0 = match, 0.0 = no match)
4. **Keyword Presence**: Whether keyword appears in content
5. **Action**: Recommended action
6. **Reasoning**: Detailed explanation

## Programmatic Usage

You can also use the advanced processor programmatically:

```python
from src.advanced_processor import AdvancedDataProcessor

# Initialize processor
processor = AdvancedDataProcessor(use_apify=False)

# Process keywords with conversion data
results_df = processor.process_keyword_analysis(
    spreadsheet_id="your_spreadsheet_id",
    sheet_name="Sheet1",
    keyword_column="keyword",
    url_column="url",
    conversion_columns={
        'conversions': 'conversions',
        'clicks': 'clicks'
    }
)

# Get summary
summary = processor.get_analysis_summary(results_df)

# Get optimization recommendations
optimization_df = processor.get_optimization_recommendations(results_df)
```

## Tips for Best Results

1. **Use specific keywords**: More specific keywords provide better intent analysis
2. **Include conversion data**: Helps make better recommendations
3. **Review recommendations**: Not all recommendations are perfect - use your judgment
4. **Monitor over time**: Re-run analysis after making optimizations
5. **Consider context**: Some keywords may work despite poor alignment (brand terms)

## Troubleshooting

### "Column not found" error
- Check that your column names match exactly (case-sensitive)
- Verify column names in your Google Sheet

### "Failed to scrape landing page"
- Check URL accessibility
- Some sites may block scrapers - try using Apify option
- Verify URLs are correct and accessible

### Low alignment scores
- This is normal for some keywords
- Focus on keywords with high conversion potential
- Consider creating dedicated landing pages for high-value keywords

## Next Steps

After analysis:
1. Review optimization recommendations
2. Prioritize keywords with HIGH priority
3. Optimize landing pages for keywords needing improvement
4. Consider excluding keywords with poor alignment and low conversions
5. Re-run analysis after making changes

