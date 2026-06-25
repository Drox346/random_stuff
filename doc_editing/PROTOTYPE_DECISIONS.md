# DOCX Prototype Decisions

## 1. Prototype Goal

Build one narrow but usable workflow:

> A user in Open WebUI creates and revises a management decision memo from a controlled company DOCX template, using internal RAG sources, and opens the current result in a view-only browser tab.

The prototype proves that the company can reliably turn LLM output into a well-formatted DOCX. It is not a general document editor.

## 2. Fixed Scope

The prototype supports:

* DOCX only.
* Open WebUI as the user entry point.
* One controlled management decision memo template.
* Creating a document from structured fields.
* Revising known fields or sections through chat.
* Internal RAG retrieval before generation.
* A separate browser tab showing the current document.
* Downloading the current DOCX.
* Basic source-reference storage.

The prototype does not support:

* PDF generation or viewing.
* Browser editing.
* Arbitrary uploaded DOCX files.
* Generic DOCX inspection or mutation.
* Version history, checkpoints, rollback, or diffs.
* Tracked changes, comments, collaboration, or approval workflows.
* A standalone AI document workspace.
* LLM-generated OOXML.

## 3. First Document Type

Use one management decision memo template.

Suggested fields:

```text
title
date
author_or_department
decision_requested
background
options
recommendation
risks
next_steps
```

The exact wording and layout remain owned by the DOCX template. The AI supplies field values, not formatting instructions.

This document type is a good prototype target because it is useful to management, has a predictable structure, and does not require complex legal redlining or arbitrary layouts.

## 4. Core Design Decision: Regenerate, Do Not Patch

The prototype should not build a generic DOCX patch engine.

For each session, the backend stores:

1. The template ID and template version.
2. The current structured field values.
3. Source references associated with generated fields.
4. A monotonically increasing revision number.
5. The currently rendered DOCX.

When the user asks for a revision:

```text
current structured fields
    -> LLM returns validated field updates
    -> backend merges the updates
    -> backend renders the original template again
    -> current DOCX is atomically replaced
    -> revision number is incremented
```

The structured field data is the source of truth for the prototype. The DOCX is a generated artifact.

This approach is appropriate only because users cannot manually edit the DOCX in the browser. If browser editing is added later, the source-of-truth and synchronization design must be reconsidered.

## 5. Template Strategy

Use `docxtpl` with Jinja-style placeholders inside a company-created DOCX template.

Examples:

```text
{{ title }}
{{ decision_requested }}
{{ background }}
```

Use controlled paragraph and table-loop tags only where lists or repeated rows are required.

Reasons for this choice:

* It preserves the template's existing Word layout and styles.
* It is much simpler than editing arbitrary OOXML.
* Templates remain editable by normal Word users.
* It supports text, paragraph, row, image, and table-oriented template constructs.

Template rules:

* Every template has a stable `template_id` and integer `template_version`.
* Placeholder names must match the backend schema.
* Normal placeholders must remain within a single Word run.
* The template is validated in CI or by a validation command before deployment.
* A template change creates a new template version.
* Existing sessions continue using the template version with which they were created.
* No macros or DOCM templates are accepted.

Do not use content controls, bookmarks, or a logical DOCX model in this prototype. Those become relevant only when editing an existing DOCX in place.

## 6. Viewer

Use self-hosted ONLYOFFICE Docs in view-only mode, embedded in a minimal review page.

Configuration:

```text
editorConfig.mode = "view"
editorConfig.coEditing.mode = "strict"
editorConfig.coEditing.change = false
```

This selects the static/common viewer. The page does not need live updates; after a chat revision, the user reloads the viewer or opens the newly returned URL.

The ONLYOFFICE document key must include the session ID and current revision, for example:

```text
doc-{session_id}-{revision}
```

Changing the key prevents ONLYOFFICE from serving an older cached document after regeneration.

The review page contains only:

* Document title.
* Current revision number.
* Embedded view-only document.
* Refresh button.
* Download DOCX button.

Do not build a frontend framework for this. A server-rendered HTML page is sufficient.

ONLYOFFICE Docs should run as a separate container with JWT enabled and an explicitly configured secret. The document URL given to ONLYOFFICE must be an absolute URL reachable by the Document Server, not a browser-only or container-local URL.

## 7. Backend

Use Python with FastAPI.

Use:

* FastAPI for HTTP endpoints and the small review page.
* Pydantic models for field and tool-input validation.
* `docxtpl` for rendering controlled DOCX templates.
* `python-docx` only for limited output checks or subdocuments where necessary.
* SQLite for session metadata.
* Local filesystem storage for templates and generated DOCX files.

