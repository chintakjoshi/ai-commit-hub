import asyncio
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from managers.llm_manager import LLMManager

async def test_llm_connection():
    """Simple test for LLM connection"""
    print(f"Testing {settings.llm_provider} connection...")
    print(f"Model: {settings.current_model}")
    
    llm_manager = LLMManager()
    
    try:
        # Ensure session is created
        await llm_manager._ensure_session()
        print("✓ Session created successfully")
        
        # Test with a simple prompt
        test_prompt = "Hello! Please respond with 'Connection successful' and nothing else."
        print(f"Sending test prompt...")
        
        response = await llm_manager.generate_text(test_prompt)
        print(f"✓ Response received: {response[:100]}...")
        
        if "Connection successful" in response:
            print("✓ Connection test PASSED")
        else:
            print("✗ Connection test FAILED - Unexpected response")
            
    except Exception as e:
        print(f"✗ Connection test FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await llm_manager.close()

async def test_github_connection():
    """Simple test for GitHub connection"""
    from managers.github_manager import GitHubManager
    
    print("\nTesting GitHub connection...")
    
    github_manager = GitHubManager()
    
    try:
        repos = github_manager.get_repo_list()
        print(f"✓ GitHub connection successful")
        print(f"  Found {len(repos)} repositories")
        if repos:
            print(f"  First 3 repos: {repos[:3]}")
        return True
    except Exception as e:
        print(f"✗ GitHub connection failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 60)
    print("AUTO-COMMITTER CONNECTION TEST")
    print("=" * 60)
    
    # Test LLM
    await test_llm_connection()
    
    # Test GitHub
    await test_github_connection()
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())