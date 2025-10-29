# 🪶 BirdViz  
*A local, real-time display for BirdNET-Pi detections*

**BirdViz** is an open-source companion project for [BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi).  
It runs on a second computer (like a Raspberry Pi 5) connected to a display—showing live bird detections from your BirdNET-Pi installation.

The goal: create a beautiful, low-latency, fully offline visualization that turns your backyard BirdNET setup into a living, interactive display.

---

## ✨ Features

- **Instant updates** from your local BirdNET-Pi (`birdnet.local`)  
- **No cloud dependency** — runs entirely on your LAN  
- **Supports multiple displays:** OLED, e-paper, and touchscreen panels  
- **Interactive UI** — tap a species to view a full-screen image of that bird  
- **Simple to extend** — add new visualization modes or displays easily  
- **Open-source & privacy-respecting**  

---

## 🧭 System overview

```text
+---------------------------+        +-----------------------------+
|  birdnet.local            |        |  birdscreen.local           |
|  -----------------------  |        |  -------------------------  |
|  BirdNET-Pi (Raspberry)   |  --->  |  Display Pi (Raspberry)     |
|  birds.db (detections)    |        |  Fetch JSON via /api/       |
|  birdnet-api (Flask)      |        |  Render species list        |
+---------------------------+        +-----------------------------+
```

---

## ⚙️ Installation

### 1️⃣  On `birdnet.local`

This is your existing BirdNET-Pi system.  
We’ll add a lightweight **read-only JSON API** to expose detections.

#### Install dependencies
```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip
sudo useradd -r -s /usr/sbin/nologin birdapi || true
sudo mkdir -p /opt/birdnet-api/app
python3 -m venv /opt/birdnet-api/venv
/opt/birdnet-api/venv/bin/pip install flask flask-cors
```

#### Copy the API files
From this repository:
```
birdviz/src/birdnet_api/app.py
systemd/birdnet-api.service
```

Edit `birdnet-api.service` if your `birds.db` path differs  
(default: `/home/birdnet/BirdNET-Pi/scripts/birds.db`).

Install and enable:
```bash
sudo cp systemd/birdnet-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now birdnet-api
```

#### Test the API
Visit in your browser:
```
http://birdnet.local:8756/api/latest_distinct?limit=10
```
You should see JSON output of recent detections.

---

### 2️⃣  On your display device (Pi) a.k.a. `birdscreen.local`

This is your **display computer**.

#### Clone and install
```bash
cd /opt
sudo git clone https://github.com/<yourusername>/birdviz.git
cd birdviz
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil fonts-dejavu-core
pip3 install -r requirements.txt
```

#### Choose your display
Default: **Waveshare 11.9" OLED Touchscreen (vertical orientation)**

Copy its config:
```bash
cp configs/displays/waveshare_11in9.yaml configs/birdviz.yaml
```

Edit it if needed (title, number of species, etc.).

#### Run BirdViz
```bash
python3 -m birdviz.main
```

You should see a vertical list of the latest species.  
If using the touchscreen, you can tap a species to show its photo.

To run automatically:
```bash
sudo cp systemd/birdviz.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now birdviz
```

---

## 🖥️ Supported displays

| Display | Type | Interaction | Status |
|----------|------|-------------|---------|
| [Waveshare 11.9" OLED Touchscreen](docs/displays/waveshare_11in9.md) | Touch | Tap for photo | ✅ Default |
| [Waveshare 7.3" e-Paper](docs/displays/epaper_7in3.md) | Static | None | 🚧 Planned |
| 5" OLED (SSD1306) | Static | None | 🚧 Planned |

Each display is defined by:
- A **driver module** in `src/birdviz/drivers/`
- A **YAML config** in `configs/displays/`
- A **docs page** in `docs/displays/`

---

## 📱 Default display: Waveshare 11.9" OLED touchscreen

### Orientation
Vertical (portrait)

### Behavior
1. **List view**  
   - Shows the latest distinct species detected  
   - Updates every `poll_seconds` (default: 60 s)

2. **Tap interaction**  
   - Tap any species → shows full-screen photo and name  
   - Tap again → returns to list

### Data source
All data comes directly from your `birdnet.local` via:
```
/api/latest_distinct
```

### Assets
Images are loaded from:
```
src/birdviz/assets/birds/
```
You can store JPEGs named by species, e.g.:
```
Northern Cardinal.jpg
Blue Jay.jpg
```
If not found locally, BirdViz falls back to a neutral placeholder.

---

## 🧩 Configuration overview

| Key | Description | Example |
|-----|--------------|----------|
| `api_base` | Base URL for BirdNET-Pi API | `http://birdnet.local:8756` |
| `endpoint` | API endpoint to use | `/api/latest_distinct` |
| `max_species` | Number of species to display | `10` |
| `poll_seconds` | Refresh interval in seconds | `60` |
| `display.backend` | Which driver to use | `"waveshare_11in9"` |
| `display.width` / `height` | Pixel resolution | `400 × 1280` |
| `ui.title` | Title text at top of list | `"Backyard Birds"` |
| `ui.show_scientific` | Show Latin name | `false` |
| `fonts.regular` | Path to system font | `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` |

---

## 📷 Example screenshots

| List view | Species view |
|------------|---------------|
| *(mock)* | *(mock)* |

---

## 🪪 License

MIT License © 2025

---

## 🗂️ Repository structure

```text
birdviz/
├── src/
│   ├── birdviz/
│   │   ├── main.py           # main loop
│   │   ├── data.py           # BirdNET-Pi API client
│   │   ├── render.py         # layout + drawing
│   │   ├── ui_touch.py       # touchscreen interaction
│   │   ├── drivers/          # display backends
│   │   └── assets/           # local bird images
│   └── birdnet_api/          # local API service
├── configs/
│   ├── birdviz.yaml
│   └── displays/
│       ├── waveshare_11in9.yaml
│       ├── epaper_7in3.yaml
│       └── oled_5in.yaml
├── systemd/
│   ├── birdnet-api.service
│   └── birdviz.service
├── docs/
│   ├── setup_birdnet.md
│   ├── setup_birdviz.md
│   └── displays/
│       ├── waveshare_11in9.md
│       ├── epaper_7in3.md
│       └── oled_5in.md
├── LICENSE
├── README.md
└── requirements.txt
```
