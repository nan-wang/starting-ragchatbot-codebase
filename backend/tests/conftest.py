"""Shared pytest fixtures for all tests"""

import pytest
from unittest.mock import Mock
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
