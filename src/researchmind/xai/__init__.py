"""Explainable AI (XAI) package for ResearchMind."""

from researchmind.xai.evidence_strength import calculate_evidence_strength
from researchmind.xai.grounding import GroundingVerifier, extract_claims
from researchmind.xai.explainer import ResearchXAIExplainer

__all__ = [
    "calculate_evidence_strength",
    "GroundingVerifier",
    "extract_claims",
    "ResearchXAIExplainer",
]
