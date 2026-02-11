"""Helper functions to create realistic Anthropic API response mocks"""

from unittest.mock import Mock


def create_text_response(text: str, stop_reason: str = "end_turn"):
    """Create mock Anthropic text-only response"""
    text_block = Mock()
    text_block.type = "text"
    text_block.text = text

    response = Mock()
    response.stop_reason = stop_reason
    response.content = [text_block]
    return response


def create_tool_use_response(tool_name: str, tool_input: dict, tool_id: str = "tool_123"):
    """Create mock Anthropic tool use response"""
    tool_block = Mock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = tool_input
    tool_block.id = tool_id

    response = Mock()
    response.stop_reason = "tool_use"
    response.content = [tool_block]
    return response
