"""Unit tests for CourseSearchTool"""
import pytest
from unittest.mock import Mock
from search_tools import CourseSearchTool
from tests.fixtures.mock_vector_store import create_search_results, create_empty_search_results


@pytest.mark.unit
def test_execute_successful_search_with_results(mock_vector_store):
    """Test successful search returns formatted results with sources"""
    # Arrange
    search_results = create_search_results(2, "MCP Course")
    mock_vector_store.search.return_value = search_results
    mock_vector_store.get_lesson_link.side_effect = [
        "https://example.com/lesson1",
        "https://example.com/lesson2"
    ]

    tool = CourseSearchTool(mock_vector_store)

    # Act
    result = tool.execute(query="What is MCP?")

    # Assert
    assert "Content chunk 0" in result
    assert "MCP Course" in result
    assert "Lesson 1" in result
    assert len(tool.last_sources) == 2
    assert tool.last_sources[0]["lesson_link"] == "https://example.com/lesson1"
    assert tool.last_sources[0]["display_text"] == "MCP Course - Lesson 1"
    mock_vector_store.search.assert_called_once()


@pytest.mark.unit
def test_execute_empty_results(mock_vector_store):
    """Test empty search results returns appropriate message"""
    # Arrange
    empty_results = create_empty_search_results()
    mock_vector_store.search.return_value = empty_results
    tool = CourseSearchTool(mock_vector_store)

    # Act
    result = tool.execute(query="Unknown topic")

    # Assert
    assert "No relevant content found" in result
    assert len(tool.last_sources) == 0


@pytest.mark.unit
def test_execute_search_error(mock_vector_store):
    """Test search error is properly returned"""
    # Arrange
    error_results = create_empty_search_results(error_msg="Database error")
    mock_vector_store.search.return_value = error_results
    tool = CourseSearchTool(mock_vector_store)

    # Act
    result = tool.execute(query="Any query")

    # Assert
    assert "Database error" in result
    assert len(tool.last_sources) == 0


@pytest.mark.unit
def test_execute_with_course_and_lesson_filters(mock_vector_store):
    """Test search with course and lesson filters passes correct parameters"""
    # Arrange
    search_results = create_search_results(1, "MCP Course")
    mock_vector_store.search.return_value = search_results
    mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson2"
    tool = CourseSearchTool(mock_vector_store)

    # Act
    result = tool.execute(query="Tool calling", course_name="MCP", lesson_number=2)

    # Assert
    mock_vector_store.search.assert_called_once_with(
        query="Tool calling",
        course_name="MCP",
        lesson_number=2
    )
    assert "Content chunk 0" in result


@pytest.mark.unit
def test_execute_with_course_and_lesson_filters_empty_result(mock_vector_store):
    """Test that empty results with filters shows filter info"""
    # Arrange
    empty_results = create_empty_search_results()
    mock_vector_store.search.return_value = empty_results
    tool = CourseSearchTool(mock_vector_store)

    # Act
    result = tool.execute(query="Topic", course_name="MCP", lesson_number=5)

    # Assert
    assert "No relevant content found" in result
    assert "MCP" in result or "Lesson 5" in result


@pytest.mark.unit
def test_format_results_creates_proper_headers(mock_vector_store):
    """Test that formatted results contain proper headers"""
    # Arrange
    search_results = create_search_results(3, "Test Course")
    mock_vector_store.search.return_value = search_results
    mock_vector_store.get_lesson_link.return_value = None
    tool = CourseSearchTool(mock_vector_store)

    # Act
    result = tool.execute(query="Test")

    # Assert
    # Check that results are grouped by lesson
    assert "[Test Course - Lesson 1]" in result
    assert "[Test Course - Lesson 2]" in result
    assert "Content chunk" in result


@pytest.mark.unit
def test_last_sources_populated_with_lesson_links(mock_vector_store):
    """Test that last_sources contains correct structure with mixed link availability"""
    # Arrange
    search_results = create_search_results(3, "Course A")
    mock_vector_store.search.return_value = search_results
    # Return URL for first call, None for others
    mock_vector_store.get_lesson_link.side_effect = [
        "https://example.com/lesson1",
        None,
        "https://example.com/lesson3"
    ]
    tool = CourseSearchTool(mock_vector_store)

    # Act
    result = tool.execute(query="Test")

    # Assert
    assert len(tool.last_sources) == 3
    assert tool.last_sources[0]["lesson_link"] == "https://example.com/lesson1"
    assert tool.last_sources[1]["lesson_link"] is None
    assert tool.last_sources[2]["lesson_link"] == "https://example.com/lesson3"
    # Check display text format
    assert "Course A - Lesson" in tool.last_sources[0]["display_text"]


@pytest.mark.unit
def test_get_tool_definition_schema(mock_vector_store):
    """Test that tool definition has correct schema"""
    # Arrange
    tool = CourseSearchTool(mock_vector_store)

    # Act
    definition = tool.get_tool_definition()

    # Assert
    assert definition["name"] == "search_course_content"
    assert "description" in definition
    assert "input_schema" in definition

    # Check required and optional parameters
    input_schema = definition["input_schema"]
    assert "query" in input_schema["required"]

    # Check that course_name and lesson_number are in properties but not required
    properties = input_schema["properties"]
    assert "course_name" in properties
    assert "lesson_number" in properties
    assert "course_name" not in input_schema.get("required", [])
    assert "lesson_number" not in input_schema.get("required", [])
