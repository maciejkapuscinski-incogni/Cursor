"""Simple test script to verify OpenAI integration."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.openai_nlp_analyzer import OpenAINLPAnalyzer

def test_openai():
    """Test OpenAI integration."""
    print("=" * 60)
    print("OpenAI Integration Test")
    print("=" * 60)
    
    # Check config
    print(f"\n1. Configuration Check:")
    print(f"   OPENAI_API_KEY set: {bool(Config.OPENAI_API_KEY)}")
    print(f"   OPENAI_API_KEY length: {len(Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else 0}")
    print(f"   OPENAI_API_KEY starts with 'sk-': {Config.OPENAI_API_KEY.startswith('sk-') if Config.OPENAI_API_KEY else False}")
    print(f"   USE_OPENAI_NLP: {Config.USE_OPENAI_NLP}")
    print(f"   OPENAI_MODEL: {Config.OPENAI_MODEL}")
    
    if not Config.OPENAI_API_KEY:
        print("\n❌ ERROR: OPENAI_API_KEY not set in .env file")
        return False
    
    # Test initialization
    print(f"\n2. Initializing OpenAI NLP Analyzer...")
    try:
        analyzer = OpenAINLPAnalyzer()
        print("   ✅ OpenAI NLP Analyzer initialized successfully")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        return False
    
    # Test sentiment analysis
    print(f"\n3. Testing Sentiment Analysis...")
    try:
        result = analyzer.analyze_sentiment("I love this product! It's amazing!")
        print(f"   ✅ Sentiment analysis successful")
        print(f"   Result: {result['label']} (confidence: {result['score']:.2f})")
    except Exception as e:
        print(f"   ❌ Sentiment analysis failed: {e}")
        return False
    
    # Test intent analysis
    print(f"\n4. Testing Intent Analysis...")
    try:
        result = analyzer.analyze_intent("buy running shoes online")
        print(f"   ✅ Intent analysis successful")
        print(f"   Result: {result['label']} (confidence: {result['confidence']:.2f})")
    except Exception as e:
        print(f"   ❌ Intent analysis failed: {e}")
        return False
    
    # Test batch analysis
    print(f"\n5. Testing Batch Analysis...")
    try:
        texts = ["This is great!", "I hate this", "It's okay"]
        results = analyzer.analyze_batch(texts)
        print(f"   ✅ Batch analysis successful")
        print(f"   Processed {len(results)} texts")
        for i, result in enumerate(results):
            print(f"   Text {i+1}: sentiment={result['sentiment']['label']}, intent={result['intent']['label']}")
    except Exception as e:
        print(f"   ❌ Batch analysis failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! OpenAI integration is working correctly.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_openai()
    sys.exit(0 if success else 1)

