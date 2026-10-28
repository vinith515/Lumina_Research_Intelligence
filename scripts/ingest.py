"""CLI script for ingesting research papers using Unstructured.io."""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from researchmind.config import settings
from researchmind.ingestion import IngestionPipeline, UnstructuredPDFParser, DocumentCleaner, AcademicMetadataExtractor


def main():
    parser = argparse.ArgumentParser(description="Ingest research papers into ResearchMind using Unstructured.io.")
    parser.add_argument("--data-dir", type=str, default=str(settings.raw_data_path), help="Path to raw dataset")
    parser.add_argument("--sample", type=int, default=None, help="Number of sample papers to ingest (e.g. 5 or 10)")
    parser.add_argument("--category", type=str, default=None, help="Filter by category (e.g. NLP, ComputerVision)")
    parser.add_argument("--strategy", type=str, default=None, help="Unstructured strategy ('fast', 'auto', 'hi_res')")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion of already processed papers")
    args = parser.parse_args()

    console = Console()
    console.print("[bold cyan]🚀 ResearchMind Ingestion Pipeline[/bold cyan]")
    console.print(f"Data directory: [green]{args.data_dir}[/green]")
    if args.sample:
        console.print(f"Sample limit: [yellow]{args.sample} papers[/yellow]")
    if args.category:
        console.print(f"Category filter: [yellow]{args.category}[/yellow]")
    if args.strategy:
        console.print(f"Strategy: [yellow]{args.strategy}[/yellow]")

    custom_parser = UnstructuredPDFParser(strategy=args.strategy) if args.strategy else None
    pipeline = IngestionPipeline(parser=custom_parser)

    categories = [args.category] if args.category else None
    stats = pipeline.ingest_dataset(
        data_dir=Path(args.data_dir),
        limit=args.sample,
        force=args.force,
        categories=categories,
    )

    # Print summary table
    table = Table(title="Ingestion Summary", show_header=True, header_style="bold green")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="bold")

    table.add_row("Total Targeted", str(stats["targeted"]))
    table.add_row("Newly Processed", str(stats["processed"]))
    table.add_row("Already Processed", str(stats["already_processed"]))
    table.add_row("Duplicates Skipped", str(stats["duplicates"]))
    table.add_row("Failed", str(stats["failed"]))
    table.add_row("Total Pages Ingested", str(stats["total_pages"]))
    table.add_row("Total Elements Extracted", str(stats["total_elements"]))

    console.print("\n", table)

    if stats["processed_papers"]:
        sample_table = Table(title="Processed Papers Sample", show_header=True, header_style="bold blue")
        sample_table.add_column("Paper ID", style="dim", width=16)
        sample_table.add_column("Category", width=15)
        sample_table.add_column("Title", style="bold", width=40)
        sample_table.add_column("Pages", justify="right", width=6)
        sample_table.add_column("Elements", justify="right", width=9)

        for p in stats["processed_papers"][:10]:
            sample_table.add_row(
                p["paper_id"],
                p["category"],
                p["title"][:38] + ("..." if len(p["title"]) > 38 else ""),
                str(p["pages"]),
                str(p["elements"]),
            )
        console.print(sample_table)

    if stats["failed_files"]:
        console.print("\n[bold red]Failed Files:[/bold red]")
        for f in stats["failed_files"]:
            console.print(f"  - {f['path']}: {f['status']}")


if __name__ == "__main__":
    main()
