# Offline Implementation Guide

This file supplements `PROTOTYPE_DECISIONS.md` for an implementation model that cannot browse the internet.

It records the non-obvious integration details, installation traps, expected contracts, and artifacts that must be prepared before implementation starts.

## 1. Important Clarification: Prefer OpenAPI for the First Open WebUI Integration

The prototype backend is already planned as FastAPI, which automatically exposes an OpenAPI schema.

For the first prototype, connect Open WebUI directly to the FastAPI OpenAPI server instead of adding an MCP server and an MCP-to-OpenAPI proxy.

Reasons:

* Open WebUI's own documentation recommends OpenAPI for most deployments.
* It removes an extra protocol, process, dependency, and failure point.
* FastAPI already generates the required schema.
* The same application service functions can later be wrapped as MCP tools without changing document generation.

Keep transport code thin:

```text
OpenAPI endpoint
    -> application service
    -> repository + renderer

future MCP tool
    -> same application service
    -> repository + renderer
```

If the installed Open WebUI is version 0.6.31 or later, it can connect directly to an MCP server using Streamable HTTP. Native Open WebUI MCP does not support stdio or legacy SSE. If MCP is required for compatibility with `zoo code`, add a Streamable HTTP MCP adapter after the OpenAPI vertical slice works.

If the installed Open WebUI is older than 0.6.31:

* Use the FastAPI OpenAPI integration, or
* Use `mcpo` to translate a stdio/SSE MCP server to OpenAPI.

Do not implement all three paths in the prototype.

## 2. Information That Must Be Collected Before Coding

An offline implementation model must not guess these values.

Create a local `DEPLOYMENT_FACTS.md` or provide them in the implementation prompt:

```text
Host operating system and architecture:
Docker Engine version:
Docker Compose version:
Python version:
Open WebUI exact version:
Open WebUI deployment method:
Open WebUI container/service name:
Open WebUI network name:
Open WebUI public base URL:
Open WebUI can reach backend at:
ONLYOFFICE image tag and digest:
ONLYOFFICE public base URL:
Backend public base URL:
Backend internal Docker URL:
Company reverse proxy:
TLS termination location:
Company authentication method:
RAG tool name and exact input/output schema:
Whether Open WebUI passes a trustworthy user identity to tools:
Microsoft Word versions used for acceptance testing:
```

Also provide the real decision memo template. A coding model cannot create or verify a company-approved Word layout from a prose description.

## 3. Offline Artifact Bundle

Having source code is not enough. Package installers and Docker normally require internet access.

Before disconnecting, prepare:

```text
offline_bundle/
    images/
        onlyoffice-documentserver.tar
        project-backend.tar                 # once built
        open-webui.tar                      # only if it must be installed here
    wheels/
        *.whl
    docs/
        onlyoffice/
        open-webui/
        docxtpl/
        python-docx/
        fastapi/
        mcp/                                # only if MCP will be implemented
    examples/
        onlyoffice-minimal-viewer/
        openwebui-tool-connection/
    checksums/
        SHA256SUMS
    VERSION_MANIFEST.md
```

The connected preparation machine should:

1. Pin every Python dependency to an exact version.
2. Generate and commit a lock file.
3. Download wheels for the deployment operating system, CPU architecture, and Python version.
4. Pull Docker images by explicit tag.
5. Record image digests.
6. Export images with `docker save`.
7. Save the relevant official documentation pages as HTML or PDF.
8. Generate SHA-256 checksums for the bundle.
9. Test installing from the bundle on a clean machine with networking disabled.

Typical wheel preparation:

```bash
python -m pip download --dest offline_bundle/wheels -r requirements.lock
```

Typical offline installation:

```bash
python -m pip install \
  --no-index \
  --find-links offline_bundle/wheels \
  -r requirements.lock
```

Typical image preparation:

```bash
docker pull onlyoffice/documentserver:<tested-tag>
docker image inspect onlyoffice/documentserver:<tested-tag>
docker save \
  -o offline_bundle/images/onlyoffice-documentserver.tar \
  onlyoffice/documentserver:<tested-tag>
```

