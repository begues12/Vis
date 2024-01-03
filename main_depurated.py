import os
import threading
import numpy as np
from PIL import Image
import sounddevice as sd
import pygame
import math
import random
import time

class Particle:
    def __init__(self, config, screen_size):
        self.color = self.get_color(config["color"])
        self.base_size = random.randint(config["size_min"], config["size_max"])
        self.size = self.base_size
        self.velocity_range = config["velocity_range"]
        self.screen_width, self.screen_height = screen_size
        self.x = random.randint(0, self.screen_width)
        self.y = random.randint(0, self.screen_height)
        self.velocity = random.uniform(self.velocity_range[0], self.velocity_range[1])
        self.angle = random.uniform(0, 2 * math.pi)

    def get_color(self, color_config):
        if color_config == "random":
            return [random.randint(0, 255) for _ in range(3)]
        else:
            return color_config

    def update(self):
        self.x += math.cos(self.angle) * self.velocity
        self.y += math.sin(self.angle) * self.velocity
        if self.x < 0 or self.x > self.screen_width:
            self.angle = math.pi - self.angle
        if self.y < 0 or self.y > self.screen_height:
            self.angle = -self.angle

    def update_size(self, volume_level):
        new_size = self.base_size + (volume_level - 0.5) * 10
        self.size = max(1, min(new_size, self.base_size * 2))

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.size))

class ImageFolder:
    def __init__(self, path, screen_size):
        self.path = path
        self.screen_width, self.screen_height = screen_size
        self.angle_index = 0
        self.rotation_speed = 3
        self.fps_background = 2
        self.load_images()
        self.load_particle_config(screen_size)

    def load_images(self):
        self.original_bg = Image.open(os.path.join(self.path, "background.png"))
        self.background_image = self.scale_to_fit(self.original_bg)
        self.rotated_images = [self.scale_to_fit(self.original_bg.rotate(angle, expand=True)) for angle in range(0, 360, self.fps_background)]

    def scale_to_fit(self, image):
        image_ratio = image.width / image.height
        screen_ratio = self.screen_width / self.screen_height
        if image_ratio > screen_ratio:
            new_width = self.screen_width
            new_height = int(new_width / image_ratio)
        else:
            new_height = self.screen_height
            new_width = int(new_height * image_ratio)
        resized_image = image.resize((new_width, new_height))
        new_image = Image.new("RGBA", (self.screen_width, self.screen_height))
        new_image.paste(resized_image, (int((self.screen_width - new_width) / 2), int((self.screen_height - new_height) / 2)))
        return pygame.image.fromstring(new_image.tobytes(), new_image.size, new_image.mode)

    def load_particle_config(self, screen_size):
        config_path = os.path.join(self.path, "particles_config.json")
        with open(config_path, 'r') as config_file:
            self.particle_config = json.load(config_file)
            properties = self.particle_config["particle_properties"][0]
            self.particles = [Particle(properties, screen_size) for _ in range(self.particle_config["total_particles"])]

    def update_particle_size(self, volume_level):
        for particle in self.particles:
            particle.update_size(volume_level)

    def get_background_image(self):
        image_index = int(self.angle_index // self.fps_background) % len(self.rotated_images)
        self.angle_index = int((self.angle_index + self.rotation_speed) % 360)
        return self.rotated_images[image_index]

class AudioListener(threading.Thread):
    def __init__(self, update_volume_callback, threshold=0.5):
        super().__init__()
        self.update_volume_callback = update_volume_callback
        self.threshold = threshold
        self.daemon = True

    def run(self):
        while True:
            volume = self.detect_sound()
            self.update_volume_callback(volume)
            time.sleep(0.01)

    def detect_sound(self):
        recording = sd.rec(int(1 * 44100), samplerate=44100, channels=2)
        sd.wait()
        return np.max(np.abs(recording))

def get_folders_in_directory(directory):
    return [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]

def main():
    screen_width, screen_height = 800, 600
    folder_paths = get_folders_in_directory("images")
    if len(folder_paths) == 0:
        return

    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.DOUBLEBUF | pygame.HWSURFACE)
    pygame.display.set_caption('Image Viewer')

    folder = ImageFolder(folder_paths[0], (screen_width, screen_height))
    audio_listener = AudioListener(update_volume_callback=folder.update_particle_size)
    audio_listener.start()

    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type is pygame.QUIT:
                pygame.quit()
                return

        screen.fill((0, 0, 0))
        bg_img = folder.get_background_image()
        screen.blit(bg_img, bg_img.get_rect(center=(screen_width // 2, screen_height // 2)))

        for particle in folder.particles:
            particle.update()
            particle.draw(screen)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
