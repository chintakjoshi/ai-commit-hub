import aiohttp
import json
import asyncio
from typing import Dict, List, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging
from datetime import datetime
from config.settings import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter for API calls"""
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def wait_if_needed(self):
        async with self.lock:
            now = datetime.now()
            # Remove calls older than 1 minute
            self.calls = [call_time for call_time in self.calls 
                         if (now - call_time).total_seconds() < 60]
            
            if len(self.calls) >= self.calls_per_minute:
                # Wait for the oldest call to expire
                oldest = self.calls[0]
                wait_time = 60 - (now - oldest).total_seconds()
                if wait_time > 0:
                    logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
            
            self.calls.append(now)

class LLMManager:
    def __init__(self):
        self.provider = settings.llm_provider
        self.model = settings.current_model
        self.api_key = settings.api_key
        self.rate_limiter = RateLimiter(settings.requests_per_minute)
        self.session = None
        
        if not self.api_key:
            logger.warning(f"No API key found for provider: {self.provider}")
        
        # Provider-specific headers
        self.headers = self._get_provider_headers()
        
        logger.info(f"Initialized LLMManager with provider: {self.provider}, model: {self.model}")
    
    async def _ensure_session(self):
        """Ensure a session exists"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=settings.timeout_seconds)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
            logger.debug("Created new aiohttp session")
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Closed aiohttp session")
    
    def _get_provider_headers(self) -> Dict[str, str]:
        """Get headers for specific provider"""
        base_headers = {
            "Content-Type": "application/json",
        }
        
        if self.provider == "openrouter":
            return {
                **base_headers,
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com",
                "X-Title": "Auto-Committer AI"
            }
        elif self.provider == "nim":
            return {
                **base_headers,
                "Authorization": f"Bearer {self.api_key}"
            }
        elif self.provider == "google":
            return {
                **base_headers
            }
        return base_headers
    
    def _get_provider_url(self) -> str:
        """Get API URL for specific provider"""
        if self.provider == "openrouter":
            return settings.openrouter_url
        elif self.provider == "nim":
            return f"{settings.nim_base_url}/chat/completions"
        elif self.provider == "google":
            return f"{settings.google_base_url}/models/{self.model}:generateContent?key={self.api_key}"
        return settings.openrouter_url
    
    def _format_messages_for_provider(self, messages: List[Dict]) -> Any:
        """Format messages according to provider's requirements"""
        if self.provider == "openrouter":
            return {
                "model": self.model,
                "messages": messages,
                "max_tokens": settings.max_tokens,
                "temperature": settings.temperature,
                "stream": False
            }
        elif self.provider == "nim":
            return {
                "model": self.model,
                "messages": messages,
                "max_tokens": settings.max_tokens,
                "temperature": settings.temperature,
                "stream": False
            }
        elif self.provider == "google":
            # Google Gemini has different format
            google_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    # Google doesn't have system role, prepend to first user message
                    if google_messages and google_messages[-1]["role"] == "user":
                        google_messages[-1]["parts"][0]["text"] = f"{msg['content']}\n\n{google_messages[-1]['parts'][0]['text']}"
                    else:
                        # Add as first user message
                        google_messages.append({
                            "role": "user",
                            "parts": [{"text": msg["content"]}]
                        })
                else:
                    google_messages.append({
                        "role": "user" if msg["role"] == "user" else "model",
                        "parts": [{"text": msg["content"]}]
                    })
            
            return {
                "contents": google_messages,
                "generationConfig": {
                    "maxOutputTokens": settings.max_tokens,
                    "temperature": settings.temperature
                }
            }
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text using the configured free LLM API"""
        
        # Ensure we have a session
        await self._ensure_session()
        
        # Rate limiting
        await self.rate_limiter.wait_if_needed()
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request data
        url = self._get_provider_url()
        data = self._format_messages_for_provider(messages)
        
        # Update with any additional kwargs
        data.update(kwargs)
        
        try:
            logger.debug(f"Sending request to {self.provider} with model {self.model}")
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API Error {response.status}: {error_text}")
                    raise Exception(f"API returned status {response.status}")
                
                result = await response.json()
                
                # Parse response based on provider
                if self.provider == "openrouter":
                    content = result["choices"][0]["message"]["content"]
                    finish_reason = result["choices"][0]["finish_reason"]
                    
                elif self.provider == "nim":
                    content = result["choices"][0]["message"]["content"]
                    finish_reason = result["choices"][0]["finish_reason"]
                    
                elif self.provider == "google":
                    content = result["candidates"][0]["content"]["parts"][0]["text"]
                    finish_reason = result["candidates"][0]["finishReason"]
                
                logger.debug(f"Generated {len(content)} characters with finish reason: {finish_reason}")
                return content
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {e}")
            # Close the session on error to force a new one on next request
            await self.close()
            raise
        except KeyError as e:
            logger.error(f"Unexpected response format: {e}")
            logger.debug(f"Response: {result if 'result' in locals() else 'No result'}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            # Close the session on error
            await self.close()
            raise
    
    async def generate_structured_content(self, prompt: str, output_format: str = "json") -> Dict:
        """Generate structured content with format instructions"""
        
        format_instructions = {
            "json": "Return a valid JSON object.",
            "markdown": "Return well-formatted markdown.",
            "yaml": "Return valid YAML.",
            "xml": "Return valid XML."
        }
        
        structured_prompt = f"""{prompt}

Please respond in the following format:
{format_instructions.get(output_format.lower(), "Return structured text.")}

Ensure your response is complete and follows the requested format."""
        
        response = await self.generate_text(structured_prompt)
        
        # Try to parse if JSON is requested
        if output_format.lower() == "json":
            try:
                # Try to find JSON in response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    # Return as-is
                    return {"raw": response}
            except json.JSONDecodeError:
                return {"raw": response}
        
        return {"raw": response}