Typical offline image loading:

```bash
docker load -i offline_bundle/images/onlyoffice-documentserver.tar
```

Do not use floating tags such as `latest` or `main` in the offline deployment. A tag alone is not immutable; record the digest too.

## 4. Suggested Python Dependency Set

The exact versions must be pinned in the lock file after a connected test installation.

The prototype is expected to need:

```text
fastapi
uvicorn
pydantic
pydantic-settings
sqlalchemy or built-in sqlite3
jinja2
docxtpl
python-docx
PyJWT
python-multipart
httpx
itsdangerous or an equivalent signed-URL implementation
pytest
```

Prefer built-in `sqlite3` unless the team already standardizes on SQLAlchemy. For this small schema, adding an ORM is optional.

Do not install `docxtpl[subdoc]` unless subdocuments are actually used. They are not required by the proposed decision memo template.

If MCP is added later, also include the official Python MCP SDK and pin it. Do not mix it into the first renderer/viewer milestone.

## 5. Recommended Deployment Topology

Use one Docker network with stable service names:

```text
browser
   |
   +---- HTTPS ----> reverse proxy
                       |
                       +----> Open WebUI
                       +----> backend
                       +----> ONLYOFFICE Docs

Open WebUI container ---- HTTP/internal ----> backend container
ONLYOFFICE container ---- HTTP/internal ----> backend document endpoint
backend-generated viewer page ---- browser ----> ONLYOFFICE api.js
```

Three different audiences need usable URLs:

1. The browser must reach the review page and ONLYOFFICE.
2. Open WebUI must reach the tool endpoint.
3. ONLYOFFICE must reach the backend to download the DOCX.

`localhost` means a different machine or container to each audience. Do not use it in shared deployment configuration.

Recommended environment variables:

```text
PUBLIC_BACKEND_URL=https://documents.company.internal
INTERNAL_BACKEND_URL=http://backend:8000
ONLYOFFICE_PUBLIC_URL=https://office.company.internal
ONLYOFFICE_JWT_SECRET=<long-random-secret>
TOOL_API_TOKEN=<separate-long-random-secret>
SIGNED_URL_SECRET=<separate-long-random-secret>
DATA_DIR=/data
```

Do not reuse one secret for all three purposes.

## 6. ONLYOFFICE Installation Is the Most Non-Trivial Part

### 6.1 Container setup

Run a tested, pinned ONLYOFFICE Document Server image with:

* A persistent and explicitly configured `JWT_SECRET`.
* JWT enabled.
* A stable hostname.
* Enough memory for Document Server.
* A health check or startup wait.
* Reverse-proxy support for WebSocket upgrade headers.

The container may take one or two minutes to become usable on its first start.

The browser must be able to load:

```text
{ONLYOFFICE_PUBLIC_URL}/web-apps/apps/api/documents/api.js
```

The backend must not render the viewer page until the configured public URL is known.

### 6.2 View-only configuration

The review page should create the editor with a configuration shaped like:

```json
{
  "documentType": "word",
  "document": {
    "fileType": "docx",
    "key": "doc-SESSION_ID-REVISION",
    "title": "Safe document title.docx",
    "url": "http://backend:8000/internal/documents/SESSION_ID?token=SIGNED_TOKEN",
    "permissions": {
      "download": true,
      "edit": false,
      "print": true
    }
  },
  "editorConfig": {
    "mode": "view",
    "coEditing": {
      "mode": "strict",
      "change": false
    },
    "callbackUrl": "http://backend:8000/internal/onlyoffice/callback/SESSION_ID",
    "lang": "en"
  },
  "token": "ONLYOFFICE_CONFIG_JWT"
}
```

Notes:

* `document.key` is required.
* It must change when the generated file changes.
* Keep it under 128 characters and use only supported key characters.
* Use opaque session IDs; do not put document contents or user information into the key.
* `document.url` must be reachable from the ONLYOFFICE container.
* The review URL and the internal document URL are different things.
* The callback endpoint can return `{"error": 0}` for the view-only prototype. Keep it present because `callbackUrl` is part of the standard editor configuration.
* Set `permissions.edit` to `false` in addition to `editorConfig.mode = "view"`.

