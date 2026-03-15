#!/bin/bash

echo "Installing Voice Bridge Pro..."

mkdir -p models
cd models

echo "Downloading ASR model..."
wget -q https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2
tar -xjf sherpa-onnx-sense-voice-*.tar.bz2

echo "Downloading TTS model..."
wget -q https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2
tar -xjf kokoro-multi-lang-v1_0.tar.bz2

echo "Installing dependencies..."
pip install -r ../requirements.txt

echo "Installation complete."
