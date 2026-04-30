from src.rag_core.generator import generate_course_recommendation
from src.rag_core.parser import parse_recommendation_payload
from src.rag_core.pipeline import (
    CourseIndexingStats,
    RAGPipeline,
    RecommendationResult,
    RetrievedCourse,
)
from src.rag_core.prompt_builder import (
    PROMPTS_DIR,
    format_available_content,
    render_typed_prompt,
)
from src.rag_core.retriever import (
    RESOURCE_TYPE_BY_RECOMMENDATION_TYPE,
    build_resource_type_filter,
    resource_type_for_recommendation,
    retrieve_resources,
    retrieve_similar_courses,
)
from src.rag_core.schemas import RetrievedResourceRecord

__all__ = [
    # Pipeline (generic course recommendation)
    "CourseIndexingStats",
    "RAGPipeline",
    "RecommendationResult",
    "RetrievedCourse",
    "generate_course_recommendation",
    "retrieve_similar_courses",
    # Typed-recommendation pipeline
    "PROMPTS_DIR",
    "RESOURCE_TYPE_BY_RECOMMENDATION_TYPE",
    "RetrievedResourceRecord",
    "build_resource_type_filter",
    "format_available_content",
    "parse_recommendation_payload",
    "render_typed_prompt",
    "resource_type_for_recommendation",
    "retrieve_resources",
]
