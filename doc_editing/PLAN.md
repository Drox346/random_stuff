# Handover: AI-Assisted DOCX Document Workflow

## 1. Project Summary

Management asked us to investigate how our in-house AI system can help with document handling. The main goal is to make it easy for non-technical users, especially management, to create, edit, review, and export business documents with assistance from a local LLM and internal company knowledge.

The current direction is to build an AI-assisted document workflow focused primarily on DOCX documents. PDF export is considered straightforward, and PDF reading is already solved internally. The hard part is reliable DOCX creation/editing, review UX, versioning, and safe integration with internal knowledge.

The project should not be framed as “an AI Word replacement.” A better framing is:

> A local AI-assisted DOCX workflow for controlled company templates and reviewable document sessions.

The system should let users ask the AI to create or modify documents, see the result in a real document viewer/editor, review changes, manually correct if needed, and download/finalize the result.

---

## 2. Existing Environment

The company already has the following components:

* Local/in-house LLM.
* Open WebUI, mainly used by management.
* `zoo code`, mainly used by developers/technical users.
* Open WebUI vector database containing internal guidelines, policies, and company knowledge.
* Existing RAG MCP that exposes access to the Open WebUI vector DB and can be used from `zoo code`.
* Existing PDF reading capability.
* PDF export is not considered a major blocker.

Important implication:

The system does **not** need to solve RAG from scratch. Internal knowledge retrieval is already available through an MCP. This makes both Open WebUI-based and standalone document workflows more feasible.

---

## 3. Main Problem

The user-facing request sounds simple:

> “Use AI to help create and edit documents.”

But the real implementation involves:

* DOCX parsing and mutation.
* Preserving formatting, styles, numbering, headers, footers, tables, images, and layout.
* Integrating internal company guidelines through RAG.
* Providing a browser-based review/editing UI.
* Supporting document versioning.
* Avoiding accidental overwrites of manual edits.
* Exporting reliable final DOCX/PDF files.
* Maintaining audit/provenance data.
* Keeping the workflow usable for management.

The core difficulty is not whether the LLM can write decent text. The core difficulty is whether the system can turn decent LLM output into a trustworthy business document without creating cleanup work or corrupting formatting.

---

## 4. Key Design Principle

The LLM should **not** directly mutate DOCX files or emit raw OOXML.

Instead:

1. The system extracts a logical representation of the document.
2. The LLM proposes structured edit intent.
3. The document backend validates the operation.
4. A deterministic patch engine applies the change to the DOCX.
5. A new immutable document version is created.
6. The user reviews the result in a browser editor/viewer.

Example of a good internal operation:

```json
{
  "expected_version": 7,
  "operations": [
    {
      "op": "replace_section_body",
      "section_id": "risk_assessment",
      "new_blocks": [
        {
          "type": "paragraph",
          "style": "Body Text",
          "text": "The revised risk assessment text..."
        }
      ],
      "source_refs": [
        {
          "source_id": "policy-risk-management-v3",
          "chunk_id": "chunk-017"
        }
      ]
    }
  ]
}
```

Bad internal operation:

```json
{
  "instruction": "Make this document better."
}
```

The user can speak naturally, but the backend should receive structured, validated operations.

---

## 5. Architecture Direction

The preferred architecture is a split system with separate responsibilities.

```text
Open WebUI / zoo code / optional standalone UI
        |
        | MCP tools / API calls
        v
Document workflow backend
        |
        +-- DOCX session management
        +-- template handling
        +-- DOCX logical model extraction
        +-- DOCX patch engine
        +-- version store
        +-- provenance/audit store
        +-- preview/editor integration
        +-- DOCX/PDF export
        |
        v
Browser review/editor app
        |
        v
Embedded office editor/viewer
```

The MCP should not be the whole product. It should be a thin integration layer exposing document operations to Open WebUI, `zoo code`, and other agents.

The document backend should be the actual product core.

---

## 6. Components

### 6.1 RAG MCP

Already exists.

Responsibilities:

* Search internal guidelines and documents.
* Retrieve relevant chunks.
* Return stable source IDs and chunk IDs.
* Provide provenance metadata.
* Allow `zoo code` and agents to access internal knowledge.

Expected output shape:

```json
{
  "results": [
    {
      "source_id": "policy-data-retention-v4",
      "chunk_id": "chunk-017",
      "title": "Data Retention Policy v4",
      "retrieved_at": "2026-06-25T12:00:00Z",
      "text": "Relevant policy text..."
    }
  ]
}
```

### 6.2 DOCX MCP

To be built.

Responsibilities:

* Expose document actions as tools.
* Allow Open WebUI and `zoo code` to create/edit/review documents.
* Delegate actual stateful work to the document workflow backend.
* Return preview/review URLs to the user.

Potential tools:

