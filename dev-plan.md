## Phases 1 & 2 Complete
1. Initial Operating Capaability with Minimal Lovable Product for SCAs to view SBOMs and Vulnerability scans per project/run.
2. Target app (works too!) for demoing SWFT-generated artifacts from the GitHub Actions pipeline.
3. Upload artifacts to Azure Blob Storage using flat names `<project>-<run>-*.json` for indexing.

## Phase 3 — Integration & Enhancements
1. API contract tests ensuring blob fixtures return expected structures.
2. Background refresh worker (optional) to pre-cache parsed data or compute aggregates.
3. GenerativeAI based search and summarization of vulnerability findings.
4. Export/reporting endpoints (PDF/CSV) summarizing high-risk findings.
5. Webhook or queue trigger to notify SCAs when new runs arrive or thresholds exceeded.
6. Optional DoD SWFT API integration (submit `run.json`, SBOM links).

## Phase 4 — Operations
- **Deployment**: containerize backend/frontend, deploy to Azure App Service or Container Apps with managed identity.  
- **Monitoring**: Azure Monitor dashboards, alerts on 4xx/5xx, blob access metrics.  
- **Security**: routine key rotation, penetration testing, review of blob access policies.  
- **Documentation**: runbook for SCAs, onboarding guide for project teams, API reference.

## Phase 5 — Backlog & Future Work
- Persist parsed SBOM/vulnerability data into Cosmos DB/PostgreSQL for cross-run analytics.
- GenAI assists for things like what-if analysis, finding across proejcts, remediation advice, and executive summaries.
- Cross-project diffing (highlight new vulnerabilities since previous run).
- Runtime attestation data ingestion (e.g., Ratify, Defender for Cloud).
- Support additional artifact types (Cosign bundle, Terraform plans, provenance attestations).

