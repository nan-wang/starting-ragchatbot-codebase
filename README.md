# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.10 or higher (3.12 recommended)
  - **Note**: Python 3.13 is not yet fully supported by PyTorch on macOS x86_64
  - If using pyenv, ensure you have Python 3.12.2 or compatible version installed
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Set up Python version** (if using pyenv)
   ```bash
   # Create .python-version file with your Python version
   echo "3.12.2" > .python-version
   ```

3. **Create virtual environment**
   ```bash
   # For pyenv users
   uv venv --python ~/.pyenv/shims/python

   # For system Python
   uv venv --python /path/to/python3.12
   ```

4. **Install Python dependencies**
   ```bash
   uv sync
   ```

   **Note**: The project automatically installs:
   - `numpy<2` for PyTorch compatibility
   - `httpx[socks]` for proxy support
   - `torch==2.2.2` (automatically resolved for your platform)

5. **Set up environment variables**

   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Initial Startup

On first run, the application will:
1. Load all course documents from the `docs/` folder
2. Process and chunk the content
3. Create vector embeddings using ChromaDB
4. Store embeddings in `./chroma_db` directory

The startup logs will show progress:
```
Loading initial documents...
Added new course: Course Name (X chunks)
Loaded N courses with X chunks
```

## Troubleshooting

### PyTorch Platform Compatibility

**Issue**: `torch` doesn't have wheels for the current platform

**Solution**: The project is configured to resolve compatible PyTorch versions automatically via `tool.uv.required-environments` in `pyproject.toml`. If you still encounter issues:

```bash
# Ensure you're using Python 3.10-3.12 (not 3.13)
python --version

# Recreate virtual environment
rm -rf .venv
uv venv --python /path/to/python3.12
uv sync
```

### NumPy Compatibility Error

**Issue**: `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x`

**Solution**: Already fixed in dependencies. The project pins `numpy<2` for compatibility with PyTorch.

### SOCKS Proxy Error

**Issue**: `ImportError: Using SOCKS proxy, but the 'socksio' package is not installed`

**Solution**: Already fixed in dependencies. The project includes `httpx[socks]` which installs the required `socksio` package.

### Application Not Starting

If uvicorn starts but the worker process doesn't:

1. Test if the app imports correctly:
   ```bash
   cd backend
   uv run python -c "import app; print('App imported successfully')"
   ```

2. Check for errors in the startup logs
3. Verify your `.env` file exists with a valid `ANTHROPIC_API_KEY`

### Port Already in Use

**Issue**: `Address already in use` on port 8000

**Solution**:
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
cd backend
uv run uvicorn app:app --reload --port 8001
```

