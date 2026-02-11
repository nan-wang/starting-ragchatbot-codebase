"""Unit tests for RAGSystem integration"""

import pytest
from unittest.mock import Mock, patch
from rag_system import RAGSystem


@pytest.mark.unit
def test_query_without_session_id(test_config, mocker):
    """Test query without session ID doesn't update history"""
    # Arrange
    mock_vector_store = Mock()
    mock_ai_gen = Mock()
    mock_session_mgr = Mock()
    mock_tool_mgr = Mock()

    mock_ai_gen.generate_response.return_value = "Answer without session"
    mock_tool_mgr.get_last_sources.return_value = []
    mock_tool_mgr.get_tool_definitions.return_value = []
    mock_session_mgr.get_conversation_history.return_value = None

    with (
        mocker.patch("rag_system.VectorStore", return_value=mock_vector_store),
        mocker.patch("rag_system.AIGenerator", return_value=mock_ai_gen),
        mocker.patch("rag_system.SessionManager", return_value=mock_session_mgr),
        mocker.patch("rag_system.ToolManager", return_value=mock_tool_mgr),
    ):

        rag = RAGSystem(test_config)
        response, sources = rag.query("What is MCP?")

    # Assert
    assert response == "Answer without session"
    assert sources == []
    mock_session_mgr.add_exchange.assert_not_called()


@pytest.mark.unit
def test_query_with_tool_execution_and_sources(test_config, mocker):
    """Test query with tool execution properly retrieves and resets sources"""
    # Arrange
    mock_vector_store = Mock()
    mock_ai_gen = Mock()
    mock_session_mgr = Mock()
    mock_tool_mgr = Mock()

    # Configure behavior
    mock_ai_gen.generate_response.return_value = "Answer about MCP"
    mock_tool_mgr.get_last_sources.return_value = [
        {"display_text": "MCP Course - Lesson 1", "lesson_link": "http://link"}
    ]
    mock_tool_mgr.get_tool_definitions.return_value = []
    mock_session_mgr.get_conversation_history.return_value = None

    # Patch constructors
    with (
        mocker.patch("rag_system.VectorStore", return_value=mock_vector_store),
        mocker.patch("rag_system.AIGenerator", return_value=mock_ai_gen),
        mocker.patch("rag_system.SessionManager", return_value=mock_session_mgr),
        mocker.patch("rag_system.ToolManager", return_value=mock_tool_mgr),
    ):

        rag = RAGSystem(test_config)
        response, sources = rag.query("What is MCP?", session_id="session_1")

    # Assert
    assert response == "Answer about MCP"
    assert len(sources) == 1
    mock_tool_mgr.get_last_sources.assert_called_once()
    mock_tool_mgr.reset_sources.assert_called_once()
    mock_session_mgr.add_exchange.assert_called_once()


@pytest.mark.unit
def test_source_lifecycle_management(test_config, mocker):
    """Test that sources don't leak between queries"""
    # Arrange
    mock_vector_store = Mock()
    mock_ai_gen = Mock()
    mock_session_mgr = Mock()
    mock_tool_mgr = Mock()

    # First query has sources, second has none
    mock_ai_gen.generate_response.return_value = "Answer"
    mock_tool_mgr.get_last_sources.side_effect = [
        [{"display_text": "Source 1", "lesson_link": "http://link1"}],
        [],  # Second query has no sources
    ]
    mock_tool_mgr.get_tool_definitions.return_value = []
    mock_session_mgr.get_conversation_history.return_value = None

    with (
        mocker.patch("rag_system.VectorStore", return_value=mock_vector_store),
        mocker.patch("rag_system.AIGenerator", return_value=mock_ai_gen),
        mocker.patch("rag_system.SessionManager", return_value=mock_session_mgr),
        mocker.patch("rag_system.ToolManager", return_value=mock_tool_mgr),
    ):

        rag = RAGSystem(test_config)

        # Act - execute two queries
        response1, sources1 = rag.query("Query 1", session_id="session_1")
        response2, sources2 = rag.query("Query 2", session_id="session_1")

    # Assert
    assert len(sources1) == 1
    assert len(sources2) == 0
    assert mock_tool_mgr.reset_sources.call_count == 2


@pytest.mark.unit
def test_query_with_conversation_history(test_config, mocker):
    """Test that conversation history is passed to AI generator"""
    # Arrange
    mock_vector_store = Mock()
    mock_ai_gen = Mock()
    mock_session_mgr = Mock()
    mock_tool_mgr = Mock()

    mock_ai_gen.generate_response.return_value = "Response with context"
    mock_tool_mgr.get_last_sources.return_value = []
    mock_tool_mgr.get_tool_definitions.return_value = []

    conversation_history = "User: What is MCP?\nAssistant: MCP is a protocol"
    mock_session_mgr.get_conversation_history.return_value = conversation_history

    with (
        mocker.patch("rag_system.VectorStore", return_value=mock_vector_store),
        mocker.patch("rag_system.AIGenerator", return_value=mock_ai_gen),
        mocker.patch("rag_system.SessionManager", return_value=mock_session_mgr),
        mocker.patch("rag_system.ToolManager", return_value=mock_tool_mgr),
    ):

        rag = RAGSystem(test_config)
        response, sources = rag.query("Follow up question", session_id="session_1")

    # Assert
    mock_ai_gen.generate_response.assert_called_once()
    call_kwargs = mock_ai_gen.generate_response.call_args[1]
    assert call_kwargs["conversation_history"] == conversation_history


@pytest.mark.unit
def test_initialization_registers_tools(test_config, mocker):
    """Test that RAGSystem registers CourseSearchTool and CourseOutlineTool on init"""
    # Arrange
    mock_vector_store = Mock()
    mock_ai_gen = Mock()
    mock_session_mgr = Mock()
    mock_tool_mgr = Mock()

    with (
        mocker.patch("rag_system.VectorStore", return_value=mock_vector_store),
        mocker.patch("rag_system.AIGenerator", return_value=mock_ai_gen),
        mocker.patch("rag_system.SessionManager", return_value=mock_session_mgr),
        mocker.patch("rag_system.ToolManager", return_value=mock_tool_mgr),
    ):

        # Act
        rag = RAGSystem(test_config)

    # Assert - verify tools were registered
    # Should have 2 register_tool calls (CourseSearchTool and CourseOutlineTool)
    assert mock_tool_mgr.register_tool.call_count == 2

    # Verify both tool types were registered
    registered_tools = [call[0][0] for call in mock_tool_mgr.register_tool.call_args_list]
    tool_names = [type(tool).__name__ for tool in registered_tools]

    assert "CourseSearchTool" in tool_names
    assert "CourseOutlineTool" in tool_names
