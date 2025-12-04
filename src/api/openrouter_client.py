"""
OpenRouter API Client for accessing GPT, Claude, and Gemini models.
"""
import os
import json
import time
import requests
from requests.exceptions import ChunkedEncodingError, ReadTimeout, RequestException
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class OpenRouterClient:
    """Client for interacting with OpenRouter API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key. If None, reads from OPENROUTER_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable.")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional: for analytics
        }
    
    def chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a chat completion request to OpenRouter.
        
        Args:
            model: Model identifier (e.g., "openai/gpt-4-turbo-preview")
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API
        
        Returns:
            API response dictionary
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        # Retry logic for transient network errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Increase timeout for retry attempts to handle slow responses
                timeout = 180 if attempt > 0 else 120
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=timeout
                )
                break  # Success, exit retry loop
            except (ChunkedEncodingError, ReadTimeout, RequestException) as e:
                if attempt == max_retries - 1:
                    # Final attempt failed
                    raise ValueError(
                        f"Network error after {max_retries} attempts: {str(e)}\n"
                        f"This is likely a transient connection issue. Try rerunning the experiment."
                    ) from e
                # Exponential backoff: 2s, 4s, 8s
                wait_time = 2 ** (attempt + 1)
                time.sleep(wait_time)
                continue
        
        # Better error handling for 400 errors
        if response.status_code == 400:
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                error_type = error_data.get("error", {}).get("type", "Bad Request")
                raise ValueError(
                    f"OpenRouter API 400 Bad Request: {error_type}\n"
                    f"Error message: {error_message}\n"
                    f"Model: {model}\n"
                    f"Check if the model name is correct and parameters are valid."
                )
            except (json.JSONDecodeError, KeyError):
                raise ValueError(
                    f"OpenRouter API 400 Bad Request\n"
                    f"Response: {response.text[:500]}\n"
                    f"Model: {model}\n"
                    f"Payload: {json.dumps(payload, indent=2)[:500]}"
                )
        
        response.raise_for_status()
        return response.json()
    
    def get_response_text(self, response: Dict[str, Any]) -> str:
        """
        Extract the response text from API response.
        
        Args:
            response: API response dictionary
        
        Returns:
            Response text content
        """
        return response["choices"][0]["message"]["content"]
    
    def generate_response(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate a response from a model given a prompt.
        
        Args:
            model: Model identifier
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated response text
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return self.get_response_text(response)


# Convenience functions for specific models
def get_gpt_client(api_key: Optional[str] = None) -> OpenRouterClient:
    """Get OpenRouter client configured for GPT models."""
    return OpenRouterClient(api_key)


def get_claude_client(api_key: Optional[str] = None) -> OpenRouterClient:
    """Get OpenRouter client configured for Claude models."""
    return OpenRouterClient(api_key)


def get_gemini_client(api_key: Optional[str] = None) -> OpenRouterClient:
    """Get OpenRouter client configured for Gemini models."""
    return OpenRouterClient(api_key)

