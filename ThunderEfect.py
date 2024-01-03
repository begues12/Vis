import pygame
import random

class ThunderEffect:
    def __init__(self, screen, duration=100, fade_duration=500):
        self.screen = screen
        self.duration = duration
        self.fade_duration = fade_duration
        self.start_time = None
        self.active = False
        self.phase = 0
        self.thunder_count = 0

    def start(self):
        self.start_time = pygame.time.get_ticks()
        self.active = True
        self.phase = 1
        self.thunder_count = 0

    def draw_lightning(self):
        start_pos = (random.randint(0, self.screen.get_width()), 0)
        end_pos = (random.randint(0, self.screen.get_width()), self.screen.get_height())
        pygame.draw.line(self.screen, (255, 255, 255), start_pos, end_pos, 2)

    def update(self, new_folder, current_folder, screen):
        if not self.active:
            return current_folder

        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - self.start_time

        if self.phase == 1:
            if elapsed_time <= self.duration:
                self.draw_lightning()
            else:
                screen.fill((255, 255, 255))  # Pantalla en blanco
                self.phase = 2
                self.start_time = current_time
        elif self.phase == 2 and elapsed_time > self.duration:
            self.thunder_count += 1
            if self.thunder_count >= 3:
                self.active = False
                self.phase = 0
                return new_folder
            else:
                self.phase = 1
                self.start_time = current_time

        return current_folder
