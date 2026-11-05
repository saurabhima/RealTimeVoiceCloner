#!/usr/bin/env bash
# Install RealTimeVoiceCloner on Raspberry Pi OS (Bookworm, 64-bit) and enable autostart.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev libportaudio2 portaudio19-dev alsa-utils libasound2-plugins
python3 -m venv "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/pip" install -U pip
"$REPO_DIR/.venv/bin/pip" install -e "$REPO_DIR[onnx]"
sudo usermod -aG audio "$USER"
sed "s#@REPO@#$REPO_DIR#g; s#@USER@#$USER#g" "$REPO_DIR/scripts/rtvc.service" | sudo tee /etc/systemd/system/rtvc.service >/dev/null
sudo systemctl daemon-reload
echo "Installed. Edit configs/default.toml (set consent_acknowledged), then:"
echo "  sudo systemctl enable --now rtvc"
