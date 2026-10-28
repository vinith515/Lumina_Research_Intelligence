"""Answer claim extraction and evidence grounding verification."""

import logging
import re
from typing import List, Dict, Optional, Tuple, Set
from researchmind.schemas.models import (
    RetrievalCandidate,
    Citation,
    ClaimExplanation,
    GroundingAssessment,
    EvidenceStrength,
)
from researchmind.xai.evidence_strength import calculate_evidence_strength
from researchmind.config import settings

logger = logging.getLogger(__name__)


def extract_claims(answer_text: str) -> List[str]:
    """Split generated answer into atomic claim statements, removing markdown headers and bullet markers."""
    lines = answer_text.strip().split("\n")
    sentences: List[str] = []

    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line or cleaned_line.startswith("#") or cleaned_line.lower().startswith("source"):
            continue

        # Strip bullet points
        cleaned_line = re.sub(r"^[-*•\d\.]+\s*", "", cleaned_line)
        if not cleaned_line:
            continue

        # Split on sentence terminals (.!?)
        raw_sents = re.split(r"(?<=[.!?])\s+", cleaned_line)
        for s in raw_sents:
            s_clean = s.strip()
            # Remove citation tags like [1] or [Paper A, p.5] for text matching
            s_norm = re.sub(r"\[\d+\]", "", s_clean).strip()
            if len(s_norm) > 20 and not s_norm.lower().startswith("references") and not s_norm.lower().startswith("sources"):
                sentences.append(s_clean)

    return sentences


