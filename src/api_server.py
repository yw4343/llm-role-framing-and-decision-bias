"""
Flask API server for running experiments and retrieving results.
"""
import os
import sys
import re
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import threading
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.experiment_runner import ExperimentRunner
from src.models.experiment import ExperimentRun, ExperimentResponse

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Store running experiments
running_experiments = {}
experiment_status = {}
experiment_stop_flags = {}  # Track stop requests

def extract_choice(response_text: str) -> str:
    """Extract the choice (A, B, C, or D) from model response text."""
    if not response_text:
        return ""
    
    text = response_text.strip()
    
    # Primary pattern: "Choice: Option A" format
    pattern1 = r'Choice:\s*Option\s+([ABCD])'
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Fallback patterns
    pattern2 = r'\b([ABCD])\s*\)'
    match = re.search(pattern2, text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    pattern3 = r'(?:option|choice|select|answer|decision|recommendation|choose)\s+([ABCD])'
    match = re.search(pattern3, text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    return ""

def run_experiment_async(env_vars: dict, experiment_id: str):
    """Run experiment in a separate thread."""
    try:
        experiment_status[experiment_id] = {"status": "initializing", "progress": 0, "total": 0, "current": 0, "error": None, "message": "Initializing..."}
        experiment_stop_flags[experiment_id] = False
        
        # Set environment variables
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            if key not in ['SCENARIOS', 'ROLES']:
                os.environ[key] = str(value)
        
        try:
            # Set environment variables before initializing runner
            # Map RESPONSE_MODEL_1 and RESPONSE_MODEL_2 to GPT_MODEL and CLAUDE_MODEL
            if os.getenv("RESPONSE_MODEL_1"):
                os.environ["GPT_MODEL"] = os.getenv("RESPONSE_MODEL_1")
            if os.getenv("RESPONSE_MODEL_2"):
                os.environ["CLAUDE_MODEL"] = os.getenv("RESPONSE_MODEL_2")
            if os.getenv("RESPONSE_TEMPERATURE"):
                os.environ["TEMPERATURE"] = os.getenv("RESPONSE_TEMPERATURE")
            
            # Initialize runner (it will read from env vars)
            runner = ExperimentRunner()
            
            # Override runner config with env vars if needed
            runner.gpt_model = os.getenv("GPT_MODEL", runner.gpt_model)
            runner.claude_model = os.getenv("CLAUDE_MODEL", runner.claude_model)
            runner.num_iterations = int(os.getenv("NUM_ITERATIONS", runner.num_iterations))
            runner.temperature = float(os.getenv("TEMPERATURE", runner.temperature))
            
            if os.getenv("JUDGE_MODEL"):
                runner.evaluator.judge_model = os.getenv("JUDGE_MODEL")
            if os.getenv("JUDGE_TEMPERATURE"):
                runner.evaluator.judge_temperature = float(os.getenv("JUDGE_TEMPERATURE"))
            
            # Get shared scenarios and roles (same for both models)
            scenarios = env_vars.get('SCENARIOS', list(runner.scenarios.keys()))
            roles = env_vars.get('ROLES', list(runner.roles.keys()))
            
            # Calculate total
            models = [runner.gpt_model, runner.claude_model]
            total_experiments = len(models) * len(scenarios) * len(roles) * runner.num_iterations
            experiment_status[experiment_id]["total"] = total_experiments
            experiment_status[experiment_id]["status"] = "running"
            experiment_status[experiment_id]["message"] = "Starting experiment..."
            
            # Check if stopped before starting
            if experiment_stop_flags.get(experiment_id, False):
                experiment_status[experiment_id] = {
                    "status": "stopped",
                    "progress": 0,
                    "error": "Experiment was stopped by user"
                }
                return
            
            # Run experiment with progress tracking
            experiment_run = runner.run_experiment_with_progress(
                models=models,
                scenarios=scenarios,
                roles=roles,
                progress_callback=lambda current, total, message: update_progress(experiment_id, current, total, message),
                stop_flag=lambda: experiment_stop_flags.get(experiment_id, False)
            )
            
            # Check if stopped during execution
            if experiment_stop_flags.get(experiment_id, False):
                experiment_status[experiment_id] = {
                    "status": "stopped",
                    "progress": experiment_status[experiment_id].get("progress", 0),
                    "error": "Experiment was stopped by user"
                }
                return
            
            # Update config to include selected scenarios/roles (already included by run_experiment, but ensure they're there)
            experiment_run.config['scenarios'] = scenarios
            experiment_run.config['roles'] = roles
            
            # Save results
            results_dir = project_root / "results"
            results_dir.mkdir(exist_ok=True)
            output_file = results_dir / f"experiment_{experiment_run.run_id[:8]}.json"
            experiment_run.to_json(str(output_file))
            
            experiment_status[experiment_id] = {
                "status": "completed",
                "progress": 100,
                "total": total_experiments,
                "current": total_experiments,
                "run_id": experiment_run.run_id,
                "output_file": str(output_file),
                "error": None,
                "message": "Completed successfully"
            }
        finally:
            # Restore original environment variables
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
                    
    except Exception as e:
        experiment_status[experiment_id] = {
            "status": "error",
            "progress": experiment_status.get(experiment_id, {}).get("progress", 0),
            "error": str(e)
        }

def update_progress(experiment_id: str, current: int, total: int, message: str = ""):
    """Update progress for an experiment."""
    if experiment_id in experiment_status:
        progress = int((current / total * 100)) if total > 0 else 0
        experiment_status[experiment_id].update({
            "progress": progress,
            "current": current,
            "total": total,
            "message": message or f"Processing {current} of {total}"
        })

@app.route('/api/experiments/run', methods=['POST'])
def run_experiment():
    """Run a new experiment with provided environment variables."""
    data = request.json
    
    required_fields = ['OPENROUTER_API_KEY', 'RESPONSE_MODEL_1', 'RESPONSE_MODEL_2', 'JUDGE_MODEL']
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
    
    # Validate that models are from different families
    model1_family = data['RESPONSE_MODEL_1'].split('/')[0].lower()
    model2_family = data['RESPONSE_MODEL_2'].split('/')[0].lower()
    judge_family = data['JUDGE_MODEL'].split('/')[0].lower()
    
    families = set([model1_family, model2_family, judge_family])
    if len(families) < 3:
        return jsonify({
            "error": "All three models must be from different LLM families. "
                     f"Found families: {families}"
        }), 400
    
    # Generate experiment ID
    experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    # Start experiment in background thread
    env_vars = {
        'OPENROUTER_API_KEY': data['OPENROUTER_API_KEY'],
        'RESPONSE_MODEL_1': data['RESPONSE_MODEL_1'],
        'RESPONSE_MODEL_2': data['RESPONSE_MODEL_2'],
        'JUDGE_MODEL': data['JUDGE_MODEL'],
        'SCENARIOS': data.get('SCENARIOS', []),
        'ROLES': data.get('ROLES', []),
        'NUM_ITERATIONS': data.get('NUM_ITERATIONS', 3),
        'RESPONSE_TEMPERATURE': data.get('RESPONSE_TEMPERATURE', 0.1),
        'JUDGE_TEMPERATURE': data.get('JUDGE_TEMPERATURE', 0.0),
    }
    
    # Validate scenarios and roles are provided
    if not env_vars['SCENARIOS'] or not env_vars['ROLES']:
        return jsonify({"error": "Please select at least one scenario and role"}), 400
    
    thread = threading.Thread(target=run_experiment_async, args=(env_vars, experiment_id))
    thread.daemon = True
    thread.start()
    
    running_experiments[experiment_id] = thread
    
    return jsonify({
        "experiment_id": experiment_id,
        "status": "started"
    }), 200

@app.route('/api/experiments/<experiment_id>/status', methods=['GET'])
def get_experiment_status(experiment_id):
    """Get the status of a running experiment."""
    if experiment_id not in experiment_status:
        return jsonify({"error": "Experiment not found"}), 404
    
    return jsonify(experiment_status[experiment_id]), 200

@app.route('/api/experiments/<experiment_id>/stop', methods=['POST'])
def stop_experiment(experiment_id):
    """Stop a running experiment."""
    if experiment_id not in experiment_status:
        return jsonify({"error": "Experiment not found"}), 404
    
    status = experiment_status[experiment_id].get("status")
    if status not in ["running", "initializing"]:
        return jsonify({"error": f"Cannot stop experiment with status: {status}"}), 400
    
    # Set stop flag
    experiment_stop_flags[experiment_id] = True
    experiment_status[experiment_id]["status"] = "stopping"
    experiment_status[experiment_id]["message"] = "Stopping experiment..."
    
    return jsonify({"message": "Stop request received", "experiment_id": experiment_id}), 200

@app.route('/api/experiments', methods=['GET'])
def list_experiments():
    """List all completed experiments."""
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)
    
    experiment_files = list(results_dir.glob("experiment_*.json"))
    experiments = []
    
    for exp_file in sorted(experiment_files, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            experiment_run = ExperimentRun.from_json(str(exp_file))
            experiments.append({
                "run_id": experiment_run.run_id,
                "timestamp": experiment_run.timestamp,
                "filename": exp_file.name,
                "num_responses": len(experiment_run.responses)
            })
        except Exception as e:
            continue
    
    return jsonify(experiments), 200

@app.route('/api/experiments/<run_id>/results', methods=['GET'])
def get_experiment_results(run_id):
    """Get results for a specific experiment."""
    results_dir = project_root / "results"
    
    # Try to find the experiment file
    exp_file = results_dir / f"experiment_{run_id[:8]}.json"
    if not exp_file.exists():
        # Try to find by full run_id
        for file in results_dir.glob("experiment_*.json"):
            try:
                exp_run = ExperimentRun.from_json(str(file))
                if exp_run.run_id == run_id:
                    exp_file = file
                    break
            except:
                continue
    
    if not exp_file.exists():
        return jsonify({"error": "Experiment not found"}), 404
    
    try:
        experiment_run = ExperimentRun.from_json(str(exp_file))
        
        # Convert to table format (similar to CSV output)
        data = []
        for response in experiment_run.responses:
            if response.evaluation:
                choice = extract_choice(response.response)
                data.append({
                    "id": f"{response.scenario_id}_{response.role_id}_{response.model}_{response.iteration}",
                    "scenario": response.scenario_id,
                    "role": response.role_id,
                    "model": response.model.split("/")[-1],
                    "full_model": response.model,
                    "iteration": response.iteration,
                    "choice": choice,
                    "rationality": response.evaluation.rationality,
                    "comprehensiveness": response.evaluation.comprehensiveness,
                    "analytical_depth": response.evaluation.analytical_depth,
                    "integrity": response.evaluation.integrity,
                    "bias_mitigation": response.evaluation.bias_mitigation,
                    "average_score": response.evaluation.average_score(),
                    "response": response.response,
                    "prompt": response.prompt,
                    "timestamp": response.timestamp
                })
        
        return jsonify({
            "run_id": experiment_run.run_id,
            "timestamp": experiment_run.timestamp,
            "config": experiment_run.config,
            "results": data
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error loading experiment: {str(e)}"}), 500

@app.route('/api/experiments/<run_id>/response/<path:response_id>', methods=['GET'])
def get_response_detail(run_id, response_id):
    """Get detailed information about a specific response."""
    results_dir = project_root / "results"
    
    # Try to find the experiment file
    exp_file = results_dir / f"experiment_{run_id[:8]}.json"
    if not exp_file.exists():
        # Try to find by full run_id
        for file in results_dir.glob("experiment_*.json"):
            try:
                exp_run = ExperimentRun.from_json(str(file))
                if exp_run.run_id == run_id:
                    exp_file = file
                    break
            except:
                continue
    
    if not exp_file.exists():
        return jsonify({"error": "Experiment not found"}), 404
    
    try:
        experiment_run = ExperimentRun.from_json(str(exp_file))
        
        # URL decode the response_id in case it was encoded
        from urllib.parse import unquote
        decoded_response_id = unquote(response_id)
        
        for response in experiment_run.responses:
            response_key = f"{response.scenario_id}_{response.role_id}_{response.model}_{response.iteration}"
            if response_key == decoded_response_id:
                choice = extract_choice(response.response)
                return jsonify({
                    "id": response_key,
                    "scenario": response.scenario_id,
                    "role": response.role_id,
                    "model": response.model.split("/")[-1],
                    "full_model": response.model,
                    "iteration": response.iteration,
                    "choice": choice,
                    "response": response.response,
                    "prompt": response.prompt,
                    "evaluation": response.evaluation.to_dict() if response.evaluation else None,
                    "timestamp": response.timestamp
                }), 200
        
        return jsonify({"error": f"Response not found. Looking for: {decoded_response_id}"}), 404
    except Exception as e:
        return jsonify({"error": f"Error loading response: {str(e)}"}), 500

@app.route('/api/experiments/<run_id>/download', methods=['GET'])
def download_experiment(run_id):
    """Download the JSON file for a completed experiment."""
    results_dir = project_root / "results"
    
    # Try to find the experiment file
    exp_file = results_dir / f"experiment_{run_id[:8]}.json"
    if not exp_file.exists():
        # Try to find by full run_id
        for file in results_dir.glob("experiment_*.json"):
            try:
                exp_run = ExperimentRun.from_json(str(file))
                if exp_run.run_id == run_id:
                    exp_file = file
                    break
            except:
                continue
    
    if not exp_file.exists():
        return jsonify({"error": "Experiment not found"}), 404
    
    try:
        # Send the file with appropriate headers
        return send_file(
            str(exp_file),
            mimetype='application/json',
            as_attachment=True,
            download_name=exp_file.name
        )
    except Exception as e:
        return jsonify({"error": f"Error downloading experiment: {str(e)}"}), 500

if __name__ == '__main__':
    import sys
    # Try port 5001 first (5000 is often used by AirPlay on macOS)
    port = 5001
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    print("=" * 60)
    print("Starting Flask API Server")
    print("=" * 60)
    print(f"Server running on: http://localhost:{port}")
    print(f"API endpoint: http://localhost:{port}/api")
    print("=" * 60)
    print("\nMake sure to keep this server running while using the frontend.")
    print("If port 5001 is in use, you can specify a different port:")
    print("  python src/api_server.py 5002\n")
    
    try:
        app.run(debug=True, port=port, host='0.0.0.0')
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\nError: Port {port} is already in use.")
            print(f"Try running with a different port:")
            print(f"  python src/api_server.py {port + 1}")
            sys.exit(1)
        raise
