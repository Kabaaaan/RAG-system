-- Purpose: add a generated SHA-256 hash to rag_resources and prevent duplicate text payloads.
--
-- Up
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE rag_resources
    ADD COLUMN hash VARCHAR(64)
    GENERATED ALWAYS AS (encode(digest(text, 'sha256'), 'hex')) STORED;

ALTER TABLE rag_resources
    ADD CONSTRAINT uq_rag_resources_hash UNIQUE (hash);

-- Down (rollback)
ALTER TABLE rag_resources
    DROP CONSTRAINT IF EXISTS uq_rag_resources_hash;

ALTER TABLE rag_resources
    DROP COLUMN IF EXISTS hash;
