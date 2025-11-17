# BirdViz – Visualization for BirdNET-Pi
![alt text](https://github.com/wolos/birdviz/blob/main/assets/birdviz_2.jpg?raw=true)

**About**  
BirdViz is a typography forward visualization tool that helps you know which birds to watch and listen for in your yard. It leverages tech to promote real observation outside using your ears and eyes.  

In real time, BirdViz shows the last 10 unique bird species detected in your yard, accessible from any browser on your local network.  

BirdViz is a companion project to the amazing BirdNET-Pi project. You’ll need a working BirdNET-Pi installation before using BirdViz.  

**One‑line install (Raspberry Pi):**
```bash
curl -fsSL https://raw.githubusercontent.com/wolos/birdviz/main/install.sh | bash
```

**What you get**
- A fast, read‑only **JSON API** for BirdNET‑Pi:  
  `/recentunique?limit=N`, `/events` (SSE), `/last`, `/debug`
- A **live dashboard** at **http://birdnet.local:8090/**
- **No changes** to BirdNET‑Pi’s files; reads the database in read‑only mode
- **Auto‑start on boot** via a user‑level systemd service

**Requirements**
- Raspberry Pi with BirdNET‑Pi already running  
- Raspberry Pi OS (Bookworm recommended) with Python 3  
- BirdNET‑Pi database at `~/BirdNET-Pi/scripts/birds.db` (default)

---

## Quick start

1) Run the installer:
```bash
curl -fsSL https://raw.githubusercontent.com/wolos/birdviz/main/install.sh | bash
```

2) Open the dashboard (same network):
```
http://birdnet.local:8090/
```

3) Try the API:
```bash
curl -s "http://birdnet.local:8090/recentunique?limit=10" | jq .
```

> The installer auto‑detects your username and home directory. No manual path edits needed.

---

## Usage tips

- Show more/less species in the API:
  ```
  http://birdnet.local:8090/recentunique?limit=25
  ```
- Logs (live):
  ```bash
  journalctl --user -u birdnet-sidecar.service -f
  ```
- Restart after edits:
  ```bash
  systemctl --user restart birdnet-sidecar.service
  ```

---

## Update / Uninstall

**Update to latest sidecar & deps**
```bash
systemctl --user stop birdnet-sidecar.service
cd ~/birdnet-sidecar
curl -fsSL https://raw.githubusercontent.com/wolos/birdviz/main/sidecar.py -o app/sidecar.py
~/birdnet-sidecar/bin/pip install --upgrade pip flask==3.0.0
systemctl --user start birdnet-sidecar.service
```

**Uninstall**
```bash
systemctl --user disable --now birdnet-sidecar.service
rm -f ~/.config/systemd/user/birdnet-sidecar.service
systemctl --user daemon-reload
rm -rf ~/birdnet-sidecar
```

---

## API Endpoints

| Endpoint                     | Description                         | Example                                |
|-----------------------------|-------------------------------------|----------------------------------------|
| `/last`                     | Most recent detection               | `/last`                                |
| `/recentunique?limit=N`     | Last N unique species (new→old)     | `/recentunique?limit=25`               |
| `/events`                   | Live Server‑Sent Events stream      | `/events`                              |
| `/debug`                    | Diagnostic info                     | `/debug`                               |

---

## Notes

- Read‑only: never writes to BirdNET‑Pi’s DB.
- Low overhead: lightweight polling, no extra heavy deps.
- Default DB path is `~/BirdNET-Pi/scripts/birds.db`. If you’ve moved it, edit `DB_PATH` in `sidecar.py`.

---

## Manual install (advanced)

If you prefer not to use the installer, your original manual flow is preserved here inside a collapsible section.

<details>
<summary>Show manual steps</summary>

1) Create environment
```bash
python3 -m venv ~/birdnet-sidecar
~/birdnet-sidecar/bin/pip install --upgrade pip
~/birdnet-sidecar/bin/pip install flask==3.0.0
```

2) Add app
```bash
mkdir -p ~/birdnet-sidecar/app
# place sidecar.py at ~/birdnet-sidecar/app/sidecar.py
```

3) Systemd user service
```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/birdnet-sidecar.service <<'EOF'
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
systemctl --user enable --now birdnet-sidecar.service
```

4) Verify
```bash
systemctl --user --no-pager --full status birdnet-sidecar.service
curl -s http://127.0.0.1:8090/debug | jq .
curl -s "http://127.0.0.1:8090/recentunique?limit=10" | jq .
```

</details>

---

## License

MIT
