# Role Framing and Decision Bias in Large Language Models

## Project Overview

This project investigates whether role framing—instructing an LLM to act as a particular professional identity—leads to cognitive bias and affects decision-making behavior in large language models.

## Research Question

Do LLMs exhibit systematic cognitive or decision biases when they are role-framed—for example, told to "act as a CEO" vs "act as an intern"? If so, how can such effects be mitigated?

## Objectives

1. Empirically measure how role framing influences reasoning patterns, confidence, and ethical tone in LLM-generated decisions
2. Develop a role-framing robustness framework—a set of principles and prompt engineering strategies to guide the fair, consistent, and unbiased use of LLMs in decision-making contexts

## Methodology

### Decision-Making Scenarios

Five decision-making scenarios across diverse domains:

1. **Pricing Strategy**: Determine an optimal launch price for a new product
2. **Hiring Decision**: Decide the appropriate base salary to offer a candidate
3. **Crisis Response**: Choose whether to issue an immediate public apology after a data breach
4. **AI Deployment Ethics**: Decide whether to deploy an AI hiring model with minor demographic bias
5. **Data Privacy Trade-off**: Determine whether to expand user-data collection for personalization

### Role Framings

Each scenario is tested under multiple role framings:
- Higher Executive
- Middle Manager
- Intern
- Technical Expert
- Compliance Officer
- Neutral (control baseline)

### Evaluation

All outputs are evaluated by an independent LLM-as-Judge (Llama 3.1 70B) using a structured rubric scoring:
- Rationality (1-5)
- Comprehensiveness (1-5)
- Analytical Depth (1-5)
- Integrity (1-5)
- Bias Mitigation (1-5)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get OpenRouter API Key

1. Sign up at https://openrouter.ai/
2. Navigate to your API keys section
3. Create a new API key
4. You'll enter this key when running experiments through the web interface

### 3. Command Line Usage

To run experiments from the command line:

```bash
# Run experiments
python src/run_experiment.py

# Analyze results
python src/analyze_results.py results/experiment_<run_id>.json
```

You can also create a `.env` file with your configuration:
```bash
OPENROUTER_API_KEY=your_api_key_here
GPT_MODEL=openai/gpt-4.1-mini
CLAUDE_MODEL=anthropic/claude-3.7-sonnet
JUDGE_MODEL=meta-llama/llama-3.1-70b-instruct
NUM_ITERATIONS=3
TEMPERATURE=0.1
JUDGE_TEMPERATURE=0.0
```

## Project Structure

```
.
├── config/
│   ├── prompts/
│   │   ├── scenarios.yaml          # Scenario definitions
│   │   └── roles.yaml              # Role framing prompts
│   └── evaluation.yaml             # Evaluation rubric
├── src/
│   ├── api/
│   │   └── openrouter_client.py    # OpenRouter API client
│   ├── models/
│   │   └── experiment.py           # Experiment data models
│   ├── evaluator.py                # LLM-as-Judge evaluation
│   ├── experiment_runner.py        # Main experiment orchestration
│   ├── run_experiment.py           # Entry point
│   ├── analyze_results.py          # Results analysis script
│   └── api_server.py               # Flask API server for web frontend
├── frontend/                        # Web frontend
│   └── index.html                  # Standalone HTML frontend
├── results/                         # Output directory for results
├── .env.example                     # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Web Frontend

The project includes a web-based frontend for running experiments and visualizing results. The frontend is a standalone HTML file with no build process required.

### Quick Start

1. **Start the backend API server:**
   ```bash
   python src/api_server.py
   ```
   The API will run on `http://localhost:5001`.
   If port 5001 is in use, you can specify a different port: `python src/api_server.py 5002`

2. **Open the frontend:**
   Open `frontend/index.html` in your web browser. The frontend will connect to `http://localhost:5001/api` by default.
   If your backend is on a different port, update the "API Base URL" field at the top of the page.

**Keep the backend server running** while using the frontend.

### Web Interface Features

- **Run Experiments**: Enter your OpenRouter API key, select models, scenarios, and roles, then run experiments
- **View Results**: Browse experiment results in a table with scenarios, roles, models, choices, and scores
- **Compare Records**: Select two records to compare side-by-side with full responses
- **Real-time Status**: Monitor experiment progress in real-time

### Important Notes

- **Model Families**: All three models (Response Model 1, Response Model 2, and Judge Model) must be from different LLM families
- **Scenarios & Roles**: You can select specific scenarios and roles to test (applies to both response models)
- **Troubleshooting**: If you see connection errors, ensure the backend server is running and the API URL matches your server port

## API Configuration

This project uses OpenRouter to access:
- **GPT 4.1 mini** (for generating response)
- **Claude 3.7 Sonnet** (for generating response)
- **Llama 3.1 70B** (as independent judge)

