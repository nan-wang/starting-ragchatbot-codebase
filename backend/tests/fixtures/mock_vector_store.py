"""Helper functions to create SearchResults objects for testing"""
from vector_store import SearchResults


def create_search_results(num_results: int, course_title: str) -> SearchResults:
    """Create SearchResults with specified number of documents"""
    documents = [f"Content chunk {i} about the course" for i in range(num_results)]
    metadata = [
        {
            "course_title": course_title,
            "lesson_number": (i % 3) + 1,  # Rotate through lessons 1-3
            "chunk_index": i
        }
        for i in range(num_results)
    ]
    distances = [0.1 * i for i in range(num_results)]

    return SearchResults(
        documents=documents,
        metadata=metadata,
        distances=distances,
        error=None
    )


def create_empty_search_results(error_msg: str = None) -> SearchResults:
    """Create empty SearchResults with optional error"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[],
        error=error_msg
    )
