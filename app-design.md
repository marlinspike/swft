# SWFT Application Design

> Keep this file current. The AI assistant injects every section into its system prompt so Authorizing Officials (AOs) and developers receive accurate, grounded answers.

## 1. Mission Objectives
- Programme charter, target accreditation levels, and key success metrics.
- AO decision cadence, stakeholder personas, and reporting expectations.
- Assumptions or constraints that influence release and authorization strategy.

## 2. System Overview
- Text description of the architecture plus links to diagrams (Mermaid, draw.io, or images).
- Source control, CI/CD, evidence storage, runtime environments, and how they connect.
- Trust boundaries, data flows, encryption, and logging points.

## 3. Component Glossary
Provide a table that maps every major component to its owner and purpose.

| Component | Owner | Description | Critical Dependencies |
|-----------|-------|-------------|-----------------------|
| e.g. `backend/app` | Platform Team | FastAPI service that indexes artefacts from storage | Azure Storage, Redis cache |

## 4. Evidence Catalogue
- How SBOM, Trivy, run manifests, and any other artefacts are generated, signed, and stored.
- Retention policies, encryption posture, and access governance (RBAC, network rules).
- Promotion flow between IL2, IL4, IL5 (or equivalent) environments.

## 5. Control Mapping
- Map NIST 800-53, DoD SRG, or programme-specific controls to pipeline stages and artefacts.
- Identify inherited versus system-specific controls.
- Note automated versus manual verification steps and the expected evidence.

## 6. Auto-Context Hints for the Assistant
- List any additional artefacts you want automatically passed to the assistant (for example, config JSON, pen-test summaries).
- Provide short guidance on how the assistant should interpret tricky fields or known caveats.

## 7. Operational Playbooks
- Responder procedures for failed runs, critical CVEs, policy drift, or cosign failures.
- Escalation contacts, SLA targets, and how to re-run or roll back deployments.
- Links to PagerDuty, Teams channels, or ticket queues that should be referenced.

## 8. Environment Matrix
Capture environment-specific details that the AO may ask about.

| Environment | Hosting | Data classification | AuthN/AuthZ notes | Change window |
|-------------|---------|---------------------|------------------|---------------|
| IL2 Dev | Azure Commercial | Public | GitHub OIDC + Azure AD | Daily 08:00-18:00 ET |

## 9. Architecture Decisions and Risks
- Summaries of ADRs or notable design trade-offs with links to full documents.
- Known risks, open mitigations, and expected completion dates.
- Backlog items that would materially change the authorization posture.

## 10. Change Log
Maintain a simple dated history so the assistant can reference recent updates.

| Date | Change | Author |
|------|--------|--------|
| 2025-11-06 | Initial outline committed to support AO assistant conversations. | Platform Team |
