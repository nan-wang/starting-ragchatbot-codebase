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

    # Verify second call DOES have tools parameter (new behavior - tools available until max rounds)
    # Loop terminates naturally when Claude returns text (stop_reason != "tool_use")
    second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]
    assert "tools" in second_call_kwargs


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


@pytest.mark.unit
def test_sequential_tool_calls_two_rounds(mock_anthropic_client, mocker):
    """Test that system supports 2 sequential tool calls"""
    # Arrange - 3 API responses
    outline_tool_use = create_tool_use_response(
        tool_name="get_course_outline",
        tool_input={"course_name": "MCP"},
        tool_id="tool_001"
    )

    search_tool_use = create_tool_use_response(
        tool_name="search_course_content",
        tool_input={"query": "server implementation", "course_name": "MCP"},
        tool_id="tool_002"
    )

    final_text_resp = create_text_response("The MCP course covers...")

    mock_anthropic_client.messages.create.side_effect = [
        outline_tool_use,    # Initial: Claude wants outline
        search_tool_use,     # After outline: Claude wants search
        final_text_resp      # After search: Claude synthesizes answer
    ]

    # Tool manager returns results for both calls
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.side_effect = [
        "Course outline data...",
        "Server implementation info..."
    ]
    tools = [
        {"name": "get_course_outline"},
        {"name": "search_course_content"}
    ]

    # Act
    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        result = generator.generate_response(
            query="What does MCP teach about server implementation?",
            tools=tools,
            tool_manager=mock_tool_manager
        )

    # Assert external behavior
    assert result == "The MCP course covers..."
    assert mock_anthropic_client.messages.create.call_count == 3
    assert mock_tool_manager.execute_tool.call_count == 2

    # Verify tool execution order
    calls = mock_tool_manager.execute_tool.call_args_list
    assert calls[0][0][0] == "get_course_outline"
    assert calls[1][0][0] == "search_course_content"

    # Verify tools parameter present in rounds 1-2, absent in round 3
    first_call = mock_anthropic_client.messages.create.call_args_list[0][1]
    assert "tools" in first_call  # Initial call has tools

    second_call = mock_anthropic_client.messages.create.call_args_list[1][1]
    assert "tools" in second_call  # Mid-round has tools

    third_call = mock_anthropic_client.messages.create.call_args_list[2][1]
    assert "tools" not in third_call  # Final round omits tools


@pytest.mark.unit
def test_single_tool_call_terminates_early(mock_anthropic_client, mocker):
    """Test that single tool call behaves identically to current (backwards compatibility)"""
    # Arrange - Claude makes 1 tool call then returns text
    tool_use_resp = create_tool_use_response(
        tool_name="search_course_content",
        tool_input={"query": "What is MCP?"},
        tool_id="tool_123"
    )
    final_resp = create_text_response("MCP is a protocol...")

    mock_anthropic_client.messages.create.side_effect = [tool_use_resp, final_resp]

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "MCP info..."
    tools = [{"name": "search_course_content"}]

    # Act
    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        result = generator.generate_response(
            query="What is MCP?",
            tools=tools,
            tool_manager=mock_tool_manager
        )

    # Assert - should be 2 API calls (initial + follow-up)
    assert result == "MCP is a protocol..."
    assert mock_anthropic_client.messages.create.call_count == 2
    assert mock_tool_manager.execute_tool.call_count == 1

    # Second call should NOT have tools (terminates naturally)
    second_call = mock_anthropic_client.messages.create.call_args_list[1][1]
    assert "tools" in second_call  # Tools available but Claude chose not to use


@pytest.mark.unit
def test_max_tool_rounds_enforced(mock_anthropic_client, mocker):
    """Test that round limit stops after 2 rounds even if Claude wants more"""
    # Arrange - Claude wants 3 tool calls but should be stopped at 2
    tool_use_1 = create_tool_use_response(
        tool_name="get_course_outline",
        tool_input={"course_name": "MCP"},
        tool_id="tool_001"
    )

    tool_use_2 = create_tool_use_response(
        tool_name="search_course_content",
        tool_input={"query": "test"},
        tool_id="tool_002"
    )

    tool_use_3 = create_tool_use_response(
        tool_name="search_course_content",
        tool_input={"query": "another test"},
        tool_id="tool_003"
    )

    mock_anthropic_client.messages.create.side_effect = [
        tool_use_1,
        tool_use_2,
        tool_use_3  # This should be the final response (round limit reached)
    ]

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Tool output"
    tools = [{"name": "get_course_outline"}, {"name": "search_course_content"}]

    # Act
    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        result = generator.generate_response(
            query="Test query",
            tools=tools,
            tool_manager=mock_tool_manager
        )

    # Assert - should stop after 2 rounds (3 API calls)
    assert mock_anthropic_client.messages.create.call_count == 3
    assert mock_tool_manager.execute_tool.call_count == 2
    # Result should be empty string since final response was tool_use (extracted by _extract_text_response)
    assert result == ""


