"""
LLM-as-Judge evaluator using Llama for independent evaluation.
"""
import os
import json
import re
from typing import Dict, Optional
from dotenv import load_dotenv
import yaml

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.models.experiment import EvaluationScores
from src.api.openrouter_client import OpenRouterClient

load_dotenv()


class LLMJudgeEvaluator:
    """Evaluator using LLM-as-Judge approach with Llama."""
    
    def __init__(self, judge_model: Optional[str] = None, judge_temperature: Optional[float] = None):
        """
        Initialize evaluator.
        
        Args:
            judge_model: Model to use as judge (defaults to Llama from env)
            judge_temperature: Temperature for judge model (defaults to 0.0 or from JUDGE_TEMPERATURE env)
        """
        self.judge_model = judge_model or os.getenv("JUDGE_MODEL", "meta-llama/llama-3.1-70b-instruct")
        self.judge_temperature = judge_temperature if judge_temperature is not None else float(os.getenv("JUDGE_TEMPERATURE", "0.0"))
        self.client = OpenRouterClient()
        self._load_evaluation_config()
    
    def _load_evaluation_config(self):
        """Load evaluation rubric and prompt template."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "config",
            "evaluation.yaml"
        )
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.prompt_template = self.config["judge_prompt_template"]
    
    def evaluate_response(
        self,
        scenario_name: str,
        scenario_description: str,
        role_name: str,
        response_text: str,
        temperature: Optional[float] = None
    ) -> EvaluationScores:
        """
        Evaluate a response using LLM-as-Judge.
        
        Args:
            scenario_name: Name of the scenario
            scenario_description: Full scenario description
            role_name: Name of the role framing used
            response_text: The response text to evaluate
            temperature: Temperature for judge model (defaults to self.judge_temperature)
        
        Returns:
            EvaluationScores object
        """
        if temperature is None:
            temperature = self.judge_temperature
        
        prompt = self.prompt_template
        prompt = prompt.replace("{scenario_name}", str(scenario_name))
        prompt = prompt.replace("{role_name}", str(role_name))
        prompt = prompt.replace("{scenario_description}", str(scenario_description))
        prompt = prompt.replace("{response_text}", str(response_text))
        
        system_prompt = (
            "You are an expert evaluator assessing decision-making quality. "
            "Provide objective, consistent evaluations based on the rubric. "
            "Always respond with valid JSON in the exact format specified."
        )
        
        try:
            judge_response = self.client.generate_response(
                model=self.judge_model,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=256
            )
            
            if not judge_response or len(judge_response.strip()) == 0:
                raise ValueError("Empty response from judge model")
            
            # Extract JSON from response
            json_text = self._extract_json(judge_response)
            
            if not json_text or len(json_text.strip()) == 0:
                raise ValueError("Could not extract JSON from judge response")
            
            try:
                evaluation_data = json.loads(json_text)
            except json.JSONDecodeError as json_err:
                raise ValueError(f"Invalid JSON in judge response: {str(json_err)}") from json_err
            
            # Validate required fields
            required_fields = ["rationality", "comprehensiveness", "analytical_depth", "integrity", "bias_mitigation"]
            missing_fields = [field for field in required_fields if field not in evaluation_data]
            if missing_fields:
                raise ValueError(f"Missing required fields in evaluation: {missing_fields}")
            
            return EvaluationScores(
                rationality=float(evaluation_data["rationality"]),
                comprehensiveness=float(evaluation_data["comprehensiveness"]),
                analytical_depth=float(evaluation_data["analytical_depth"]),
                integrity=float(evaluation_data["integrity"]),
                bias_mitigation=float(evaluation_data["bias_mitigation"]),
                overall_justification=evaluation_data.get("overall_justification", "")
            )
        
        except ValueError as e:
            return EvaluationScores(
                rationality=3.0,
                comprehensiveness=3.0,
                analytical_depth=3.0,
                integrity=3.0,
                bias_mitigation=3.0,
                overall_justification=f"Evaluation error: {str(e)}"
            )
        except Exception as e:
            return EvaluationScores(
                rationality=3.0,
                comprehensiveness=3.0,
                analytical_depth=3.0,
                integrity=3.0,
                bias_mitigation=3.0,
                overall_justification=f"Evaluation error: {str(e)}"
            )
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text, handling markdown code blocks.
        """
        if not text:
            return ""
        
        # Try to find JSON in code blocks (more flexible pattern)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Try to find JSON object directly (greedy match for nested objects)
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # Try a more aggressive pattern for JSON
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return ""