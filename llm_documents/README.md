# Local Document Workflow PoC

Local-only proof of concept for document tooling for non-technical teams such as HR, finance, and compliance.

The showcase reads DOCX, XLSX, and PDF files, asks a local Ollama model to synthesize the content, then writes edited DOCX and XLSX outputs. Document content stays on the machine running the workflow.

## What It Shows

- Local document ingestion with Docling for office formats and `pypdf` for fast PDF manual extraction.
- Local LLM synthesis through Ollama, defaulting to the small local model `qwen2.5:0.5b`.
- A simple explicit workflow for loading documents, synthesizing, and writing outputs.
- DOCX output generation with `docxtpl`.
- XLSX workbook editing with `openpyxl`.
- A packaged long-form ASUS BIOS manual PDF extracted locally with `pypdf`.

## Setup

Use Python 3.11, 3.12, or 3.13 if possible. Some document packages may not yet publish wheels for Python 3.14.

```bash
cd llm_documents
python3.12 -m venv .venv  # or another Python 3.11-3.13 interpreter
source .venv/bin/activate
pip install -e .
ollama pull qwen2.5:0.5b
```

Ollama must be running locally on its default endpoint. The code does not expose a remote Ollama URL option because the purpose of this PoC is local document processing.

The default model is intentionally tiny so the demo can run on low-resource local systems. If a larger model is installed, pass it with `--model`, for example `llm-documents demo --model granite4.1:8b`.

## Dependencies

Python package dependencies are declared in `pyproject.toml`.

| Dependency | Used for |
| --- | --- |
| `docling` | Primary DOCX and XLSX document conversion into Markdown-like text for LLM prompts. |
| `docxtpl` | Rendering the generated LLM brief into an editable DOCX from a template. |
| `ollama` | Direct local Ollama chat API integration. |
| `openpyxl` | XLSX fallback reading, demo workbook creation, and output workbook editing. |
| `pypdf` | Fast local PDF text extraction for manuals and other PDF sources. |
| `python-docx` | DOCX fallback reading and creation of the generated DOCX template/demo source. |
| `rich` | Formatted terminal tables and previews in the CLI. |
| `typer` | Command-line interface and options for the demos and document workflow. |

External tools:

- Ollama is required at runtime for local LLM synthesis.
- LibreOffice is optional and only needed for `--export-pdf` or `demo-export-pdf`.

## Run The Showcase

Generate sample DOCX, XLSX, and PDF files, feed them through the workflow, and write edited outputs:

```bash
llm-documents demo --output-dir demo_run --export-pdf
```

Expected outputs:

- `demo_run/sources/bios_support_notes.docx`
- `demo_run/sources/bios_triage_workbook.xlsx`
- `demo_run/sources/asus_bios_manual.pdf`
- `demo_run/llm_brief.docx`
- `demo_run/llm_workbook.xlsx`
- `demo_run/pdf/llm_brief.pdf`
- `demo_run/pdf/llm_workbook.pdf`

`llm_workbook.xlsx` is an edited copy of the first input workbook when an `.xlsx` source is present. The original sheets are preserved and a new `LLM Summary` sheet is inserted.

## Tool Demos

Each local tool path has a focused demo:

| Command | Shows | Main output |
| --- | --- | --- |
| `llm-documents demo-read-docx` | DOCX extraction with Docling, falling back to `python-docx` if needed | terminal preview |
| `llm-documents demo-read-xlsx` | XLSX extraction with Docling, falling back to `openpyxl` if needed | terminal preview |
| `llm-documents demo-read-pdf` | PDF text extraction with local `pypdf` | terminal preview |
| `llm-documents demo-cache-pdf-md` | PDF to Markdown extraction cache using the packaged ASUS BIOS manual | `demo_run/.llm-documents-cache/*.md` |
| `llm-documents demo-write-docx` | DOCX generation with `docxtpl` | `demo_run/tool_demos/docx_brief_demo.docx` |
| `llm-documents demo-write-xlsx` | XLSX workbook editing with `openpyxl` | `demo_run/tool_demos/xlsx_report_demo.xlsx` |
| `llm-documents demo-export-pdf` | PDF export with local LibreOffice headless mode | `demo_run/tool_demos/pdf/pdf_export_source.pdf` |

`demo-export-pdf` uses local LibreOffice in headless mode. It is optional and requires `libreoffice` or `soffice` on `PATH`.

## Try Local Files

```bash
llm-documents run \
  ./path/to/source.docx \
  ./path/to/workbook.xlsx \
  ./path/to/report.pdf \
  ./path/to/cached-extract.md \
  --question "Summarize the project status, risks, and next actions." \
  --output-dir out
```

## Use Case: Cached PDF Extraction

Large manuals, policies, contracts, and audit packs are expensive to parse repeatedly. The `demo-cache-pdf-md` command uses the packaged ASUS BIOS manual PDF to show a PDF to Markdown extraction step that writes a cached `.md` file into `demo_run/.llm-documents-cache`. Later runs can read the cached Markdown directly when the PDF has not changed, avoiding repeated extraction of the same large document.

```bash
llm-documents demo-cache-pdf-md --output-dir demo_run
```

For example:

```text
demo_run/sources/asus_bios_manual.pdf -> demo_run/.llm-documents-cache/asus_bios_manual-<cache-id>.md
```

The cache metadata tracks the source path, file size, modified time, parser, and cache format version. This keeps local document processing fast while still preserving the local-only privacy model.

## Notes

- Docling is tried first for DOCX and XLSX conversion. If it cannot parse a file, the workflow falls back to `python-docx` or `openpyxl`. PDFs use `pypdf` directly for fast local extraction.
- PDF export uses local LibreOffice only; no document content is sent to an external service.
- Some document parsing packages may download model assets during setup or first use. For sensitive documents, pre-warm those assets before using the workflow offline.
- The workflow is intentionally explicit instead of agentic. An orchestration framework such as LangGraph can be added later if a use case needs branching, retries, human review loops, or more complex tool planning.
