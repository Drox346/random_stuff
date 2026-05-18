from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from llm_documents.document_io import (
    DocumentSnapshot,
    create_demo_documents,
    export_to_pdf,
    extract_pdf_to_markdown_cache,
    read_document,
    render_docx_brief,
    write_xlsx_report,
)
from llm_documents.graph import run_document_workflow
from llm_documents.llm import DEFAULT_MODEL


app = typer.Typer(help="Local-only document workflow proof of concept.")
console = Console()


@app.command()
def demo(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for demo inputs and outputs."),
    ] = Path("demo_run"),
    question: Annotated[
        str,
        typer.Option("--question", "-q", help="Question to ask across all demo documents."),
    ] = (
        "Create a support handoff from these local documents. Summarize the BIOS issue, "
        "identify risks, list safe recovery or triage actions, and cite evidence from the manual."
    ),
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Ollama model tag."),
    ] = DEFAULT_MODEL,
    export_pdf: Annotated[
        bool,
        typer.Option("--export-pdf", help="Export generated DOCX/XLSX outputs to PDF with local LibreOffice."),
    ] = False,
) -> None:
    """Create demo documents, run the workflow, and write DOCX/XLSX outputs."""
    source_dir = output_dir / "sources"
    document_paths = create_demo_documents(source_dir)
    state = run_document_workflow(
        document_paths=document_paths,
        output_dir=output_dir,
        question=question,
        model=model,
    )
    if export_pdf:
        state["pdf_outputs"] = [
            str(export_to_pdf(input_path=Path(state["docx_output"]), output_dir=output_dir / "pdf")),
            str(export_to_pdf(input_path=Path(state["xlsx_output"]), output_dir=output_dir / "pdf")),
        ]
    _print_result(state)


@app.command()
def run(
    documents: Annotated[
        list[Path],
        typer.Argument(help="Input .docx, .xlsx, .pdf, and/or .md files."),
    ],
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for generated DOCX/XLSX outputs."),
    ] = Path("out"),
    question: Annotated[
        str,
        typer.Option("--question", "-q", help="Question to ask across all documents."),
    ] = "Summarize these documents and identify risks and next actions.",
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Ollama model tag."),
    ] = DEFAULT_MODEL,
) -> None:
    """Run the workflow on existing documents."""
    missing = [path for path in documents if not path.exists()]
    if missing:
        raise typer.BadParameter(f"Missing files: {', '.join(str(path) for path in missing)}")

    state = run_document_workflow(
        document_paths=documents,
        output_dir=output_dir,
        question=question,
        model=model,
    )
    _print_result(state)


@app.command("demo-read-docx")
def demo_read_docx(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for demo inputs and outputs."),
    ] = Path("demo_run"),
) -> None:
    """Show local DOCX reading."""
    snapshot = _read_demo_source(output_dir, ".docx")
    _print_snapshot(snapshot)


@app.command("demo-read-xlsx")
def demo_read_xlsx(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for demo inputs and outputs."),
    ] = Path("demo_run"),
) -> None:
    """Show local XLSX reading."""
    snapshot = _read_demo_source(output_dir, ".xlsx")
    _print_snapshot(snapshot)


@app.command("demo-read-pdf")
def demo_read_pdf(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for demo inputs and outputs."),
    ] = Path("demo_run"),
) -> None:
    """Show local PDF reading."""
    snapshot = _read_demo_source(output_dir, ".pdf")
    _print_snapshot(snapshot)


@app.command("demo-cache-pdf-md")
def demo_cache_pdf_md(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for demo inputs and outputs."),
    ] = Path("demo_run"),
) -> None:
    """Show cached PDF to Markdown extraction using the packaged demo PDF."""
    paths = _ensure_demo_sources(output_dir)
    pdf_path = next(path for path in paths if path.suffix.lower() == ".pdf")
    cache_dir = output_dir / ".llm-documents-cache"

    first = extract_pdf_to_markdown_cache(pdf_path=pdf_path, cache_dir=cache_dir)
    second = extract_pdf_to_markdown_cache(pdf_path=pdf_path, cache_dir=cache_dir)

    table = Table(title="PDF Markdown cache demo")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Source PDF", second.source_path)
    table.add_row("Markdown cache", second.markdown_path)
    table.add_row("Metadata", second.metadata_path)
    table.add_row("First run", "cache hit" if first.cache_hit else "extracted PDF")
    table.add_row("Second run", "cache hit" if second.cache_hit else "extracted PDF")
    table.add_row("Characters", str(len(second.content)))
    console.print(table)
    console.print("\n[bold]Cached Markdown preview[/bold]")
    console.print(second.content[:1800])


