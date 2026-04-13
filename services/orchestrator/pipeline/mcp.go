package pipeline

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
)

type MCPClient struct {
	URL string
}

func NewMCPClient() *MCPClient {
	url := os.Getenv("MCP_URL")
	if url == "" {
		url = "http://localhost:8000"
	}
	return &MCPClient{URL: url}
}

// Simple direct HTTP call fallback since FastMCP standard SSE might be complex
// In reality FastMCP can also expose direct REST endpoints for generic calling.
func (c *MCPClient) Call(ctx context.Context, toolName string, args map[string]interface{}) (string, error) {
	payload := map[string]interface{}{
		"arguments": args,
	}
	jsonData, _ := json.Marshal(payload)

	req, err := http.NewRequestWithContext(ctx, "POST", fmt.Sprintf("%s/tools/%s", c.URL, toolName), bytes.NewBuffer(jsonData))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	bodyBytes, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("MCP failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	return string(bodyBytes), nil
}
