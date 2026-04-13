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

type TTSClient struct {
	URL string
}

func NewTTSClient() *TTSClient {
	url := os.Getenv("TTS_URL")
	if url == "" {
		url = "http://localhost:8002"
	}
	return &TTSClient{URL: url}
}

func (c *TTSClient) Speak(ctx context.Context, text string) (io.ReadCloser, error) {
	payload := map[string]string{
		"text": text,
	}
	jsonData, _ := json.Marshal(payload)

	req, err := http.NewRequestWithContext(ctx, "POST", c.URL+"/speak", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		defer resp.Body.Close()
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("TTS failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	return resp.Body, nil
}
