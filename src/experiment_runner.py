"""
Main experiment runner for role framing experiments.
"""
import os
import yaml
import uuid
from datetime import datetime
from typing import List, Dict
from tqdm import tqdm
from dotenv import load_dotenv

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.api.openrouter_client import OpenRouterClient
from src.models.experiment import ExperimentResponse, ExperimentRun
from src.evaluator import LLMJudgeEvaluator

load_dotenv()


class ExperimentRunner:
    """Orchestrates the role framing experiment."""
    
    def __init__(self):
        """Initialize experiment runner."""
        self.client = OpenRouterClient()
        self.evaluator = LLMJudgeEvaluator()
        self._load_configs()
        
        # Model configuration
        self.gpt_model = os.getenv("GPT_MODEL", "openai/gpt-4.1-mini")
        self.claude_model = os.getenv("CLAUDE_MODEL", "anthropic/claude-3.7-sonnet")
        self.num_iterations = int(os.getenv("NUM_ITERATIONS", "3"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.1"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1000"))
    
    def _load_configs(self):
        """Load scenario and role configurations."""
        base_path = os.path.join(os.path.dirname(__file__), "..", "config", "prompts")
        
        # Load scenarios
        scenarios_path = os.path.join(base_path, "scenarios.yaml")
        with open(scenarios_path, 'r') as f:
            scenarios_data = yaml.safe_load(f)
        self.scenarios = scenarios_data["scenarios"]
        
        # Load roles
        roles_path = os.path.join(base_path, "roles.yaml")
        with open(roles_path, 'r') as f:
            roles_data = yaml.safe_load(f)
        self.roles = roles_data["roles"]
    
    def _build_prompt(self, scenario: Dict, role: Dict) -> str:
        """
        Build the full prompt combining role framing and scenario.
        
        Args:
            scenario: Scenario dictionary with description
            role: Role dictionary with framing
        
        Returns:
            Complete prompt string
        """
        role_framing = role["framing"]
        scenario_description = scenario["description"]
        
        prompt = f"{role_framing}\n\n{scenario_description}"
        return prompt
    
    def _generate_response(
        self,
        model: str,
        prompt: str,
        iteration: int
    ) -> str:
        """
        Generate response from a model.
        
        Args:
            model: Model identifier
            prompt: Full prompt
            iteration: Iteration number
        
        Returns:
            Generated response
        """
        try:
            response = self.client.generate_response(
                model=model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response
        except Exception:
            # Let caller handle and surface detailed API or unexpected errors
            raise
    
    def run_experiment_with_progress(
        self,
        models: List[str] = None,
        scenarios: List[str] = None,
        roles: List[str] = None,
        progress_callback=None,
        stop_flag=None
    ) -> ExperimentRun:
        """
        Run the complete experiment with progress tracking and stop support.
        
        Args:
            models: List of model identifiers to use (defaults to GPT and Claude)
            scenarios: List of scenario IDs to test (defaults to all)
            roles: List of role IDs to test (defaults to all)
            progress_callback: Callback function(current, total, message) to update progress
            stop_flag: Callable that returns True if experiment should stop
        
        Returns:
            ExperimentRun object with all responses
        """
        if models is None:
            models = [self.gpt_model, self.claude_model]
        if scenarios is None:
            scenarios = list(self.scenarios.keys())
        if roles is None:
            roles = list(self.roles.keys())
        
        run_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        responses = []
        
        # Calculate total number of experiments
        total_experiments = len(models) * len(scenarios) * len(roles) * self.num_iterations
        total_with_eval = total_experiments  # Each response gets evaluated
        
        print(f"Starting experiment run: {run_id}")
        print(f"Models: {models}")
        print(f"Scenarios: {len(scenarios)}")
        print(f"Roles: {len(roles)}")
        print(f"Iterations per combination: {self.num_iterations}")
        print(f"Total experiments: {total_experiments}")
        print("-" * 60)
        
        current = 0
        with tqdm(total=total_with_eval, desc="Running experiments") as pbar:
            # Generate responses
            for model in models:
                if stop_flag and stop_flag():
                    break
                for scenario_id in scenarios:
                    if stop_flag and stop_flag():
                        break
                    scenario = self.scenarios[scenario_id]
                    for role_id in roles:
                        if stop_flag and stop_flag():
                            break
                        role = self.roles[role_id]
                        prompt = self._build_prompt(scenario, role)
                        
                        for iteration in range(1, self.num_iterations + 1):
                            if stop_flag and stop_flag():
                                break
                            
                            # Update progress
                            current += 1
                            message = f"Model: {model.split('/')[-1]}, Scenario: {scenario_id}, Role: {role_id}, Iteration: {iteration}"
                            if progress_callback:
                                progress_callback(current, total_with_eval, message)
                            
                            # Generate response
                            response_text = self._generate_response(
                                model=model,
                                prompt=prompt,
                                iteration=iteration
                            )
                            
                            if stop_flag and stop_flag():
                                break
                            
                            # Evaluate response
                            evaluation = self.evaluator.evaluate_response(
                                scenario_name=scenario["name"],
                                scenario_description=scenario["description"],
                                role_name=role["name"],
                                response_text=response_text
                            )
                            
                            # Store response
                            experiment_response = ExperimentResponse(
                                scenario_id=scenario_id,
                                role_id=role_id,
                                model=model,
                                iteration=iteration,
                                prompt=prompt,
                                response=response_text,
                                evaluation=evaluation
                            )
                            responses.append(experiment_response)
                            
                            pbar.update(1)
                            pbar.set_postfix({
                                "model": model.split("/")[-1],
                                "scenario": scenario_id,
                                "role": role_id,
                                "iter": iteration
                            })
        
        config = {
            "models": models,
            "scenarios": scenarios,
            "roles": roles,
            "num_iterations": self.num_iterations,
            "temperature": self.temperature,
            "judge_temperature": self.evaluator.judge_temperature,
            "max_tokens": self.max_tokens,
            "judge_model": self.evaluator.judge_model
        }
        
        experiment_run = ExperimentRun(
            run_id=run_id,
            timestamp=timestamp,
            config=config,
            responses=responses
        )
        
        return experiment_run
    
    def run_experiment(
        self,
        models: List[str] = None,
        scenarios: List[str] = None,
        roles: List[str] = None
    ) -> ExperimentRun:
        """
        Run the complete experiment.
        
        Args:
            models: List of model identifiers to use (defaults to GPT and Claude)
            scenarios: List of scenario IDs to test (defaults to all)
            roles: List of role IDs to test (defaults to all)
        
        Returns:
            ExperimentRun object with all responses
        """
        if models is None:
            models = [self.gpt_model, self.claude_model]
        if scenarios is None:
            scenarios = list(self.scenarios.keys())
        if roles is None:
            roles = list(self.roles.keys())
        
        run_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        responses = []
        
        # Calculate total number of experiments
        total_experiments = len(models) * len(scenarios) * len(roles) * self.num_iterations
        total_with_eval = total_experiments  # Each response gets evaluated
        
        print(f"Starting experiment run: {run_id}")
        print(f"Models: {models}")
        print(f"Scenarios: {len(scenarios)}")
        print(f"Roles: {len(roles)}")
        print(f"Iterations per combination: {self.num_iterations}")
        print(f"Total experiments: {total_experiments}")
        print("-" * 60)
        
        with tqdm(total=total_with_eval, desc="Running experiments") as pbar:
            # Generate responses
            for model in models:
                for scenario_id in scenarios:
                    scenario = self.scenarios[scenario_id]
                    for role_id in roles:
                        role = self.roles[role_id]
                        prompt = self._build_prompt(scenario, role)
                        
                        for iteration in range(1, self.num_iterations + 1):
                            # Generate response
                            response_text = self._generate_response(
                                model=model,
                                prompt=prompt,
                                iteration=iteration
                            )
                            
                            # Evaluate response
                            evaluation = self.evaluator.evaluate_response(
                                scenario_name=scenario["name"],
                                scenario_description=scenario["description"],
                                role_name=role["name"],
                                response_text=response_text
                            )
                            
                            # Store response
                            experiment_response = ExperimentResponse(
                                scenario_id=scenario_id,
                                role_id=role_id,
                                model=model,
                                iteration=iteration,
                                prompt=prompt,
                                response=response_text,
                                evaluation=evaluation
                            )
                            responses.append(experiment_response)
                            
                            pbar.update(1)
                            pbar.set_postfix({
                                "model": model.split("/")[-1],
                                "scenario": scenario_id,
                                "role": role_id,
                                "iter": iteration
                            })
        
        config = {
            "models": models,
            "scenarios": scenarios,
            "roles": roles,
            "num_iterations": self.num_iterations,
            "temperature": self.temperature,
            "judge_temperature": self.evaluator.judge_temperature,
            "max_tokens": self.max_tokens,
            "judge_model": self.evaluator.judge_model
        }
        
        experiment_run = ExperimentRun(
            run_id=run_id,
            timestamp=timestamp,
            config=config,
            responses=responses
        )
        
        return experiment_run

