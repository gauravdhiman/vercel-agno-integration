#!/bin/bash
# Script to start the server with automatic generation of frontend tools

# Change to the script directory
cd "$(dirname "$0")"

# Check if the virtual environment exists
if [ ! -d ".venv-server" ]; then
    echo "Virtual environment not found. Creating one..."
    python -m venv .venv-server
fi

# Activate the virtual environment
source .venv-server/bin/activate

# Check if requirements are installed
if ! python -c "import fastapi" &> /dev/null; then
    echo "Installing required packages..."
    if command -v uv &> /dev/null; then
        uv pip install -r requirements.txt
    else
        pip install -r requirements.txt
    fi
fi

# Run the generator script
echo "Generating frontend tools..."
python generate_frontend_tools.py

# Check if the generator was successful
if [ $? -ne 0 ]; then
    echo "Failed to generate frontend tools. Please check the error messages above."
    exit 1
fi

# Start the server
echo "Starting server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
