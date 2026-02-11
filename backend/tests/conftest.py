"""Shared pytest fixtures for all tests"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from vector_store import SearchResults
from models import Course, Lesson, CourseChunk
from config import Config


@pytest.fixture
def test_config():
    """Test configuration with safe defaults"""
    config = Config()
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.CHROMA_PATH = "./test_chroma_db"
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    return config


@pytest.fixture
def sample_course():
    """Sample course with 2 lessons"""
    return Course(
        title="Introduction to Model Context Protocol",
        course_link="https://example.com/mcp",
        instructor="Dr. Smith",
        lessons=[
            Lesson(lesson_number=1, title="MCP Basics", lesson_link="https://example.com/lesson1"),
            Lesson(
                lesson_number=2, title="Tool Calling", lesson_link="https://example.com/lesson2"
            ),
        ],
    )


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore with standard methods"""
    store = Mock()
    store.search = Mock()
    store.get_lesson_link = Mock(return_value=None)
    store.get_course_outline = Mock()
    return store


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    client = Mock()
    client.messages = Mock()
    client.messages.create = Mock()
    return client


# --- API test fixtures ---

@pytest.fixture
def mock_rag_system():
    """Mock RAGSystem for API endpoint testing"""
    rag = Mock()
    rag.query = Mock(return_value=(
        "MCP stands for Model Context Protocol.",
        [{"display_text": "MCP Course - Lesson 1", "lesson_link": "https://example.com/lesson1"}]
    ))
    rag.get_course_analytics = Mock(return_value={
        "total_courses": 2,
        "course_titles": ["Introduction to MCP", "Computer Use with Claude"]
    })
    rag.session_manager = Mock()
    rag.session_manager.create_session = Mock(return_value="session_1")
    return rag


@pytest.fixture
def test_app(mock_rag_system):
    """FastAPI test app with API routes only (no static file mount).

    Defines routes inline to avoid importing app.py, which mounts a
    static-files directory that doesn't exist in the test environment.
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    app = FastAPI()

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceInfo(BaseModel):
        display_text: str
        lesson_link: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceInfo]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Wire routes to the mock_rag_system injected by the fixture
    rag = mock_rag_system

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag.session_manager.create_session()
            answer, sources = rag.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def api_client(test_app):
    """HTTPX test client for the FastAPI test app"""
    from starlette.testclient import TestClient
    return TestClient(test_app)
