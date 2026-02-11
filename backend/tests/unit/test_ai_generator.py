"""Unit tests for AIGenerator"""
import pytest
from unittest.mock import Mock, patch
from ai_generator import AIGenerator
from tests.fixtures.mock_anthropic import create_tool_use_response, create_text_response


@pytest.mark.unit
def test_generate_response_without_tools_returns_direct_answer(mock_anthropic_client, mocker):
    """Test that responses without tools return directly"""
    # Arrange
    text_response = create_text_response("The answer is 42")
    mock_anthropic_client.messages.create.return_value = text_response

    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

        # Act
        result = generator.generate_response(query="What is the answer?")

    # Assert
    assert result == "The answer is 42"
    assert mock_anthropic_client.messages.create.call_count == 1


@pytest.mark.unit
def test_generate_response_with_tool_use_triggers_two_phase_flow(mock_anthropic_client, mocker):
    """Test that tool use triggers two-phase API flow"""
    # Arrange
    tool_use_resp = create_tool_use_response(
        tool_name="search_course_content",
        tool_input={"query": "What is MCP?"},
        tool_id="tool_123"
    )
    final_resp = create_text_response("MCP is a protocol for AI systems")

    mock_anthropic_client.messages.create.side_effect = [tool_use_resp, final_resp]

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Found info about MCP..."
    mock_tool_manager.get_tool_definitions.return_value = [
        {"name": "search_course_content"}
    ]

    # Patch Anthropic constructor
    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        result = generator.generate_response(
            query="What is MCP?",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager
        )

    # Assert
    assert result == "MCP is a protocol for AI systems"
    assert mock_anthropic_client.messages.create.call_count == 2
    mock_tool_manager.execute_tool.assert_called_once_with(
        "search_course_content",
        query="What is MCP?"
    )

    # Verify second call has no tools parameter
    second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]
    assert "tools" not in second_call_kwargs


@pytest.mark.unit
def test_handle_tool_execution_message_structure(mock_anthropic_client, mocker):
    """Test that tool execution creates correct message structure"""
    # Arrange
    tool_use_resp = create_tool_use_response(
        tool_name="search_course_content",
        tool_input={"query": "test"},
        tool_id="tool_abc123"
    )
    final_resp = create_text_response("Final answer")

    mock_anthropic_client.messages.create.side_effect = [tool_use_resp, final_resp]

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Tool output string"
    mock_tool_manager.get_tool_definitions.return_value = [{"name": "search_course_content"}]

    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        generator.generate_response(
            query="test",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager
        )

    # Assert - check the second API call structure
    second_call = mock_anthropic_client.messages.create.call_args_list[1]
    messages = second_call[1]["messages"]

    # Find the tool_result message
    tool_result_msg = None
    for msg in messages:
        if msg["role"] == "user" and isinstance(msg["content"], list):
            for content_block in msg["content"]:
                if content_block.get("type") == "tool_result":
                    tool_result_msg = content_block
                    break

    assert tool_result_msg is not None
    assert tool_result_msg["tool_use_id"] == "tool_abc123"
    assert tool_result_msg["content"] == "Tool output string"


@pytest.mark.unit
def test_conversation_history_injected_into_system_prompt(mock_anthropic_client, mocker):
    """Test that conversation history is included in system prompt"""
    # Arrange
    text_response = create_text_response("Response with history")
    mock_anthropic_client.messages.create.return_value = text_response

    conversation_history = "User: Hi\nAssistant: Hello"

    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        generator.generate_response(
            query="Follow up question",
            conversation_history=conversation_history
        )

    # Assert - check system prompt includes history
    call_kwargs = mock_anthropic_client.messages.create.call_args[1]
    system_prompt = call_kwargs["system"]

    assert system_prompt is not None
    assert conversation_history in system_prompt


@pytest.mark.unit
def test_temperature_set_to_zero(mock_anthropic_client, mocker):
    """Test that temperature is set to 0 for deterministic responses"""
    # Arrange
    text_response = create_text_response("Response")
    mock_anthropic_client.messages.create.return_value = text_response

    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        generator.generate_response(query="Test")

    # Assert
    call_kwargs = mock_anthropic_client.messages.create.call_args[1]
    assert call_kwargs["temperature"] == 0


@pytest.mark.unit
def test_tool_choice_auto_when_tools_provided(mock_anthropic_client, mocker):
    """Test that tool_choice is set to auto when tools are provided"""
    # Arrange
    text_response = create_text_response("Response")
    mock_anthropic_client.messages.create.return_value = text_response

    mock_tool_manager = Mock()
    tools = [{"name": "search_course_content"}]

    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        generator.generate_response(
            query="Test",
            tools=tools,
            tool_manager=mock_tool_manager
        )

    # Assert
    call_kwargs = mock_anthropic_client.messages.create.call_args[1]
    assert "tool_choice" in call_kwargs
    assert call_kwargs["tool_choice"]["type"] == "auto"
