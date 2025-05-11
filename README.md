# Vercel Agno Integration

This project integrates the Agno AI agent with a Vercel frontend using the Vercel AI SDK.

## Project Structure

- `server/`: Backend server code using FastAPI and Agno
- `ui/`: Frontend code using Next.js and Vercel AI SDK
- `common/`: Shared code between frontend and backend
- `scripts/`: Development and utility scripts

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- pnpm (for the UI)
- uv (optional, for faster package installation)

### Backend Setup

The easiest way to set up the backend is to use the provided start script, which handles everything automatically:

```bash
cd server
./start_server.sh
```

This script will:
1. Create a virtual environment if it doesn't exist
2. Install required packages
3. Generate the frontend tools Python file
4. Start the server

If you prefer to set up manually:

1. Navigate to the server directory:
   ```bash
   cd server
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv-server
   source .venv-server/bin/activate  # On Windows: .venv-server\Scripts\activate
   ```

3. Install dependencies (using uv for faster installation if available):
   ```bash
   # Using uv (recommended)
   pip install uv
   uv pip install -r requirements.txt

   # Or using standard pip
   pip install -r requirements.txt
   ```

4. Generate the frontend tools Python file:
   ```bash
   python generate_frontend_tools.py
   ```

5. Start the server using the provided script:
   ```bash
   ./start_server.sh
   ```

   This is recommended over running uvicorn directly as it ensures the frontend tools are properly generated.

### Frontend Setup