```text
create_docx_session
create_docx_from_template
inspect_docx_structure
get_docx_section
apply_docx_patch
rewrite_docx_section
validate_docx_against_guidelines
get_docx_review_url
list_docx_versions
restore_docx_version
export_docx
export_pdf
finalize_docx
```

The DOCX MCP should not own the actual document state. It should call the document backend.

### 6.3 Document Workflow Backend

This is the central service.

Responsibilities:

* Own document sessions.
* Store original and generated DOCX files.
* Store immutable versions.
* Extract a logical model from DOCX.
* Apply validated patches to DOCX.
* Track source/provenance metadata.
* Generate preview/editor URLs.
* Handle finalization and export.
* Record audit events.

Session data should include:

```text
session_id
owner/user
source_doc_id or template_id
current_version
created_at
updated_at
expires_at
original_docx
current_docx
logical_model_snapshots
patch_history
source_refs
audit_log
export_files
review_url
```

### 6.4 Browser Review/Editor App

This is the user-facing document surface.

Responsibilities:

* Display the current DOCX version.
* Allow manual edits if supported.
* Show version history.
* Show validation warnings.
* Allow download/export.
* Allow finalize/approve.
* Potentially show source references per section later.
* Potentially include an AI side panel later.

This can begin as a simple review app opened from Open WebUI links, but should be designed so it can grow into a standalone document workspace.

### 6.5 Embedded Office Editor

Do not implement DOCX rendering yourself.

Candidates:

* ONLYOFFICE Docs.
* Collabora Online.
* Nextcloud Office / Collabora stack.

For a custom app, ONLYOFFICE appears especially interesting because it has strong DOCX editing support and custom AI/plugin integration possibilities. Nextcloud Office + Assistant/Context Chat is worth evaluating as a more packaged platform option.

---

## 7. Frontend Options

There are two possible product shapes.

### Option A: Open WebUI-Centered Workflow

Flow:

```text
User opens Open WebUI
    -> asks AI to create/edit a document
    -> AI uses RAG MCP for internal context
    -> AI uses DOCX MCP for document session/editing
    -> DOCX MCP returns review URL
    -> user reviews document in separate browser tab
    -> user asks for further changes in Open WebUI
    -> document updates
    -> user downloads/finalizes
```

Pros:

* Reuses existing Open WebUI adoption.
* Reuses existing LLM/RAG access.
* Faster initial delivery.
* Good enough for many management workflows.
* Works with `zoo code`.

Cons:

* Chat and document review are split across tabs.
* Selection-based editing is awkward.
* Manual edit synchronization must be handled carefully.
* UX ceiling is lower than a dedicated document workspace.

### Option B: Standalone Document Workspace

Flow:

```text
User opens dedicated document app
    -> creates/opens a DOCX session
    -> sees document editor
    -> uses embedded AI panel
    -> AI calls RAG MCP and document backend
    -> changes appear directly in document
    -> user reviews/downloads/finalizes
```

Pros:

* Better document-centric UX.
* Supports selecting text and asking AI to rewrite that exact selection.
* Better version/diff/provenance UI.
* Better long-term product shape.

Cons:

* Requires solving or integrating auth/user management.
* Requires direct LLM/agent orchestration.
* More frontend/backend product work.
* More maintenance.

### Recommended Path

Build the backend as standalone-capable, but start with Open WebUI integration.

Suggested phased approach:

```text
Phase 1:
Open WebUI + DOCX MCP + document backend + review app.

Phase 2:
Improve review app with version history, validation warnings, manual edit sync.

Phase 3:
Add AI side panel to review app.

Phase 4:
If the workflow proves valuable, evolve review app into full standalone document workspace.
```

This avoids a big-bang standalone build while keeping the architecture from becoming trapped inside Open WebUI.

---

## 8. DOCX Strategy

DOCX must be treated as structured Office Open XML, not plain text.

Avoid arbitrary string replacement when possible. DOCX text can be split across runs, styles, hyperlinks, comments, bookmarks, fields, and numbering structures.

### Supported First

Focus on managed documents:

* Company templates.
* Known sections.
* Known styles.
* Known placeholders.
* Known table structures.
* Stable anchors such as content controls, bookmarks, or explicit template markers.

### Avoid Initially

Do not promise reliable support for arbitrary uploaded DOCX files.

Arbitrary DOCX files should initially support only:

* Text extraction.
* Summarization.
* Best-effort inspection.
* Suggestions.
* Maybe simple section replacement if structure is clear.
* Manual review/edit after AI-generated copy.

### Stable Anchors

Preferred anchor types, best to worst:

```text
content controls with stable IDs
bookmarks
custom XML mappings
explicit placeholder tags
known heading hierarchy
paragraph fingerprinting
raw text search
```

Raw text search should be a fallback, not the primary mechanism.

---

