#!/bin/bash

echo "Installing Voice Bridge..."

# 创建模型目录
mkdir -p models/whisper
mkdir -p models/piper

echo "Voice Bridge uses Whisper and Piper models."
echo "Whisper model will be downloaded automatically on first use."
echo "Please run 'python scripts/download_models.py' to download Piper TTS models."

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Installation complete."
echo ""
echo "Next steps:"
echo "1. Run 'python scripts/download_models.py' to download TTS models"
echo "2. Run 'python main.py' to start the server"
