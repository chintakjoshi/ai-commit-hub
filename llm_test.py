import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings

print("=" * 60)
print("LLM CONNECTION TEST")
print("=" * 60)

print(f"\nChecking configuration:")
print(f"LLM Provider: {settings.llm_provider}")
print(f"Model: {settings.current_model}")
print(f"API Key Available: {'Yes' if settings.api_key else 'No'}")

if settings.api_key:
    print(f"API Key (first 10 chars): {settings.api_key[:10]}...")
else:
    print("❌ ERROR: No API key found!")
    print(f"\nPlease check your .env file and ensure {settings.llm_provider.upper()}_API_KEY is set")
    sys.exit(1)

# Try to import LLM Manager
try:
    from managers.llm_manager import LLMManager
    print("✓ LLM Manager imported successfully")
except Exception as e:
    print(f"❌ Error importing LLM Manager: {e}")
    sys.exit(1)

async def test():
    print("\nTesting LLM connection...")
    llm = LLMManager()
    
    try:
        # Ensure session is created
        await llm._ensure_session()
        print("✓ Session created successfully")
        
        # Test with a simple prompt
        test_prompt = "Hello! Please respond with 'test passed' and nothing else."
        print(f"Sending test prompt...")
        
        response = await llm.generate_text(test_prompt)
        print(f"✓ Response received: {response}")
        
        if "test passed" in response.lower():
            print("✓ Connection test PASSED")
        else:
            print(f"⚠️  Unexpected response, but connection works")
            
    except Exception as e:
        print(f"❌ Connection test FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await llm.close()

if __name__ == "__main__":
    asyncio.run(test())