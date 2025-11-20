SET search_path TO swft, public;

CREATE TABLE IF NOT EXISTS run_evidence (
  id BIGSERIAL PRIMARY KEY,
  run_fk BIGINT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  evidence_fk BIGINT NOT NULL REFERENCES evidence_files(id) ON DELETE CASCADE,
  UNIQUE (run_fk, evidence_fk)
);

