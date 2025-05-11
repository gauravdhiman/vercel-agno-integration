#!/bin/bash
# Script to update requirements.txt from the current environment

# Change to the script directory
cd "$(dirname "$0")"

# Activate the virtual environment if it exists
if [ -d ".venv-server" ]; then
    source .venv-server/bin/activate
fi

# Check if requirements.in exists
if [ -f "requirements.in" ]; then
    echo "Found requirements.in, using it as the base..."
    
    # Create a temporary file with the header
    cat > requirements.txt.tmp << EOL
# Core packages from requirements.in
$(cat requirements.in)

# Development tools
uv==0.1.24  # Fast Python package installer and resolver

# Dependencies (frozen from current environment - $(date))
EOL

    # Add the frozen dependencies, excluding the ones already in requirements.in
    pip freeze | grep -v -f <(grep -v '^#' requirements.in | sed 's/==.*//' | sed 's/$/==/') >> requirements.txt.tmp
    
    # Replace the old requirements.txt with the new one
    mv requirements.txt.tmp requirements.txt
    echo "Updated requirements.txt successfully!"
else
    echo "requirements.in not found, creating requirements.txt directly from installed packages..."
    pip freeze > requirements.txt
    echo "Created requirements.txt successfully!"
fi
