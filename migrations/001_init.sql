-- ═══════════════════════════════════════════
-- MOMO — Database Schema
-- Postgres 16 + pgvector
-- ═══════════════════════════════════════════

-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════
-- TABLE: sessions
-- One row per continuous "conversation session"
-- ═══════════════════════════════════════════
CREATE TABLE sessions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,
    summary     TEXT,
    meta        JSONB DEFAULT '{}'::JSONB
);

-- ═══════════════════════════════════════════
-- TABLE: messages
-- Every turn in every conversation
-- ═══════════════════════════════════════════
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool', 'system')),
    content         TEXT NOT NULL,
    tool_name       TEXT,
    tool_args       JSONB,
    tool_result     JSONB,
    tokens_used     INTEGER,
    latency_ms      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);
CREATE INDEX idx_messages_role    ON messages(role);

-- ═══════════════════════════════════════════
-- TABLE: memories
-- Semantic memory — embedded chunks from conversations
-- ═══════════════════════════════════════════
CREATE TABLE memories (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  UUID REFERENCES sessions(id) ON DELETE SET NULL,
    message_id  UUID REFERENCES messages(id) ON DELETE SET NULL,
    content     TEXT NOT NULL,
    embedding   vector(768),
    source      TEXT DEFAULT 'conversation',
    importance  FLOAT DEFAULT 1.0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accessed_at TIMESTAMPTZ
);

CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX idx_memories_source ON memories(source);

-- ═══════════════════════════════════════════
-- TABLE: voice_profiles
-- Stores paths/metadata for cloned voice source files
-- ═══════════════════════════════════════════
CREATE TABLE voice_profiles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    audio_paths     TEXT[] NOT NULL,
    is_active       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ═══════════════════════════════════════════
-- TABLE: mcp_tool_calls
-- Audit log of every MCP tool invocation
-- ═══════════════════════════════════════════
CREATE TABLE mcp_tool_calls (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  UUID REFERENCES sessions(id) ON DELETE SET NULL,
    tool_name   TEXT NOT NULL,
    arguments   JSONB NOT NULL DEFAULT '{}'::JSONB,
    result      JSONB,
    success     BOOLEAN,
    error_msg   TEXT,
    latency_ms  INTEGER,
    called_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tool_calls_name    ON mcp_tool_calls(tool_name);
CREATE INDEX idx_tool_calls_session ON mcp_tool_calls(session_id);

-- ═══════════════════════════════════════════
-- TABLE: config
-- Runtime configuration key-value store
-- ═══════════════════════════════════════════
CREATE TABLE config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed defaults
INSERT INTO config (key, value, description) VALUES
    ('wake_word',               'momo',                         'Wake word for activation'),
    ('groq_model',              'llama-3.3-70b-versatile',      'Default Groq LLM model'),
    ('function_model',          'functiongemma',                 'Ollama model for tool routing'),
    ('tts_language',            'en',                            'XTTS-v2 language code'),
    ('memory_top_k',            '5',                             'How many memories to inject per turn'),
    ('memory_embedding_model',  'nomic-embed-text',        'OpenAI or local embedding model'),
    ('system_persona',          'You are MOMO, an advanced AI assistant. You are helpful, direct, and precise. You speak like a refined AI — calm, capable, and a touch witty. Never break character.', 'System persona injected into every LLM call'),
    ('asr_port',                '8001',                          'Internal ASR service port'),
    ('tts_port',                '8002',                          'Internal TTS service port'),
    ('mcp_port',                '8000',                          'Internal MCP server port'),
    ('main_port',               '3030',                          'External orchestrator port');
