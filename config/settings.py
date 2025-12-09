import os
from typing import Dict, List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # GitHub
    github_token: str = Field(..., env="GITHUB_TOKEN")
    github_username: str = Field(..., env="GITHUB_USERNAME")
    
    # Free LLM APIs
    openrouter_api_key: Optional[str] = Field(None, env="OPENROUTER_API_KEY")
    nim_api_key: Optional[str] = Field(None, env="NIM_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    
    # Provider selection
    llm_provider: str = Field("openrouter", env="LLM_PROVIDER")
    
    # Model names for each provider
    llm_model: str = Field("togethercomputer/CodeLlama-34b-Instruct", env="LLM_MODEL")
    nim_model: str = Field("microsoft/phi-4-mini-instruct", env="NIM_MODEL")
    google_model: str = Field("gemini-2.0-flash", env="GOOGLE_MODEL")
    
    # API endpoints
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    google_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    
    # App
    max_commits_per_day: int = Field(30, env="MAX_COMMITS_PER_DAY")
    min_commits_per_day: int = Field(20, env="MIN_COMMITS_PER_DAY")
    repo_base_path: str = Field("./repos", env="REPO_BASE_PATH")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    max_tokens: int = Field(4000, env="MAX_TOKENS")
    temperature: float = Field(0.7, env="TEMPERATURE")
    
    # Rate limiting
    requests_per_minute: int = Field(10, env="REQUESTS_PER_MINUTE")
    max_retries: int = Field(3, env="MAX_RETRIES")
    timeout_seconds: int = Field(30, env="TIMEOUT_SECONDS")
    
    # Randomization
    min_time_between_commits: int = Field(900, env="MIN_TIME_BETWEEN_COMMITS")
    max_time_between_commits: int = Field(7200, env="MAX_TIME_BETWEEN_COMMITS")
    
    @validator('llm_provider')
    def validate_provider(cls, v):
        valid_providers = ['openrouter', 'nim', 'google']
        if v not in valid_providers:
            raise ValueError(f'Provider must be one of {valid_providers}')
        return v
    
    @property
    def current_model(self) -> str:
        """Get the model name for current provider"""
        provider_models = {
            'openrouter': self.llm_model,
            'nim': self.nim_model,
            'google': self.google_model
        }
        return provider_models.get(self.llm_provider, self.llm_model)
    
    @property
    def api_key(self) -> str:
        """Get API key for current provider"""
        provider_keys = {
            'openrouter': self.openrouter_api_key,
            'nim': self.nim_api_key,
            'google': self.google_api_key
        }
        return provider_keys.get(self.llm_provider)
    
    class Config:
        env_file = ".env"

settings = Settings()