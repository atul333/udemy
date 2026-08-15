#!/bin/bash
# -----------------------------------------------
# Udemy Course Coupons Bot - Linux Startup Script
# -----------------------------------------------
# Usage:
#   chmod +x start_bot.sh
#   ./start_bot.sh

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOT_SCRIPT="Udemy_Coupons_bot.py"
LOG_FILE="$BOT_DIR/bot.log"

# Activate virtual environment if present
if [ -d "$BOT_DIR/venv" ]; then
    source "$BOT_DIR/venv/bin/activate"
elif [ -d "$HOME/venv" ]; then
    source "$HOME/venv/bin/activate"
fi

# Determine python command
PYTHON_CMD="python3"
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
fi

echo "=========================================="
echo "Starting Udemy Course Coupons Bot"
echo "Directory: $BOT_DIR"
echo "Python:    $(which $PYTHON_CMD)"
echo "Log file:  $LOG_FILE"
echo "=========================================="

cd "$BOT_DIR" || { echo "ERROR: Cannot access bot directory"; exit 1; }

# Trap SIGINT and SIGTERM to exit cleanly
trap "echo 'Stopping bot...'; exit 0" SIGINT SIGTERM

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bot running..."
    $PYTHON_CMD "$BOT_SCRIPT" >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bot process exited with code $EXIT_CODE. Restarting in 5s (Press Ctrl+C to stop)..."
    sleep 5
done

