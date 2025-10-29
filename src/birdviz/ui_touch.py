import pygame
from typing import Optional

class TouchUI:
    def __init__(self, width:int, height:int, title:str):
        pygame.display.init()
        pygame.font.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True

    def blit_image(self, pil_image):
        mode = pil_image.mode
        size = pil_image.size
        data = pil_image.tobytes()
        if mode == "RGBA":
            surface = pygame.image.fromstring(data, size, "RGBA")
        else:
            surface = pygame.image.fromstring(data, size, "RGB")
        self.screen.blit(surface, (0,0))
        pygame.display.flip()

    def poll_tap(self) -> Optional[tuple]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return None
            if event.type == pygame.MOUSEBUTTONUP:
                x, y = event.pos
                return (x, y)
        return None

    def tick(self, fps=60):
        self.clock.tick(fps)
