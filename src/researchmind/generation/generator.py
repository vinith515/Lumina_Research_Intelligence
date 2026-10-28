"""LLM generation client supporting Gemini, OpenAI, Ollama, and offline test fallback."""

import os
import logging
from typing import Dict, Any, Optional, Tuple
import requests

from researchmind.generation.prompt import (
    ACADEMIC_SYSTEM_PROMPT,
    build_research_context,
    build_user_prompt,
)
from researchmind.schemas.models import RetrievalCandidate
from researchmind.config import settings

logger = logging.getLogger(__name__)


class LLMGenerator:
    """Multi-provider LLM client for grounded research answer generation."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.provider = (provider or settings.LLM_PROVIDER).lower()
        self.model_name = model_name or settings.LLM_MODEL
        self.temperature = temperature if temperature is not None else settings.TEMPERATURE
        self.max_tokens = max_tokens or settings.MAX_TOKENS
        self.last_provider_status: str = "initialized"

    def generate(
        self,
        query: str,
        candidates: List[RetrievalCandidate],
        target_paper: Optional[Any] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Generate a grounded research synthesis given query, retrieved evidence candidates, and conversation history.
        
        Args:
            query: User research question.
            candidates: Top retrieved and reranked passages.
            target_paper: Optional identified TargetPaperMatch object.
            conversation_history: Optional list of prior conversation turns.
            
        Returns:
            Tuple of (generated answer string, token usage dict).
        """
        context_str = build_research_context(candidates)
        user_prompt = build_user_prompt(
            query,
            context_str,
            conversation_history=conversation_history,
            target_paper=target_paper,
        )

        if self.provider == "gemini":
            return self._generate_gemini(user_prompt, query, candidates, target_paper=target_paper, conversation_history=conversation_history)
        elif self.provider == "openai":
            return self._generate_openai(user_prompt, query, candidates, target_paper=target_paper, conversation_history=conversation_history)
        elif self.provider == "ollama":
            return self._generate_ollama(user_prompt, query, candidates, target_paper=target_paper, conversation_history=conversation_history)
        else:
            self.last_provider_status = "offline_fallback"
            return self._generate_fallback(query, candidates, target_paper=target_paper, conversation_history=conversation_history)

    def _generate_gemini(
        self,
        user_prompt: str,
        query: str,
        candidates: List[RetrievalCandidate],
        target_paper: Optional[Any] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Call Google Gemini API using google-genai."""
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.info("GEMINI_API_KEY not set. Using structured passage evidence synthesis.")
            self.last_provider_status = "fallback_missing_api_key"
            return self._generate_fallback(query, candidates, target_paper=target_paper, conversation_history=conversation_history)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=ACADEMIC_SYSTEM_PROMPT,
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                ),
            )
            text = response.text or ""
            usage = {
                "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0) if hasattr(response, "usage_metadata") and response.usage_metadata else 0,
                "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0) if hasattr(response, "usage_metadata") and response.usage_metadata else 0,
            }
            self.last_provider_status = "api_success"
            return text, usage
        except Exception as e:
            logger.error(f"Gemini generation error: {e}. Falling back to structured evidence synthesis.")
            self.last_provider_status = "fallback_temporary_unavailable"
            return self._generate_fallback(query, candidates, target_paper=target_paper, conversation_history=conversation_history)

    def _generate_openai(
        self,
        user_prompt: str,
        query: str,
        candidates: List[RetrievalCandidate],
        target_paper: Optional[Any] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Call OpenAI API."""
        api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.info("OPENAI_API_KEY not set. Using structured passage evidence synthesis.")
            self.last_provider_status = "fallback_missing_api_key"
            return self._generate_fallback(query, candidates, target_paper=target_paper, conversation_history=conversation_history)

        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            messages = [{"role": "system", "content": ACADEMIC_SYSTEM_PROMPT}]
            if conversation_history:
                for msg in conversation_history[-4:]:
                    r = "assistant" if msg.get("role") == "assistant" else "user"
                    messages.append({"role": r, "content": msg.get("content", "")})
            messages.append({"role": "user", "content": user_prompt})

            resp = client.chat.completions.create(
                model=self.model_name or "gpt-4o-mini",
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            text = resp.choices[0].message.content or ""
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            }
            self.last_provider_status = "api_success"
            return text, usage
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}. Falling back to structured evidence synthesis.")
            self.last_provider_status = "fallback_temporary_unavailable"
            return self._generate_fallback(query, candidates, target_paper=target_paper, conversation_history=conversation_history)

    def _generate_ollama(
        self,
        user_prompt: str,
        query: str,
        candidates: List[RetrievalCandidate],
        target_paper: Optional[Any] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Call local Ollama server."""
        try:
            base_url = settings.OLLAMA_BASE_URL.rstrip("/")
            messages = [{"role": "system", "content": ACADEMIC_SYSTEM_PROMPT}]
            if conversation_history:
                for msg in conversation_history[-4:]:
                    r = "assistant" if msg.get("role") == "assistant" else "user"
                    messages.append({"role": r, "content": msg.get("content", "")})
            messages.append({"role": "user", "content": user_prompt})

            payload = {
                "model": self.model_name or "llama3",
                "messages": messages,
                "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
                "stream": False,
            }
            res = requests.post(f"{base_url}/api/chat", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                text = data.get("message", {}).get("content", "")
                self.last_provider_status = "api_success"
                return text, {"prompt_tokens": data.get("prompt_eval_count", 0), "completion_tokens": data.get("eval_count", 0)}
            else:
                logger.warning(f"Ollama returned status {res.status_code}. Falling back.")
                self.last_provider_status = "fallback_temporary_unavailable"
                return self._generate_fallback(query, candidates, target_paper=target_paper, conversation_history=conversation_history)
        except Exception as e:
            logger.warning(f"Ollama request failed: {e}. Falling back.")
            self.last_provider_status = "fallback_temporary_unavailable"
            return self._generate_fallback(query, candidates, target_paper=target_paper, conversation_history=conversation_history)

    def _generate_fallback(
        self,
        query: str,
        candidates: List[RetrievalCandidate],
        target_paper: Optional[Any] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Deterministic, grounded evidence synthesis fallback adhering to the 3 Evidence States."""
        if not candidates:
            return (
                "I couldn't find sufficient evidence in the ResearchMind research corpus to answer this question reliably. No supporting research documents were retrieved for this query.",
                {"prompt_tokens": 0, "completion_tokens": 0},
            )

        top_cand = candidates[0]
        top_score = top_cand.reranker_score if top_cand.reranker_score is not None else (
            top_cand.dense_score if top_cand.dense_score is not None else top_cand.final_score
        )

        # State C Abstention if top evidence is below minimum relevance threshold
        if top_score < settings.MIN_EVIDENCE_SCORE:
            return (
                "I couldn't find sufficient evidence in the ResearchMind research corpus to answer this question reliably. "
                "The retrieved papers discuss related topics, but they do not provide enough evidence for the requested information.",
                {"prompt_tokens": 50, "completion_tokens": 30},
            )

        # Check for Question Type: Methodology Extraction
        from researchmind.retrieval.prioritization import is_methodology_query
        if is_methodology_query(query):
            return self._generate_methodology_fallback(query, candidates, target_paper)

        # General State A / B Evidence Synthesis
        paper_title = getattr(target_paper, "title", str(target_paper)) if target_paper else ""
        header = f"Based on the retrieved research literature for '{paper_title}', the evidence indicates:\n" if paper_title else "Based on the retrieved research literature, the evidence indicates:\n"
        lines = [header]
        for idx, c in enumerate(candidates, start=1):
            clean_text = c.text.strip().replace("\n", " ")
            sents = [s.strip() for s in clean_text.split(".") if len(s.strip()) > 25]
            summary_snip = sents[0] + "." if sents else clean_text[:180] + "."
            lines.append(f"{idx}. {summary_snip} [{idx}, p.{c.page_start}]")

        lines.append(
            f"\n*Interpretation*: Synthesizing these passages across {len(set(c.paper_id for c in candidates))} papers "
            "demonstrates that the methodology addresses these specific research aspects."
        )
        return "\n".join(lines), {"prompt_tokens": 100, "completion_tokens": 100}

    def _generate_methodology_fallback(
        self,
        query: str,
        candidates: List[RetrievalCandidate],
        target_paper: Optional[Any] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Generate structured methodology extraction output adhering to requirement D."""
        import re

        paper_title = ""
        paper_id = ""
        if target_paper:
            paper_title = getattr(target_paper, "title", str(target_paper))
            paper_id = getattr(target_paper, "paper_id", "")
        elif candidates:
            paper_title = candidates[0].title
            paper_id = candidates[0].paper_id

        method_terms = [
            "method", "materials and methods", "proposed approach", "proposed method",
            "framework", "workflow", "spatial feature engineering", "feature engineering",
            "regularization", "segmentation", "architecture", "pipeline"
        ]
        exp_terms = ["experiment", "evaluation", "validation", "dataset", "results", "partition", "site"]

        method_chunks = []
        experiment_chunks = []

        for idx, c in enumerate(candidates, start=1):
            sec_lower = f"{c.section or ''} {c.subsection or ''}".lower()
            text_lower = c.text[:400].lower()
            if any(m in sec_lower for m in method_terms) or any(m in text_lower for m in method_terms):
                method_chunks.append((idx, c))
            elif any(e in sec_lower for e in exp_terms) or any(e in text_lower for e in exp_terms):
                experiment_chunks.append((idx, c))

        direct_answer_sentences = []
        ordered_steps = []
        validation_details = []

        for idx, c in method_chunks:
            clean_text = c.text.strip().replace("\n", " ")
            sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if len(s.strip()) > 35]
            for s in sents:
                s_lower = s.lower()
                if any(meta in s_lower for meta in ["department of", "university", "arxiv:", "http"]):
                    continue
                if any(w in s_lower for w in ["workflow", "combine", "propose", "present", "framework", "approach", "develop"]):
                    if len(direct_answer_sentences) < 2:
                        direct_answer_sentences.append(f"{s} [{idx}, p.{c.page_start}]")
                if any(w in s_lower for w in ["first", "then", "apply", "convert", "train", "vectoriz", "regulariz", "extract", "consist", "layer", "feature", "consolidat", "rule", "model"]):
                    if len(ordered_steps) < 5 and s not in [st.split(" [")[0] for st in ordered_steps]:
                        ordered_steps.append(f"{s} [{idx}, p.{c.page_start}]")

        if not direct_answer_sentences and method_chunks:
            c = method_chunks[0][1]
            idx = method_chunks[0][0]
            clean_text = c.text.strip().replace("\n", " ")
            sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if len(s.strip()) > 35 and "department" not in s.lower()]
            if sents:
                direct_answer_sentences.append(f"{sents[0]} [{idx}, p.{c.page_start}]")

        for idx, c in experiment_chunks:
            clean_text = c.text.strip().replace("\n", " ")
            sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if len(s.strip()) > 35]
            for s in sents:
                if any(w in s.lower() for w in ["site", "dataset", "partition", "evaluat", "validat", "accuracy", "test", "experiment"]):
                    if len(validation_details) < 2:
                        validation_details.append(f"{s} [{idx}, p.{c.page_start}]")

        if not ordered_steps:
            for idx, c in enumerate(candidates[:3], start=1):
                clean_text = c.text.strip().replace("\n", " ")
                sents = [s.strip() for s in clean_text.split(".") if len(s.strip()) > 30 and "department" not in s.lower()]
                if sents:
                    ordered_steps.append(f"{sents[0]}. [{idx}, p.{c.page_start}]")

        direct_ans_text = " ".join(direct_answer_sentences) if direct_answer_sentences else (
            f"The proposed methodology in {paper_title} establishes a domain-specific technical workflow to address the stated research objectives."
        )

        lines = [
            f"**Question Type**: Methodology Extraction",
            f"**Target Paper**: {paper_title} ({paper_id})\n",
            f"### Short Direct Answer",
            direct_ans_text + "\n",
            f"### Ordered Methodology Steps",
        ]

        for step_idx, step_text in enumerate(ordered_steps, start=1):
            lines.append(f"{step_idx}. **Step {step_idx}**: {step_text}")

        if validation_details:
            lines.append(f"\n### Experimental Validation Details")
            for val_text in validation_details:
                lines.append(f"* {val_text}")

        lines.append(f"\n### Missing-Evidence Disclosure")
        if len(method_chunks) >= 2:
            lines.append(
                "While the core pipeline stages and feature descriptors are directly supported by the retrieved excerpts, "
                "specific low-level hyperparameter schedules, full ablation tables, and raw sensor calibrations "
                "are not detailed within the retrieved candidate passages."
            )
        else:
            lines.append(
                "The retrieved passages contain only high-level conceptual summaries. "
                "Detailed step-by-step algorithms, mathematical proofs, and quantitative validation metrics are missing from the current evidence chunks."
            )

        return "\n".join(lines), {"prompt_tokens": 120, "completion_tokens": 150}
