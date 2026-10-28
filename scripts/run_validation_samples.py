"""Execute the 8 representative manual validation queries and compile detailed traces."""

import sys
from pathlib import Path
sys.path.insert(0, "src")

import json
import time
from researchmind.pipeline.rag import ResearchMindRAG

SAMPLE_QUERIES = [
    {
        "id": "sample_01",
        "title": "Query 1: 'What is NLP?' (Corpus-Grounded Synthesis vs. Textbook Chatbot)",
        "query": "What is NLP?",
        "intent": "Demonstrates that ResearchMind answers using indexed NLP literature (e.g. ACL checklists, token representations, benchmark evaluations) rather than generating an ungrounded general textbook definition."
    },
    {
        "id": "sample_02",
        "title": "Query 2: Direct Methodology / Strong Evidence (ADOPD Anomaly Distillation)",
        "query": "What benchmark datasets are used to evaluate reference-privileged on-policy distillation in ADOPD?",
        "intent": "Demonstrates State A (Strong / Sufficient Evidence) with exact inline citations and section grounding."
    },
    {
        "id": "sample_03",
        "title": "Query 3: Out-of-Domain Query / Insufficient Evidence Abstention",
        "query": "What ingredients and baking temperatures are required to bake traditional sourdough bread?",
        "intent": "Demonstrates State C (Insufficient Evidence Abstention) where the system correctly refuses to answer out-of-corpus trivia."
    },
    {
        "id": "sample_04",
        "title": "Query 4: Partial Evidence / Evidence Gap Disclosure",
        "query": "What are the exact training hardware specifications and total energy consumption in kilowatt-hours for the DUET video model?",
        "intent": "Demonstrates State B (Partial / Moderate Evidence) where supported facts are cited while explicit evidence gaps are disclosed."
    },
    {
        "id": "sample_05",
        "title": "Query 5: Cross-Paper Synthesis (Diffusion & Video Generation Distillation)",
        "query": "What common distillation strategies are used in diffusion and video generation models in the GenerativeAI corpus?",
        "intent": "Demonstrates synthesis across multiple indexed papers within a single domain."
    },
    {
        "id": "sample_06",
        "title": "Query 6: Cross-Domain Synthesis (NLP Instruction Tuning vs. Medical Vision Routing)",
        "query": "How do mixture-of-experts routing techniques differ between distributed NLP instruction tuning and medical vision diagnosis?",
        "intent": "Demonstrates cross-domain retrieval bridging NLP and Computer Vision / Deep Learning literature."
    },
    {
        "id": "sample_07",
        "title": "Query 7: Weak Evidence Query (Borderline Relevance)",
        "query": "How are quantum spin liquid hamiltonians optimized using neural network wavefunctions?",
        "intent": "Demonstrates Weak Evidence handling when only loose mathematical physics analogies exist in the corpus."
    },
    {
        "id": "sample_08",
        "title": "Query 8: Multi-Modal Model Diffing & Feature Steering",
        "query": "How does Multimodal Model Diffing discover and control model features?",
        "intent": "Demonstrates precise mechanistic explainability and provenance tracking on high-confidence papers."
    }
]

def main():
    rag = ResearchMindRAG()
    results = []

    print(f"Executing {len(SAMPLE_QUERIES)} representative validation queries...")
    for q_spec in SAMPLE_QUERIES:
        print(f"\n---> Running: {q_spec['query']}")
        t0 = time.time()
        resp = rag.query(
            query=q_spec["query"],
            retrieval_mode="hybrid_rerank",
            top_k=5,
            enable_xai=True,
        )
        elapsed_ms = (time.time() - t0) * 1000
        print(f"     Done in {elapsed_ms:.1f} ms | Evidence State: {resp.evidence_state} | Abstained: {resp.abstained}")
        results.append({
            "spec": q_spec,
            "response": resp.model_dump(),
            "elapsed_ms": elapsed_ms,
        })

    out_file = Path("experiments/sample_validation_outputs.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Saved all validation query outputs to {out_file}")

if __name__ == "__main__":
    main()
