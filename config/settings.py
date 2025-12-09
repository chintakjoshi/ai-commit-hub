import os
from typing import Dict, List, Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # GitHub
    github_token: str = Field(..., env="GITHUB_TOKEN")
    github_username: str = Field(..., env="GITHUB_USERNAME")
    
    # LLM
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    llm_provider: str = Field("openai", env="LLM_PROVIDER")
    model_name: str = Field("gpt-4-turbo-preview", env="MODEL_NAME")
    
    # App
    max_commits_per_day: int = Field(30, env="MAX_COMMITS_PER_DAY")
    min_commits_per_day: int = Field(20, env="MIN_COMMITS_PER_DAY")
    repo_base_path: str = Field("./repos", env="REPO_BASE_PATH")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Safety
    min_time_between_commits: int = 900  # 15 minutes in seconds
    max_time_between_commits: int = 7200  # 2 hours in seconds
    
    class Config:
        env_file = ".env"

settings = Settings()