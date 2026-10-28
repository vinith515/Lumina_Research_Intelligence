"""CLI tool for querying ResearchMind with Dense, BM25, Hybrid RRF, Cross-Encoder Reranking, and XAI."""

import argparse
import json
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from researchmind.config import settings
from researchmind.schemas.models import RetrievalMode, RAGResponse
from researchmind.pipeline.rag import ResearchMindRAG


def display_rag_response(response: RAGResponse, console: Console, show_xai: bool = True, show_debug: bool = False):
    """Display rich formatted response to the terminal."""
    console.print()
    console.print(Panel(
        f"[bold white]{response.answer}[/bold white]",
        title=f"[bold green]💡 ResearchMind Answer ({response.retrieval_mode.upper()})[/bold green]",
        subtitle=f"⏱️ {response.latency_ms:.1f}ms",
        border_style="green",
    ))

    # Citations Table
    if response.sources:
        table = Table(title="📚 Verified Traceable Citations", show_header=True, header_style="bold cyan")
        table.add_column("Ref", justify="center", width=5)
        table.add_column("Paper Title", style="bold", width=38)
        table.add_column("Section", width=22)
        table.add_column("Page", justify="center", width=7)
        table.add_column("Score", justify="right", width=8)

        for idx, s in enumerate(response.sources, start=1):
            table.add_row(
                f"[{idx}]",
                s.title[:36] + ("..." if len(s.title) > 36 else ""),
                s.section[:20],
                f"p.{s.page_start}",
                f"{s.retrieval_score:.3f}",
            )
        console.print(table)

    # XAI Report
    if show_xai and response.xai_explanation:
        xai = response.xai_explanation
        console.print("\n[bold yellow]🔬 Explainable AI (XAI) Grounding & Provenance[/bold yellow]")
        console.print(f"Overall Evidence Strength: [bold {'green' if xai.evidence_strength.value == 'Strong Evidence' else 'yellow'}]{xai.evidence_strength.value}[/]")
        console.print(f"Claims Grounded: [green]{xai.grounding.supported_claims}/{xai.grounding.total_claims}[/green] ({xai.grounding.grounded_ratio * 100:.1f}%)")

        if show_debug:
            console.print(f"\n[dim]{xai.human_readable_report}[/dim]")


def run_query(rag: ResearchMindRAG, query_text: str, mode: str, top_k: int, show_xai: bool, show_debug: bool, output_json: bool):
    console = Console()
    if mode == "all":
        modes = ["bm25", "dense", "hybrid", "hybrid_rerank"]
        for m in modes:
            console.print(f"\n[bold magenta]==================== MODE: {m.upper()} ====================[/bold magenta]")
            resp = rag.query(query=query_text, retrieval_mode=m, top_k=top_k, enable_xai=show_xai)
            display_rag_response(resp, console, show_xai=show_xai, show_debug=show_debug)
    else:
        resp = rag.query(query=query_text, retrieval_mode=mode, top_k=top_k, enable_xai=show_xai)
        if output_json:
            print(resp.model_dump_json(indent=2))
        else:
            display_rag_response(resp, console, show_xai=show_xai, show_debug=show_debug)


def interactive_mode(rag: ResearchMindRAG, mode: str, top_k: int, show_xai: bool, show_debug: bool):
    console = Console()
    console.print("[bold green]ResearchMind Interactive Search (type 'exit' or 'quit' to stop)[/bold green]\n")
    while True:
        try:
            query_str = console.input("[bold cyan]Query > [/bold cyan]").strip()
            if not query_str:
                continue
            if query_str.lower() in ["exit", "quit", "q"]:
                break
            run_query(rag, query_str, mode, top_k, show_xai, show_debug, output_json=False)
        except (KeyboardInterrupt, EOFError):
            break
    console.print("\n[yellow]Goodbye![/yellow]")


def main():
    parser = argparse.ArgumentParser(description="Query the ResearchMind scientific research assistant.")
    parser.add_argument("--query", "-q", type=str, default=None, help="Research question to ask")
    parser.add_argument("--mode", "-m", type=str, default="hybrid_rerank", choices=["dense", "bm25", "hybrid", "hybrid_rerank", "all"], help="Retrieval mode")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of evidence chunks to retrieve")
    parser.add_argument("--xai", action="store_true", default=True, help="Display XAI explanation and grounding report")
    parser.add_argument("--debug", "-d", action="store_true", help="Display full signal trace (dense, bm25, RRF, reranker)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    parser.add_argument("--interactive", "-i", action="store_true", help="Launch interactive search session")
    args = parser.parse_args()

    rag = ResearchMindRAG()

    if args.interactive or not args.query:
        interactive_mode(rag, args.mode, args.top_k, args.xai, args.debug)
    else:
        run_query(rag, args.query, args.mode, args.top_k, args.xai, args.debug, args.json)


if __name__ == "__main__":
    main()
