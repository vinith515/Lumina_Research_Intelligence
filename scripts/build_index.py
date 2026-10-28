"""CLI script for building Vector (ChromaDB) and Sparse (BM25) indexes from research chunks."""

import argparse
import sys
from pathlib import Path
from typing import List
from rich.console import Console

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from researchmind.config import settings
from researchmind.schemas.models import ResearchChunk
from researchmind.embeddings.embedder import ResearchEmbedder
from researchmind.indexing.vector_index import VectorIndexManager
from researchmind.indexing.bm25_index import BM25IndexManager


def load_all_chunks(chunks_dir: Path) -> List[ResearchChunk]:
    """Load all chunk JSONL files from chunks directory."""
    all_chunks: List[ResearchChunk] = []
    chunk_files = list(chunks_dir.glob("*.jsonl"))
    for cf in chunk_files:
        with open(cf, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    all_chunks.append(ResearchChunk.model_validate_json(line))
    return all_chunks


def main():
    parser = argparse.ArgumentParser(description="Build Vector and BM25 indexes for ResearchMind.")
    parser.add_argument("--chunks-dir", type=str, default=str(settings.chunks_dir), help="Directory of chunk files")
    parser.add_argument("--skip-vector", action="store_true", help="Skip building ChromaDB vector index")
    parser.add_argument("--skip-bm25", action="store_true", help="Skip building BM25 sparse index")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding generation batch size")
    args = parser.parse_args()

    console = Console()
    console.print("[bold cyan]🔨 ResearchMind Dual Index Builder[/bold cyan]")

    chunks_path = Path(args.chunks_dir)
    chunks = load_all_chunks(chunks_path)
    console.print(f"Loaded [green]{len(chunks)}[/green] research chunks from {chunks_path}")

    if not chunks:
        console.print("[bold red]❌ No chunks found! Run `python scripts/chunk.py` first.[/bold red]")
        return

    # 1. Build Vector Index
    if not args.skip_vector:
        console.print("\n[bold yellow]1. Generating embeddings & building Vector Index (ChromaDB)...[/bold yellow]")
        embedder = ResearchEmbedder(batch_size=args.batch_size)
        vector_mgr = VectorIndexManager()

        texts = [c.text for c in chunks]
        embeddings = embedder.embed_documents(texts, show_progress=True, use_cache=True)
        vector_mgr.add_chunks(chunks=chunks, embeddings=embeddings)
        console.print(f"[bold green]✅ Vector index built successfully! Total records: {vector_mgr.count()}[/bold green]")

    # 2. Build BM25 Sparse Index
    if not args.skip_bm25:
        console.print("\n[bold yellow]2. Tokenizing & building BM25 Sparse Index...[/bold yellow]")
        bm25_mgr = BM25IndexManager()
        bm25_mgr.build_index(chunks)
        console.print(f"[bold green]✅ BM25 index built successfully! Total records: {bm25_mgr.count()}[/bold green]")

    console.print("\n[bold green]🎉 Index building completed! System is ready to query.[/bold green]")


if __name__ == "__main__":
    main()