1. Navigate to the UI directory:
   ```bash
   cd ui
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Start the development server:
   ```bash
   pnpm dev
   ```

## Frontend Tools

The project uses a shared schema for frontend tools between the backend and frontend. The schema is defined in TypeScript in `common/frontend_tools.ts` and automatically converted to Python for the backend.

### Adding a New Frontend Tool

You can add new frontend tools using the interactive wizard:

```bash
./scripts/tool_schema_wizard.js
```

The wizard will guide you through:
1. Defining the tool name and description
2. Adding parameters with types and descriptions
3. Updating the TypeScript definitions
4. Generating the Python code automatically

Alternatively, you can manually:

1. Edit `common/frontend_tools.ts` to add your new tool definition
2. Run the generator script to update the Python file:
   ```bash
   node scripts/generate_frontend_tools_python.js
   ```
3. Create any necessary UI components for the new tool
4. The backend will automatically pick up the new tool definition

## Development

### Development Scripts

The project includes several development scripts in the `scripts` directory to automate common tasks:

#### `scripts/tool_schema_wizard.js`

**Purpose**: Interactive wizard for creating or updating frontend tool schemas.

**Usage**:
```bash
./scripts/tool_schema_wizard.js
```

**What it does**:
- Guides you through defining a new frontend tool with parameters
- Validates inputs to ensure they meet requirements
- Updates the TypeScript definitions in `common/frontend_tools.ts`
- Automatically runs the Python generator script

**Output**:
- Updates `common/frontend_tools.ts` with new tool definitions
- Generates `common/frontend_tools.py` via the generator script

**Benefits**:
- Prevents common errors in manual schema editing
- Ensures consistent naming conventions
- Automates repetitive code generation tasks

#### `scripts/generate_frontend_tools_python.js`

**Purpose**: Generates Python code from TypeScript frontend tool definitions.

**Usage**:
```bash
node scripts/generate_frontend_tools_python.js
```

**What it does**:
- Reads the TypeScript definitions from `common/frontend_tools.ts`
- Extracts tool names, descriptions, and parameter schemas
- Generates equivalent Python code with proper typing

**Output**:
- Creates/updates `common/frontend_tools.py`
- This file is imported by the backend to define available frontend tools

**When to use**:
- After manually editing `common/frontend_tools.ts`
- When you need to regenerate the Python file for any reason
- The wizard runs this automatically, so you don't need to run it separately if using the wizard

### Server Scripts

The server directory contains several utility scripts:

#### `server/start_server.sh`

**Purpose**: Automates the server setup and startup process.

**Usage**:
```bash
cd server
./start_server.sh
```

**What it does**:
- Creates a virtual environment if it doesn't exist
- Installs required packages
- Runs `generate_frontend_tools.py` to ensure Python definitions are up-to-date
- Starts the server with uvicorn

**When to use**:
- For local development
- As an entry point for simple deployments

#### `server/generate_frontend_tools.py`

**Purpose**: Python wrapper for the frontend tools generator.

**Usage**:
```bash
cd server
python generate_frontend_tools.py
```

**What it does**:
- Calls `scripts/generate_frontend_tools_python.js`
- Provides Python-friendly logging and error handling
- Used by `start_server.sh` to ensure Python definitions are up-to-date

#### `server/update_requirements.sh`

**Purpose**: Updates the requirements.txt file from the current environment.

**Usage**:
```bash
cd server
./update_requirements.sh
```

**What it does**:
- Creates a requirements.txt file based on requirements.in
- Adds all installed dependencies with version pinning
- Ensures reproducible builds

**When to use**:
- After installing new packages
- Before committing changes that involve new dependencies
- Before deployment

### Script Integration

These scripts are integrated into the development workflow:

1. **Server Startup**: The `server/start_server.sh` script automatically runs `server/generate_frontend_tools.py`, which in turn calls `scripts/generate_frontend_tools_python.js` to ensure the Python definitions are up-to-date.

2. **Tool Schema Wizard**: The wizard automatically runs the Python generator after updating the TypeScript definitions.

3. **Manual Updates**: If you manually edit the TypeScript definitions, you should run the generator script to update the Python file.

#### Script Workflow Diagram

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│                     │     │                     │     │                     │
│  tool_schema_wizard │     │ frontend_tools.ts   │     │ frontend_tools.py   │
│  (scripts/)         │────▶│ (common/)           │────▶│ (common/)           │
│                     │     │                     │     │                     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                     ▲                           ▲
                                     │                           │
                                     │                           │
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│                     │     │                     │     │                     │
│  start_server.sh    │────▶│ generate_frontend_  │────▶│ generate_frontend_  │
│  (server/)          │     │ tools.py (server/)  │     │ tools_python.js     │
│                     │     │                     │     │ (scripts/)          │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

This diagram shows how the scripts interact with each other and the key files they modify. The TypeScript definitions in `common/frontend_tools.ts` are the source of truth, and the Python file `common/frontend_tools.py` is generated from them.

### Managing Dependencies

The backend uses two requirements files:
- `requirements.in`: Core dependencies with loose version constraints
- `requirements.txt`: Frozen dependencies for reproducible builds

To update the requirements.txt file after installing new packages:

```bash
cd server
./update_requirements.sh
```

### Frontend Tool Development Workflow

When making changes to the frontend tools schema:

1. Use the interactive wizard for guided creation of new tools:
   ```bash
   ./scripts/tool_schema_wizard.js
   ```

2. Or manually edit `common/frontend_tools.ts` if you need more control, then run:
   ```bash
   node scripts/generate_frontend_tools_python.js
   ```

3. Restart the server with `./server/start_server.sh` to apply the changes

4. The changes will be reflected in both frontend and backend

The wizard helps prevent common errors by:
- Ensuring proper TypeScript types and JSON Schema formats
- Automatically generating consistent enum names
- Updating all necessary parts of the code
- Running the Python generator automatically

## Deployment

### Docker Deployment

The application can be deployed using Docker, which simplifies the setup process and ensures consistent environments.

#### Prerequisites

- Docker
- Docker Compose

#### Running with Docker

1. Use the provided script to build and start the Docker containers:

   ```bash
   ./docker-start.sh
   ```

   This script will:
   - Build the Docker images for both frontend and backend
   - Start the containers in detached mode
   - Display URLs for accessing the application

2. Alternatively, you can manually run Docker Compose:

   ```bash
   # For newer Docker Desktop versions
   docker compose up --build -d

   # For older Docker installations
   docker-compose up --build -d
   ```

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

4. To view logs:

   ```bash
   # For newer Docker Desktop versions
   docker compose logs -f

   # For older Docker installations
   docker-compose logs -f
   ```

5. To stop the containers:

   ```bash
   # For newer Docker Desktop versions
   docker compose down

   # For older Docker installations
   docker-compose down
   ```

### Manual Deployment

For manual deployment without Docker:

1. Ensure all dependencies are in `requirements.txt`
2. Make sure the frontend tools Python file is generated during the build process
3. Set up the appropriate environment variables for your deployment platform

The `start_server.sh` script can be used as an entry point for simple deployments.