### 6.3 JWT signing

ONLYOFFICE JWT is not the same token as the application's signed review/download URL.

Generate the configuration token with HMAC-SHA256 using the exact same secret configured in the ONLYOFFICE container:

```python
import jwt

config_without_token = {
    "documentType": "word",
    "document": {
        "fileType": "docx",
        "key": document_key,
        "title": safe_title,
        "url": internal_document_url,
        "permissions": {
            "download": True,
            "edit": False,
            "print": True,
        },
    },
    "editorConfig": {
        "mode": "view",
        "coEditing": {
            "mode": "strict",
            "change": False,
        },
        "callbackUrl": callback_url,
        "lang": "en",
    },
}

onlyoffice_token = jwt.encode(
    config_without_token,
    onlyoffice_jwt_secret,
    algorithm="HS256",
)

config = {
    **config_without_token,
    "token": onlyoffice_token,
}
```

The JWT payload must match the configuration being sent. Do not sign one dictionary and then mutate its signed fields.

Local/private document URLs require token validation. Keep JWT enabled even for an internal prototype.

### 6.4 Internal-address request filtering

Some ONLYOFFICE versions reject downloads from private IP addresses or internal Docker DNS names as an SSRF protection.

Symptom:

```text
The viewer loads but reports that the document could not be downloaded.
ONLYOFFICE logs show a blocked private/local address or download error.
```

Preferred fix:

* Give the backend a stable HTTPS hostname that ONLYOFFICE can resolve and reach.

Prototype-only fallback inside an isolated network:

* Configure ONLYOFFICE's request-filtering agent to allow the required private address.
* Restrict the backend endpoint with signed URLs and network policy.
* Never broadly expose that relaxed Document Server to untrusted users.

The exact request-filtering setting varies by ONLYOFFICE release. Preserve the official configuration documentation for the selected image in the offline bundle and test this before disconnecting.

Do not tell the implementation model to disable SSL verification globally or turn off JWT to make downloads work.

### 6.5 Reverse proxy

The reverse proxy must:

* Forward the original host and protocol.
* Support WebSocket `Upgrade` and `Connection` headers.
* Allow request and response sizes sufficient for DOCX files.
* Use timeouts long enough for Document Server startup and conversion.
* Expose ONLYOFFICE and the backend under stable origins.

If the browser shows a blank frame, inspect:

* Browser developer-console errors.
* Mixed HTTP/HTTPS content.
* Content Security Policy frame restrictions.
* Failure to load `api.js`.
* Reverse-proxy WebSocket errors.
* Incorrect public versus internal URL usage.

## 7. Minimal Viewer HTML Contract

The server-rendered review page needs:

```html
<script src="{{ onlyoffice_public_url }}/web-apps/apps/api/documents/api.js"></script>
<div id="onlyoffice-editor"></div>
<script>
  const config = {{ editor_config_json | safe }};
  const editor = new DocsAPI.DocEditor("onlyoffice-editor", config);
</script>
```

Requirements:

* Serialize `editor_config_json` with a real JSON serializer.
* Do not construct JavaScript by concatenating document titles or URLs.
* Escape the JSON safely for embedding in HTML.
* Do not mark arbitrary user strings as HTML-safe.
* Give the editor container an explicit height, such as `height: calc(100vh - 4rem)`.
* Destroy the editor instance if the page dynamically replaces it.

For the prototype, a normal full-page reload after a revision is simpler than the ONLYOFFICE `refreshFile` method.

## 8. Application URL Tokens

Use short-lived signed tokens for:

```text
/review/{session_id}?token=...
/download/{session_id}?token=...
/internal/documents/{session_id}?token=...
```

Each token should bind:

```text
purpose
session_id
revision
owner_id or authorized audience
expiry time
```

A review token must not automatically be accepted as an internal Document Server token unless that is an explicit design choice.

Reject:

