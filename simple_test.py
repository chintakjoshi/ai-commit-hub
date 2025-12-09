#!/usr/bin/env python3
"""Simple test script to verify the system works"""

import asyncio
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings

print("=" * 60)
print("SIMPLE CONFIGURATION TEST")
print("=" * 60)

print(f"\nChecking configuration...")
print(f"GitHub Username: {settings.github_username}")
print(f"LLM Provider: {settings.llm_provider}")
print(f"LLM Model: {settings.current_model}")
print(f"API Key Available: {'Yes' if settings.api_key else 'No'}")

if not settings.api_key:
    print("\n⚠️  WARNING: No API key found!")
    print(f"Please check your .env file and ensure {settings.llm_provider.upper()}_API_KEY is set")
else:
    print(f"API Key (first 10 chars): {settings.api_key[:10]}...")

print(f"\nCommit Settings:")
print(f"  Min commits per day: {settings.min_commits_per_day}")
print(f"  Max commits per day: {settings.max_commits_per_day}")
print(f"  Min time between commits: {settings.min_time_between_commits} seconds")
print(f"  Max time between commits: {settings.max_time_between_commits} seconds")

print("\nChecking directories...")
required_dirs = [
    "./config",
    "./agents",
    "./managers",
    "./utils",
    "./repos",
    "./data/templates",
    "./data/cache"
]

for dir_path in required_dirs:
    if os.path.exists(dir_path):
        print(f"  ✓ {dir_path}")
    else:
        print(f"  ✗ {dir_path} (missing)")

print("\n" + "=" * 60)
print("To run the setup wizard: python main.py --setup")
print("To test connections: python main.py --test")
print("=" * 60)