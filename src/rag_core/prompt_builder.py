from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from src.rag_core.schemas import RetrievedCourse, RetrievedResourceRecord

# ---------------------------------------------------------------------------
# Shared path to the prompts directory
# ---------------------------------------------------------------------------

#: Absolute path to ``src/prompts/``.  Both the generic RAGPipeline and the
#: typed-recommendation pipeline read their templates from this directory.
PROMPTS_DIR: Path = Path(__file__).resolve().parents[1] / "prompts"


def render_prompt(*, prompt_path: Path, courses_context: str, user_query: str) -> str:
    template = prompt_path.read_text(encoding="utf-8")
    if "{courses_context}" not in template or "{user_query}" not in template:
        raise ValueError("Prompt template must contain '{courses_context}' and '{user_query}' placeholders.")
    return template.format(courses_context=courses_context, user_query=user_query)


# ---------------------------------------------------------------------------
# Typed-recommendation prompt helpers
# ---------------------------------------------------------------------------


def format_available_content(resources: Sequence[RetrievedResourceRecord]) -> str:
    """Format a list of retrieved resources into a numbered context block for the LLM.

    Each resource is rendered with its title, type, URL, a short text fragment
    (capped at 500 characters), and its relevance score.

    Args:
        resources: Retrieved resources, typically already sorted by score.

    Returns:
        Multi-line string ready to be injected into a prompt template as
        ``{available_content}``.
    """
    lines: list[str] = []
    for index, resource in enumerate(resources, start=1):
        fragment = resource.chunk_text.replace("\n", " ").strip()
        if len(fragment) > 500:
            fragment = fragment[:497] + "..."
        lines.append(
            "\n".join(
                [
                    f"{index}. {resource.title}",
                    f"Type: {resource.resource_type or 'unknown'}",
                    f"URL: {resource.url or 'n/a'}",
                    f"Fragment: {fragment or 'n/a'}",
                    f"Relevance: {resource.score:.3f}",
                ]
            )
        )
    return "\n\n".join(lines)


def render_typed_prompt(
    *,
    recommendation_type: str,
    available_content: str,
    digital_traces: str,
    prompts_dir: Path,
) -> str:
    """Render a type-specific recommendation prompt.

    Reads the template file ``{prompts_dir}/{recommendation_type}.txt`` and
    substitutes the ``{available_content}`` and ``{digital_traces}``
    placeholders.

    Args:
        recommendation_type: Slug identifying the recommendation type
            (e.g. ``"cold"``, ``"hot"``, ``"warm"``, ``"after_sale"``).
        available_content: Pre-formatted string listing the retrieved resources.
        digital_traces: User's digital footprint profile text.
        prompts_dir: Directory that contains the ``*.txt`` prompt templates.

    Returns:
        Fully rendered prompt string ready to be sent to the LLM.

    Raises:
        ValueError: If the prompt file for *recommendation_type* does not exist.
    """
    prompt_path = prompts_dir / f"{recommendation_type}.txt"
    if not prompt_path.exists():
        raise ValueError(f"Prompt file for recommendation type '{recommendation_type}' was not found (expected: {prompt_path}).")
    template = prompt_path.read_text(encoding="utf-8")
    return template.format(available_content=available_content, digital_traces=digital_traces)


# ---------------------------------------------------------------------------
# Course-pipeline prompt helpers
# ---------------------------------------------------------------------------


def format_courses_context(courses: Sequence[RetrievedCourse]) -> str:
    if not courses:
        return "Похожие курсы не найдены."

    lines: list[str] = []
    for index, course in enumerate(courses, start=1):
        short_description = course.description.strip().replace("\n", " ")
        if len(short_description) > 300:
            short_description = short_description[:297] + "..."
        lines.append(f"{index}. {course.name}\nОписание: {short_description}\nСемантическая релевантность: {course.score:.3f}")
    return "\n\n".join(lines)