* Expired tokens.
* Tokens for another purpose.
* Tokens for another session.
* Tokens for an older revision where the route promises the current revision.
* Unknown or finalized sessions where the operation is not allowed.

Use a constant-time signature comparison through a maintained signing library.

## 9. Open WebUI Connection Details

### 9.1 OpenAPI path

For the recommended prototype path:

1. Start FastAPI on an address reachable by Open WebUI.
2. Verify `/openapi.json` and `/docs`.
3. Register the backend as an OpenAPI external tool server.
4. Use a global/admin tool server for a shared management pilot.
5. Configure bearer authentication with `TOOL_API_TOKEN`.
6. Explicitly enable the global tools for the pilot users or model.

If Open WebUI runs in Docker, `localhost` is the Open WebUI container itself. Use the backend's Docker service name or another reachable hostname.

Open WebUI distinguishes:

* User tool servers: requests may originate from the browser.
* Global tool servers: requests originate from the Open WebUI backend.

Use a global tool server for this prototype so internal credentials and storage are not exposed to browsers.

### 9.2 Native MCP path, if chosen later

Requirements:

```text
Open WebUI >= 0.6.31
MCP transport = Streamable HTTP
Stable WEBUI_SECRET_KEY
MCP URL reachable from Open WebUI backend
```

Select `MCP (Streamable HTTP)` in Open WebUI, not `OpenAPI`.

Do not configure a stdio MCP command in Open WebUI. That format is for desktop/local MCP hosts and will not work as a native Open WebUI server connection.

### 9.3 Model capability

The local LLM must reliably call tools and follow JSON schemas.

Before integrating RAG or DOCX:

1. Expose a harmless echo/test endpoint.
2. Verify the model chooses it when asked.
3. Verify required arguments are present.
4. Verify it can make two sequential tool calls.
5. Verify it can use a returned `session_id` in a later turn.
6. Verify tool output URLs are shown as clickable links rather than rewritten.

If native function calling is unreliable, use an Open WebUI agent/prompt workflow that explicitly instructs the model when to call each tool. Do not debug document generation and tool-calling quality at the same time.

## 10. API Shape for Open WebUI

Keep endpoint names and descriptions unusually explicit because a local model must select them.

Recommended endpoints:

```text
POST /tools/create_decision_memo
POST /tools/revise_decision_memo
GET  /tools/decision_memos/{session_id}
POST /tools/decision_memos/{session_id}/finalize
```

Avoid two separate tools whose descriptions overlap heavily.

The create endpoint should accept completed structured fields rather than `user_request` alone:

```json
{
  "title": "Supplier pilot decision",
  "author_or_department": "Operations",
  "decision_requested": "Approve a six-month pilot.",
  "background": "...",
  "options": [
    {
      "name": "Approve pilot",
      "summary": "..."
    }
  ],
  "recommendation": "...",
  "risks": ["..."],
  "next_steps": ["..."],
  "source_refs": []
}
```

The revise endpoint should accept only changed fields:

```json
{
  "expected_revision": 2,
  "field_updates": {
    "recommendation": "Revised recommendation"
  },
  "source_refs": {
    "recommendation": []
  }
}
```

Recommended error body:

```json
{
  "error": {
    "code": "stale_revision",
    "message": "Expected revision 2, but the current revision is 3.",
    "current_revision": 3,
    "recovery": "Read the current memo and retry the requested field updates."
  }
}
```

Use machine-readable codes:

```text
validation_error
session_not_found
forbidden
stale_revision
session_finalized
template_error
render_failed
viewer_unavailable
```

## 11. Identity Limitation in Open WebUI

Do not assume that a generic external tool call automatically carries a trustworthy Open WebUI user ID.

Before implementing per-user authorization, inspect the exact installed Open WebUI behavior and determine whether it sends:

```text
authenticated user ID
chat ID
message ID
configured service credential
```

If only one shared service token is available, the backend cannot securely distinguish individual users from that token alone.

For the prototype, choose one explicit mode:

### Shared pilot mode

