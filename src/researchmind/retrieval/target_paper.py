"""Target paper identification, title matching, and clarification logic."""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

from researchmind.config import settings

logger = logging.getLogger(__name__)


class TargetPaperMatch(BaseModel):
    """Result of identifying a target research paper from a user query."""
    paper_id: str = ""
    title: str = ""
    confidence: float = 0.0
    is_explicit_target_query: bool = False
    needs_clarification: bool = False
    clarification_message: str = ""


class PaperCatalogRegistry:
    """In-memory index of catalog papers for fast title and ID matching."""

    _instance: Optional["PaperCatalogRegistry"] = None
    _catalog: Dict[str, Dict[str, Any]] = {}
    _normalized_index: List[Dict[str, Any]] = []

    def __init__(self, catalog_path: Optional[Path] = None):
        self.catalog_path = catalog_path or (settings.metadata_path / "catalog.json")
        self._load_catalog()

    @classmethod
    def get_instance(cls, catalog_path: Optional[Path] = None) -> "PaperCatalogRegistry":
        if cls._instance is None:
            cls._instance = cls(catalog_path)
        return cls._instance

    def _normalize(self, text: str) -> str:
        """Lowercase, remove punctuation and extra whitespace."""
        text = re.sub(r"[^\w\s]", " ", text.lower())
        return re.sub(r"\s+", " ", text).strip()

    def _tokenize(self, text: str) -> set:
        """Meaningful word tokens (len >= 3, excluding common stop words)."""
        stop_words = {"the", "and", "for", "with", "via", "using", "from", "paper", "research", "study"}
        words = re.findall(r"\b[a-zA-Z0-9-]{3,}\b", text.lower())
        return {w for w in words if w not in stop_words}

    def _load_catalog(self):
        if not self.catalog_path.exists():
            logger.warning(f"Catalog file not found at {self.catalog_path}")
            return

        try:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                self._catalog = json.load(f)

            self._normalized_index = []
            for pid, info in self._catalog.items():
                title = info.get("title") or ""
                filename = info.get("filename") or ""
                clean_title = self._normalize(title)
                tokens = self._tokenize(title)

                self._normalized_index.append({
                    "paper_id": pid,
                    "title": title,
                    "filename": filename,
                    "normalized_title": clean_title,
                    "tokens": tokens,
                })
            logger.info(f"Loaded {len(self._normalized_index)} papers into PaperCatalogRegistry.")
        except Exception as e:
            logger.error(f"Failed to load paper catalog: {e}")

    def find_target_paper(
        self,
        query: str,
        min_confidence: float = 0.60,
        context_paper: Optional[TargetPaperMatch] = None,
    ) -> Optional[TargetPaperMatch]:
        """Detect and match target paper from query string, resolving conversational context if provided."""
        if not self._normalized_index:
            self._load_catalog()

        q_norm = self._normalize(query)
        q_tokens = self._tokenize(query)

        # Step 1: Check for explicit paper ID mention (e.g. paper_0853d9c3ae9c)
        pid_match = re.search(r"\b(paper_[0-9a-f]{12})\b", query, re.IGNORECASE)
        if pid_match:
            pid = pid_match.group(1).lower()
            for entry in self._normalized_index:
                if entry["paper_id"] == pid:
                    return TargetPaperMatch(
                        paper_id=entry["paper_id"],
                        title=entry["title"],
                        confidence=1.0,
                        is_explicit_target_query=True,
                    )

        # Step 2: Check for explicit linguistic paper cues
        # Examples: "research paper GEOAI-BASED...", "in the paper...", "technique followed in the research paper..."
        paper_cue_patterns = [
            r"research\s+paper\s*[:\s*]+([^\?]+)",
            r"in\s+(?:the\s+)?paper\s*[:\s*]+([^\?]+)",
            r"for\s+(?:the\s+)?(?:paper|model)\s*[:\s*]+([^\?]+)",
            r"paper\s+titled\s*[:\s*]+([^\?]+)",
            r"paper\s+named\s*[:\s*]+([^\?]+)",
            r'["\']([^"\']{15,})["\']',  # Quoted long title
        ]

        extracted_candidate = ""
        is_explicit_cue = False

        for pattern in paper_cue_patterns:
            m = re.search(pattern, query, re.IGNORECASE)
            if m:
                raw_cand = m.group(1).strip()
                # Strip trailing question/clause after comma (e.g. ", how is error detected")
                cleaned_cand = re.split(r",\s*(?:how|what|why|which|where|when|can|does|did|is|are)\b", raw_cand, flags=re.IGNORECASE)[0].strip()
                extracted_candidate = cleaned_cand
                is_explicit_cue = True
                break

        # Check if generic cue like "in the research paper" without title or ambiguous
        generic_unspecified_cues = [
            r"^(what|how|why|describe|explain).*(in the research paper|in the proposed method|in this paper)\??$",
            r"^(what|how).*(technique followed in the research paper)\??$",
        ]
        for g_pat in generic_unspecified_cues:
            if re.search(g_pat, q_norm) and len(extracted_candidate.split()) <= 2:
                # If we have an active context paper from the ongoing conversation, resolve to it!
                if context_paper and getattr(context_paper, "paper_id", None):
                    return TargetPaperMatch(
                        paper_id=context_paper.paper_id,
                        title=context_paper.title,
                        confidence=1.0,
                        is_explicit_target_query=True,
                        needs_clarification=False,
                    )
                # Otherwise, user asked about "the research paper" without context and didn't specify which one
                return TargetPaperMatch(
                    paper_id="",
                    title="",
                    confidence=0.0,
                    is_explicit_target_query=True,
                    needs_clarification=True,
                    clarification_message=(
                        "Could you please clarify which paper you are referring to? "
                        "I was unable to identify the target paper from your query across the 316 indexed research papers."
                    ),
                )

        # Step 3: Match against catalog
        best_match = None
        best_score = 0.0

        search_text = extracted_candidate if extracted_candidate else query
        search_norm = self._normalize(search_text)
        search_tokens = self._tokenize(search_text)

        for entry in self._normalized_index:
            title_norm = entry["normalized_title"]
            title_tokens = entry["tokens"]
            if not title_tokens:
                continue

            # Check exact substring containment in either direction
            if title_norm and len(title_norm) > 15:
                if title_norm in q_norm or title_norm in search_norm:
                    score = 1.0
                elif (search_norm and len(search_norm) > 20 and search_norm in title_norm):
                    score = 0.95
                elif any(search_norm in part for part in title_norm.split(":") if len(search_norm) > 15):
                    score = 0.90
                else:
                    # Token overlap against title tokens
                    target_tokens_pool = search_tokens if search_tokens else q_tokens
                    common = title_tokens.intersection(target_tokens_pool)
                    if common:
                        title_cov = len(common) / len(title_tokens)
                        search_cov = len(common) / len(target_tokens_pool) if target_tokens_pool else 0
                        # If a large sequence of key tokens matches (>= 4 tokens)
                        if len(common) >= 4:
                            score = max((title_cov * 0.7) + (search_cov * 0.3), 0.78)
                        else:
                            score = (title_cov * 0.7) + (search_cov * 0.3)
                    else:
                        score = 0.0
            else:
                score = 0.0

            if score > best_score:
                best_score = score
                best_match = entry

        # Decision rule
        if best_match and best_score >= min_confidence:
            return TargetPaperMatch(
                paper_id=best_match["paper_id"],
                title=best_match["title"],
                confidence=round(best_score, 3),
                is_explicit_target_query=is_explicit_cue or (best_score >= 0.75),
                needs_clarification=False,
            )

        # If user has an active context paper and current query uses anaphoric pronouns or follow-up phrasing
        if context_paper and getattr(context_paper, "paper_id", None):
            if has_anaphoric_reference(query) or is_conversational_follow_up(query):
                logger.info(
                    f"Context-aware resolution: Bound query '{query}' to active paper '{context_paper.title}' ({context_paper.paper_id})"
                )
                return TargetPaperMatch(
                    paper_id=context_paper.paper_id,
                    title=context_paper.title,
                    confidence=1.0,
                    is_explicit_target_query=True,
                    needs_clarification=False,
                )

        # If user explicitly asked about a specific paper, but confidence is low
        if is_explicit_cue and (not best_match or best_score < min_confidence):
            return TargetPaperMatch(
                paper_id="",
                title="",
                confidence=round(best_score, 3) if best_match else 0.0,
                is_explicit_target_query=True,
                needs_clarification=True,
                clarification_message=(
                    f"Could you please clarify which paper you are referring to? "
                    f"I found a borderline match ('{best_match['title'] if best_match else 'None'}' with confidence {best_score:.2f}), "
                    "which is below the certainty threshold. Please provide the exact title, authors, or paper ID."
                ),
            )

        return None


