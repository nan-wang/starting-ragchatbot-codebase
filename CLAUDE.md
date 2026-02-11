# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**IMPORTANT**: This project uses `uv` for Python package management. Always use `uv run` to execute Python commands. Never use `pip` or run Python scripts directly.

### Running the Application
```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

Access points:
- Web UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

### Dependency Management
```bash
# Install/sync dependencies
uv sync

# Add new dependency
uv add <package-name>

# NEVER use pip directly - always use uv
```

### Code Quality
```bash
# Check formatting (fails if unformatted code found)
./scripts/quality.sh check

# Auto-format all Python files
./scripts/quality.sh format

# Or run black directly
uv run black backend/ main.py
uv run black --check backend/ main.py
```

**Formatting**: This project uses [black](https://black.readthedocs.io/) with a line length of 100. Configuration is in `pyproject.toml` under `[tool.black]`. All Python code must pass `black --check` before committing.

### Environment Setup
Required `.env` file in root directory:
```
ANTHROPIC_API_KEY=your_key_here
```

## Architecture Overview

### Tool-Based RAG Architecture

This system uses **Anthropic's tool calling** rather than traditional RAG retrieve-then-answer flow. Claude receives the user query and **autonomously decides** whether to use the `search_course_content` tool.

**Key architectural decision**: The AI agent controls search behavior, not the application logic. This enables:
- Answering general questions without search
- Intelligent course name resolution
- Single search per query (enforced via system prompt)

### Query Processing Flow

```
User Query → FastAPI Endpoint → RAG System → AI Generator
                                      ↓
                           ┌──────────┴──────────┐
                           ↓                     ↓
                    Session Manager      Tool Manager
                    (conversation        (registers &
                     history)            executes tools)
                                              ↓
                                      CourseSearchTool
                                              ↓
                                      Vector Store
                                      (ChromaDB)
