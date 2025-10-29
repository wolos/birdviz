# Setup on birdnet.local

1. Install Python venv and Flask:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-venv python3-pip
   sudo useradd -r -s /usr/sbin/nologin birdapi || true
   sudo mkdir -p /opt/birdnet-api/app
   python3 -m venv /opt/birdnet-api/venv
   /opt/birdnet-api/venv/bin/pip install flask flask-cors
   ```

2. Copy `src/birdnet_api/app.py` to `/opt/birdnet-api/app/app.py`.

3. Copy `systemd/birdnet-api.service` to `/etc/systemd/system/` and enable:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now birdnet-api
   ```

4. Test:
   - `http://birdnet.local:8756/api/health`
   - `http://birdnet.local:8756/api/latest_distinct?limit=10`
