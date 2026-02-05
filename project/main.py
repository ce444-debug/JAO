import pygame
import sys
from menu import SuperMeleeMenu
from game import Game
from project.config import SCREEN_W, SCREEN_H
from title_screen import TitleScreen  # 2025-12-10: добавлен импорт титульного экрана VOID ENGINE


def run_title_screen(screen, clock):
    """
    2025-12-10: новая функция.
    Причина: показать кинематографичный титульный экран VOID ENGINE до входа в меню.
    """
    title_screen = TitleScreen(
        (SCREEN_W, SCREEN_H),
        "assets/ui/void_engine_title.png"  # путь к постеру титульного экрана
    )

    while not title_screen.done:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            title_screen.handle_event(event)

        title_screen.update(dt)
        title_screen.draw(screen)
        pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    run_title_screen(screen, clock)  # 2025-12-10: показ титульного экрана перед главным меню

    menu = SuperMeleeMenu(screen, clock)
    state = "MENU"

    while True:
        if state == "MENU":
            config = menu.display()
            game = Game(config, menu)
            state = game.run()
        else:
            menu.save_last_config()
            pygame.quit()
            sys.exit()


if __name__ == "__main__":
    main()
