package pipeline

import (
	"context"
	"fmt"
	"io"
	"log"

	"github.com/momo/orchestrator/db"
)

type Pipeline struct {
	db     *db.DB
	router *Router
	groq   *GroqClient
	tts    *TTSClient
	mcp    *MCPClient
}

type Response struct {
	Text        string
	AudioStream io.ReadCloser
}

func NewPipeline(database *db.DB) *Pipeline {
	return &Pipeline{
		db:     database,
		router: NewRouter(),
		groq:   NewGroqClient(),
		tts:    NewTTSClient(),
		mcp:    NewMCPClient(),
	}
}

func (p *Pipeline) Run(ctx context.Context, transcript string, sessionID string) (*Response, error) {
	log.Printf("[Pipeline] Session %s got input: '%s'\n", sessionID, transcript)

	// 1. Get embedding (placeholder - assuming local or remote embedding service)
	// embedding, _ := p.getEmbedding(ctx, transcript)
	// memories, _ := p.db.RecallMemories(ctx, embedding, 5)

	// Temporarily mock memories string
	memoriesStr := ""

	// 2. Ask FunctionGemma: does this need a tool?
	decision, err := p.router.Decide(ctx, transcript)
	if err != nil {
		log.Printf("[Pipeline] Router error fallback: %v\n", err)
		decision = &ToolDecision{NeedsTool: false}
	}

	var toolResult string
	if decision.NeedsTool {
		log.Printf("[Pipeline] Calling tool %s with args %+v\n", decision.ToolName, decision.Arguments)
		toolResult, err = p.mcp.Call(ctx, decision.ToolName, decision.Arguments)
		if err != nil {
			toolResult = fmt.Sprintf("Error running tool: %v", err)
		}
		// 3. Log tool call
		p.db.LogToolCall(ctx, sessionID, decision.ToolName, decision.Arguments, toolResult)
	}

	// 4. Load recent history
	history, _ := p.db.GetMessages(ctx, sessionID, 20)
	persona, _ := p.db.GetSystemPersona(ctx)

	// 5. Build messages array for Groq
	messages := p.buildMessages(persona, memoriesStr, history, transcript, toolResult)

	// 6. Call Groq
	responseText, err := p.groq.Chat(ctx, messages)
	if err != nil {
		return nil, fmt.Errorf("LLM error: %w", err)
	}

	// 7. Save exchange
	p.db.SaveMessage(ctx, sessionID, "user", transcript)
	p.db.SaveMessage(ctx, sessionID, "assistant", responseText)

	// 8. Upsert memory embedding (placeholder logic)
	// p.db.UpsertMemory(ctx, sessionID, responseText, embedding)

	// 9. Send to TTS
	audioStream, err := p.tts.Speak(ctx, responseText)
	if err != nil {
		log.Printf("[Pipeline] TTS Error: %v\n", err)
		// Return text anyway, just without audio
	}

	return &Response{Text: responseText, AudioStream: audioStream}, nil
}

func (p *Pipeline) buildMessages(persona, memories string, history []db.Message, currentToken, toolResult string) []map[string]string {
	var out []map[string]string

	systemPrompt := persona
	if memories != "" {
		systemPrompt += "\n\n[Long-term memory context]\n" + memories
	}
	out = append(out, map[string]string{"role": "system", "content": systemPrompt})

	for _, msg := range history {
		out = append(out, map[string]string{"role": msg.Role, "content": msg.Content})
	}

	if toolResult != "" {
		ut := fmt.Sprintf("%s\n\n[Tool Result: %s]", currentToken, toolResult)
		out = append(out, map[string]string{"role": "user", "content": ut})
	} else {
		out = append(out, map[string]string{"role": "user", "content": currentToken})
	}

	return out
}