* One restricted management pilot group.
* Sessions are accessible to that group.
* No claim of per-user isolation.
* Random session IDs and signed URLs still apply.

### Trusted identity mode

* Reverse proxy or Open WebUI sends a signed user identity.
* Backend validates the signature or trusted proxy header.
* `owner_id` is enforced on every operation.

Do not trust a caller-provided JSON `owner_id`.

## 12. `docxtpl` Details the Implementation Model Needs

### 12.1 Template tags

Normal variables:

```text
{{ title }}
{{ background }}
```

Tags must have spaces after opening delimiters and before closing delimiters.

Jinja tags must remain in the same Word run. Word may split visually continuous text into several runs after formatting or editing, so template tests are mandatory.

Special structural tags include:

```text
{%p ... %}   paragraph
{%tr ... %}  table row
{%tc ... %}  table column
{%r ... %}   run
```

Do not use the same structural tag twice in one paragraph, row, column, or run.

### 12.2 Escaping

`docxtpl` does not escape XML-sensitive characters by default.

Always render untrusted/generated strings with:

```python
template.render(context, autoescape=True)
```

Test at least:

```text
&
<
>
quotes
German umlauts
emoji
Arabic or CJK text if relevant
newlines
very long paragraphs
```

### 12.3 Newlines and paragraphs

For a normal string variable:

```text
\n = line break
\a = new paragraph
\t = tab
\f = page break
```

Do not let the LLM emit control conventions such as `\a` directly. Convert a typed list of paragraphs into the required representation in deterministic backend code.

### 12.4 Lists

Prefer actual template loops over putting bullet characters into one string.

Example template rows or paragraphs should be built and tested in Word. The backend should provide:

```json
{
  "risks": [
    {"text": "Risk one"},
    {"text": "Risk two"}
  ]
}
```

Do not ask the LLM to choose Word style names.

### 12.5 Variable validation

Before rendering:

```python
required = template.get_undeclared_template_variables()
```

Compare the returned set with the approved schema.

Fail if:

* The template contains an unknown variable.
* A required schema field is absent.
* A required field is blank.

After rendering, also inspect all XML parts in the DOCX ZIP for unresolved Jinja delimiters. Checking only visible paragraphs with `python-docx` can miss headers, footers, text boxes, and other parts.

### 12.6 Do not reuse a mutated template instance across requests

Create a new `DocxTemplate` instance for each render. This avoids accidental state leakage between sessions and keeps concurrent requests simpler.

## 13. DOCX Validation Details

A DOCX is a ZIP package. Minimum automated checks:

```text
File starts as a readable ZIP archive.
[Content_Types].xml exists.
word/document.xml exists.
All ZIP entries can be read without CRC errors.
python-docx can open the output.
No unresolved {{, }}, {%, or %} markers remain in XML parts.
Output size is within configured bounds.
Expected title text exists.
```

Also guard against ZIP bombs when any DOCX input is ever accepted. The current prototype accepts only trusted templates, so this is primarily a future concern.

Automated checks cannot confirm pagination or visual fidelity. Keep golden sample files and manually open them in:

* ONLYOFFICE viewer.
* A supported desktop Microsoft Word version.

Test long content that crosses a page boundary. Headers, footers, table rows, and orphaned headings often fail only under realistic lengths.

## 14. SQLite and Concurrency

The prototype can use one SQLite database, but configure it deliberately:

```text
foreign_keys = ON
journal_mode = WAL
busy_timeout = 5000 ms or similar
```

Revision updates must be atomic:

```sql
UPDATE sessions
SET current_revision = current_revision + 1,
    current_fields_json = ?,
    updated_at = ?
WHERE session_id = ?
  AND current_revision = ?
  AND status = 'active';
```

If the affected row count is zero, return `stale_revision`, `session_finalized`, or `session_not_found` after checking the current row.

Recommended render flow:

1. Read and validate the active session.
2. Merge validated field updates.
3. Render to a unique candidate path in the session directory.
4. Validate the candidate DOCX.
5. Begin a short database transaction.
6. Atomically compare/update the revision and `current_docx_path`.
7. Commit.
8. Delete the previously referenced DOCX.

