"""Generation package for ResearchMind."""

from researchmind.generation.prompt import (
    ACADEMIC_SYSTEM_PROMPT,
    build_research_context,
    build_user_prompt,
)
from researchmind.generation.generator import LLMGenerator

__all__ = [
    "ACADEMIC_SYSTEM_PROMPT",
    "build_research_context",
    "build_user_prompt",
    "LLMGenerator",
]
