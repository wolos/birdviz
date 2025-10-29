# Setup on the display device (BirdViz)

1. Install dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-pil fonts-dejavu-core
   pip3 install -r requirements.txt
   ```

2. Select a display config (default Waveshare 11.9" OLED):
   ```bash
   cp configs/displays/waveshare_11in9.yaml configs/birdviz.yaml
   ```

3. Run:
   ```bash
   python3 -m birdviz.main
   ```

4. Optional systemd:
   ```bash
   sudo cp systemd/birdviz.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now birdviz
   ```
