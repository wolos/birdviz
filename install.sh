#!/usr/bin/env bash
set -euo pipefail

# ——— Config ———
REPO_RAW="https://raw.githubusercontent.com/wolos/birdviz/main"
APP_DIR="${HOME}/birdnet-sidecar"
SERVICE_NAME="birdnet-sidecar.service"
PYTHON_BIN="$(command -v python3 || true)"

# ——— Preconditions ———
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "ERROR: python3 not found. Install Python 3 and re-run." >&2
  exit 1
fi
if [[ "${EUID}" -eq 0 ]]; then
  echo "NOTE: You’re running as root. This installer sets up a *user* service."
  echo "It will install into: ${HOME}"
fi

echo "Installing BirdViz Sidecar for user: $(whoami)"
echo "Home: ${HOME}"
echo

# ——— Create venv & install deps ———
mkdir -p "${APP_DIR}/app"
"${PYTHON_BIN}" -m venv "${APP_DIR}"
"${APP_DIR}/bin/pip" install --upgrade pip
"${APP_DIR}/bin/pip" install "flask==3.0.0"

# ——— Fetch sidecar.py ———
curl -fsSL "${REPO_RAW}/sidecar.py" -o "${APP_DIR}/app/sidecar.py"
chmod +x "${APP_DIR}/app/sidecar.py"

# ——— Systemd user service ———
mkdir -p "${HOME}/.config/systemd/user"
cat > "${HOME}/.config/systemd/user/${SERVICE_NAME}" <<'EOF'
[Unit]
Description=BirdNET-Pi Sidecar (read-only API + live dashboard)
After=network-online.target

[Service]
WorkingDirectory=%h/birdnet-sidecar/app
ExecStart=%h/birdnet-sidecar/bin/python %h/birdnet-sidecar/app/sidecar.py
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=1

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "${SERVICE_NAME}" || true

# ——— Enable linger so the user service starts at boot ———
if command -v loginctl >/dev/null 2>&1; then
  if loginctl enable-linger "$(whoami)" 2>/dev/null; then
    echo "Enabled user lingering for $(whoami) (auto-start at boot)."
  else
    echo "TIP: For auto-start at boot, run: sudo loginctl enable-linger $(whoami)"
  fi
fi

echo
echo "✅ BirdViz Sidecar installed."
echo "   Dashboard:  http://birdnet.local:8090/"
echo "   Logs:       journalctl --user -u ${SERVICE_NAME} -f"
echo "   API test:   curl -s \"http://127.0.0.1:8090/recentunique?limit=10\" | jq .
