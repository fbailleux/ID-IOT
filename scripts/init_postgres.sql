-- ─────────────────────────────────────────────
-- Episodic RAG — Schéma PostgreSQL
-- Mémoire long terme des expériences passées
-- ─────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table principale des épisodes
CREATE TABLE IF NOT EXISTS episodes (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query       TEXT NOT NULL,
    answer      TEXT NOT NULL,
    session_id  VARCHAR(64) NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata    JSONB DEFAULT '{}',
    embedding   JSONB NOT NULL,  -- vecteur sérialisé
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour les recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(session_id);
CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON episodes(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_metadata ON episodes USING gin(metadata);

-- Table de télémétrie cognitive (optionnel)
CREATE TABLE IF NOT EXISTS cognitive_sessions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  VARCHAR(64) UNIQUE NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,
    query_count INTEGER DEFAULT 0,
    metadata    JSONB DEFAULT '{}'
);

-- Vue : épisodes récents avec score de récence
CREATE OR REPLACE VIEW recent_episodes AS
SELECT
    id,
    query,
    answer,
    session_id,
    timestamp,
    metadata,
    EXTRACT(EPOCH FROM (NOW() - timestamp)) / 3600 AS hours_ago
FROM episodes
ORDER BY timestamp DESC;

COMMENT ON TABLE episodes IS 'Mémoire épisodique long terme — expériences passées du système cognitif';
COMMENT ON TABLE cognitive_sessions IS 'Suivi des sessions utilisateur';
