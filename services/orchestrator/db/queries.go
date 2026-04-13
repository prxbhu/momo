package db

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

type Message struct {
	ID        string
	Role      string
	Content   string
	CreatedAt time.Time
}

type Memory struct {
	Content string
}

type Session struct {
	ID        string          `json:"id"`
	StartedAt time.Time       `json:"started_at"`
	EndedAt   *time.Time      `json:"ended_at"`
	Summary   *string         `json:"summary"`
	Meta      json.RawMessage `json:"meta"`
}

func (db *DB) CreateSession(ctx context.Context) (string, error) {
	var id string
	err := db.conn.QueryRowContext(ctx, "INSERT INTO sessions DEFAULT VALUES RETURNING id").Scan(&id)
	return id, err
}

func (db *DB) GetSessions(ctx context.Context, limit, offset int) ([]Session, error) {
	rows, err := db.conn.QueryContext(ctx,
		"SELECT id, started_at, ended_at, summary, meta FROM sessions ORDER BY started_at DESC LIMIT $1 OFFSET $2",
		limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var sessions []Session
	for rows.Next() {
		var s Session
		var meta []byte
		if err := rows.Scan(&s.ID, &s.StartedAt, &s.EndedAt, &s.Summary, &meta); err != nil {
			return nil, err
		}
		s.Meta = meta
		sessions = append(sessions, s)
	}
    // Return empty slice instead of nil for better JSON serialization
    if sessions == nil {
        sessions = []Session{}
    }
	return sessions, nil
}

func (db *DB) SaveMessage(ctx context.Context, sessionID, role, content string) error {
	_, err := db.conn.ExecContext(ctx,
		"INSERT INTO messages (session_id, role, content) VALUES ($1, $2, $3)",
		sessionID, role, content)
	return err
}

func (db *DB) GetMessages(ctx context.Context, sessionID string, limit int) ([]Message, error) {
	rows, err := db.conn.QueryContext(ctx,
		"SELECT id, role, content, created_at FROM messages WHERE session_id = $1 ORDER BY created_at ASC LIMIT $2",
		sessionID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var msgs []Message
	for rows.Next() {
		var m Message
		if err := rows.Scan(&m.ID, &m.Role, &m.Content, &m.CreatedAt); err != nil {
			return nil, err
		}
		msgs = append(msgs, m)
	}
	return msgs, nil
}

func (db *DB) RecallMemories(ctx context.Context, embedding []float32, topK int) ([]Memory, error) {
	embeddingJSON, err := json.Marshal(embedding)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal embedding: %w", err)
	}

	rows, err := db.conn.QueryContext(ctx,
		"SELECT content FROM memories ORDER BY embedding <=> $1::vector LIMIT $2",
		string(embeddingJSON), topK)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var memories []Memory
	for rows.Next() {
		var m Memory
		if err := rows.Scan(&m.Content); err != nil {
			return nil, err
		}
		memories = append(memories, m)
	}
	return memories, nil
}

func (db *DB) UpsertMemory(ctx context.Context, sessionID, content string, embedding []float32) error {
	embeddingJSON, err := json.Marshal(embedding)
	if err != nil {
		return fmt.Errorf("failed to marshal embedding: %w", err)
	}

	_, err = db.conn.ExecContext(ctx,
		"INSERT INTO memories (session_id, content, embedding) VALUES ($1, $2, $3::vector)",
		sessionID, content, string(embeddingJSON))
	return err
}

func (db *DB) LogToolCall(ctx context.Context, sessionID, toolName string, args interface{}, result string) error {
	argsJSON, _ := json.Marshal(args)
	resultJSON, _ := json.Marshal(map[string]string{"result": result})

	_, err := db.conn.ExecContext(ctx,
		"INSERT INTO mcp_tool_calls (session_id, tool_name, arguments, result, success) VALUES ($1, $2, $3, $4, true)",
		sessionID, toolName, string(argsJSON), string(resultJSON))
	return err
}

func (db *DB) GetSystemPersona(ctx context.Context) (string, error) {
	var persona string
	err := db.conn.QueryRowContext(ctx, "SELECT value FROM config WHERE key = 'system_persona'").Scan(&persona)
	if err != nil {
		// Fallback if not found
		return "You are MOMO, an advanced AI assistant. You are helpful, direct, and precise.", nil
	}
	return persona, nil
}
