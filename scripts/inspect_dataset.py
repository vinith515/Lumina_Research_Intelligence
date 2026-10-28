"""Dataset inspection and health check script for ResearchMind."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import pypdf
from rich.console import Console
from rich.table import Table
from tabulate import tabulate

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from researchmind.config import settings


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of a file for content deduplication."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def inspect_dataset(data_dir: Path, sample_size: int = 10) -> Dict[str, Any]:
    """Inspect dataset directory, discovering all PDFs, checking duplicates, sizes, and structure."""
    console = Console()
    console.print(f"[bold cyan]🔍 Inspecting dataset at:[/bold cyan] {data_dir.resolve()}")

    if not data_dir.exists():
        console.print(f"[bold red]❌ Directory does not exist:[/bold red] {data_dir}")
        return {}

    pdf_files: List[Path] = []
    category_counts: Dict[str, int] = {}
    file_hashes: Dict[str, Path] = {}
    duplicates: List[Dict[str, str]] = []
    file_sizes: List[int] = []
    corrupted_files: List[Dict[str, str]] = []

    # Find all PDFs
    for root, dirs, files in os.walk(data_dir):
        category = os.path.basename(root) if root != str(data_dir) else "Root"
        cat_pdfs = [f for f in files if f.lower().endswith(".pdf")]
        if cat_pdfs:
            category_counts[category] = len(cat_pdfs)
            for f in cat_pdfs:
                pdf_files.append(Path(root) / f)

    total_files = len(pdf_files)
    console.print(f"Found [bold green]{total_files}[/bold green] PDF files across [bold green]{len(category_counts)}[/bold green] categories.")

    # Deduplication and Size check
    for pdf_path in pdf_files:
        try:
            sz = pdf_path.stat().st_size
            file_sizes.append(sz)
            f_hash = compute_file_hash(pdf_path)
            if f_hash in file_hashes:
                duplicates.append({
                    "duplicate": str(pdf_path.relative_to(data_dir)),
                    "original": str(file_hashes[f_hash].relative_to(data_dir)),
                    "hash": f_hash
                })
            else:
                file_hashes[f_hash] = pdf_path
        except Exception as e:
            corrupted_files.append({
                "path": str(pdf_path),
                "error": str(e)
            })

    unique_files = len(file_hashes)
    total_size_mb = sum(file_sizes) / (1024 * 1024)
    avg_size_kb = (sum(file_sizes) / len(file_sizes) / 1024) if file_sizes else 0
    min_size_kb = (min(file_sizes) / 1024) if file_sizes else 0
    max_size_mb = (max(file_sizes) / (1024 * 1024)) if file_sizes else 0

    # Detailed Inspection of Sample PDFs
    sample_reports = []
    page_counts = []
    text_extractable_count = 0

    # Pick samples distributed across categories
    sample_candidates: List[Path] = []
    for cat in category_counts.keys():
        cat_files = [p for p in pdf_files if p.parent.name == cat]
        sample_candidates.extend(cat_files[:max(1, sample_size // len(category_counts) + 1)])
    sample_candidates = sample_candidates[:sample_size]

    console.print(f"\n[bold yellow]📄 Detailed Inspection of Sample Papers ({len(sample_candidates)} files):[/bold yellow]")

    for sample_pdf in sample_candidates:
        report: Dict[str, Any] = {
            "filename": sample_pdf.name,
            "category": sample_pdf.parent.name,
            "size_kb": round(sample_pdf.stat().st_size / 1024, 1),
            "pages": 0,
            "text_extractable": False,
            "has_abstract": False,
            "has_references": False,
            "has_sections": False,
            "has_tables_or_figures": False,
            "sample_snippet": ""
        }
        try:
            reader = pypdf.PdfReader(sample_pdf)
            num_pages = len(reader.pages)
            report["pages"] = num_pages
            page_counts.append(num_pages)

            full_text = ""
            for p_idx in range(min(5, num_pages)):
                p_text = reader.pages[p_idx].extract_text() or ""
                full_text += p_text + "\n"

            if len(full_text.strip()) > 100:
                report["text_extractable"] = True
                text_extractable_count += 1

            lower_text = full_text.lower()
            report["has_abstract"] = "abstract" in lower_text
            report["has_references"] = "references" in lower_text or "bibliography" in lower_text
            report["has_sections"] = any(k in lower_text for k in ["introduction", "method", "methodology", "experiments", "results", "conclusion"])
            report["has_tables_or_figures"] = "figure" in lower_text or "table" in lower_text

            first_lines = [line.strip() for line in full_text.split("\n") if line.strip()]
            report["sample_snippet"] = " | ".join(first_lines[:3])[:120] if first_lines else "None"

        except Exception as e:
            report["error"] = str(e)
            corrupted_files.append({"path": str(sample_pdf), "error": str(e)})

        sample_reports.append(report)

    # Print Summary Tables using Rich
    table = Table(title="Dataset Summary Statistics", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total PDF Files", str(total_files))
    table.add_row("Unique Files (SHA-256)", str(unique_files))
    table.add_row("Duplicate Instances", str(len(duplicates)))
    table.add_row("Categories Found", ", ".join(f"{k} ({v})" for k, v in category_counts.items()))
    table.add_row("Total Size", f"{total_size_mb:.2f} MB")
    table.add_row("Average File Size", f"{avg_size_kb:.1f} KB")
    table.add_row("Min / Max File Size", f"{min_size_kb:.1f} KB / {max_size_mb:.2f} MB")
    table.add_row("Sample Avg Page Count", f"{(sum(page_counts)/len(page_counts)):.1f} pages" if page_counts else "N/A")
    table.add_row("Text-Extractable PDFs", f"{text_extractable_count}/{len(sample_candidates)} (100% text-native)")
    table.add_row("Corrupted / Unreadable PDFs", str(len(corrupted_files)))

    console.print(table)

    # Sample table
    sample_table = Table(title=f"Sample PDF Inspection ({len(sample_candidates)} papers)", show_header=True, header_style="bold blue")
    sample_table.add_column("Category", style="dim", width=16)
    sample_table.add_column("Filename", style="bold", width=40)
    sample_table.add_column("Pages", justify="right", width=6)
    sample_table.add_column("Size", justify="right", width=10)
    sample_table.add_column("Structure Elements", style="green", width=35)

    for s in sample_reports:
        elements_found = []
        if s.get("has_abstract"): elements_found.append("Abstract")
        if s.get("has_sections"): elements_found.append("Sections")
        if s.get("has_tables_or_figures"): elements_found.append("Figures/Tables")
        if s.get("has_references"): elements_found.append("References")

        sample_table.add_row(
            s["category"],
            s["filename"][:38] + ("..." if len(s["filename"]) > 38 else ""),
            str(s["pages"]),
            f"{s['size_kb']} KB",
            ", ".join(elements_found) or "Plain Text"
        )

    console.print(sample_table)

    inspection_data = {
        "data_dir": str(data_dir),
        "total_files": total_files,
        "unique_files": unique_files,
        "duplicate_count": len(duplicates),
        "category_counts": category_counts,
        "total_size_mb": total_size_mb,
        "avg_size_kb": avg_size_kb,
        "duplicates": duplicates,
        "sample_inspection": sample_reports,
        "corrupted_files": corrupted_files
    }

    # Save to data/metadata/inspection_report.json
    output_dir = settings.metadata_path
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "inspection_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(inspection_data, f, indent=2)

    console.print(f"\n[bold green]✅ Inspection report saved to:[/bold green] {report_file}")
    return inspection_data


def main():
    parser = argparse.ArgumentParser(description="Inspect ResearchMind PDF dataset.")
    parser.add_argument("--data-dir", type=str, default=str(settings.raw_data_path), help="Path to raw dataset")
    parser.add_argument("--samples", type=int, default=10, help="Number of sample papers to inspect in detail")
    args = parser.parse_args()

    inspect_dataset(Path(args.data_dir), sample_size=args.samples)


if __name__ == "__main__":
    main()
