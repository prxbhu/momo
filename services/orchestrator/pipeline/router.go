package pipeline

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
)

type Router struct {
	OllamaURL    string
	Model        string
}

func NewRouter() *Router {
	url := os.Getenv("OLLAMA_URL")
	if url == "" {
		url = "http://localhost:11434"
	}
	model := os.Getenv("FUNCTION_MODEL")
	if model == "" {
		model = "functiongemma"
	}
	return &Router{OllamaURL: url, Model: model}
}

type ToolDecision struct {
	NeedsTool bool                   `json:"needs_tool"`
	ToolName  string                 `json:"tool_name"`
	Arguments map[string]interface{} `json:"arguments"`
}

func (r *Router) Decide(ctx context.Context, text string) (*ToolDecision, error) {
	systemPrompt := `You are a function routing agent. Decide whether the user utterance requires a tool call or can be answered directly.
Available tools:
- search_web(query)
- fetch_url(url)
- get_news(topic)
- get_current_time(timezone)
- get_system_info()
- get_weather(location)
- get_calendar_events(days_ahead)
- create_calendar_event(title, date, time, duration_minutes)
- control_device(device_id, action, value)
- list_devices()
- remember_fact(fact, category)
- recall_facts(query)

Respond in JSON only with format: {"needs_tool": bool, "tool_name": string|null, "arguments": object}`

	reqBody := map[string]interface{}{
		"model":  r.Model,
		"prompt": fmt.Sprintf("%s\n\nUser utterance: \"%s\"", systemPrompt, text),
		"stream": false,
		"format": "json",
	}

	jsonData, _ := json.Marshal(reqBody)
	resp, err := http.Post(r.OllamaURL+"/api/generate", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var ollamaRes struct {
		Response string `json:"response"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&ollamaRes); err != nil {
		return nil, err
	}

	var decision ToolDecision
	if err := json.Unmarshal([]byte(ollamaRes.Response), &decision); err != nil {
		// LLM didn't return valid JSON, assume no tool
		return &ToolDecision{NeedsTool: false}, nil
	}
	return &decision, nil
}