This is sufficient for a single-instance internal prototype and avoids introducing object storage, PostgreSQL, a task queue, or a separate frontend application prematurely.

Suggested layout:

```text
doc_editing/
    app/
        api/
        mcp/
        models/
        rendering/
        storage/
        viewer/
    templates/
        decision_memo/
            v1/
                template.docx
                schema.json
    data/
        app.db
        sessions/
            {session_id}/
                current.docx
    tests/
    compose.yaml
```

Generated files should be written to a temporary file, validated, and moved into place atomically. Never render directly over `current.docx`.

## 8. Minimal Session Model

Store:

```text
session_id
owner_id
template_id
template_version
title
current_revision
current_fields_json
source_refs_json
created_at
updated_at
status
current_docx_path
```

`status` only needs:

```text
active
finalized
expired
```

There is no version table in the prototype. `current_revision` exists to invalidate viewer caches and reject stale updates, not to provide rollback.

## 9. Minimal DOCX MCP

Expose only these tools:

### `create_decision_memo`

Inputs:

```text
title
user_request
optional structured facts
RAG source references
```

Returns:

```text
session_id
revision
review_url
download_url
```

### `revise_decision_memo`

Inputs:

```text
session_id
expected_revision
requested_change
optional additional RAG source references
```

The LLM produces updates only for known fields. The backend validates and merges them before rerendering.

Returns the new revision and a fresh review URL.

### `get_decision_memo`

Returns current metadata and field values so the agent can understand the current state before revising it.

### `get_decision_memo_review_url`

Returns a fresh short-lived review URL for the current revision.

### `finalize_decision_memo`

Marks the current document as finalized and prevents further revisions. For the prototype, finalization does not move the file into another company system.

Do not expose low-level operations such as `apply_docx_patch`, arbitrary paths, arbitrary template names, or raw OOXML.

## 10. LLM Output Contract

The user may ask naturally for changes, but the LLM-facing operation must be constrained.

Example:

```json
{
  "expected_revision": 2,
  "field_updates": {
    "recommendation": "Approve the proposed supplier for a six-month pilot.",
    "risks": [
      "Migration work may exceed the initial estimate.",
      "The pilot requires a data-processing review."
    ]
  },
  "source_refs": [
    {
      "source_id": "supplier-policy-v3",
      "chunk_id": "chunk-014",
      "retrieved_at": "2026-06-25T12:00:00Z"
    }
  ]
}
```

Validation rules:

* Reject unknown fields.
* Reject an update if `expected_revision` is stale.
* Enforce field types and conservative length limits.
* Require a non-empty title and recommendation.
* Require source references for claims presented as company policy.
* Treat retrieved text as data, never as tool instructions.
* Escape template values according to the rendering library's requirements.

On a stale revision, the agent must call `get_decision_memo` and regenerate its proposed field updates against the current state.

## 11. RAG and Provenance

Use the existing RAG MCP before creating or revising policy-sensitive content.

Store source references per field:

```json
{
  "recommendation": [
    {
      "source_id": "supplier-policy-v3",
      "chunk_id": "chunk-014",
      "title": "Supplier Policy v3",
      "retrieved_at": "2026-06-25T12:00:00Z"
    }
  ]
}
```

For the prototype:

* Source references are stored in SQLite.
* They are not embedded into the DOCX.
* They do not need a dedicated UI.
* They are returned by `get_decision_memo` for debugging and audit.
* A source reference means “used while generating this field,” not “proves every statement in this field.”

Do not build post-generation semantic compliance validation yet. Perform only deterministic checks.

## 12. Deterministic Validation

Before replacing the current DOCX:

1. Validate the structured fields with Pydantic.
2. Confirm all required template variables are present.
3. Reject unexpected template variables.
4. Render to a temporary DOCX.
5. Confirm the result is a valid ZIP/OOXML package.
6. Reopen it with `python-docx`.
7. Check that no unresolved `{{ ... }}` or `{% ... %}` template markers remain.
8. Confirm the resulting file is below a configured size limit.
9. Atomically replace `current.docx`.

Keep a small fixture suite that renders representative short, long, empty-optional, list, special-character, and Unicode inputs.

The final acceptance check should include opening generated samples in both ONLYOFFICE and desktop Microsoft Word. Automated package validation alone cannot prove layout fidelity.

## 13. Authentication and Security

For the internal prototype:

