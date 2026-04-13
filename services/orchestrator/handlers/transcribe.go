package handlers

import (
	"encoding/base64"
	"encoding/json"
	"net/http"

	"github.com/momo/orchestrator/pipeline"
)

type TranscribeRequest struct {
	Text      string `json:"text"`
	SessionID string `json:"session_id"`
}

type ChatResponse struct {
	Response  string `json:"response"`
	Audio     []byte `json:"audio,omitempty"`
	ToolUsed  string `json:"tool_used,omitempty"`
	LatencyMs int    `json:"latency_ms,omitempty"`
}

func MakeTranscribeHandler(pipe *pipeline.Pipeline) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req TranscribeRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		// Run the pipeline (Groq -> TTS)
		res, err := pipe.Run(r.Context(), req.Text, req.SessionID)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")

		flusher, ok := w.(http.Flusher)
		if !ok {
			http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
			return
		}

		textMap := map[string]string{"response": res.Text}
		textJSON, _ := json.Marshal(textMap)
		w.Write(textJSON)
		w.Write([]byte("\n"))
		flusher.Flush()

		// Stream audio chunks
		if res.AudioStream != nil {
			defer res.AudioStream.Close()
			buf := make([]byte, 4096)
			for {
				n, err := res.AudioStream.Read(buf)
				if n > 0 {
					chunkMap := map[string]string{
						"audio_chunk": base64.StdEncoding.EncodeToString(buf[:n]),
					}
					chunkJSON, _ := json.Marshal(chunkMap)
					w.Write(chunkJSON)
					w.Write([]byte("\n"))
					flusher.Flush()
				}
				if err != nil {
					break
				}
			}
		}
	}
}
