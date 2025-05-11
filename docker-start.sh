#!/bin/bash
# Script to build and start the Docker containers

# Print colored messages
function print_message() {
  local color=$1
  local message=$2

  case $color in
    "green") echo -e "\033[0;32m$message\033[0m" ;;
    "blue") echo -e "\033[0;34m$message\033[0m" ;;
    "yellow") echo -e "\033[0;33m$message\033[0m" ;;
    "red") echo -e "\033[0;31m$message\033[0m" ;;
    *) echo "$message" ;;
  esac
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  print_message "red" "Docker is not installed. Please install Docker first."
  exit 1
fi

# Determine which Docker Compose command to use
# Modern Docker Desktop uses 'docker compose' while older versions use 'docker-compose'
DOCKER_COMPOSE_CMD="docker compose"
if command -v docker-compose &> /dev/null; then
  DOCKER_COMPOSE_CMD="docker-compose"
elif ! docker compose version &> /dev/null; then
  print_message "red" "Docker Compose is not available. Please install Docker Compose or update Docker Desktop."
  exit 1
fi

print_message "blue" "Using Docker Compose command: $DOCKER_COMPOSE_CMD"

# Build and start the containers
print_message "blue" "Building and starting Docker containers..."
$DOCKER_COMPOSE_CMD up --build -d

# Check if containers are running
if [ $? -eq 0 ]; then
  print_message "green" "Docker containers are now running!"
  print_message "green" "Frontend: http://localhost:3000"
  print_message "green" "Backend: http://localhost:8000"
else
  print_message "red" "Failed to start Docker containers. Check the logs for more information."
  exit 1
fi

# Show logs
print_message "yellow" "To view logs, run: $DOCKER_COMPOSE_CMD logs -f"
print_message "yellow" "To stop the containers, run: $DOCKER_COMPOSE_CMD down"
