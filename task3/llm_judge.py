from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

# Import LLM client for judging
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from llm_client import get_llm_client

logger = logging.getLogger(__name__)

# prompt_version: v1.0
# changelog: initial version
JUDGE_SYSTEM_PROMPT = """You are an evaluator. Score this AI output against the criteria.

Output to evaluate: {actual_output}
Criteria: {expected_criteria}

Return JSON:
{{
  "score": 0.0 to 1.0,
  "reasoning": "why this score",
  "passed": true or false
}}"""


def llm_judge(actual_output: Any, expected_criteria: str) -> dict[str, Any]:
    """Evaluate AI output against criteria using LLM as judge.
    
    Args:
        actual_output: The actual output from the AI system
        expected_criteria: The criteria to evaluate against
        
    Returns:
        Dictionary with score, reasoning, and passed status
    """
    llm_client = get_llm_client()
    
    # Convert actual_output to string for evaluation
    if isinstance(actual_output, dict):
        actual_str = json.dumps(actual_output, indent=2)
    elif hasattr(actual_output, "model_dump"):
        actual_str = json.dumps(actual_output.model_dump(), indent=2)
    else:
        actual_str = str(actual_output)
    
    system_prompt = JUDGE_SYSTEM_PROMPT.format(
        actual_output=actual_str,
        expected_criteria=expected_criteria
    )
    
    user_prompt = "Evaluate the output against the criteria."
    
    try:
        result = llm_client.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=256,
            prompt_version="v1.0"
        )
        
        # Ensure result has required fields
        if "score" not in result:
            result["score"] = 0.5
        if "reasoning" not in result:
            result["reasoning"] = "No reasoning provided"
        if "passed" not in result:
            result["passed"] = result.get("score", 0) >= 0.8
        
        # Convert score to float if it's a string
        if isinstance(result["score"], str):
            try:
                result["score"] = float(result["score"])
            except ValueError:
                result["score"] = 0.5
        
        return result
        
    except Exception as e:
        logger.error(f"LLM judge failed: {e}")
        # Return a default judgment if LLM fails
        return {
            "score": 0.5,
            "reasoning": f"LLM judge failed: {e}",
            "passed": False
        }
