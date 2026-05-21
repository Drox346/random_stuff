# Architecture Options

This note captures the current product direction for local document intelligence. It assumes the project already operates inside the required compliance and privacy boundary.

## Goal

Build a document workflow platform for office documents and business users. The system should check documents against criteria, summarize or extract risks, cite evidence, and generate review artifacts such as DOCX, XLSX, or PDF reports.

The goal is not to commit to Python, LangChain, agents, or any specific model framework. Those are implementation choices. The durable product pieces are document access, extraction, caching, retrieval, rules, local model calls, artifact generation, permissions, and auditability.

## Design Assumptions

- Document processing runs on approved local infrastructure.
- Heavy document parsing and model calls belong on server-side workers, not office laptops.
- Cached Markdown, chunks, embeddings, summaries, logs, and generated artifacts should be treated like source documents.
- Access control should be enforced on the backend, not only in the UI.
- Document reads, cache use, model calls, and generated artifacts should be auditable.

## Current PoC

The current proof of concept is a vertical slice:

```text
DOCX/XLSX/PDF/MD input
  -> local extraction / cached Markdown
  -> explicit Python workflow
  -> direct local Ollama chat call
  -> DOCX and XLSX outputs
```

This is useful because it proves the basic mechanics:

- Office/PDF extraction can happen locally.
- Large PDF extraction can be cached as Markdown.
- Cached Markdown can be reused as a normal input.
- Local models can be called without an agent framework.
- Editable DOCX/XLSX artifacts can be generated.

It is not yet the final architecture. It is a server-side worker prototype.

## Recommended Shape

Use a modular local server platform:

```text
Document sources
  upload companion
  internal file shares
  internal DMS
  internal Git repositories
  server-side watched folders

Document registry
  source metadata
  hashes
  ACLs
  cache status
  retention policy

Extraction and cache layer
  source file -> normalized Markdown/text
  optional large-document topic split
  metadata and page references

Search and evidence layer
  keyword/FTS search
  optional local vector search
  chunk/topic retrieval
  cited source spans

Workflow layer
  contract criteria review
  policy compliance check
  risk/deadline extraction
  weekly or daily scheduled checks
  report generation

Local model layer
  direct calls to local model servers
  model-specific adapters kept thin

Artifact layer
  DOCX/XLSX/PDF outputs
  findings JSON
  audit logs
```

The user-facing UI and any upload companion should be clients of this backend. They should not run heavy document parsing frameworks, model servers, or workflow logic on office laptops.

## Viable Options

### Explicit Python Worker

Use Python services for extraction, caching, retrieval, model calls, and artifact generation.

Upsides:

- Fast to iterate.
- Strong document library ecosystem.
- Easy to run as an internal worker.
- Works well for DOCX/XLSX/report generation.
- Current PoC already follows this path.

Downsides:

- Dependency stack can be heavy.
- Native wheels and parser/model assets need controlled packaging.
- Needs production hardening around queues, timeouts, packaging, and audit logs.

Best fit:

- Server-side workers and scheduled jobs.
- Controlled internal deployments.
- Fast evolution of document workflows.

### Local Extraction Service

Use a dedicated local extraction service such as Apache Tika, LibreOffice headless, Docling workers, or a combination behind one internal API.

Upsides:

- Cleaner boundary between app code and extraction engines.
- Easier to swap parsers over time.
- Good for broad file-format coverage.

Downsides:

- More services to operate.
- Layout-aware Markdown quality may vary by engine and file type.
- Still needs controlled packaging and operational ownership.

Best fit:

- Production ingestion layer once formats and scale grow.

### Local Search/Index First

Store extracted Markdown/text in a local index before calling the LLM.

Upsides:

- Better evidence selection.
- Less context waste.
- Supports recurring checks and many questions over the same documents.
- Makes citations and audit trails easier.

Downsides:

- More moving parts.
- ACLs must apply to chunks/index entries, not only files.
- Vector search adds model and storage complexity if used.

Best fit:

- Long manuals, policies, contracts, and recurring compliance reviews.

### Upload Companion

Use a small desktop companion only for local file selection and on-demand upload to the internal backend.

Upsides:

- Better local folder UX than browser upload.
- Avoids running LLM/document stacks on office laptops.
- Can upload only selected/requested files.

Downsides:

- Still needs install/update/security review.
- Must avoid arbitrary path reads.
- Needs clear user-facing audit of what was uploaded.

Best fit:

- Interactive business workflows over local files.

### Server-Side Scheduler

Run recurring checks directly on server-accessible sources.

Upsides:

- Reliable automation.
- No dependency on office laptops being online.
- Reuses the same extraction/cache/rules/report tooling.

Downsides:

- Requires server-accessible document sources.
- Needs careful notification and ownership model.
- Permissions and retention rules must be precise.

Best fit:

- Daily/weekly checks over internal folders, repositories, or document systems.

## Less Attractive Options

- Running heavy parsing/model stacks on office laptops.
- Making a generic autonomous agent the default compliance reviewer.
- Building workflow logic only into the UI or upload companion.
- Letting cached text, chunks, or reports bypass the document permission model.

## Agent Frameworks

An agent framework is not needed for the current PoC. The main workflow is linear and easier to audit as explicit steps.

Keep agent orchestration as an option for later if a real use case needs:

- branching tool plans,
- human review loops,
- retries and fallback strategies,
- long-running stateful workflows,
- or developer-facing experimentation.

For compliance workflows, default to deterministic orchestration:

```text
ruleset
  -> retrieve relevant evidence
  -> run deterministic checks where possible
  -> ask local LLM to judge ambiguous items
  -> produce cited findings
  -> generate report
```

## Near-Term Recommendation

Keep the current PoC small and framework-light:

- direct local Ollama calls,
- explicit Python workflow steps,
- local extraction and cached Markdown,
- no LangChain/LangGraph dependency,
- generated DOCX/XLSX artifacts.

Next, build one realistic workflow such as contract criteria review:

```text
contract document
  -> extract/cache
  -> retrieve clauses
  -> apply versioned checklist
  -> produce pass/fail/needs-review findings
  -> cite evidence
  -> generate review report
```

Use that workflow to evaluate whether the Python worker stack is enough or whether a dedicated extraction/search service is needed.