Use candidate names such as `candidate-{random-id}.docx`; they are implementation artifacts, not user-visible history. The database points to the one current file. This avoids replacing the old file before the database accepts the revision. If the database update fails, delete the candidate. If cleanup fails after commit, the current pointer remains correct and a startup or scheduled cleanup can remove unreferenced candidates.

For a prototype, serialize updates per session with an in-process lock in addition to the database revision check. Document that multiple backend replicas are unsupported.

## 15. File and Filename Safety

Never derive storage paths from a title.

Storage:

```text
data/sessions/{random_session_id}/{random_file_id}.docx
```

The database's `current_docx_path` selects the one live artifact. Old unreferenced files are deleted after a successful revision and by periodic cleanup; they are not exposed as document history.

Download filename:

```text
sanitized-title.docx
```

Sanitization rules:

* Remove path separators and control characters.
* Remove leading/trailing dots and spaces.
* Use a maximum base-name length.
* Always append `.docx` server-side.
* Provide an ASCII fallback in `Content-Disposition`.

Serve with:

```text
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
X-Content-Type-Options: nosniff
Content-Disposition: attachment; ...
Cache-Control: private, no-store
```

The internal ONLYOFFICE document endpoint may use `inline` rather than `attachment`, but should retain safe content type and authorization.

## 16. Template Creation Procedure

The template author should:

1. Start from the approved company memo.
2. Replace variable text with exact placeholder names.
3. Preserve styles, headers, footers, page setup, and fixed labels.
4. Create repeated risk, option, and next-step structures using tested `docxtpl` loops.
5. Avoid placing placeholders in text boxes or shapes unless specifically tested.
6. Ensure each normal placeholder is one Word run.
7. Save as DOCX, not DOCM.
8. Open and resave once in the supported desktop Word version.
9. Render the fixture set.
10. Approve screenshots or sample outputs before integration work continues.

Supply the offline implementation model with:

```text
template.docx
schema.json
example_context_minimal.json
example_context_full.json
expected-output screenshots
```

## 17. Suggested Test Matrix

### Renderer tests

```text
Minimum valid memo.
All fields populated.
Optional fields absent.
One item and many items in each list.
XML-sensitive characters.
Unicode.
Long paragraphs.
Long table cells.
No unresolved template tags.
Invalid schema field rejected.
Missing required field rejected.
```

### Session tests

```text
Create session.
Read session.
Valid revision update.
Stale revision rejected.
Finalized session rejects revision.
Unknown session rejected.
Concurrent revisions allow only one winner.
```

### Security tests

```text
Invalid service bearer token.
Expired review token.
Review token used on download endpoint.
Token for another session.
Path traversal strings in titles and IDs.
Non-DOCX template.
Oversized field.
HTML/script text remains document text and is not executed in review page.
```

### Integration tests

```text
Open WebUI reaches backend.
Open WebUI model invokes create tool.
Returned review URL is clickable.
Browser reaches review page.
Browser loads ONLYOFFICE api.js.
ONLYOFFICE reaches internal DOCX endpoint.
ONLYOFFICE displays current revision.
New revision changes document key.
Reload shows new content.
Download opens in Word.
```

## 18. Troubleshooting Order

When the viewer fails, test each hop separately:

1. Can the browser open the backend health endpoint?
2. Can the browser load ONLYOFFICE `api.js`?
3. Can the Open WebUI container call the backend health endpoint?
4. Can the ONLYOFFICE container resolve the backend hostname?
5. Can the ONLYOFFICE container download the signed DOCX URL?
6. Is the application URL token valid from ONLYOFFICE's clock and network?
7. Does the ONLYOFFICE configuration JWT use the same secret?
8. Does the JWT payload exactly match the editor configuration?
9. Is `document.key` new for the new revision?
10. Do ONLYOFFICE logs report private-address filtering?
11. Is the reverse proxy forwarding WebSocket upgrades?
12. Is the browser blocking mixed content or framing?

