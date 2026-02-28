#!/bin/bash
# Start both FastAPI and Streamlit
# Railway provides $PORT for the public-facing service

set -e

API_PORT=8000
UI_PORT=${PORT:-8501}

# Start FastAPI backend in background
uvicorn app.main:app --host 0.0.0.0 --port $API_PORT &
API_PID=$!

# Wait for API to be ready (up to 30 seconds)
echo "Waiting for FastAPI to start on port $API_PORT..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:$API_PORT/health > /dev/null 2>&1; then
        echo "FastAPI is ready (took ${i}s)"
        break
    fi
    if ! kill -0 $API_PID 2>/dev/null; then
        echo "ERROR: FastAPI process died during startup"
        exit 1
    fi
    sleep 1
done

# Final check — if API still isn't up after 30s, exit
if ! curl -sf http://localhost:$API_PORT/health > /dev/null 2>&1; then
    echo "ERROR: FastAPI failed to start within 30 seconds"
    exit 1
fi

# Start Streamlit frontend on Railway's PORT
exec streamlit run ui/streamlit_app.py \
  --server.port $UI_PORT \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