## 9. MVP Scope

The MVP should be narrow and reliable.

Recommended first supported workflows:

1. Create a new DOCX from a company template.
2. Fill sections using internal guidelines from RAG.
3. Rewrite known sections.
4. Add or replace paragraphs in known sections.
5. Generate simple tables from structured data.
6. Open the document in a browser review/editor.
7. Store immutable versions.
8. Download DOCX and PDF.
9. Allow manual final correction.
10. Store source/provenance metadata.

Recommended first document types:

* Policy document.
* Management report.
* Meeting summary / decision memo.
* Internal announcement.
* Vendor/customer assessment report.

Avoid initially:

* Arbitrary legal redlines.
* Tracked changes.
* Comments.
* Footnotes.
* Complex image positioning.
* Arbitrary layout changes.
* Arbitrary unknown DOCX mutation.
* Trying to become a full Word replacement.

---

## 10. Provenance and Validation

The system should use RAG both before and after generation.

Generation flow:

```text
user request
    -> retrieve relevant internal guidelines
    -> select template
    -> generate structured content
    -> apply to DOCX
    -> store source refs
    -> render/review
```

Validation flow:

```text
current document version
    -> retrieve relevant guidelines
    -> check generated sections
    -> identify missing/conflicting/unsupported content
    -> show warnings before finalization
```

Potential validation checks:

```text
Does the document use current company terminology?
Does it include required confidentiality wording?
Does it follow the selected template?
Does it mention the correct approval body?
Does it conflict with current internal guidelines?
Are claims supported by retrieved sources?
Were all required sections filled?
```

Validation result example:

```json
{
  "status": "needs_review",
  "checks": [
    {
      "severity": "warning",
      "section_id": "data_retention",
      "message": "Retention period differs from the current internal guideline.",
      "source_refs": [
        {
          "source_id": "policy-data-retention-v4",
          "chunk_id": "chunk-017"
        }
      ]
    }
  ]
}
```

---

## 11. Versioning Model

Every AI or manual edit should create a new immutable version.

Store:

```text
version_0000_original.docx
version_0001.docx
version_0001.logical.json
version_0001.patch.json
version_0002.docx
version_0002.logical.json
version_0002.patch.json
...
```

Each patch should include:

```text
session_id
base_version
new_version
operation list
actor
timestamp
source_refs
validation result
```

Use optimistic concurrency:

```json
{
  "expected_version": 5,
  "operations": [...]
}
```

If the current version is not 5 anymore, reject or require merge/rebase.

This prevents AI changes from silently overwriting manual edits.

---

## 12. Security Requirements

Minimum security requirements:

* No arbitrary filesystem access from MCP.
* Use document IDs/session IDs, not raw paths.
* Per-user permissions.
* Short-lived review/download URLs.
* Access checks on every session/version/export.
* Audit log for reads, edits, exports, finalization.
* Path traversal protection.
* File type validation.
* Macro handling policy for DOCM or macro-enabled files.
* HTML sanitization if any HTML preview is used.
* Rate limits.
* Clear session expiry/cleanup policy.
* Explicit finalize/approve step before saving to canonical document storage.

Do not let the LLM decide final storage paths, filenames, recipients, or access permissions without deterministic validation.

---

## 13. Existing Software to Evaluate

There may not be a perfect off-the-shelf solution, but several components/products are relevant.

### Nextcloud Office + Assistant / Context Chat

Potentially closest packaged platform:

* Self-hosted file/user/document platform.
* Office editing via Collabora.
* AI assistant/context chat/RAG capabilities.
* Good candidate if the goal is to avoid building too much custom infrastructure.

Risk:

* May not support the desired structured AI patch/version/provenance workflow.
* Could be less flexible than a custom MCP/document backend.

### ONLYOFFICE Docs

Strong candidate as embedded DOCX editor:

* Browser-based DOCX editing.
* Collaborative editing.
* Can be embedded into a custom web app.
* Has plugin/custom AI integration options.
* Could be used as the editor surface for the document review app.

Risk:

* Still requires building the workflow backend.
* Integration effort is non-trivial.

### Collabora Online

Good office editor engine:

* Self-hostable.
* Strong LibreOffice-based document rendering/editing.
* Often used through Nextcloud.

Risk:

* Custom AI integration may be less direct than with ONLYOFFICE.
* Better as an editor component than as the whole solution.

### Docmost / Wiki-style Systems

Good for knowledge/wiki workflows, not DOCX-native management documents.

### Microsoft 365 Copilot / Google Workspace Gemini / Notion AI

Good product references, but likely not acceptable if local/self-hosted/in-house LLM is required.

---

## 14. Key Risks

### 14.1 DOCX Fidelity

The main technical risk.

Mitigation:

* Start with company templates.
* Use stable anchors.
* Use a real office editor.
* Limit first supported operations.