* Put the backend and ONLYOFFICE behind the company's authenticated reverse proxy.
* Authenticate MCP-to-backend calls with a dedicated service token.
* Pass a stable Open WebUI user identifier as `owner_id` if the integration exposes one.
* If Open WebUI cannot provide a trustworthy user ID, explicitly run the prototype as a small shared-team pilot instead of pretending it has per-user isolation.
* Use short-lived signed review and download URLs.
* Authorize every session operation against `owner_id` where trustworthy identity is available.
* Keep session IDs random and unguessable.
* Accept only configured template IDs.
* Never accept filesystem paths through MCP or HTTP inputs.
* Serve DOCX files with a fixed safe content type and sanitized filename.
* Keep JWT enabled between the backend and ONLYOFFICE.
* Do not log document contents, retrieved chunks, signed URLs, or secrets.
* Reject DOC, DOCM, and all non-DOCX uploads. The prototype does not need an upload endpoint at all.

This is an internal prototype security model, not a production authorization design.

## 14. Storage and Cleanup

Use SQLite plus local disk on one persistent backend host.

Defaults:

* Expire inactive sessions after 30 days.
* Delete expired DOCX files and their session rows with a scheduled cleanup command.
* Keep finalized sessions for 90 days during the pilot unless company policy requires another period.
* Limit each session to one current DOCX.
* Set conservative request, field, and output-file size limits.

Backups are not required for the prototype. Users should download finalized documents they need to retain.

## 15. User Flow

```text
User asks Open WebUI to create a decision memo
    -> agent retrieves relevant internal sources through RAG MCP
    -> agent calls create_decision_memo
    -> backend validates fields and renders current.docx
    -> tool returns a signed review URL
    -> user opens the URL in a separate tab
    -> ONLYOFFICE displays the DOCX in view-only mode

User requests a revision in Open WebUI
    -> agent reads current session state
    -> agent optionally retrieves more sources
    -> agent calls revise_decision_memo with expected_revision
    -> backend rerenders current.docx and increments revision
    -> agent returns a fresh review URL
    -> user reloads or reopens the viewer
```

## 16. Prototype Acceptance Criteria

The prototype is successful when:

1. A user can create a decision memo from Open WebUI.
2. The memo uses the approved DOCX template and retains its styles, header, footer, and basic layout.
3. At least two fields can be revised through subsequent chat instructions.
4. A stale revision is rejected instead of silently overwriting a newer update.
5. The returned review URL opens the current DOCX in a separate, view-only browser tab.
6. The viewer shows the latest revision after reload or a newly generated URL.
7. The current DOCX can be downloaded and opened successfully in Microsoft Word.
8. Required fields and unresolved template tags are detected before publication.
9. RAG source IDs are retained for generated policy-sensitive fields.
10. No API or MCP input can select an arbitrary filesystem path or arbitrary template.

## 17. Deferred Decisions

Do not decide these until the prototype demonstrates value:

* Manual browser editing and save synchronization.
* Immutable versions and rollback.
* Visual or semantic diffs.
* A generic logical DOCX model.
* Content controls or bookmark-based in-place patching.
* Arbitrary uploaded DOCX support.
* Post-generation LLM validation.
* PDF export.
* Standalone document workspace.
* Multi-user collaboration.
* Production database and object storage.
* Canonical records storage and approval workflow.

## 18. Implementation Order

1. Create and validate the decision memo DOCX template.
2. Build a local renderer from fixed JSON to DOCX.
3. Add deterministic output validation and fixture tests.
4. Add the FastAPI session and download endpoints.
5. Integrate ONLYOFFICE in static view-only mode.
6. Add the four minimal MCP operations.
7. Connect Open WebUI and the existing RAG MCP.
8. Run the workflow with real management-style examples.

The first technical spike should prove template rendering and ONLYOFFICE viewing before building the MCP integration.

## 19. References

* [ONLYOFFICE view-only configuration](https://api.onlyoffice.com/docs/docs-api/get-started/how-it-works/viewing/)
* [ONLYOFFICE document configuration, keys, and source URLs](https://api.onlyoffice.com/docs/docs-api/usage-api/config/document/)
* [ONLYOFFICE editor configuration](https://api.onlyoffice.com/docs/docs-api/usage-api/config/editor/)
* [ONLYOFFICE Docs Docker installation and JWT configuration](https://helpcenter.onlyoffice.com/docs/installation/docs-community-install-docker.aspx)
* [python-docx-template documentation](https://docxtpl.readthedocs.io/en/latest/)
* [python-docx documentation](https://python-docx.readthedocs.io/en/latest/)
* [FastAPI documentation](https://fastapi.tiangolo.com/)
* [SQLite appropriate-use guidance](https://www.sqlite.org/whentouse.html)
