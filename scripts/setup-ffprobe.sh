#!/bin/bash
# Setup script to install ffprobe for Key Moments timestamp extraction
# This is required for accurate video duration detection

set -e

echo "🎬 Setting up ffprobe for Stage Buddy..."

# Check if ffprobe is already installed
if command -v ffprobe &> /dev/null; then
    echo "✅ ffprobe is already installed at $(which ffprobe)"
    ffprobe -version | head -1
    exit 0
fi

# Try apt-get first (requires internet)
echo "📦 Attempting to install via apt-get..."
if sudo apt-get update && sudo apt-get install -y ffmpeg 2>/dev/null; then
    echo "✅ ffmpeg installed successfully via apt-get"
    ffprobe -version | head -1
    exit 0
fi

# Fallback: download static binary
echo "⚠️  apt-get failed, downloading static binary..."
TEMP_FILE=$(mktemp)
curl -L https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0/ffprobe-linux-x64 -o "$TEMP_FILE"
chmod +x "$TEMP_FILE"
sudo mv "$TEMP_FILE" /usr/local/bin/ffprobe

echo "✅ ffprobe installed successfully (static binary)"
ffprobe -version | head -1
