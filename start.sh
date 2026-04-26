#!/bin/bash
set -euo pipefail

PORT="${PORT:-8000}"

# Start the Telegram Bot & Schedulers in the background
echo "🚀 Starting CareDost Bot..."
python main.py &

# Start the Flask Dashboard in the foreground
echo "📊 Starting CareDost Dashboard..."
# Using gunicorn for production stability if available, else falling back to python
if command -v gunicorn > /dev/null; then
    gunicorn --bind "0.0.0.0:${PORT}" dashboard.app:app
else
    python -m dashboard.app
fi