Do not debug all containers through the browser UI alone. Capture:

```text
backend logs
Open WebUI logs
ONLYOFFICE logs
reverse-proxy logs
browser console
browser network trace
```

Never include secrets or full signed URLs in shared logs.

## 19. Work That Still Requires a Human or Connected Preparation Step

An offline coding model cannot safely complete these alone:

* Select and download tested Docker image versions.
* Accept and review software licenses.
* Build the approved DOCX template in Word.
* Obtain internal DNS names and TLS certificates.
* Configure the company reverse proxy and SSO.
* Determine the installed Open WebUI version and tool behavior.
* Provide the exact existing RAG MCP contract.
* Confirm whether trustworthy user identity propagation exists.
* Perform visual acceptance in Microsoft Word.
* Decide whether ONLYOFFICE private-address filtering may be relaxed.
* Import packages and images into the disconnected environment.

These are prerequisites, not coding tasks to leave implicit.

## 20. Recommended Offline Implementation Sequence

Give the offline model one milestone at a time:

1. Render fixture JSON into DOCX with no server.
2. Add DOCX package validation and tests.
3. Add SQLite sessions and optimistic revision updates.
4. Add FastAPI create/read/revise/download endpoints.
5. Test FastAPI's OpenAPI schema with direct HTTP calls.
6. Add signed review and internal document URLs.
7. Integrate ONLYOFFICE using a hard-coded known-good DOCX.
8. Switch ONLYOFFICE to the generated current DOCX.
9. Connect the FastAPI OpenAPI tool server to Open WebUI.
10. Verify local-model tool calling with no RAG.
11. Add the existing RAG workflow.
12. Run the complete management memo scenario.

Do not begin with Open WebUI, RAG, document rendering, and ONLYOFFICE all connected. A failure would have too many plausible causes.

## 21. Offline Documentation to Preserve

Save these pages or their relevant contents in the offline bundle:

* ONLYOFFICE Docker installation and persistent JWT setup.
* ONLYOFFICE view-only configuration.
* ONLYOFFICE document configuration, especially `key` and `url`.
* ONLYOFFICE JWT signature configuration.
* ONLYOFFICE browser-token payload requirements.
* ONLYOFFICE reverse-proxy instructions for the selected proxy.
* ONLYOFFICE private-address request-filtering configuration for the selected image.
* Open WebUI OpenAPI tool-server integration.
* Open WebUI native MCP requirements for the installed version.
* `docxtpl` template syntax, escaping, lists/tables, and variable inspection.
* `python-docx` API documentation.
* FastAPI request models, security dependencies, file responses, and testing.
* SQLite WAL, transactions, and locking behavior.
* Official Python MCP SDK documentation if MCP is included.

Online references used to prepare this guide:

* [Open WebUI native MCP](https://docs.openwebui.com/features/mcp/)
* [Open WebUI OpenAPI integration](https://docs.openwebui.com/features/plugin/tools/openapi-servers/open-webui/)
* [Open WebUI MCP-to-OpenAPI support](https://docs.openwebui.com/features/plugin/tools/openapi-servers/mcp/)
* [ONLYOFFICE view-only mode](https://api.onlyoffice.com/docs/docs-api/get-started/how-it-works/viewing/)
* [ONLYOFFICE document configuration](https://api.onlyoffice.com/docs/docs-api/usage-api/config/document/)
* [ONLYOFFICE security](https://api.onlyoffice.com/docs/docs-api/get-started/how-it-works/security/)
* [ONLYOFFICE signatures](https://api.onlyoffice.com/docs/docs-api/additional-api/signature/)
* [ONLYOFFICE browser signature](https://api.onlyoffice.com/docs/docs-api/additional-api/signature/browser/)
* [ONLYOFFICE Docker installation](https://helpcenter.onlyoffice.com/docs/installation/docs-community-install-docker.aspx)
* [`docxtpl` documentation](https://docxtpl.readthedocs.io/en/latest/)
* [Official Python MCP server guide](https://modelcontextprotocol.io/docs/develop/build-server)
