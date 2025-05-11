# Vercel Agno Integration

This project integrates the Agno AI agent with a Vercel frontend using the Vercel AI SDK.

## Project Structure

- `server/`: Backend server code using FastAPI and Agno
- `ui/`: Frontend code using Next.js and Vercel AI SDK
- `common/`: Shared code between frontend and backend

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

1. Edit `common/frontend_tools.ts` to add your new tool definition
2. Run the generator script to update the Python file:
   ```bash
   cd common
   node generate_python.js
   ```
3. Create any necessary UI components for the new tool
4. The backend will automatically pick up the new tool definition

## Development

### Managing Dependencies

The backend uses two requirements files:
- `requirements.in`: Core dependencies with loose version constraints
- `requirements.txt`: Frozen dependencies for reproducible builds

To update the requirements.txt file after installing new packages:

```bash
cd server
./update_requirements.sh
```

### Frontend Tool Development

When making changes to the frontend tools schema:

1. Edit `common/frontend_tools.ts`
2. Run the generator script or restart the server with `./start_server.sh`
3. The changes will be reflected in both frontend and backend

## Deployment

For deployment:

1. Ensure all dependencies are in `requirements.txt`
2. Make sure the frontend tools Python file is generated during the build process
3. Set up the appropriate environment variables for your deployment platform

The `start_server.sh` script can be used as an entry point for simple deployments.