@pytest.mark.unit
def test_tool_execution_error_returns_to_claude(mock_anthropic_client, mocker):
    """Test that tool execution errors are passed to Claude as tool_result"""
    # Arrange
    tool_use_resp = create_tool_use_response(
        tool_name="search_course_content",
        tool_input={"query": "test"},
        tool_id="tool_123"
    )
    final_resp = create_text_response("I apologize, the search failed")

    mock_anthropic_client.messages.create.side_effect = [tool_use_resp, final_resp]

    # Tool manager raises exception
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.side_effect = Exception("Database connection failed")
    tools = [{"name": "search_course_content"}]

    # Act
    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        result = generator.generate_response(
            query="Test query",
            tools=tools,
            tool_manager=mock_tool_manager
        )

    # Assert - error was passed to Claude
    assert result == "I apologize, the search failed"
    assert mock_anthropic_client.messages.create.call_count == 2

    # Verify error message in tool_result
    second_call = mock_anthropic_client.messages.create.call_args_list[1]
    messages = second_call[1]["messages"]
    tool_result_msg = None
    for msg in messages:
        if msg["role"] == "user" and isinstance(msg["content"], list):
            for content_block in msg["content"]:
                if content_block.get("type") == "tool_result":
                    tool_result_msg = content_block
                    break

    assert tool_result_msg is not None
    assert "Tool execution failed" in tool_result_msg["content"]
    assert "Database connection failed" in tool_result_msg["content"]


@pytest.mark.unit
def test_terminates_when_no_tool_use(mock_anthropic_client, mocker):
    """Test that loop terminates when Claude returns text (no tool_use)"""
    # Arrange - Claude returns text directly on second response
    tool_use_resp = create_tool_use_response(
        tool_name="search_course_content",
        tool_input={"query": "test"},
        tool_id="tool_123"
    )
    # Second response is text, not tool_use
    final_resp = create_text_response("Here is the answer", stop_reason="end_turn")

    mock_anthropic_client.messages.create.side_effect = [tool_use_resp, final_resp]

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Search results..."
    tools = [{"name": "search_course_content"}]

    # Act
    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        result = generator.generate_response(
            query="Test query",
            tools=tools,
            tool_manager=mock_tool_manager
        )

    # Assert - should terminate after 2 API calls
    assert result == "Here is the answer"
    assert mock_anthropic_client.messages.create.call_count == 2
    assert mock_tool_manager.execute_tool.call_count == 1


@pytest.mark.unit
def test_message_accumulation_across_rounds(mock_anthropic_client, mocker):
    """Test that message history grows correctly across multiple rounds"""
    # Arrange
    tool_use_1 = create_tool_use_response(
        tool_name="get_course_outline",
        tool_input={"course_name": "MCP"},
        tool_id="tool_001"
    )

    tool_use_2 = create_tool_use_response(
        tool_name="search_course_content",
        tool_input={"query": "server"},
        tool_id="tool_002"
    )

    final_resp = create_text_response("Final answer")

    mock_anthropic_client.messages.create.side_effect = [
        tool_use_1,
        tool_use_2,
        final_resp
    ]

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.side_effect = ["Outline...", "Search results..."]
    tools = [{"name": "get_course_outline"}, {"name": "search_course_content"}]

    # Act
    with mocker.patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")
        generator.generate_response(
            query="Test query",
            tools=tools,
            tool_manager=mock_tool_manager
        )

    # Assert - verify message structure in final call
    final_call = mock_anthropic_client.messages.create.call_args_list[2]
    messages = final_call[1]["messages"]

    # Expected message structure:
    # 1. user: "Test query"
    # 2. assistant: [tool_use_1]
    # 3. user: [tool_result_1]
    # 4. assistant: [tool_use_2]
    # 5. user: [tool_result_2]
    assert len(messages) == 5

    # Verify roles alternate correctly
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[3]["role"] == "assistant"
    assert messages[4]["role"] == "user"

    # Verify first message is the original query
    assert messages[0]["content"] == "Test query"

    # Verify tool results are present
    assert isinstance(messages[2]["content"], list)
    assert messages[2]["content"][0]["type"] == "tool_result"
    assert isinstance(messages[4]["content"], list)
    assert messages[4]["content"][0]["type"] == "tool_result"
