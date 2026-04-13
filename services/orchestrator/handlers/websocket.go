package handlers

import (
	"log"
	"net/http"

	"github.com/gorilla/websocket"
	"github.com/momo/orchestrator/pipeline"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all for prototype
	},
}

func MakeWebSocketHandler(pipe *pipeline.Pipeline) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Println("[WS] Upgrade error:", err)
			return
		}
		defer conn.Close()

		// Read dummy start message to establish session
		var startMsg struct {
			SessionID string `json:"session_id"`
		}
		if err := conn.ReadJSON(&startMsg); err != nil {
			log.Println("[WS] Error reading start message:", err)
			return
		}

		sessionID := startMsg.SessionID
		log.Printf("[WS] Connected session %s\n", sessionID)

		// Loop: read raw text (simulating ASR feed) and stream back audio
		for {
			_, msg, err := conn.ReadMessage()
			if err != nil {
				log.Println("[WS] Read loop exited:", err)
				break
			}

			text := string(msg)
			if text == "" {
				continue
			}

			// Run pipeline
			res, err := pipe.Run(r.Context(), text, sessionID)
			if err != nil {
				log.Println("[WS] Pipeline error:", err)
				conn.WriteJSON(map[string]string{"error": err.Error()})
				continue
			}

			// First send the text response metadata
			if err := conn.WriteJSON(map[string]interface{}{
				"type":     "response_text",
				"response": res.Text,
			}); err != nil {
				break
			}

			// Then stream the live audio chunks as sequential binary frames
			if res.AudioStream != nil {
				err := func() error {
					defer res.AudioStream.Close()
					buf := make([]byte, 4096) // 4KB chunks
					for {
						n, readErr := res.AudioStream.Read(buf)
						if n > 0 {
							if writeErr := conn.WriteMessage(websocket.BinaryMessage, buf[:n]); writeErr != nil {
								return writeErr
							}
						}
						if readErr != nil {
							break // EOF or error reading from TTS
						}
					}
					return nil
				}()

				// If writing to the websocket failed, break the main loop
				if err != nil {
					log.Println("[WS] Error writing audio stream:", err)
					break
				}
			}
		}
	}
}
