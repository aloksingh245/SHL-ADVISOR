#!/bin/bash

# SHL Advisor - All-in-One Start Script

# Check for API Key
if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY is not set."
    echo "Please run: export GEMINI_API_KEY='your-api-key' and try again."
    exit 1
fi

echo "--- Starting SHL Advisor System ---"

# 1. Start Backend in background
echo "Starting Backend..."
source venv/bin/activate
python3 run_backend.py &
BACKEND_PID=$!

# 2. Start Frontend
echo "Starting Frontend..."
cd frontend
npm start

# When frontend stops, kill backend
kill $BACKEND_PID