@app.command("demo-write-docx")
def demo_write_docx(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for demo inputs and outputs."),
    ] = Path("demo_run"),
) -> None:
    """Show DOCX generation with docxtpl."""
    documents = _read_all_demo_sources(output_dir)
    output_path = render_docx_brief(
        output_path=output_dir / "tool_demos" / "docx_brief_demo.docx",
        title="DOCX Tool Demo",
        question="Show that the local tool can render an editable DOCX artifact.",
        answer="This DOCX was generated locally from a docxtpl template using extracted source metadata.",
        sources=documents,
    )
    _print_paths("DOCX write demo", [output_path])


@app.command("demo-write-xlsx")
def demo_write_xlsx(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for demo inputs and outputs."),
    ] = Path("demo_run"),
) -> None:
    """Show XLSX workbook editing with openpyxl."""
    documents = _read_all_demo_sources(output_dir)
    base_workbook = next(Path(doc.path) for doc in documents if doc.kind == "xlsx")
    output_path = write_xlsx_report(
        output_path=output_dir / "tool_demos" / "xlsx_report_demo.xlsx",
        question="Show that the local tool can edit an XLSX workbook.",
        answer="This workbook was created locally by copying the demo XLSX and inserting an LLM Summary sheet.",
        sources=documents,
        base_workbook_path=base_workbook,
    )
    _print_paths("XLSX write demo", [output_path])


@app.command("demo-export-pdf")
def demo_export_pdf(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for demo inputs and outputs."),
    ] = Path("demo_run"),
) -> None:
    """Show local PDF export with LibreOffice."""
    documents = _read_all_demo_sources(output_dir)
    docx_output = render_docx_brief(
        output_path=output_dir / "tool_demos" / "pdf_export_source.docx",
        title="PDF Export Tool Demo",
        question="Show local LibreOffice PDF export.",
        answer="This DOCX is converted to PDF locally with LibreOffice headless mode.",
        sources=documents,
    )
    pdf_output = export_to_pdf(input_path=docx_output, output_dir=output_dir / "tool_demos" / "pdf")
    _print_paths("PDF export demo", [docx_output, pdf_output])


def _print_result(state: dict) -> None:
    table = Table(title="Workflow outputs")
    table.add_column("Artifact")
    table.add_column("Path")
    table.add_row("DOCX brief", state["docx_output"])
    table.add_row("XLSX workbook", state["xlsx_output"])
    for idx, pdf_output in enumerate(state.get("pdf_outputs", []), start=1):
        table.add_row(f"PDF export {idx}", pdf_output)
    console.print(table)
    console.print("\n[bold]LLM answer[/bold]")
    console.print(state["answer"])


def _ensure_demo_sources(output_dir: Path) -> list[Path]:
    source_dir = output_dir / "sources"
    expected = [
        source_dir / "bios_support_notes.docx",
        source_dir / "bios_triage_workbook.xlsx",
        source_dir / "asus_bios_manual.pdf",
    ]
    if not all(path.exists() for path in expected):
        return create_demo_documents(source_dir)
    return expected


def _read_demo_source(output_dir: Path, suffix: str) -> DocumentSnapshot:
    paths = _ensure_demo_sources(output_dir)
    source = next(path for path in paths if path.suffix.lower() == suffix)
    return read_document(source)


def _read_all_demo_sources(output_dir: Path) -> list[DocumentSnapshot]:
    return [read_document(path) for path in _ensure_demo_sources(output_dir)]


def _print_snapshot(snapshot: DocumentSnapshot) -> None:
    table = Table(title="Read demo")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("File", snapshot.path)
    table.add_row("Kind", snapshot.kind)
    table.add_row("Parser", snapshot.parser)
    table.add_row("Characters", str(len(snapshot.content)))
    console.print(table)
    console.print("\n[bold]Extract preview[/bold]")
    console.print(snapshot.content[:1800])


def _print_paths(title: str, paths: list[Path]) -> None:
    table = Table(title=title)
    table.add_column("Artifact")
    table.add_column("Path")
    for path in paths:
        table.add_row(path.suffix.lstrip(".").upper() or "File", str(path))
    console.print(table)


if __name__ == "__main__":
    app()
