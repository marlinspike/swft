## Phase 1 — Infra & Basics (Complete)
1. ~~FastAPI backend + React frontend scaffolded with CI-friendly project structure.~~ -- DONE
2. ~~GitHub Actions pipeline generates run manifests, SBOM, and Trivy JSON artefacts.~~ -- DONE
3. ~~Azure Blob Storage ingestion (flat `<project>-<run>-*.json` naming) powering the dashboard.~~ -- DONE
4. ~~Run detail UI with SBOM/Trivy summaries, raw JSON viewers, and authorization signal charts.~~ -- DONE

## Phase 2 — Operational & Daily Use Enhancements (Complete)
1. ~~Sample FastAPI workload and “build low, deploy high” workflow maintained for demos.~~ -- DONE
2. ~~UX refinements: breadcrumbs, light/dark mode, download buttons, info popovers.~~ -- DONE
3. ~~app-design.md knowledge base + AI assistant with personas, streaming, keyboard shortcuts, and auto-context (run manifest, SBOM, Trivy).~~ -- DONE
4. ~~Model catalogue + OpenAI/Azure configuration surfaced via `/assistant/config`, including token-limit metadata.~~ -- DONE

## Phase 3 — Integration & Enhancements
1. ~~GenerativeAI-based search and summarization of vulnerability findings.~~ -- DONE
2. Webhook or queue trigger to notify SCAs when new runs arrive or thresholds exceeded.
3. Optional DoD SWFT API integration (submit `run.json`, SBOM links).

## Phase 4 — Operations
- **Deployment**  
  - Containerize backend/frontend.  
  - Deploy to Azure App Service or Container Apps with managed identity.  
- **Monitoring**: Azure Monitor dashboards, alerts on 4xx/5xx, blob access metrics.  
- **Security**: routine key rotation, penetration testing, review of blob access policies.  
- **Documentation**: runbook for SCAs, onboarding guide for project teams, API reference.

## Phase 5 — Backlog & Future Work
- Persist parsed SBOM/vulnerability data into Cosmos DB/PostgreSQL for cross-run analytics.
- GenAI assists for what-if analysis, cross-project findings, remediation advice, executive summaries.
- Cross-project diffing (highlight new vulnerabilities since previous run).
- Runtime attestation data ingestion (e.g., Ratify, Defender for Cloud).
- Support additional artifact types (Cosign bundle, Terraform plans, provenance attestations).


---

Add an implementation-notes editor in the SWFT workspace so teams can edit app-design.md directly in the web UI.

Order: 1 (fastest win — repurposes existing artifact plumbing and gives immediate user value).
Difficulty: Medium; mostly frontend form + new API endpoint to read/write the markdown blob.
Expose inherited/not-applicable tags for each control (ownership + status toggles).

Order: 2 (requires a couple of new API methods plus UX for listing implemented requirements).
Difficulty: Medium-high; involves schema reads, extra state in the React page, and careful UX so assessors don’t get overwhelmed.


Workspace Flow

Entry (SWFT landing): Keep the /swft roster as the gateway. Surface each project with status chips (e.g., “Boundary ready,” “Evidence synced,” “Notes updated ⟲ 2 days ago”) so users know what needs attention before they click into a workspace. Add a right‑aligned “+ New Project” button to guide creation without the CLI.

Workspace overview: Expand the hero card into three quick metrics (Boundary, Implementation Notes, Evidence) with colored states and tooltips. Include a “Last updated” timestamp for each data set so teams instantly see whether they’re in sync.

Project Boundary card: Maintain the two-column selector UI but add (1) inline typeahead chips (like multi-select pills) to reduce scrolling through lookup lists and (2) a mini preview of the saved boundary text vs. draft, with a “view diff” option so edits feel reversible. Place the “Save” button at the top-right of the card too, matching common form patterns.

Implementation Notes card (new):