### 14.2 Bad Review UX

If preview/download/manual correction are awkward, management will not use it.

Mitigation:

* Use browser review/editor.
* Keep download/finalize simple.
* Make current version obvious.
* Avoid preview mismatch with final DOCX.

### 14.3 RAG Hallucination / Weak Provenance

RAG does not guarantee correctness.

Mitigation:

* Store source refs.
* Run validation checks.
* Show warnings.
* Keep audit trail.

### 14.4 Scope Creep

The project can easily become an attempt to rebuild Word, SharePoint, and an AI compliance system.

Mitigation:

* Start with selected document types.
* Support controlled templates.
* Explicitly reject unsupported document features in v1.

### 14.5 Manual Edit Synchronization

Users may manually edit the document after AI edits.

Mitigation:

* Save manual edits as new versions.
* Regenerate logical model after manual saves.
* Use optimistic concurrency for patches.

---

## 15. Suggested Agent Tasks

The next agent should investigate and/or prototype the following.

### Task 1: Evaluate Editor Component

Compare:

* ONLYOFFICE Docs embedded in a custom app.
* Collabora Online embedded in a custom app.
* Nextcloud Office + Assistant/Context Chat as a packaged alternative.

Focus on:

* DOCX fidelity.
* API/plugin support.
* Integration effort.
* Self-hosting.
* Auth integration.
* Ability to save versions.
* Ability to react to external AI patch updates.
* Ability to support manual edits and save callbacks.

### Task 2: Define DOCX Patch Operations

Design minimal v1 patch schema.

Candidate operations:

```text
replace_section_body
insert_paragraph_after_section
rewrite_paragraph
fill_placeholder
update_table_rows
append_appendix
set_title
set_metadata
```

Define validation rules and failure modes.

### Task 3: Define Logical Document Model

Design JSON representation extracted from DOCX.

Needs to represent:

* Sections/headings.
* Paragraphs.
* Tables.
* Styles.
* Anchors.
* Basic metadata.
* Source refs.
* Block IDs.

### Task 4: Prototype Template-Based DOCX Generation

Use a company-like DOCX template with placeholders/content controls.

Goal:

* Create session from template.
* Fill sections from structured data.
* Save versioned DOCX.
* Open in browser editor/viewer.
* Export/download.

### Task 5: Prototype AI Patch Flow

Flow:

```text
RAG MCP retrieves policy chunks
LLM generates section content
DOCX MCP applies structured patch
document backend creates version
review app displays updated DOCX
```

### Task 6: Define Provenance Flow

Ensure source refs from RAG MCP can be attached to generated document sections.

Need stable IDs:

```text
source_id
chunk_id
retrieved_at
title
optional hash
```

### Task 7: Security Review

Define:

* Auth model.
* Session access checks.
* Download token handling.
* File handling restrictions.
* Audit events.
* Cleanup policy.

---

## 16. Recommended First Milestone

Build a vertical slice, not a generic platform.

Target milestone:

> Generate and edit one controlled DOCX template using RAG-backed content, with browser review and versioned export.

Concrete success criteria:

1. User starts from Open WebUI or `zoo code`.
2. Agent retrieves relevant internal context through RAG MCP.
3. Agent creates document session from a known DOCX template.
4. Agent fills/replaces two known sections.
5. Backend creates versioned DOCX.
6. Review URL opens the document in browser editor/viewer.
7. User can download DOCX/PDF.
8. Manual edit creates a new version.
9. A second AI edit applies to the latest version.
10. Source refs and patch history are stored.

---

## 17. Non-Goals for v1

Do not implement:

* Full arbitrary DOCX editing.
* Custom DOCX rendering engine.
* Full replacement for Word.
* Complex legal redlining.
* Full track-changes support.
* Generic file manager.
* Full document approval workflow.
* Multi-user real-time co-authoring logic unless provided by embedded editor.
* Deep integration into every company storage system.
* AI-generated raw OOXML.

---

## 18. Current Best Recommendation

The most pragmatic path is:

```text
Build the document backend as standalone-capable.
Expose it through a DOCX MCP.
Use Open WebUI initially for management interaction.
Use the existing RAG MCP for company knowledge.
Use a browser review/editor app for DOCX inspection and download.
Use an existing office editor such as ONLYOFFICE or Collabora.
Allow the review app to evolve into a standalone document workspace later.
```

This gives a fast first integration without closing off a better long-term UX.

The system should be kept modular:

```text
RAG MCP = company knowledge access
DOCX MCP = document tool access
Document backend = deterministic document state/mutation
Review app = human document UX
Open WebUI/zoo code = AI interaction/orchestration
```

The project is worth doing if scoped tightly around controlled DOCX workflows and company templates. It becomes risky if framed as arbitrary AI document editing.
::: 
