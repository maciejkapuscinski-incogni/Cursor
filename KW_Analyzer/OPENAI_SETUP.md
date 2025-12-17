# OpenAI NLP Integration Guide

This guide explains how to use OpenAI's API for faster NLP analysis instead of local models.

## Benefits

- **Much Faster**: No need to load large models locally
- **No GPU Required**: Runs entirely via API
- **Better Accuracy**: OpenAI's models are highly optimized
- **Scalable**: Can handle large batches efficiently
- **Cost-Effective**: Using `gpt-4o-mini` is very affordable (~$0.15 per 1M input tokens)

## Setup

### 1. Install OpenAI Package

```bash
pip install openai>=1.0.0
```

Or reinstall all requirements:
```bash
pip install -r requirements.txt
```

### 2. Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key

### 3. Configure Environment

Add to your `.env` file:

```bash
OPENAI_API_KEY=sk-your-api-key-here
USE_OPENAI_NLP=true
OPENAI_MODEL=gpt-4o-mini
```

**Model Options:**
- `gpt-4o-mini` (Recommended) - Fast and cost-effective, great for sentiment/intent
- `gpt-4o` - More accurate but slower and more expensive
- `gpt-3.5-turbo` - Fast and cheap alternative

### 4. Use in Dashboard

1. Open the dashboard
2. In the sidebar, check **"Use OpenAI for NLP"**
3. Run your analysis

The system will automatically use OpenAI for all NLP tasks (sentiment and intent analysis).

## Cost Estimation

Using `gpt-4o-mini`:
- **Input**: ~$0.15 per 1M tokens
- **Output**: ~$0.60 per 1M tokens

**Example**: Analyzing 100 keywords with average 1000 words each:
- Input tokens: ~100,000 tokens = $0.015
- Output tokens: ~2,000 tokens = $0.0012
- **Total: ~$0.02 per 100 keywords**

## Performance Comparison

| Method | Speed | Setup | Cost |
|--------|-------|-------|------|
| Local Models | Slow (GPU) | Complex | Free |
| OpenAI API | Fast | Simple | ~$0.02/100 keywords |

## Fallback Behavior

If OpenAI is enabled but API key is missing or invalid:
- System automatically falls back to local models
- Warning message is logged
- Analysis continues without interruption

## Troubleshooting

### "OpenAI API key is required" error
- Check that `OPENAI_API_KEY` is set in `.env`
- Verify the key is correct (starts with `sk-`)
- Make sure you have credits in your OpenAI account

### Slow performance
- Check your internet connection
- Consider using `gpt-4o-mini` instead of `gpt-4o`
- Verify API rate limits aren't being hit

### High costs
- Use `gpt-4o-mini` model (cheapest option)
- Monitor usage in OpenAI dashboard
- Consider batching requests

## Switching Between Methods

You can switch between OpenAI and local models:
- **Dashboard**: Use the checkbox in sidebar
- **Programmatic**: Set `use_openai=True/False` when initializing `KeywordAnalyzer`
- **Config**: Set `USE_OPENAI_NLP=true/false` in `.env`

## Best Practices

1. **Start with OpenAI**: Much faster for initial testing
2. **Use gpt-4o-mini**: Best balance of speed and cost
3. **Monitor costs**: Check OpenAI dashboard regularly
4. **Batch processing**: System automatically batches efficiently
5. **Fallback ready**: Keep local models installed as backup

