# 🪶 BirdNET-Pi Sidecar
### A lightweight, read-only live API and dashboard for [BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi)

This **Sidecar** adds a fast, real-time JSON API and browser dashboard to your existing BirdNET-Pi installation — without modifying BirdNET-Pi itself.

It reads BirdNET-Pi’s detections database in **read-only** mode and provides:

- `/recentunique` → the latest **unique species** detections (customizable limit)
- `/events` → an instant live stream of detections (Server-Sent Events)
- `/last`, `/debug` → simple JSON endpoints for automation and diagnostics
- a lightweight, self-hosted **dashboard** at **http://birdnet.local:8090/**

---

## ✨ Features

- Instantly updates when new detections occur (no page refresh)
- Works alongside BirdNET-Pi — **no modification** to BirdNET-Pi required
- Starts automatically on boot with `systemd`
- Returns the **last N unique species**, sorted newest → oldest
- Clean JSON APIs for use by other devices or scripts on your network

---

## 🧩 Requirements

- Raspberry Pi (tested on Pi 5)
- Existing [BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi) installation
- Python 3 (included with Raspberry Pi OS)
- BirdNET-Pi database (default path): `~/BirdNET-Pi/scripts/birds.db`

> **Note:** If your system uses a different username (not `pi`), replace `/home/pi/...` with your actual username in all steps below.

---

## ⚙️ 1) Create the sidecar environment

SSH into your BirdNET-Pi machine:

```bash
ssh pi@birdnet.local
```

Create and configure a Python environment:

```bash
python3 -m venv ~/birdnet-sidecar
~/birdnet-sidecar/bin/pip install --upgrade pip
~/birdnet-sidecar/bin/pip install flask==3.0.0
```

---

## 📁 2) Add the sidecar app

Create the app directory:

```bash
mkdir -p ~/birdnet-sidecar/app
```

Place the **unique** sidecar script at `~/birdnet-sidecar/app/sidecar.py`.  
(If you downloaded this repository, the file is already included.)

Upload manually if needed:

```bash
scp sidecar.py pi@birdnet.local:~/birdnet-sidecar/app/sidecar.py
```

---

## 🧾 3) Create a user-level systemd service

This ensures the sidecar starts automatically when the Pi boots.

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

---

## 🧪 4) Verify installation

Check that the service is running:

```bash
systemctl --user --no-pager --full status birdnet-sidecar.service
```

Test the API locally:

```bash
curl -s http://127.0.0.1:8090/debug | jq .
curl -s "http://127.0.0.1:8090/recentunique?limit=10" | jq .
```

If you see valid JSON (bird names, timestamps, etc.), it’s working 🎉

---

## 🖥️ 5) View the live dashboard

Open a browser on your network and visit:

**http://birdnet.local:8090/**

You’ll see the **latest 10 unique species**, updating instantly as new detections happen.  
When a species is re-detected, it jumps to the top of the list (no duplicates).

---

## 🔢 6) Adjust how many detections are shown

Change the number of results by adding a `limit` parameter:

```
http://birdnet.local:8090/recentunique?limit=25
```

To change the dashboard’s default on first load, edit the fetch line inside `sidecar.py`:

```js
fetch('/recentunique?limit=25',{cache:'no-store'})
```

---

## 🔍 7) API Endpoints

| Endpoint | Description | Example |
|---------:|-------------|---------|
| `/last` | Most recent detection | `/last` |
| `/recentunique?limit=N` | Last N **unique species** | `/recentunique?limit=25` |
| `/events` | Live Server-Sent Events stream | `/events` |
| `/debug` | Diagnostic info | `/debug` |

---

## 🪶 8) Maintenance & troubleshooting

Restart the service after edits:

```bash
systemctl --user restart birdnet-sidecar.service
```

View logs in real time:

```bash
journalctl --user -u birdnet-sidecar.service -f
```

Run the app manually (foreground test):

```bash
cd ~/birdnet-sidecar/app
~/birdnet-sidecar/bin/python sidecar.py
```

If it prints `Running on http://0.0.0.0:8090`, you’re good to go.

---

## 🧱 Folder structure

```
/home/pi/
 ├── BirdNET-Pi/
 │   └── scripts/birds.db
 └── birdnet-sidecar/
     ├── app/
     │   └── sidecar.py
     └── bin/
```

---

## 💡 Notes

- The sidecar **never writes** to BirdNET-Pi’s database — it’s read-only.
- Uses lightweight polling (no heavy dependencies like `watchdog`).
- Adjust `DB_PATH` in the script if your `birds.db` lives elsewhere.

---

## 📄 License

MIT License — use freely and modify as you like.
