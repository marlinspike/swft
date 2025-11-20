CREATE SCHEMA IF NOT EXISTS swft;
SET search_path TO swft, public;

CREATE TYPE ownership_t AS ENUM ('Provider','Shared','Customer');
CREATE TYPE status_t    AS ENUM ('Satisfied','Partial','Risk');
CREATE TYPE evidence_kind_t AS ENUM ('sbom','trivy','signature','stp','other');
CREATE TYPE evidence_role_t AS ENUM ('partial-telemetry','procedural','technical');
CREATE TYPE scope_t AS ENUM ('commercial','gov');
CREATE TYPE policy_state_t AS ENUM ('Compliant','NonCompliant','Unknown');

CREATE TABLE IF NOT EXISTS version_registry (
  id BIGSERIAL PRIMARY KEY,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  source_uri TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  version TEXT NOT NULL,
  added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(kind, name)
);

CREATE TABLE IF NOT EXISTS catalog_controls (
  control_id TEXT PRIMARY KEY,
  family TEXT NOT NULL,
  title TEXT,
  parameters_json JSONB NOT NULL,
  assessment_objectives_json JSONB NOT NULL,
  catalog_version_ref BIGINT NOT NULL REFERENCES version_registry(id)
);

CREATE TABLE IF NOT EXISTS baseline_profiles (
  id BIGSERIAL PRIMARY KEY,
  profile_name TEXT UNIQUE NOT NULL,
  profile_version_ref BIGINT NOT NULL REFERENCES version_registry(id)
);

CREATE TABLE IF NOT EXISTS baseline_controls (
  profile_id BIGINT NOT NULL REFERENCES baseline_profiles(id) ON DELETE CASCADE,
  control_id TEXT NOT NULL REFERENCES catalog_controls(control_id) ON DELETE CASCADE,
  PRIMARY KEY(profile_id, control_id)
);

CREATE TABLE IF NOT EXISTS policy_initiatives (
  id BIGSERIAL PRIMARY KEY,
  initiative_id TEXT NOT NULL,
  scope scope_t NOT NULL,
  initiative_version_ref BIGINT NOT NULL REFERENCES version_registry(id)
);

CREATE TABLE IF NOT EXISTS policy_definitions (
  policy_definition_id TEXT PRIMARY KEY,
  display_name TEXT,
  category TEXT
);

CREATE TABLE IF NOT EXISTS policy_mappings (
  initiative_fk BIGINT NOT NULL REFERENCES policy_initiatives(id) ON DELETE CASCADE,
  control_id TEXT NOT NULL REFERENCES catalog_controls(control_id) ON DELETE CASCADE,
  policy_definition_fk TEXT NOT NULL REFERENCES policy_definitions(policy_definition_id) ON DELETE CASCADE,
  PRIMARY KEY(initiative_fk, control_id, policy_definition_fk)
);

CREATE TABLE IF NOT EXISTS policy_states (
  id BIGSERIAL PRIMARY KEY,
  initiative_fk BIGINT NOT NULL REFERENCES policy_initiatives(id) ON DELETE CASCADE,
  control_id TEXT NOT NULL REFERENCES catalog_controls(control_id) ON DELETE CASCADE,
  policy_definition_fk TEXT NOT NULL REFERENCES policy_definitions(policy_definition_id) ON DELETE CASCADE,
  assignment_id TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  compliance_state policy_state_t NOT NULL,
  last_evaluated TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_files (
  id BIGSERIAL PRIMARY KEY,
  kind evidence_kind_t NOT NULL,
  file_path TEXT NOT NULL,
  content_hash TEXT NOT NULL UNIQUE,
  size_bytes BIGINT NOT NULL,
  collected_at TIMESTAMPTZ NOT NULL,
  run_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sbom_components (
  id BIGSERIAL PRIMARY KEY,
  evidence_fk BIGINT NOT NULL REFERENCES evidence_files(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  version TEXT,
  purl TEXT,
  licenses TEXT
);

CREATE TABLE IF NOT EXISTS trivy_findings (
  id BIGSERIAL PRIMARY KEY,
  evidence_fk BIGINT NOT NULL REFERENCES evidence_files(id) ON DELETE CASCADE,
  cve_id TEXT NOT NULL,
  severity TEXT NOT NULL,
  pkg TEXT,
  installed_version TEXT,
  fixed_version TEXT,
  artifact TEXT,
  path TEXT
);

CREATE TABLE IF NOT EXISTS signatures (
  id BIGSERIAL PRIMARY KEY,
  evidence_fk BIGINT NOT NULL REFERENCES evidence_files(id) ON DELETE CASCADE,
  image_digest TEXT NOT NULL,
  verified BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
  id BIGSERIAL PRIMARY KEY,
  project_key TEXT UNIQUE NOT NULL,
  boundary_description TEXT
);

CREATE TABLE IF NOT EXISTS project_services (
  project_fk BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  service_name TEXT NOT NULL,
  PRIMARY KEY(project_fk, service_name)
);

CREATE TABLE IF NOT EXISTS project_regions (
  project_fk BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  region_name TEXT NOT NULL,
  PRIMARY KEY(project_fk, region_name)
);

CREATE TABLE IF NOT EXISTS parameter_values (
  project_fk BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  control_id TEXT NOT NULL REFERENCES catalog_controls(control_id) ON DELETE CASCADE,
  param_id TEXT NOT NULL,
  value TEXT NOT NULL,
  PRIMARY KEY(project_fk, control_id, param_id)
);

CREATE TABLE IF NOT EXISTS implemented_requirements (
  id BIGSERIAL PRIMARY KEY,
  project_fk BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  control_id TEXT NOT NULL REFERENCES catalog_controls(control_id) ON DELETE CASCADE,
  ownership ownership_t NOT NULL,
  narrative TEXT,
  status status_t NOT NULL,
  UNIQUE(project_fk, control_id)
);

CREATE TABLE IF NOT EXISTS impl_req_evidence (
  impl_req_fk BIGINT NOT NULL REFERENCES implemented_requirements(id) ON DELETE CASCADE,
  evidence_fk BIGINT NOT NULL REFERENCES evidence_files(id) ON DELETE CASCADE,
  role evidence_role_t NOT NULL,
  PRIMARY KEY(impl_req_fk, evidence_fk)
);

CREATE TABLE IF NOT EXISTS back_matter_resources (
  id BIGSERIAL PRIMARY KEY,
  project_fk BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  href TEXT NOT NULL,
  evidence_fk BIGINT REFERENCES evidence_files(id)
);

CREATE TABLE IF NOT EXISTS runs (
  id BIGSERIAL PRIMARY KEY,
  project_fk BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  run_id TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  UNIQUE(project_fk, run_id)
);

CREATE TABLE IF NOT EXISTS outputs (
  id BIGSERIAL PRIMARY KEY,
  project_fk BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  run_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('ssp','poam')),
  file_path TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  FOREIGN KEY(project_fk, run_id) REFERENCES runs(project_fk, run_id)
);

CREATE TABLE IF NOT EXISTS components (
  id BIGSERIAL PRIMARY KEY,
  component_key TEXT UNIQUE NOT NULL,
  kind TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS impl_req_components (
  impl_req_fk BIGINT NOT NULL REFERENCES implemented_requirements(id) ON DELETE CASCADE,
  component_fk BIGINT NOT NULL REFERENCES components(id) ON DELETE CASCADE,
  description TEXT,
  PRIMARY KEY(impl_req_fk, component_fk)
);
