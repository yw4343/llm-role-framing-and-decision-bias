"""
Analysis script for experiment results.
"""
import sys
import re
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.experiment import ExperimentRun


def extract_choice(response_text: str) -> str:
    """
    Extract the choice (A, B, C, or D) from model response text.
    Looks for "Choice: Option A" format first, then falls back to other patterns.
    
    Args:
        response_text: The full response text from the model
        
    Returns:
        The extracted choice letter (A, B, C, or D), or empty string if not found
    """
    if not response_text:
        return ""
    
    text = response_text.strip()
    
    # Primary pattern: "Choice: Option A" format
    pattern1 = r'Choice:\s*Option\s+([ABCD])'
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Fallback patterns for other formats
    pattern2 = r'\b([ABCD])\s*\)'
    match = re.search(pattern2, text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    pattern3 = r'(?:option|choice|select|answer|decision|recommendation|choose)\s+([ABCD])'
    match = re.search(pattern3, text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    return ""

def analyze_experiment(results_file: str):
    """
    Analyze experiment results and generate summary statistics.
    
    Args:
        results_file: Path to experiment results JSON file
    """
    # Load experiment run
    experiment_run = ExperimentRun.from_json(results_file)
    
    print("=" * 80)
    print(f"Experiment Analysis: {experiment_run.run_id}")
    print(f"Timestamp: {experiment_run.timestamp}")
    print("=" * 80)
    print()
    
    # Collect data for analysis
    data = []
    for response in experiment_run.responses:
        if response.evaluation:
            choice = extract_choice(response.response)
            data.append({
                "scenario": response.scenario_id,
                "role": response.role_id,
                "model": response.model.split("/")[-1],
                "iteration": response.iteration,
                "choice": choice,
                "rationality": response.evaluation.rationality,
                "comprehensiveness": response.evaluation.comprehensiveness,
                "analytical_depth": response.evaluation.analytical_depth,
                "integrity": response.evaluation.integrity,
                "bias_mitigation": response.evaluation.bias_mitigation,
                "average_score": response.evaluation.average_score()
            })
    
    if not data:
        print("No evaluation data found.")
        return
    
    df = pd.DataFrame(data)
    
    # Summary statistics by scenario and role
    print("Summary Statistics by Scenario and Role")
    print("-" * 80)
    summary = df.groupby(["scenario", "role", "model"])["average_score"].agg([
        "mean", "std", "count"
    ]).round(2)
    print(summary)
    print()
    
    # Average scores by role (across all scenarios)
    print("Average Scores by Role (across all scenarios)")
    print("-" * 80)
    role_scores = df.groupby(["role", "model"])["average_score"].mean().unstack(fill_value=0)
    print(role_scores.round(2))
    print()
    
    # Average scores by scenario (across all roles)
    print("Average Scores by Scenario (across all roles)")
    print("-" * 80)
    scenario_scores = df.groupby(["scenario", "model"])["average_score"].mean().unstack(fill_value=0)
    print(scenario_scores.round(2))
    print()
    
    # Dimension analysis
    print("Average Scores by Dimension")
    print("-" * 80)
    dimensions = ["rationality", "comprehensiveness", "analytical_depth", "integrity", "bias_mitigation"]
    for dim in dimensions:
        print(f"\n{dim.replace('_', ' ').title()}:")
        dim_scores = df.groupby(["role", "model"])[dim].mean().unstack(fill_value=0)
        print(dim_scores.round(2))
    
    # Role comparison (role vs neutral baseline)
    print("\n" + "=" * 80)
    print("Role Comparison vs Neutral Baseline")
    print("-" * 80)
    
    neutral_scores = df[df["role"] == "neutral"].groupby(["scenario", "model"])["average_score"].mean()
    
    for role in df["role"].unique():
        if role == "neutral":
            continue
        role_scores = df[df["role"] == role].groupby(["scenario", "model"])["average_score"].mean()
        
        print(f"\n{role.replace('_', ' ').title()}:")
        for (scenario, model), score in role_scores.items():
            neutral_score = neutral_scores.get((scenario, model), None)
            if neutral_score:
                diff = score - neutral_score
                print(f"  {scenario[:30]:30} | {model[:20]:20} | Score: {score:.2f} | Diff from neutral: {diff:+.2f}")
    
    # Save detailed CSV
    output_file = Path(results_file).parent / f"analysis_{experiment_run.run_id[:8]}.csv"
    df.to_csv(output_file, index=False)
    print(f"\nDetailed data saved to: {output_file}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py <results_file.json>")
        print("\nExample:")
        print("  python src/analyze_results.py results/experiment_abc12345.json")
        sys.exit(1)
    
    results_file = sys.argv[1]
    if not Path(results_file).exists():
        print(f"Error: File not found: {results_file}")
        sys.exit(1)
    
    analyze_experiment(results_file)


if __name__ == "__main__":
    main()

