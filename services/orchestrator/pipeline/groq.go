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

type GroqClient struct {
	APIKey string
	Model  string
	URL    string
}

func NewGroqClient() *GroqClient {
	model := os.Getenv("GROQ_MODEL")
	if model == "" {
		model = "llama-3.3-70b-versatile"
	}
	return &GroqClient{
		APIKey: os.Getenv("GROQ_API_KEY"),
		Model:  model,
		URL:    "https://api.groq.com/openai/v1/chat/completions",
	}
}

func (c *GroqClient) Chat(ctx context.Context, messages []map[string]string) (string, error) {
	if c.APIKey == "" {
		return "I am unable to process your request right now. Groq API key is missing.", nil
	}

	payload := map[string]interface{}{
		"model":    c.Model,
		"messages": messages,
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}

	req, err := http.NewRequestWithContext(ctx, "POST", c.URL, bytes.NewBuffer(jsonData))
	if err != nil {
		return "", err
	}

	req.Header.Set("Authorization", "Bearer "+c.APIKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("Groq request failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	var res struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return "", err
	}

	if len(res.Choices) == 0 {
		return "", fmt.Errorf("no response returned from Groq")
	}

	return res.Choices[0].Message.Content, nil
}
