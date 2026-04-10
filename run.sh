#!/bin/bash

# ==============================================================================
# MOMO Local Development Runner
# Starts all services locally, using a native local Postgres server.
# ==============================================================================

# Ensure the script stops on errors
set -e

echo "🚀 Starting MOMO local environment..."

# 1. Check Local Postgres & Run Migrations
echo "📦 Checking local Postgres Database..."
export PGPASSWORD="IAmCrazy1"

# Check if we can connect to the local db
if psql -h localhost -p 5432 -U postgres -d momo -c '\q' 2>/dev/null; then
    echo "✅ Local Postgres is accessible."
    echo "🗄️ Running migrations..."
    # Run the init script. Errors are ignored if tables already exist due to IF NOT EXISTS in your SQL.
    psql -h localhost -p 5432 -U postgres -d momo -f migrations/001_init.sql > /dev/null 2>&1 || true
else
    echo "❌ Error: Could not connect to local Postgres at localhost:5432."
    echo "Please ensure your Postgres server is running, and the 'momo' user and database exist."
    exit 1
fi

# ==============================================================================
# Service Launchers
# ==============================================================================

# Function to clean up background processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down MOMO services..."
    kill $MCP_PID $TTS_PID $ASR_PID $ORCH_PID 2>/dev/null
    echo "👋 Goodbye!"
    exit 0
}

# Trap Ctrl+C (SIGINT) and exit (SIGTERM) to run the cleanup function
trap cleanup SIGINT SIGTERM EXIT

# Load environment variables if .env exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# 2. Start MCP Server (Port 8000)
echo "🛠️  Starting MCP Server (Port 8000)..."
cd services/mcp
export PORT=8000
python3 server.py &
MCP_PID=$!
cd ../..

# 3. Start ASR Service (Port 8001)
echo "🎙️  Starting ASR Service (Port 8001)..."
cd services/asr
export PORT=8001
export ORCHESTRATOR_URL="http://localhost:3030"
uvicorn main:app --host 0.0.0.0 --port $PORT &
ASR_PID=$!
cd ../..

# 4. Start TTS Service (Port 8002)
echo "🔊 Starting TTS Service (Port 8002)..."
cd services/tts
export PORT=8002
export VOICE_SAMPLE_DIR="../../voice_samples"
uvicorn main:app --host 0.0.0.0 --port $PORT &
TTS_PID=$!
cd ../..

# Give Python services a moment to bind their ports
sleep 2

# 5. Start Go Orchestrator (Port 3030)
echo "🧠 Starting Orchestrator (Port 3030)..."
cd services/orchestrator
export PORT=3030
export ASR_URL="http://localhost:8001"
export TTS_URL="http://localhost:8002"
export MCP_URL="http://localhost:8000"
export OLLAMA_URL="http://localhost:11434"
export POSTGRES_URL="postgres://postgres:IAmCrazy1@localhost:5432/momo?sslmode=disable"
go run main.go &
ORCH_PID=$!
cd ../..

echo "========================================================"
echo "✨ MOMO IS LIVE! ✨"
echo "========================================================"
echo "Services running at:"
echo " - Orchestrator : http://localhost:3030"
echo " - ASR Service  : http://localhost:8001"
echo " - TTS Service  : http://localhost:8002"
echo " - MCP Server   : http://localhost:8000"
echo ""
echo "Microphone is active. Say 'hey momo' to trigger the pipeline."
echo "Press Ctrl+C to stop all services."
echo "========================================================"

# Wait indefinitely so the script doesn't exit
wait