class GroundingVerifier:
    """Verifies that generated answer claims are strictly grounded in retrieved evidence chunks."""

    def __init__(self, token_overlap_threshold: float = 0.40):
        self.token_overlap_threshold = token_overlap_threshold

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful alphanumeric keywords, excluding short stop words."""
        words = re.findall(r"\b[a-zA-Z0-9-]{3,}\b", text.lower())
        stop_words = {
            "the", "and", "that", "this", "with", "from", "for", "are", "was", "were",
            "been", "have", "has", "had", "will", "would", "could", "should", "paper",
            "study", "authors", "model", "using", "which", "their", "these", "those",
            "such", "also", "into", "more", "most", "than", "when", "where", "while"
        }
        return {w for w in words if w not in stop_words}

    def _check_claim_answers_question(self, claim: str, query: str) -> Tuple[bool, str]:
        """Check if a claim directly answers the user's question rather than being metadata/boilerplate."""
        if not query:
            return True, "No query provided for question relevance check."

        claim_lower = claim.lower()
        query_lower = query.lower()

        # Pure boilerplate or metadata phrases do NOT answer questions
        boilerplate_cues = [
            "based on the retrieved research literature",
            "department of computer science",
            "university",
            "arxiv:",
            "project website:",
            "all rights reserved",
            "corrigendum",
            "conflict of interest",
            "author contributions",
        ]
        if any(cue in claim_lower for cue in boilerplate_cues):
            return False, "Claim is boilerplate or paper metadata (author/institution), not an answer."

        # If query asks about methodology, techniques, or how something works
        method_triggers = ["technique", "method", "how does", "how do", "approach", "workflow", "algorithm", "architecture"]
        if any(trig in query_lower for trig in method_triggers):
            # Check if claim describes methodological/technical concepts
            method_cues = [
                "use", "using", "propose", "framework", "model", "segment", "feature",
                "regulariz", "train", "dataset", "filter", "classif", "detect", "step",
                "process", "algorithm", "network", "approach", "evaluat", "validat",
                "achieve", "consist", "layer", "loss", "optimi", "denois", "distill"
            ]
            has_method_content = any(c in claim_lower for c in method_cues)
            if not has_method_content:
                return False, "Claim does not contain methodological actions or technical explanations addressing the query."

        return True, "Claim addresses query topic and technical context."

    def verify_grounding(
        self,
        answer: str,
        evidence_chunks: List[RetrievalCandidate],
        query: Optional[str] = None,
        target_paper_id: Optional[str] = None,
        target_paper_title: Optional[str] = None,
    ) -> Tuple[List[ClaimExplanation], GroundingAssessment]:
        """Assess grounding of all claims in the generated answer against retrieved evidence.
        
        Performs 3 distinct checks per claim:
        1. Is the claim supported by the cited passage? (Passage Support)
        2. Does the claim answer the user's question? (Question Relevance)
        3. Does the cited passage belong to the requested paper? (Target-Paper Consistency)
        
        Args:
            answer: Raw generated LLM answer.
            evidence_chunks: Chunks provided in the prompt context.
            query: User's original research question.
            target_paper_id: Optional ID of explicitly requested target paper.
            target_paper_title: Optional Title of explicitly requested target paper.
            
        Returns:
            Tuple of (List of ClaimExplanation objects, GroundingAssessment).
        """
        claims = extract_claims(answer)
        if not claims:
            # Fallback if no clean sentences parsed
            claims = [answer.strip()[:200]] if answer.strip() else []

        claim_explanations: List[ClaimExplanation] = []
        supported_count = 0

        for idx, claim in enumerate(claims, start=1):
            claim_keywords = self._extract_keywords(claim)
            matching_chunks: List[RetrievalCandidate] = []
            supporting_citations: List[Citation] = []

            # Check 1: Passage Support Check
            for cand in evidence_chunks:
                chunk_keywords = self._extract_keywords(cand.text)
                if not claim_keywords:
                    continue

                overlap = len(claim_keywords.intersection(chunk_keywords)) / len(claim_keywords)
                if overlap >= self.token_overlap_threshold:
                    matching_chunks.append(cand)
                    supporting_citations.append(
                        Citation(
                            paper_id=cand.paper_id,
                            title=cand.title,
                            authors=cand.authors,
                            page_start=cand.page_start,
                            page_end=cand.page_end,
                            section=cand.section,
                            subsection=cand.subsection,
                            chunk_id=cand.chunk_id,
                            retrieval_score=cand.final_score,
                            retrieval_method="hybrid_rerank",
                            snippet=cand.text[:150] + "...",
                        )
                    )

            is_supported_by_passage = len(matching_chunks) > 0

            # Check 2: Question Relevance Check
            answers_question, q_relevance_desc = self._check_claim_answers_question(claim, query or "")

            # Check 3: Target Paper Consistency Check
            if target_paper_id:
                if matching_chunks:
                    belongs_to_target_paper = all(c.paper_id == target_paper_id for c in matching_chunks)
                else:
                    belongs_to_target_paper = False
            else:
                belongs_to_target_paper = True

            # Overall claim grounding status requires all 3 checks
            is_grounded = is_supported_by_passage and answers_question and belongs_to_target_paper

            if is_grounded:
                supported_count += 1
                strength, strength_desc = calculate_evidence_strength(matching_chunks)
                rationale = (
                    f"Verified (3/3 checks passed): Supported by {len(matching_chunks)} chunks in target paper; "
                    f"addresses user question. ({strength_desc})"
                )
            else:
                failures = []
                if not is_supported_by_passage:
                    failures.append("unsupported by retrieved passage")
                if not answers_question:
                    failures.append(f"does not answer question ({q_relevance_desc})")
                if not belongs_to_target_paper:
                    failures.append(f"cross-paper contamination (expected paper '{target_paper_id}')")
                
                strength = EvidenceStrength.INSUFFICIENT
                rationale = f"Failed verification: {'; '.join(failures)}."

            claim_explanations.append(
                ClaimExplanation(
                    claim=claim,
                    claim_index=idx,
                    is_grounded=is_grounded,
                    is_supported_by_passage=is_supported_by_passage,
                    answers_question=answers_question,
                    belongs_to_target_paper=belongs_to_target_paper,
                    supporting_chunk_ids=[c.chunk_id for c in matching_chunks],
                    supporting_citations=supporting_citations,
                    evidence_strength=strength,
                    rationale=rationale,
                    verification_method="3-Way Relevance & Grounding Verification",
                )
            )

        total_claims = len(claims)
        unsupported_count = total_claims - supported_count
        grounded_ratio = round(supported_count / total_claims, 3) if total_claims > 0 else 1.0

        overall_strength, _ = calculate_evidence_strength(evidence_chunks)

        hallucination_warning = None
        if unsupported_count > 0:
            hallucination_warning = (
                f"Warning: {unsupported_count} out of {total_claims} claims failed 3-way verification (passage support, question relevance, or target paper match)."
            )

        assessment = GroundingAssessment(
            total_claims=total_claims,
            supported_claims=supported_count,
            unsupported_claims=unsupported_count,
            grounded_ratio=grounded_ratio,
            evidence_strength_overall=overall_strength,
            verification_method="3-Way Relevance & Grounding Verification",
            hallucination_warning=hallucination_warning,
            target_paper_id=target_paper_id,
            target_paper_title=target_paper_title,
        )

        return claim_explanations, assessment
