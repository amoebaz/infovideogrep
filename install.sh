#!/usr/bin/env bash
# InfoVideoGrep — installation script
# Installs all dependencies needed to run the project.
# Run once: ./install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== InfoVideoGrep Installer ==="
echo ""

# --- Python ---
echo "[1/6] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.10+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Found Python $PYTHON_VERSION"

# --- Virtual environment ---
echo "[2/6] Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Created venv/"
else
    echo "  venv/ already exists"
fi
source venv/bin/activate

# --- Python dependencies ---
echo "[3/6] Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  Installed: faster-whisper, yt-dlp, openai, pyyaml, httpx, pytest"

# --- CUDA libraries for faster-whisper (only if GPU is present) ---
echo "[4/6] Checking GPU support..."
if ! command -v nvidia-smi &>/dev/null; then
    echo "  No NVIDIA GPU detected — running in CPU mode"
    echo "  Make sure config.yaml has: whisper.device: cpu, whisper.compute_type: int8"
elif python -c "import ctypes; ctypes.CDLL('libcublas.so.12')" 2>/dev/null; then
    echo "  CUDA libraries already available"
else
    echo "  Installing nvidia-cublas-cu12 and nvidia-cudnn-cu12..."
    pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 -q
    echo "  Installed. If this fails at runtime, install CUDA Toolkit:"
    echo "    sudo apt install nvidia-cuda-toolkit"
fi

# --- yt-dlp system binary ---
echo "[5/6] Checking yt-dlp..."
if command -v yt-dlp &>/dev/null; then
    echo "  yt-dlp found: $(yt-dlp --version)"
else
    echo "  yt-dlp will be used from the venv (installed via pip)"
fi

# --- Ollama (optional, for fallback LLM) ---
echo "[6/6] Checking Ollama (optional, for fallback LLM)..."
if command -v ollama &>/dev/null; then
    echo "  Ollama found: $(ollama --version 2>&1 | head -1)"
else
    echo "  Ollama not found. Install it for local LLM fallback:"
    echo "    curl -fsSL https://ollama.com/install.sh | sh"
    echo "  (This is optional — the script works without it)"
fi

# --- Config check ---
echo ""
echo "=== Setup checklist ==="
if [ -f "config.yaml" ]; then
    if grep -q "YOUR_BOT_TOKEN" config.yaml; then
        echo "  [ ] Edit config.yaml: set your Telegram bot token"
    else
        echo "  [x] config.yaml configured"
    fi
else
    echo "  [ ] Create config.yaml (copy from config.yaml.example)"
fi

echo ""
echo "=== Done! ==="
echo ""
echo "Usage:"
echo "  ./run.sh              Process pending messages"
echo "  ./run.sh --watch      Poll continuously (every 60s)"
echo "  ./run.sh --watch 30   Poll continuously (every 30s)"
echo "  ./run.sh --help       Show all options"
