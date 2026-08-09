from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for LLM calls with consistent settings and error handling."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM client.
        
        Args:
            api_key: Groq API key. If None, reads from GROQ_API_KEY env var.
        """
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"
        self.temperature = 0.0
    
    def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        prompt_version: str = "v1.0",
    ) -> dict[str, Any]:
        """Call LLM with deterministic settings and error handling.
        
        Args:
            system_prompt: System prompt for the LLM
            user_prompt: User prompt for the LLM
            max_tokens: Maximum tokens in response
            prompt_version: Version identifier for the prompt (for logging)
            
        Returns:
            Parsed JSON response from LLM
            
        Raises:
            ValueError: If LLM response cannot be parsed as JSON
        """
        try:
            logger.info(f"LLM call with prompt_version: {prompt_version}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=max_tokens,
            )
            
            response_text = response.choices[0].message.content
            logger.debug(f"LLM raw response: {response_text}")
            
            try:
                parsed = json.loads(response_text)
                return parsed
            except json.JSONDecodeError:
                return {"text": response_text}
                
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise


_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
