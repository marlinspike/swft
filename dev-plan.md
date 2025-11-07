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
