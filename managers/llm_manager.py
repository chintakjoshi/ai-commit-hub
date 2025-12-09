import openai
import anthropic
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from config.settings import settings

class LLMManager:
    def __init__(self):
        self.provider = settings.llm_provider
        
        if self.provider == "openai" and settings.openai_api_key:
            self.client = openai.OpenAI(api_key=settings.openai_api_key)
        elif self.provider == "anthropic" and settings.anthropic_api_key:
            self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        else:
            raise ValueError("No valid LLM provider configured")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text using LLM with retry logic"""
        
        if self.provider == "openai":
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=settings.model_name,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
            
        elif self.provider == "anthropic":
            messages = [{"role": "user", "content": prompt}]
            
            response = self.client.messages.create(
                model=settings.model_name,
                system=system_prompt,
                messages=messages,
                **kwargs
            )
            return response.content[0].text
    
    async def generate_structured_content(self, prompt: str, output_format: str) -> Dict:
        """Generate structured content (JSON, YAML, etc.)"""
        structured_prompt = f"""{prompt}
        
        Return the response in the following format:
        {output_format}
        
        Ensure the response is valid and properly structured."""
        
        response = await self.generate_text(structured_prompt)
        # Parse response based on format
        # Implementation depends on your needs
        return {"raw": response}