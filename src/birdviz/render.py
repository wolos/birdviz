from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any

def render_list(
    width:int, height:int, title:str, rows:List[Dict[str,Any]],
    font_path:str, font_px:int, line_spacing_px:int, show_sci:bool
):
    img = Image.new("RGB", (width, height), (0,0,0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_px)

    y = 20
    draw.text((24, y), title, font=font, fill=(255,255,255))
    y += font_px + 16

    for r in rows:
        cn = (r.get("common_name") or "Unknown").strip()
        sci = r.get("scientific_name")
        line = f"• {cn}"
        if show_sci and sci:
            line += f" ({sci})"
        draw.text((30, y), line, font=font, fill=(220,220,220))
        y += font_px + line_spacing_px
        if y > height - (font_px + 16):
            break
    return img

def render_species_fullscreen(width:int, height:int, name:str, image_path:str, font_path:str, font_px:int):
    img = Image.new("RGB", (width, height), (0,0,0))
    draw = ImageDraw.Draw(img)
    try:
        bird = Image.open(image_path).convert("RGB")
        bird.thumbnail((width, height-100))
        bx = (width - bird.width)//2
        by = (height - 100 - bird.height)//2 + 40
        img.paste(bird, (bx, by))
    except Exception:
        pass
    font = ImageFont.truetype(font_path, font_px)
    w, h = draw.textsize(name, font=font)
    draw.text(((width - w)//2, height - h - 24), name, font=font, fill=(255,255,255))
    return img
