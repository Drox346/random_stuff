from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

from llm_documents.document_io import (
    DocumentSnapshot,
    read_document,
    render_docx_brief,
    write_xlsx_report,
)
from llm_documents.llm import DEFAULT_MODEL, chat_with_ollama


class DocumentWorkflowState(TypedDict, total=False):
    document_paths: list[str]
    output_dir: str
    question: str
    model: str
    documents: list[DocumentSnapshot]
    answer: str
    docx_output: str
    xlsx_output: str


def run_document_workflow(
    *,
    document_paths: list[Path],
    output_dir: Path,
    question: str,
    model: str = DEFAULT_MODEL,
) -> DocumentWorkflowState:
    """Run the document workflow as explicit, auditable server-side steps."""
    state: DocumentWorkflowState = {
        "document_paths": [str(path) for path in document_paths],
        "output_dir": str(output_dir),
        "question": question,
        "model": model,
    }
    for step in (load_documents, synthesize_with_llm, render_docx, write_xlsx):
        state.update(step(state))
    return state


def load_documents(state: DocumentWorkflowState) -> DocumentWorkflowState:
    paths = [Path(path) for path in state["document_paths"]]
    return {"documents": [read_document(path) for path in paths]}


def synthesize_with_llm(state: DocumentWorkflowState) -> DocumentWorkflowState:
    model = state.get("model") or DEFAULT_MODEL
    documents = state["documents"]
    prompt = _build_prompt(question=state["question"], documents=documents)
    response = chat_with_ollama(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You analyze office documents for a user. "
                    "Use only the supplied document extracts. "
                    "Return concise plain text with sections named Summary, Risks, "
                    "Deadlines, Actions, and Evidence. Do not use Markdown formatting."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    return {"answer": _plain_text(response)}


def render_docx(state: DocumentWorkflowState) -> DocumentWorkflowState:
    output_dir = Path(state["output_dir"])
    output_path = render_docx_brief(
        output_path=output_dir / "llm_brief.docx",
        title="Local LLM Document Brief",
        question=state["question"],
        answer=state["answer"],
        sources=state["documents"],
    )
    return {"docx_output": str(output_path)}


def write_xlsx(state: DocumentWorkflowState) -> DocumentWorkflowState:
    output_dir = Path(state["output_dir"])
    base_workbook_path = _first_xlsx_path(state["documents"])
    output_path = write_xlsx_report(
        output_path=output_dir / "llm_workbook.xlsx",
        question=state["question"],
        answer=state["answer"],
        sources=state["documents"],
        base_workbook_path=base_workbook_path,
    )
    return {"xlsx_output": str(output_path)}


def _build_prompt(*, question: str, documents: list[DocumentSnapshot]) -> str:
    extracts = []
    for idx, document in enumerate(documents, start=1):
        content = _prompt_content(document.content)
        extracts.append(
            f"## Source {idx}: {Path(document.path).name}\n"
            f"Type: {document.kind}\n"
            f"Parser: {document.parser}\n\n"
            f"{content}"
        )
    joined = "\n\n---\n\n".join(extracts)
    return f"Question: {question}\n\nDocument extracts:\n\n{joined}"


def _prompt_content(text: str, *, limit: int = 9000) -> str:
    if len(text) <= limit:
        return text

    keywords = [
        "Load Optimized Defaults",
        "Optimierte Standardwerte",
        "CMOS",
        "Qfan",
        "QFan",
        "Boot",
        "BIOS-Setup",
        "instabil",
    ]
    excerpts = [_truncate(text, limit=3000)]
    lower_text = text.lower()
    for keyword in keywords:
        index = lower_text.find(keyword.lower())
        if index == -1:
            continue
        start = max(0, index - 900)
        end = min(len(text), index + 1400)
        excerpts.append(f"[Excerpt around '{keyword}']\n{text[start:end]}")

    curated = "\n\n...\n\n".join(_dedupe_excerpts(excerpts))
    return _truncate(curated, limit=limit)


def _dedupe_excerpts(excerpts: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for excerpt in excerpts:
        key = excerpt[:300]
        if key in seen:
            continue
        seen.add(key)
        unique.append(excerpt)
    return unique


def _truncate(text: str, *, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[Truncated for prompt length]"


def _first_xlsx_path(documents: list[DocumentSnapshot]) -> Path | None:
    for document in documents:
        if document.kind == "xlsx":
            return Path(document.path)
    return None


def _plain_text(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", text)
    return text.strip()
