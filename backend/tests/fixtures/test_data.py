"""Predefined test data for consistent testing"""
from models import Course, Lesson


MCP_COURSE = Course(
    title="Introduction to Model Context Protocol",
    course_link="https://example.com/mcp",
    instructor="Dr. Smith",
    lessons=[
        Lesson(
            lesson_number=1,
            title="MCP Basics",
            lesson_link="https://example.com/mcp/lesson1"
        ),
        Lesson(
            lesson_number=2,
            title="Tool Calling",
            lesson_link="https://example.com/mcp/lesson2"
        )
    ]
)


COMPUTER_USE_COURSE = Course(
    title="Computer Use with Claude",
    course_link="https://example.com/computer-use",
    instructor="Dr. Johnson",
    lessons=[
        Lesson(lesson_number=1, title="Introduction"),
        Lesson(lesson_number=2, title="Advanced Usage")
    ]
)
