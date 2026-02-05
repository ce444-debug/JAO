import random
import pygame
from config import FIELD_W, FIELD_H, GAME_SCREEN_W, SCREEN_H
from project.model.utils import wrap_delta

def generate_colored_stars(count):
    stars = []
    for _ in range(count):
        x = random.uniform(0, FIELD_W)
        y = random.uniform(0, FIELD_H)
        r = random.randint(150, 255)
        g = random.randint(150, 255)
        b = random.randint(150, 255)
        stars.append((x, y, (r, g, b)))
    return stars

def draw_star_layer_colored(screen, star_list, global_camx, global_camy, parallax, zoom):
    layerCamX = (global_camx * parallax) % FIELD_W
    layerCamY = (global_camy * parallax) % FIELD_H
    for (starX, starY, color) in star_list:
        dx = wrap_delta(layerCamX, starX, FIELD_W)
        dy = wrap_delta(layerCamY, starY, FIELD_H)
        sx = (GAME_SCREEN_W / 2) + dx * zoom
        sy = (SCREEN_H / 2) + dy * zoom
        pygame.draw.circle(screen, color, (int(sx), int(sy)), 2)
