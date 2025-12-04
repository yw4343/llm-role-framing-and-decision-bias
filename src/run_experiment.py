"""
Entry point for running role framing experiments.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.experiment_runner import ExperimentRunner


def main():
    """Main entry point for experiments."""
    # Ensure results directory exists
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    # Initialize runner
    runner = ExperimentRunner()
    
    # Run experiment
    print("=" * 60)
    print("Role Framing and Decision Bias Experiment")
    print("=" * 60)
    print()
    
    experiment_run = runner.run_experiment()
    
    # Save results
    output_file = results_dir / f"experiment_{experiment_run.run_id[:8]}.json"
    experiment_run.to_json(str(output_file))
    
    print()
    print("=" * 60)
    print(f"Experiment completed!")
    print(f"Results saved to: {output_file}")
    print(f"Total responses: {len(experiment_run.responses)}")
    print("=" * 60)
    
    # Print summary statistics
    if experiment_run.responses:
        print("\nSummary Statistics:")
        print("-" * 60)
        
        # Group by scenario and role
        from collections import defaultdict
        scores_by_combo = defaultdict(list)
        
        for response in experiment_run.responses:
            if response.evaluation:
                key = (response.scenario_id, response.role_id, response.model)
                scores_by_combo[key].append(response.evaluation.average_score())
        
        # Print average scores
        for (scenario, role, model), scores in sorted(scores_by_combo.items()):
            avg_score = sum(scores) / len(scores)
            print(f"{scenario[:20]:20} | {role[:20]:20} | {model.split('/')[-1][:20]:20} | Avg: {avg_score:.2f}")


if __name__ == "__main__":
    main()

