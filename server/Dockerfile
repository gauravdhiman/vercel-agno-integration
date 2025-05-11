# Use an image with both Python and Node.js
FROM nikolaik/python-nodejs:python3.10-nodejs18

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY server/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the common directory first (needed for frontend tools generation)
COPY common/ ../common/

# Copy the scripts directory (needed for frontend tools generation)
COPY scripts/ ../scripts/

# Copy the server code
COPY server/ .

# Generate the frontend tools Python file during build
RUN echo "Generating frontend tools during build..." && \
    node ../scripts/generate_frontend_tools_python.js && \
    echo "Frontend tools generated successfully"

# Make the start script executable
RUN chmod +x start_server.sh

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["./start_server.sh"]
