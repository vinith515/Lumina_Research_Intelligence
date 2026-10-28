"""CLI script for evaluating and comparing retrieval, abstention, and XAI methods across paper and chunk levels."""

import argparse
import json
import sys
from pathlib import Path
from typing import List
from rich.console import Console
from tabulate import tabulate

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from researchmind.config import settings
from researchmind.schemas.models import EvaluationQuery, EvaluationResult
from researchmind.evaluation.evaluation import BenchmarkEvaluator
from researchmind.pipeline.rag import ResearchMindRAG


def load_benchmark_dataset(eval_path: Path, split_filter: str = "all") -> List[EvaluationQuery]:
    """Load benchmark dataset and filter by split if specified."""
    if not eval_path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {eval_path}")

    with open(eval_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = [EvaluationQuery.model_validate(item) for item in data]
    if split_filter in ["val", "validation"]:
        queries = [q for q in queries if q.split == "validation"]
    elif split_filter in ["test", "heldout"]:
        queries = [q for q in queries if q.split == "test"]

    return queries


def main():
    parser = argparse.ArgumentParser(description="Evaluate and compare ResearchMind retrieval & abstention modes.")
    parser.add_argument("--eval-file", type=str, default=str(settings.metadata_path / "benchmark_suite_expanded.json"), help="Path to evaluation queries JSON")
    parser.add_argument("--split", type=str, default="test", choices=["val", "validation", "test", "all"], help="Dataset split to evaluate")
    parser.add_argument("--eval-level", type=str, default="both", choices=["paper", "chunk", "both"], help="Evaluation granularity")
    parser.add_argument("--sweep-thresholds", action="store_true", help="Perform abstention threshold sweep on validation split")
    parser.add_argument("--profile-latency", action="store_true", help="Profile latency across all pipeline sub-stages")
    parser.add_argument("--top-k", type=int, default=10, help="Retrieval evaluation depth")
    parser.add_argument("--output-prefix", type=str, default="benchmark_comparison", help="Prefix for output experiment files")
    parser.add_argument("--save-all", action="store_true", default=True, help="Save all benchmark CSV, JSON, and MD reports")
    args = parser.parse_args()

    console = Console()
    console.print("[bold cyan]📊 ResearchMind Research-Grade Evaluation & Benchmark[/bold cyan]")

    eval_file_path = Path(args.eval_file)
    queries = load_benchmark_dataset(eval_file_path, split_filter=args.split)
    console.print(f"Loaded [green]{len(queries)}[/green] queries (Split: [bold yellow]{args.split.upper()}[/]) from {eval_file_path.name}")

    rag = ResearchMindRAG()
    evaluator = BenchmarkEvaluator(rag_pipeline=rag)

    # 1. Threshold Sweep
    threshold_results = []
    if args.sweep_thresholds or args.split in ["val", "validation"]:
        console.print("\n[yellow]🔬 Sweeping Abstention Thresholds [0.20 to 0.50] on Validation Set...[/yellow]")
        val_queries = load_benchmark_dataset(eval_file_path, split_filter="validation")
        threshold_results = evaluator.sweep_abstention_thresholds(val_queries)
        headers = ["Threshold", "Abstention Acc", "Selective Acc", "Unsupported Ans %", "False Abstention %"]
        rows = [
            [f"{r['threshold']:.2f}", f"{r['abstention_accuracy']*100:.1f}%", f"{r['selective_accuracy']*100:.1f}%", f"{r['unsupported_answer_rate']*100:.1f}%", f"{r['false_abstention_rate']*100:.1f}%"]
            for r in threshold_results
        ]
        console.print(tabulate(rows, headers=headers, tablefmt="github"))

    # 2. Latency Profiling
    latency_profile = {}
    if args.profile_latency:
        console.print("\n[yellow]⏱️ Profiling Sub-Stage Latency Breakdown (Mean / Median / P95)...[/yellow]")
        latency_profile = evaluator.profile_latency_stages(queries, sample_size=min(15, len(queries)))
        headers_lat = ["Stage", "Mean (ms)", "Median (ms)", "P95 (ms)"]
        rows_lat = [
            [s.replace("_", " ").title(), f"{st['mean_ms']:.1f}", f"{st['median_ms']:.1f}", f"{st['p95_ms']:.1f}"]
            for s, st in latency_profile.items()
        ]
        console.print(tabulate(rows_lat, headers=headers_lat, tablefmt="github"))

    # 3. Retrieval & Generation Evaluation
    paper_results = {}
    chunk_results = {}

    if args.eval_level in ["paper", "both"]:
        console.print("\n[bold magenta]📄 Running Paper-Level Retrieval Benchmark (BM25, Dense, Hybrid, Hybrid+Rerank)...[/bold magenta]")
        paper_results = evaluator.evaluate_queries(queries=queries, eval_level="paper", top_k=args.top_k)
        console.print(evaluator.format_comparison_table(paper_results))

    if args.eval_level in ["chunk", "both"]:
        console.print("\n[bold blue]🧩 Running Chunk-Level Evidence Retrieval Benchmark...[/bold blue]")
        chunk_results = evaluator.evaluate_queries(queries=queries, eval_level="chunk", top_k=args.top_k)
        console.print(evaluator.format_comparison_table(chunk_results))

    # 4. Save structured outputs
    if args.save_all:
        if not threshold_results:
            val_queries = load_benchmark_dataset(eval_file_path, split_filter="validation")
            threshold_results = evaluator.sweep_abstention_thresholds(val_queries)
        if not latency_profile:
            latency_profile = evaluator.profile_latency_stages(queries, sample_size=min(10, len(queries)))

        evaluator.save_all_experiment_reports(
            paper_results=paper_results,
            chunk_results=chunk_results,
            threshold_sweep=threshold_results,
            latency_profile=latency_profile,
        )
        console.print(f"\n[bold green]✅ All evaluation benchmarks successfully generated and saved to {settings.experiments_path}[/bold green]")


if __name__ == "__main__":
    main()
