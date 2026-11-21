"""
HospitalOps AI — Knowledge Answer Generation Package.

Provides grounded RAG question answering over hospital knowledge documents.
"""

from app.knowledge.generation.answer_generator import GroundedAnswerGenerator
from app.knowledge.generation.citation_validator import (
    build_all_retrieved_references,
    extract_markers,
    validate_citations,
)
from app.knowledge.generation.contracts import (
    AnswerHealthResponse,
    AnswerStatus,
    AnswerType,
    CitationReference,
    GenerationMetadata,
    KnowledgeAnswerRequest,
    KnowledgeAnswerResponse,
    RawAnswerOutput,
    RetrievalSummary,
)
from app.knowledge.generation.prompt_builder import (
    PROMPT_VERSION,
    build_correction_message,
    build_system_prompt,
    build_user_message,
    is_clinical_query,
)
from app.knowledge.generation.provider import (
    LLMMessage,
    LLMProvider,
    MockLLMProvider,
    NullLLMProvider,
    OpenAICompatibleProvider,
)
from app.knowledge.generation.service import KnowledgeAnswerService

__all__ = [
    "AnswerHealthResponse",
    "AnswerStatus",
    "AnswerType",
    "CitationReference",
    "GenerationMetadata",
    "GroundedAnswerGenerator",
    "KnowledgeAnswerRequest",
    "KnowledgeAnswerResponse",
    "KnowledgeAnswerService",
    "LLMMessage",
    "LLMProvider",
    "MockLLMProvider",
    "NullLLMProvider",
    "OpenAICompatibleProvider",
    "PROMPT_VERSION",
    "RawAnswerOutput",
    "RetrievalSummary",
    "build_all_retrieved_references",
    "build_correction_message",
    "build_system_prompt",
    "build_user_message",
    "extract_markers",
    "is_clinical_query",
    "validate_citations",
]
