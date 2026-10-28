"""Script to test the live ResearchMind RAG pipeline on a diverse battery of questions."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from researchmind.pipeline.rag import ResearchMindRAG

TEST_QUESTIONS = [
    {
        "category": "Direct Methodology (Computer Vision / Industrial Anomaly Detection)",
        "query": "How does reference-privileged on-policy distillation work in ADOPD?",
        "expected_state": "State A (Strong Evidence)",
    },
    {
        "category": "Generative AI / Video Distillation",
        "query": "What is the DUET framework for video distillation and how does it balance quality and diversity?",
        "expected_state": "State A (Strong Evidence)",
    },
    {
        "category": "Cross-Domain Synthesis (NLP + Deep Learning)",
        "query": "How do Mixture of Experts (MoE) routing techniques operate across distributed NLP and vision models?",
        "expected_state": "State A / B (Multi-Paper Synthesis)",
    },
    {
        "category": "Corpus-Grounded Definition (NLP)",
        "query": "What is NLP and how do checklists improve reproducibility in NLP evaluations?",
        "expected_state": "State A (Corpus-Grounded Synthesis)",
    },
    {
        "category": "Partial Evidence with Gap Disclosure",
        "query": "What are the exact training GPU cluster configurations and total power consumption in kWh for the DUET model?",
        "expected_state": "State B (Partial Evidence with Gap Disclosure) or State C (Abstention)",
    },
    {
        "category": "Out-of-Domain / Insufficient Evidence (Strict Abstention)",
        "query": "What ingredients and baking temperatures are needed to bake traditional sourdough bread?",
        "expected_state": "State C (Deterministic Abstention)",
    }
]

def main():
    console = Console()
    console.print(Panel(
        "[bold cyan]ResearchMind 2.0 — Live RAG Pipeline Verification[/bold cyan]\n"
        "Testing live retrieval, reranking, evidence states, grounding, and provenance across diverse queries.",
        border_style="cyan"
    ))

    rag = ResearchMindRAG()

    for idx, item in enumerate(TEST_QUESTIONS, 1):
        console.print(f"\n[bold yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]")
        console.print(f"[bold white]Query #{idx} [{item['category']}][/bold white]")
        console.print(f"[cyan]Question:[/cyan] [bold]{item['query']}[/bold]")
        console.print(f"[dim]Target Behavior: {item['expected_state']}[/dim]\n")

        t0 = time.time()
        resp = rag.query(
            query=item["query"],
            retrieval_mode="hybrid_rerank",
            top_k=5,
            enable_xai=True,
        )
        elapsed_ms = (time.time() - t0) * 1000

        # State banner
        state = resp.evidence_state or "unknown"
        state_color = "green" if state == "strong" else ("yellow" if state == "partial" else "red")
        abstained_badge = "[bold red]ABSTAINED[/bold red]" if resp.abstained else "[bold green]ANSWERED[/bold green]"

        console.print(f"Evidence State: [{state_color} bold]{state.upper()}[/{state_color} bold] | Status: {abstained_badge} | Latency: [bold]{elapsed_ms:.1f} ms[/bold]")

        # Answer panel
        console.print(Panel(
            Markdown(resp.answer.strip()),
            title=f"[bold green]Answer & Synthesis[/bold green]",
            border_style=state_color,
        ))

        # Sources table
        if resp.sources:
            table = Table(title="Top Retrieved Evidence Sources", show_header=True, header_style="bold cyan")
            table.add_column("#", justify="center", width=4)
            table.add_column("Paper ID", width=16)
            table.add_column("Title", width=34)
            table.add_column("Section", width=22)
            table.add_column("Page", justify="center", width=7)
            table.add_column("Norm Score", justify="right", width=10)

            for s_idx, src in enumerate(resp.sources, 1):
                title = (src.title or "Unknown")[:32] + ("..." if len(src.title or "") > 32 else "")
                sec = (src.section or "Body")[:20]
                pages = f"p.{src.page_start}" if src.page_start else "N/A"
                table.add_row(
                    f"[{s_idx}]",
                    src.paper_id,
                    title,
                    sec,
                    pages,
                    f"{src.retrieval_score:.4f}"
                )
            console.print(table)
        else:
            console.print("[dim italic]No sources retrieved.[/dim italic]")

        # XAI diagnostics
        if resp.xai_explanation:
            xai = resp.xai_explanation
            console.print(f"[bold]Grounding Overlap:[/] {xai.grounding.supported_claims}/{xai.grounding.total_claims} claims verified ({xai.grounding.grounded_ratio * 100:.1f}%)")

    console.print(f"\n[bold green]✅ Completed testing across all {len(TEST_QUESTIONS)} question categories![/bold green]\n")

if __name__ == "__main__":
    main()
