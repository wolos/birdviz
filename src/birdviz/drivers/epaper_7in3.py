# Placeholder e-paper driver. Replace with waveshare_epd library calls if needed.
class EPaper73:
    def __init__(self, rotate=0):
        self.rotate = rotate
    def show(self, img):
        # For now, write to file for debugging
        img.save(f"./epaper_{__import__('time').time():.0f}.png")
