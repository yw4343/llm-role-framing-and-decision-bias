#!/bin/bash

# Start script for the LLM Role Framing Experiment Web Interface

echo "Starting LLM Role Framing Experiment Web Interface..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies if needed
echo "Checking Python dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Starting backend API server on http://localhost:5001..."
python src/api_server.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

echo ""
echo "Backend API server is running on http://localhost:5001"
echo ""
echo "To use the frontend:"
echo "1. Open frontend/index.html in your web browser"
echo "2. Or navigate to: file://$(pwd)/frontend/index.html"
echo ""
echo "Press Ctrl+C to stop the backend server"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping backend server..."
    kill $BACKEND_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
