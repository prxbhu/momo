package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gorilla/mux"
	"github.com/momo/orchestrator/db"
	"github.com/momo/orchestrator/handlers"
	"github.com/momo/orchestrator/pipeline"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "3030"
	}

	// 1. Initialize Database
	postgresURL := os.Getenv("POSTGRES_URL")
	if postgresURL == "" {
		postgresURL = "postgres://postgres:IAmCrazy1@localhost:5432/momo?sslmode=disable"
	}

	database, err := db.NewPostgresDB(postgresURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer database.Close()

	// 2. Initialize Pipeline
	pipe := pipeline.NewPipeline(database)

	// 3. Setup Handlers
	r := mux.NewRouter()

	r.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"ok"}`))
	}).Methods("GET")

	// API Endpoints
	api := r.PathPrefix("/api").Subrouter()
	api.HandleFunc("/transcribe", handlers.MakeTranscribeHandler(pipe)).Methods("POST")
	api.HandleFunc("/chat", handlers.MakeChatHandler(pipe)).Methods("POST")

	// Session management
	api.HandleFunc("/sessions", handlers.GetSessions(database)).Methods("GET")
	api.HandleFunc("/sessions", handlers.CreateSession(database)).Methods("POST")
	api.HandleFunc("/sessions/{id}/messages", handlers.GetSessionMessages(database)).Methods("GET")
	api.HandleFunc("/sessions/{id}", handlers.DeleteSession(database)).Methods("DELETE")

	// WebSocket
	r.HandleFunc("/ws/audio", handlers.MakeWebSocketHandler(pipe))

	// Static Files fallback
	r.PathPrefix("/").Handler(http.FileServer(http.Dir("./static")))

	log.Printf("[Orchestrator] Starting on port %s...\n", port)
	if err := http.ListenAndServe(":"+port, r); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