def has_anaphoric_reference(query: str) -> bool:
    """Check if query contains pronouns or references back to an existing entity/paper."""
    q_lower = query.lower()
    patterns = [
        r"\b(it|its|itself)\b",
        r"\b(this|that)\s+(paper|study|model|approach|framework|architecture|technique|method|work|author|authors|article)\b",
        r"\bthe\s+(paper|study|model|approach|framework|architecture|technique|method|work|authors?|article)\b",
        r"\btheir\s+(approach|method|methodology|findings|results|architecture|model|framework|paper|work|claims)\b",
        r"\b(they|them)\b",
        r"\b(in\s+the\s+paper|in\s+this\s+paper|in\s+the\s+research\s+paper)\b",
        r"\b(summarize\s+it|explain\s+it|what\s+about\s+it)\b",
    ]
    for pat in patterns:
        if re.search(pat, q_lower):
            return True
    return False


def is_conversational_follow_up(query: str) -> bool:
    """Detect if query is a follow-up question likely targeting the active topic in conversation."""
    q_lower = query.lower()
    # Explicit cross-corpus queries shouldn't bind to single paper
    cross_corpus_cues = ["all papers", "across papers", "other papers", "compare papers", "in the database", "overall corpus"]
    if any(c in q_lower for c in cross_corpus_cues):
        return False

    follow_up_cues = [
        r"^(what|how|why|can\s+you|explain|describe|tell\s+me\s+about)\s+(the\s+)?(dataset|methodology|technique|architecture|results|evaluation|limitations|contributions|findings|experiments|conclusions?)\b",
        r"^(what\s+are|what\s+were)\s+(the\s+)?(limitations|results|contributions|findings|datasets?|metrics)\b",
        r"^(what\s+was\s+the\s+accuracy|how\s+did\s+it\s+perform|what\s+score\s+did\s+it\s+achieve)\b",
    ]
    for pat in follow_up_cues:
        if re.search(pat, q_lower):
            return True
    return False


def contextualize_retrieval_query(
    query: str,
    target_paper: Optional[TargetPaperMatch],
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Enrich a conversational or pronoun-heavy query into a standalone query for dense/sparse retrieval."""
    if not target_paper or not target_paper.title:
        return query

    clean_query = query.strip()
    title = target_paper.title.strip()

    # If the title is already present in the query, return as-is
    if title.lower() in clean_query.lower():
        return clean_query

    # Prepend the title to ensure dense embeddings and BM25 keywords match the specific paper
    return f"{title}: {clean_query}"


def identify_target_paper(
    query: str,
    catalog_path: Optional[Path] = None,
    min_confidence: float = 0.60,
    context_paper: Optional[TargetPaperMatch] = None,
) -> Optional[TargetPaperMatch]:
    """Convenience functional wrapper to identify target paper from query and optional context."""
    registry = PaperCatalogRegistry.get_instance(catalog_path)
    return registry.find_target_paper(
        query,
        min_confidence=min_confidence,
        context_paper=context_paper,
    )