Placement: Directly under the Boundary card so the narrative flows from metadata into prose.
Layout: Split into tabs — “Current Draft” (rich text Markdown editor, auto-save indicators, commenter avatars) and “History” (list of prior snapshots tied to run IDs or commit timestamps). Add helper chips for frequently referenced sections (Mission, Components, Controls) to keep writers anchored.
Workflow: Editing auto-locks to avoid collisions; a “Publish & Sync to pipeline” button reuses the artifact uploader so the next build grabs the new content automatically. Confirmation toast explains when the assistant and exporter will see the changes.
Control Parameters & Ownership: Combine into a single “Controls you’re working on” accordion. Each control row shows: parameters (editable inline as today) and an ownership/status pill (Provider/Shared/Customer/Not Applicable) with a small dropdown. Collapsing the row reveals implementation-note snippets pulled from the editor so writers and parameter owners stay aligned. Add filtering chips (e.g., “AC family,” “Missing value,” “Provider-owned”) to make the list manageable.

Evidence ingestion:

Auto Import tab: Keep the current light/dark contrast but add a timeline showing recent run IDs with badges (SBOM stored, Trivy stored, Signature missing). Clicking a badge replays the ingestion call, which encourages the “no CLI” mantra.
Manual Upload tab: Convert the stacked forms into cards with drag‑and‑drop, progress bars, and success/error badges aligned to the rest of the design system. Offer a “Download sample JSON” link so users know the schema each upload expects.
Azure Policy imports: Break into two steps: (1) select initiatives (built-in or upload) with clear descriptions, (2) track import history with status icons and linked evidence. A timeline view reassures users that these heavyweight operations completed without digging through logs.

Run detail + Assistant: Maintain the evidence viewer but mirror the workspace’s styling (same font weights, pill buttons). When a run has a newer app-design.md, highlight the delta and offer a “Promote to current draft” action to keep the narrative fresh.

Flow Considerations

Guided onboarding: For new projects, show a checklist panel (“1. Define boundary, 2. Draft implementation notes, 3. Import catalog, 4. Capture evidence”). Each item links to the card where the action lives and flips green when done.

Context persistence: Store unsaved edits (boundary text, implementation notes) in local state so page refreshes are safe. Show subtle “Unsaved changes” chips near the top nav.

Consistency: Reuse the same chip styles, button shapes, and status colors across cards so the workspace reads like a cohesive form, not a patchwork of utilities.

Accessibility: Ensure selectable chips and dropdowns are keyboard-friendly, expose ARIA labels for Save/Import buttons, and keep color contrast high in both light and dark themes.

This flow keeps everything in-browser, surfaces the highest-priority actions up front, and adds the implementation-notes UX in a way that feels native to the existing design system—all while making the experience attractive and approachable for both dev teams and assessors.



----

app-design.md Source of Truth

Treat the document as project-scope canonical content that lives alongside the other SWFT assets. Store the “current draft” in the compliance database (Postgres) or in the appdesign blob container with metadata marking it as the active version. Each pipeline run then copies that snapshot into its artifacts, so historical builds keep their version while the assistant always reads the latest project draft.
Flow: the workspace editor writes to the canonical record → backend updates the project’s “current app-design” field (or blob + pointer) → the AI assistant (and eventual SSP export) fetches this latest draft immediately. Builds continue to archive the snapshot for replay. This delivers the behavior you want: as soon as someone updates the doc in the UI, the assistant answers with the new content, and future builds automatically embed it.
Ownership / Not Applicable

Keep ownership tied to control responsibility (Provider, Shared, Customer). “Authorizing Official” isn’t a control owner; the AO evaluates evidence rather than implementing controls.
Recommended flow: default to Customer, let teams set Provider (Azure/GitHub), Shared, or mark a control as Not Applicable with a dedicated status flag. Once the SSP export is ready, the AO can review and lock those values, but there’s no need for an “Authorizing Official” owner—better to track reviewer sign-off separately (e.g., a validated_by audit field).
So: Ownership remains about who implements the control; status tracks Ready, Partial, Not Applicable. When you’re building the SSP, you might flip status to Submitted or Awaiting AO, but ownership shouldn’t change to AO.