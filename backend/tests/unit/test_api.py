"""API endpoint tests for the FastAPI application.

Uses the test_app / api_client fixtures from conftest.py which define
routes inline (mirroring app.py) to avoid static-file mount issues.
"""
import pytest
from unittest.mock import Mock


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for POST /api/query"""

    def test_query_returns_answer_and_sources(self, api_client, mock_rag_system):
        """Successful query returns answer, sources, and session_id"""
        response = api_client.post("/api/query", json={
            "query": "What is MCP?",
            "session_id": "session_1"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "MCP stands for Model Context Protocol."
        assert data["session_id"] == "session_1"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["display_text"] == "MCP Course - Lesson 1"
        assert data["sources"][0]["lesson_link"] == "https://example.com/lesson1"

        mock_rag_system.query.assert_called_once_with("What is MCP?", "session_1")

    def test_query_without_session_id_creates_new_session(self, api_client, mock_rag_system):
        """When no session_id is provided, backend creates one"""
        response = api_client.post("/api/query", json={
            "query": "Tell me about tool calling"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session_1"
        mock_rag_system.session_manager.create_session.assert_called_once()
        mock_rag_system.query.assert_called_once_with("Tell me about tool calling", "session_1")

    def test_query_with_explicit_session_id_skips_creation(self, api_client, mock_rag_system):
        """When session_id is provided, no new session is created"""
        response = api_client.post("/api/query", json={
            "query": "Explain embeddings",
            "session_id": "session_42"
        })

        assert response.status_code == 200
        assert response.json()["session_id"] == "session_42"
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_query_with_empty_sources(self, api_client, mock_rag_system):
        """Query that triggers no tool use returns empty sources"""
        mock_rag_system.query.return_value = ("Hello! How can I help?", [])

        response = api_client.post("/api/query", json={
            "query": "Hi there",
            "session_id": "session_1"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Hello! How can I help?"
        assert data["sources"] == []

    def test_query_rag_system_error_returns_500(self, api_client, mock_rag_system):
        """Internal error in RAG system returns HTTP 500"""
        mock_rag_system.query.side_effect = RuntimeError("Anthropic API unavailable")

        response = api_client.post("/api/query", json={
            "query": "What is MCP?",
            "session_id": "session_1"
        })

        assert response.status_code == 500
        assert "Anthropic API unavailable" in response.json()["detail"]

    def test_query_missing_query_field_returns_422(self, api_client):
        """Request without required 'query' field returns 422 validation error"""
        response = api_client.post("/api/query", json={
            "session_id": "session_1"
        })

        assert response.status_code == 422

    def test_query_empty_body_returns_422(self, api_client):
        """Request with empty body returns 422 validation error"""
        response = api_client.post("/api/query", json={})

        assert response.status_code == 422

    def test_query_sources_with_null_lesson_link(self, api_client, mock_rag_system):
        """Sources with null lesson_link are serialized correctly"""
        mock_rag_system.query.return_value = (
            "Here is the answer.",
            [{"display_text": "Course A - Lesson 2", "lesson_link": None}]
        )

        response = api_client.post("/api/query", json={
            "query": "test",
            "session_id": "session_1"
        })

        assert response.status_code == 200
        source = response.json()["sources"][0]
        assert source["display_text"] == "Course A - Lesson 2"
        assert source["lesson_link"] is None


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for GET /api/courses"""

    def test_courses_returns_stats(self, api_client, mock_rag_system):
        """Returns course count and titles"""
        response = api_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 2
        assert "Introduction to MCP" in data["course_titles"]
        assert "Computer Use with Claude" in data["course_titles"]
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_empty_catalog(self, api_client, mock_rag_system):
        """Empty course catalog returns zero count"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = api_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_analytics_error_returns_500(self, api_client, mock_rag_system):
        """Internal error in analytics returns HTTP 500"""
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("ChromaDB down")

        response = api_client.get("/api/courses")

        assert response.status_code == 500
        assert "ChromaDB down" in response.json()["detail"]
