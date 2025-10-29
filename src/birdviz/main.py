import time, yaml, os, sys
from .data import LocalAPI
from .render import render_list, render_species_fullscreen
from .ui_touch import TouchUI

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "birds")

def load_cfg():
    with open(os.environ.get("BIRDVIZ_CONFIG", "configs/birdviz.yaml")) as f:
        return yaml.safe_load(f)

def pick_species_from_tap(rows, x, y, cfg):
    top = 20 + cfg["fonts"]["size_px"] + 16
    line_h = cfg["fonts"]["size_px"] + cfg["ui"]["line_spacing_px"]
    if y < top: return None
    idx = (y - top) // line_h
    idx = int(idx)
    if 0 <= idx < len(rows):
        return rows[idx]
    return None

def find_image_for_species(name:str):
    base = name.replace("/", "-")
    for ext in (".jpg", ".jpeg", ".png"):
        p = os.path.join(ASSETS_DIR, base + ext)
        if os.path.exists(p):
            return p
    return os.path.join(os.path.dirname(__file__), "assets", "ui", "placeholder.png")

def main():
    cfg = load_cfg()
    api = LocalAPI(cfg["api_base"])

    width = cfg["display"]["width"]
    height = cfg["display"]["height"]

    ui = TouchUI(width, height, cfg["ui"]["title"])

    mode = "list"
    selected = None
    last_fetch = 0
    rows = []

    while ui.running:
        now = time.time()
        if mode == "list" and (now - last_fetch > cfg["poll_seconds"] or not rows):
            try:
                rows = api.latest_distinct(cfg["max_species"])
                last_fetch = now
            except Exception as e:
                print("fetch error:", e, file=sys.stderr)

        if mode == "list":
            img = render_list(
                width, height, cfg["ui"]["title"], rows,
                cfg["fonts"]["regular"], cfg["fonts"]["size_px"],
                cfg["ui"]["line_spacing_px"], cfg["ui"]["show_scientific"]
            )
            ui.blit_image(img)
            tap = ui.poll_tap()
            if tap:
                pick = pick_species_from_tap(rows, tap[0], tap[1], cfg)
                if pick:
                    selected = pick
                    mode = "detail"
        else:
            name = (selected.get("common_name") or "Unknown").strip()
            img_path = find_image_for_species(name)
            img = render_species_fullscreen(
                width, height, name, img_path,
                cfg["fonts"]["regular"], max(28, cfg["fonts"]["size_px"])
            )
            ui.blit_image(img)
            tap = ui.poll_tap()
            if tap:
                mode = "list"

        ui.tick(30)

if __name__ == "__main__":
    main()
