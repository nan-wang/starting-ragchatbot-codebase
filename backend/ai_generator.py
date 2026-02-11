import anthropic
from typing import List, Optional, Dict, Any


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
- **get_course_outline**: Use for questions about course structure, lesson lists, what a course covers, or course overview. When presenting the outline, include the course title, course link, and for each lesson: lesson number and lesson title.
- **search_course_content**: Use for questions about specific topics, concepts, or details within course content.

Tool Usage Rules:
- **Up to 2 sequential tool calls per query** - Use multiple tools if needed to answer completely
- Example: First get_course_outline to understand structure, then search_course_content for details
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course structure questions**: Use get_course_outline, then present the outline
- **Course content questions**: Use search_course_content, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the outline"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)

        # Return direct response
        return response.content[0].text

    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        Supports up to 2 sequential tool call rounds per query.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        MAX_TOOL_ROUNDS = 2

        messages = base_params["messages"].copy()
        current_response = initial_response
        current_round = 0

        while current_round < MAX_TOOL_ROUNDS:
            current_round += 1

            # Termination check: no more tool use
            if current_response.stop_reason != "tool_use":
                break

            # Add AI's tool use response to messages
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls and collect results
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    try:
                        tool_result_str = tool_manager.execute_tool(
                            content_block.name, **content_block.input
                        )
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": tool_result_str,
                            }
                        )
                    except AttributeError:
                        # Malformed tool block - skip
                        continue
                    except Exception as e:
                        # Tool execution error - return error to Claude
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": f"Tool execution failed: {str(e)}",
                            }
                        )

            # If no valid tool results, terminate
            if not tool_results:
                break

            # Add tool results as user message
            messages.append({"role": "user", "content": tool_results})

            # Prepare next API call
            api_params = {**self.base_params, "messages": messages, "system": base_params["system"]}

            # Add tools for mid-rounds, omit on final round to force text response
            if current_round < MAX_TOOL_ROUNDS and "tools" in base_params:
                api_params["tools"] = base_params["tools"]
                api_params["tool_choice"] = {"type": "auto"}

            # Get next response
            current_response = self.client.messages.create(**api_params)

        return self._extract_text_response(current_response)

    def _extract_text_response(self, response) -> str:
        """
        Extract text content from API response.

        Args:
            response: Anthropic API response object

        Returns:
            Text string, or empty string if no text found
        """
        if not response.content:
            return ""

        for block in response.content:
            if hasattr(block, "type") and block.type == "text":
                return block.text

        return ""
