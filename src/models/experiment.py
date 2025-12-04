"""
Data models for experiment structure.
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime
import json


@dataclass
class EvaluationScores:
    """Evaluation scores from LLM-as-Judge."""
    rationality: float
    comprehensiveness: float
    analytical_depth: float
    integrity: float
    bias_mitigation: float
    overall_justification: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def average_score(self) -> float:
        """Calculate average score across all dimensions."""
        return (
            self.rationality +
            self.comprehensiveness +
            self.analytical_depth +
            self.integrity +
            self.bias_mitigation
        ) / 5.0


@dataclass
class ExperimentResponse:
    """Response from a model for a given scenario and role."""
    scenario_id: str
    role_id: str
    model: str
    iteration: int
    prompt: str
    response: str
    evaluation: Optional[EvaluationScores] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = asdict(self)
        if self.evaluation:
            result["evaluation"] = self.evaluation.to_dict()
        return result


@dataclass
class ExperimentRun:
    """Complete experiment run with all responses."""
    run_id: str
    timestamp: str
    config: Dict
    responses: List[ExperimentResponse]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "config": self.config,
            "responses": [r.to_dict() for r in self.responses]
        }
    
    def to_json(self, filepath: str):
        """Save to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def from_json(cls, filepath: str) -> 'ExperimentRun':
        """Load from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        responses = [
            ExperimentResponse(
                scenario_id=r["scenario_id"],
                role_id=r["role_id"],
                model=r["model"],
                iteration=r["iteration"],
                prompt=r["prompt"],
                response=r["response"],
                evaluation=EvaluationScores(**r["evaluation"]) if r.get("evaluation") else None,
                timestamp=r.get("timestamp")
            )
            for r in data["responses"]
        ]
        
        return cls(
            run_id=data["run_id"],
            timestamp=data["timestamp"],
            config=data["config"],
            responses=responses
        )