```

**Two-phase Claude API interaction**:
1. **Initial call**: Claude receives query + tool definitions, decides to search
2. **Follow-up call**: Claude receives search results, synthesizes final answer

See `QUERY_FLOW_DIAGRAM.md` for detailed flow visualization.

### Component Responsibilities

**RAG System** (`rag_system.py`):
- Central orchestrator coordinating all components
- Manages document ingestion pipeline
- Handles query processing end-to-end
- Extracts sources from tool execution

**AI Generator** (`ai_generator.py`):
- Interfaces with Anthropic API
- Implements tool calling protocol (2-phase API calls)
- System prompt configures tool usage behavior (line 8-30)
- **Important**: Temperature set to 0 for deterministic responses

**Tool Manager + CourseSearchTool** (`search_tools.py`):
- Abstract `Tool` base class for extensibility
- `CourseSearchTool` wraps vector store with formatting
- Tracks `last_sources` for UI display
- Tool definition specifies optional `course_name` and `lesson_number` parameters

**Vector Store** (`vector_store.py`):
- **Two-collection architecture**:
  - `course_catalog`: Course metadata for semantic name matching
  - `course_content`: Actual course chunks for content search
- `search()` method performs two-step lookup:
  1. Resolve partial course name to exact title via semantic search
  2. Query content with metadata filters

**Session Manager** (`session_manager.py`):
- Maintains per-session conversation history
- Limits history to `MAX_HISTORY` exchanges (default: 2)
- History injected into system prompt for context

### Document Processing Pipeline

**On startup** (`app.py:88-98`):
1. Loads all documents from `../docs` folder
2. Checks for existing courses to avoid re-indexing
3. Processes each document through `DocumentProcessor`
4. Adds course metadata to `course_catalog` collection
5. Adds content chunks to `course_content` collection

**Document format** (`document_processor.py`):
- Expects text files with "Lesson X:" markers
- Chunks text by sentences (not character-based) for better context preservation
- Configurable `CHUNK_SIZE` (800 chars) and `CHUNK_OVERLAP` (100 chars)
- Each chunk stores: `course_title`, `lesson_number`, `chunk_index`

### Configuration System

All tunable parameters in `config.py`:
- `ANTHROPIC_MODEL`: Currently "claude-sonnet-4-20250514"
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" (sentence-transformers)
- `CHUNK_SIZE`: 800 characters
- `CHUNK_OVERLAP`: 100 characters
- `MAX_RESULTS`: 5 search results
- `MAX_HISTORY`: 2 conversation exchanges
- `CHROMA_PATH`: "./chroma_db"

### Data Models

**Pydantic models** (`models.py`):
- `Course`: Represents course with title (unique ID), instructor, lessons list
- `Lesson`: Contains lesson_number, title, optional lesson_link
- `CourseChunk`: Vector store entry with content, course_title, lesson_number, chunk_index

**API models** (`app.py:38-52`):
- `QueryRequest`: {query: str, session_id: Optional[str]}
- `QueryResponse`: {answer: str, sources: List[str], session_id: str}
- `CourseStats`: {total_courses: int, course_titles: List[str]}

## Key Implementation Details

### Why Two ChromaDB Collections?

**Problem**: User queries use partial names ("MCP") but vector store needs exact course titles for filtering.

**Solution**:
- `course_catalog` enables semantic course name resolution
- `course_content` stores actual searchable material
- `VectorStore.search()` resolves names first, then searches content with exact title filter

### Tool Execution Pattern

**In `ai_generator.py:_handle_tool_execution()`**:
1. Extract tool use blocks from Claude's response
2. Execute each tool via `tool_manager.execute_tool()`
3. Format results as `tool_result` message type
4. Send back to Claude **without tools parameter** (prevents infinite loops)
5. Return Claude's final synthesized response

### Source Tracking Mechanism

Sources must survive the two-phase API interaction:
1. `CourseSearchTool.execute()` stores sources in `self.last_sources`
2. `RAGSystem.query()` retrieves via `tool_manager.get_last_sources()`
3. `tool_manager.reset_sources()` clears after retrieval
4. Sources returned to API endpoint alongside answer

### Session ID Lifecycle

- Frontend generates no session ID on first message
- Backend creates session via `session_manager.create_session()` (returns "session_1", "session_2", etc.)
- Session ID returned in response, frontend stores for subsequent queries
- Session history automatically trimmed to `MAX_HISTORY * 2` messages

## Adding New Tools

To extend with additional tools (e.g., calculator, web search):

1. Create tool class inheriting from `Tool` (`search_tools.py:6-17`)
2. Implement `get_tool_definition()` returning Anthropic tool schema
3. Implement `execute(**kwargs)` returning string result
4. Register with tool manager in `RAGSystem.__init__()`:
   ```python
   self.my_tool = MyTool()
   self.tool_manager.register_tool(self.my_tool)
   ```
5. Update system prompt in `ai_generator.py` if needed

## Frontend Architecture

**Vanilla JavaScript** (`frontend/script.js`):
- No frameworks, single-file implementation
- Manages global `currentSessionId` state
- `sendMessage()` handles API calls with loading states
- Uses `marked.js` for markdown rendering
- Displays sources in collapsible `<details>` element

**Dark mode UI** (`frontend/style.css`):
- CSS variables for theming
- Responsive chat interface with message history
- Loading animation using CSS keyframes

## Important Notes

### ChromaDB Persistence
- Vector embeddings persist in `./chroma_db` directory
- On startup, existing courses are detected and skipped
- To rebuild from scratch: delete `chroma_db` folder or call `add_course_folder(clear_existing=True)`

### System Prompt Behavior
The system prompt in `ai_generator.py:8-30` controls critical behavior:
- **"One search per query maximum"**: Prevents multiple tool calls
- **"No meta-commentary"**: Instructs Claude not to explain search process
- **Distinguishes general vs. course-specific questions**: Enables direct answers without search

Modifying this prompt significantly affects system behavior.

### Error Handling
- Vector store returns `SearchResults.empty(error_msg)` on failures
- Tool execution errors returned as strings to Claude
- Claude handles error results gracefully in final response

### CORS Configuration
`app.py` allows all origins (`allow_origins=["*"]`) and uses `TrustedHostMiddleware` for proxy compatibility. Tighten for production deployment.
