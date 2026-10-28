"""Generate RESEARCHMIND_SAMPLE_OUTPUTS.md from experiments/sample_validation_outputs.json."""

import json
from pathlib import Path

def format_sample_outputs():
    with open("experiments/sample_validation_outputs.json", "r", encoding="utf-8") as f:
        samples = json.load(f)

    md = []
    md.append("# ResearchMind — Representative Sample Execution Outputs & Verification Traces\n")
    md.append("**System Version**: ResearchMind 2.0 (Research-Ready)\n")
    md.append("**Retrieval Pipeline**: Hybrid Sparse-Dense (BM25Plus + BGE-small) + RRF ($k=60$) + BAAI/bge-reranker-base\n")
    md.append("**Evidence Verification**: Deterministic 3-State Grounding & Provenance Verification Engine\n")
    md.append("---\n")
    md.append("## Overview\n")
    md.append("This document contains end-to-end execution traces for 8 representative evaluation queries designed to probe system behaviors across different retrieval topologies and evidence states:\n")
    md.append("1. **Corpus-Grounded Synthesis vs. Textbook Chatbot** (`'What is NLP?'`)\n")
    md.append("2. **Direct Methodology / Strong Evidence** (ADOPD Benchmark Datasets)\n")
    md.append("3. **Out-of-Domain Trivia / Strict Abstention** (Traditional Sourdough Bread)\n")
    md.append("4. **Partial Evidence / Evidence Gap Disclosure** (DUET Video Training Specs)\n")
    md.append("5. **Cross-Paper Synthesis** (Generative AI Diffusion Distillation)\n")
    md.append("6. **Cross-Domain Synthesis** (NLP Instruction Tuning vs. Medical Vision MoE Routing)\n")
    md.append("7. **Weak Evidence / Borderline Relevance** (Quantum Spin Liquid Hamiltonians)\n")
    md.append("8. **Mechanistic Diffing & Explainability** (Multimodal Model Diffing Features)\n")
    md.append("\n---\n")

    for i, s in enumerate(samples, 1):
        spec = s["spec"]
        resp = s["response"]
        elapsed = s.get("elapsed_ms", 0.0)
        xai = resp.get("xai_report") or {}

        md.append(f"## {spec['title']}\n")
        md.append(f"**Query**: `{spec['query']}`  \n")
        md.append(f"**Intent / Focus**: {spec['intent']}  \n")
        md.append(f"**Execution Latency**: `{elapsed:.1f} ms` | **Retrieval Mode**: `{resp.get('retrieval_mode')}`  \n")
        md.append(f"**Assigned Evidence State**: `{resp.get('evidence_state', '').upper()}` | **Abstained**: `{resp.get('abstained')}`  \n")
        md.append("\n### 1. Generated Answer & Grounded Citations\n")
        md.append("```markdown\n" + resp.get("answer", "").strip() + "\n```\n")

        sources = resp.get("sources", [])
        md.append("### 2. Top-Ranked Retrieved Evidence (Candidate Set)\n")
        if sources:
            md.append("| # | Paper ID | Paper Title | Section | Pages | Normalized Score |\n")
            md.append("|---|----------|-------------|---------|-------|------------------|\n")
            for idx, src in enumerate(sources, 1):
                title = (src.get("title") or "Unknown")[:45]
                sec = (src.get("section") or "Body")[:35]
                pages = f"pp. {src.get('page_start')}-{src.get('page_end')}" if src.get("page_start") else "N/A"
                score = src.get("retrieval_score", 0.0)
                md.append(f"| [{idx}] | `{src.get('paper_id')}` | {title} | {sec} | {pages} | `{score:.4f}` |\n")
        else:
            md.append("*No candidate chunks passed retrieval threshold.*\n")

        md.append("\n### 3. Explainable AI (XAI) & Provenance Diagnostics\n")
        ev_strength = xai.get("evidence_strength", {})
        md.append(f"- **Evidence Strength Assessment**: `{ev_strength.get('strength')}` (Max Normalized Score: `{ev_strength.get('max_score', 0.0):.4f}`, Mean Top-3: `{ev_strength.get('mean_top3_score', 0.0):.4f}`)\n")
        md.append(f"- **Rationale**: {ev_strength.get('rationale', 'N/A')}\n")

        claims = xai.get("claim_verifications", [])
        if claims:
            md.append(f"- **Claim Grounding Verification** ({len(claims)} sentences analyzed):\n")
            for c_idx, c in enumerate(claims, 1):
                status_icon = "✅ Grounded" if c.get("grounded") else "⚠️ Ungrounded"
                citations = ", ".join(c.get("matched_citations", [])) or "None"
                claim_text = c.get("claim_text", "")
                md.append(f"  - **Sentence {c_idx}** [{status_icon}]: \"{claim_text}\" (Overlap: `{c.get('lexical_overlap_score', 0.0):.2f}`, Citations: `{citations}`)\n")

        trace = xai.get("reranking_trace", [])
        if trace:
            md.append("\n- **Retrieval Pipeline Progression (Top Candidates)**:\n")
            md.append("| Chunk ID | BM25 Rank | Dense Rank | RRF Rank | Final Rerank Score |\n")
            md.append("|----------|-----------|------------|----------|--------------------|\n")
            for t in trace[:5]:
                b_rank = t.get("sparse_rank", "N/A")
                d_rank = t.get("dense_rank", "N/A")
                r_rank = t.get("rrf_rank", "N/A")
                final_s = t.get("final_score", 0.0)
                md.append(f"| `{t.get('chunk_id')}` | {b_rank} | {d_rank} | {r_rank} | `{final_s:.4f}` |\n")

        md.append("\n---\n")

    out_path = Path("RESEARCHMIND_SAMPLE_OUTPUTS.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(md))

    print(f"Generated {out_path} ({len(md)} sections)")

if __name__ == "__main__":
    format_sample_outputs()
