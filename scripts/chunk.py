"""CLI script for chunking extracted paper elements."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from tqdm import tqdm
from rich.console import Console
from rich.table import Table

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from researchmind.config import settings
from researchmind.schemas.models import DocumentElement, PaperMetadata, ResearchChunk
from researchmind.chunking import ResearchPaperChunker


def main():
    parser = argparse.ArgumentParser(description="Generate structure-aware research chunks from parsed elements.")
    parser.add_argument("--elements-dir", type=str, default=str(settings.elements_dir), help="Directory of parsed elements")
    parser.add_argument("--output-dir", type=str, default=str(settings.chunks_dir), help="Directory for output chunks")
    parser.add_argument("--target-size", type=int, default=None, help="Target chunk size in characters")
    parser.add_argument("--max-size", type=int, default=None, help="Maximum chunk size in characters")
    args = parser.parse_args()

    console = Console()
    console.print("[bold cyan]🧩 ResearchMind Structure-Aware Chunker[/bold cyan]")

    elements_path = Path(args.elements_dir)
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    catalog_file = settings.metadata_path / "catalog.json"
    catalog: Dict[str, Any] = {}
    if catalog_file.exists():
        with open(catalog_file, "r", encoding="utf-8") as f:
            catalog = json.load(f)

    chunker = ResearchPaperChunker(
        target_size=args.target_size,
        max_size=args.max_size,
    )

    element_files = list(elements_path.glob("*.jsonl"))
    console.print(f"Found [green]{len(element_files)}[/green] element files to chunk.")

    total_chunks = 0
    sample_chunks: List[ResearchChunk] = []

    with tqdm(total=len(element_files), desc="Chunking Papers", unit="paper") as pbar:
        for elem_file in element_files:
            paper_id = elem_file.stem
            paper_meta = PaperMetadata.model_validate(catalog[paper_id]) if paper_id in catalog else None

            # Read elements
            elements: List[DocumentElement] = []
            with open(elem_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        elements.append(DocumentElement.model_validate_json(line))

            # Chunk paper
            chunks = chunker.chunk_paper(paper_id=paper_id, elements=elements, metadata=paper_meta)
            total_chunks += len(chunks)

            if len(sample_chunks) < 5 and chunks:
                sample_chunks.extend(chunks[:2])

            # Write chunks to disk
            chunk_file = output_path / f"{paper_id}.jsonl"
            with open(chunk_file, "w", encoding="utf-8") as f:
                for c in chunks:
                    f.write(c.model_dump_json() + "\n")

            # Update catalog
            if paper_id in catalog:
                catalog[paper_id]["total_chunks"] = len(chunks)

            pbar.update(1)

    # Save updated catalog
    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    console.print(f"\n[bold green]✅ Successfully created {total_chunks} research chunks across {len(element_files)} papers.[/bold green]")

    if sample_chunks:
        table = Table(title="Sample Research Chunks", show_header=True, header_style="bold blue")
        table.add_column("Chunk ID", style="dim", width=18)
        table.add_column("Section", width=22)
        table.add_column("Pages", justify="center", width=8)
        table.add_column("Tokens", justify="right", width=8)
        table.add_column("Snippet", width=45)

        for sc in sample_chunks[:5]:
            snippet = sc.text.replace("\n", " ")[:75] + "..."
            table.add_row(
                sc.chunk_id,
                sc.section[:20],
                f"{sc.page_start}-{sc.page_end}",
                str(sc.token_count),
                snippet,
            )
        console.print(table)


if __name__ == "__main__":
    main()
