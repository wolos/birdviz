# Waveshare 11.9" OLED Touchscreen (Portrait)

- Resolution used here: **400 × 1280** (portrait)
- Default behavior:
  - List of latest species (from `/api/latest_distinct`)
  - Tap a species → full-screen image view
  - Tap again → back to list

## Tips
- Make sure the desktop or KMS driver is enabled so `pygame` can create a fullscreen window.
- Adjust font size and line spacing in `configs/displays/waveshare_11in9.yaml`.
- Add species photos to `src/birdviz/assets/birds/` (e.g., `Blue Jay.jpg`).
