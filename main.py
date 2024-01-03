import os
import threading
import numpy as np
import json
from PIL import Image
import sounddevice as sd
import pygame
import math
import random
import time
import concurrent.futures
import collections

class LightningManager():
    def __init__(self, screen_width, screen_height, num_branches, num_lightnings=50):
        super().__init__()
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.num_branches = num_branches
        self.lightnings = []
        self.num_lightnings = num_lightnings
        self.daemon = True
        self.running = True
        self.current_index = 0

    def precalculate_lightnings(self):
        # Precalcular una cantidad específica de relámpagos
        for _ in range(self.num_lightnings):
            log_message("Generando relámpago" + str(len(self.lightnings) + 1) + " de " + str(self.num_lightnings))
            lightning = Lightning(self.screen_width, self.screen_height, (self.screen_width // 2, 0), self.num_branches)
            self.lightnings.append(lightning)


    def get_random_lightning(self):
        
        num_lightnings = len(self.lightnings)
        if num_lightnings == 0:
            return None
        else:
            return self.lightnings[random.randint(0, num_lightnings - 1)]
    
    def stop(self):
        self.running = False

class Particle:
    def __init__(self, config, screen_size):
        self.color = self.get_color(config["color"])
        self.size = random.randint(config["size_min"], config["size_max"])
        self.velocity_range = config["velocity_range"]
        self.screen_width, self.screen_height = screen_size
        self.x = random.randint(0, self.screen_width)
        self.y = random.randint(0, self.screen_height)
        self.velocity = random.uniform(self.velocity_range[0], self.velocity_range[1])
        self.angle = random.uniform(0, 2 * math.pi)
        self.base_size = random.randint(config["size_min"], config["size_max"])
        self.size_min = config["size_min"]
        self.size_max = config["size_max"]
        self.image = self.get_image(config.get("src")) if "src" in config else None
        
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
        self.size = max(self.size_min, min(new_size, self.size_max))

    def update_visibility(self, is_loud):
        if is_loud:
            self.size = min(self.size_max, self.size + 1) 
        else:
            self.size = max(self.size_min, self.size - 1)

    def get_image(self, src):
        try:
            image = pygame.image.load(src)
            return pygame.transform.scale(image, (self.size, self.size))
        except pygame.error:
            return None
    
    def draw(self, screen):
        if self.image:
            screen.blit(self.image, (int(self.x), int(self.y)))
        else:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
    
class Lightning:
    def __init__(self, screen_width, screen_height, start_pos, num_branches, max_depth=3):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.start_pos = start_pos
        self.branches = []
        self.num_branches = num_branches
        self.color = (255, 255, 255)
        self.max_depth = max_depth  # Profundidad máxima de ramificación

        # Iniciar la generación de ramas
        self.generate_branches(self.start_pos, self.num_branches)

    def generate_branches(self, start_pos, num_branches, depth=0):
        if depth > self.max_depth:
            return

        for _ in range(num_branches):
            length = random.randint(100, 300)

            # Evitar ángulos entre -40° a 40°
            if random.random() < 0.5:
                angle = random.uniform(-math.pi, -math.pi / 4.5)  # Ángulos hacia la izquierda y abajo
            else:
                angle = random.uniform(math.pi / 4.5, math.pi)  # Ángulos hacia la derecha y abajo

            dx = math.cos(angle) * length
            dy = math.sin(angle) * length  # Permitir que dy sea positivo o negativo

            end_pos = (start_pos[0] + dx, start_pos[1] + dy)

            self.branches.append((start_pos, end_pos, self.num_branches - depth))

            sub_branches_count = random.randint(0, 3) if depth < self.max_depth else 0

            for _ in range(sub_branches_count):
                self.generate_branches(end_pos, 1, depth + 1)



    def draw(self, screen):
        i = 0
        for branch in self.branches:
            pygame.draw.line(screen, self.color, branch[0], branch[1], 2)
            i += 1
            
class ImageFolder:
    def __init__(self, path, screen_size):
        log_message(f"Cargando carpeta: {path}")
        self.path = path
        self.screen_width, self.screen_height = screen_size
        self.angle_index = 0
        self.rotation_speed = 3
        self.fps_background = 2
        self.load_images()
        self.load_particle_config(screen_size)
        self.center_scale = 0.3
        self.background_scale = 0.6
        self.preload_images()
        self.pause_rotation = False
        self.volume_level = 0
        self.pause_duration = 200  # Duración de la pausa en milisegundos
        
    def load_images(self):
        log_message("Cargando imágenes...")
        self.original_bg = Image.open(os.path.join(self.path, "background.png"))
        self.center_image = Image.open(os.path.join(self.path, "center.png"))
        self.background_image = self.scale_to_fit(self.original_bg)

    def preload_images(self):
        self.rotated_images = []
        for angle in range(0, 360, self.fps_background):
            rotated_image = self.original_bg.rotate(angle, expand=True)
            scaled_image = self.scale_to_fit(rotated_image)
            self.rotated_images.append(pygame.image.fromstring(scaled_image.tobytes(), scaled_image.size, scaled_image.mode))
            log_message(f"Pre-cargando imagen rotada [{self.path}]: {angle} grados")
    
    def update_volume_level(self, level):
        self.volume_level = level
    
    def update_rotation_pause(self, is_loud):
        if is_loud:
            self.pause_rotation_start_time = pygame.time.get_ticks()
        self.pause_rotation = is_loud

    def update_particle_size(self, volume_level):
        for particle in self.particles:
            particle.update_size(volume_level)

    def update_particle_visibility(self, is_loud):
        for particle in self.particles:
            particle.update_visibility(is_loud)
    
    def get_background_image(self):
        current_time = pygame.time.get_ticks()
        if self.pause_rotation and current_time - self.pause_rotation_start_time < self.pause_duration:
            return self.rotated_images[int(self.angle_index // self.fps_background) % len(self.rotated_images)]
        else:
            self.pause_rotation = False
            image_index = int(self.angle_index // self.fps_background) % len(self.rotated_images)
            self.angle_index = int((self.angle_index + self.rotation_speed) % 360)
            return self.rotated_images[image_index]

    def scale_to_fit(self, image):
        image_ratio = image.width / image.height
        screen_ratio = self.screen_width / self.screen_height
        if image_ratio > screen_ratio:
            new_width = self.screen_width
            new_height = int(new_width / image_ratio)
        else:
            new_height = self.screen_height
            new_width = int(new_height * image_ratio)
        resized_image = image.resize((new_width, new_height), Image.ANTIALIAS)
        # Centrar la imagen en la pantalla
        new_image = Image.new("RGBA", (self.screen_width, self.screen_height))
        new_image.paste(resized_image, (int((self.screen_width - new_width) / 2), int((self.screen_height - new_height) / 2)))
        return new_image


    def load_particle_config(self, screen_size):
        log_message("Cargando configuración de partículas...")
        config_path = os.path.join(self.path, "particles_config.json")
        with open(config_path, 'r') as config_file:
            self.particle_config = json.load(config_file)
            properties = self.particle_config["particle_properties"][0]
            self.particles = [Particle(properties, screen_size) for _ in range(self.particle_config["total_particles"])]
            self.particle_thread = ParticleUpdateThread(self.particles)
            self.particle_thread.start()

    def start_particle_thread(self):
        # Verifica si el hilo existe y está vivo, y detenlo si es necesario
        if hasattr(self, 'particle_thread') and self.particle_thread.is_alive():
            self.particle_thread.stop()
            self.particle_thread.join()

        # Crea y comienza un nuevo hilo
        self.particle_thread = ParticleUpdateThread(self.particles)
        self.particle_thread.start()

    
    def stop_particle_thread(self):
        if hasattr(self, 'particle_thread'):
            self.particle_thread.stop()

    def get_center_image(self, time_elapsed):
        min_scale, max_scale = 0.9, 1.1
        cycle_duration = 2  # Duración del ciclo en segundos

        # Escala base que cambia con el tiempo (efecto de "respiración")
        time_scale_factor = (max_scale - min_scale) / 2 * math.sin(2 * math.pi * time_elapsed / cycle_duration) + (max_scale + min_scale) / 2

        # Escala adicional basada en el volumen (ajusta estos valores según sea necesario)
        volume_scale_factor = 1 + self.volume_level / 10

        # Factor de escala combinado
        combined_scale_factor = time_scale_factor * volume_scale_factor

        scaled_width = int(self.center_image.width * self.center_scale * combined_scale_factor)
        scaled_height = int(self.center_image.height * self.center_scale * combined_scale_factor)
        resized = self.center_image.resize((scaled_width, scaled_height), Image.ANTIALIAS)
        return pygame.image.fromstring(resized.tobytes(), resized.size, resized.mode)


    @staticmethod
    def preload_folders(paths, screen_size):
        log_message("Pre-cargando todas las carpetas...")
        return [ImageFolder(path, screen_size) for path in paths]

class CircularBuffer:
    def __init__(self, size):
        self.size = size
        self.buffer = collections.deque(maxlen=size)

    def append(self, data):
        self.buffer.append(data)

    def get(self):
        return np.concatenate(self.buffer)

class AudioProcessor(threading.Thread):
    def __init__(self, buffer_size, sample_rate=44100, channels=2):
        super().__init__()
        self.buffer = CircularBuffer(buffer_size)
        self.sample_rate = sample_rate
        self.channels = channels
        self.daemon = True
        self.volume = 0

    def run(self):
        stream = sd.InputStream(samplerate=self.sample_rate, channels=self.channels)
        with stream:
            while True:
                data, _ = stream.read(self.sample_rate // 10)  # Lee 0.1 segundos de audio
                self.buffer.append(data)
                self.volume = np.linalg.norm(data) * 10

    def get_volume(self):
        return self.volume


def get_folders_in_directory(directory):
    return [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]

class FolderLoaderManager:
    def __init__(self, folder_paths, screen_size):
        self.folder_paths = folder_paths
        self.screen_size = screen_size
        self.image_folders = []
        self.current_folder_index = 0  # Índice de la carpeta actual

    def load_folders(self):
        max_workers = get_max_workers()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.load_folder, path) for path in self.folder_paths]
            for future in concurrent.futures.as_completed(futures):
                folder = future.result()
                self.image_folders.append(folder)

    def load_folder(self, folder_path):
        folder = ImageFolder(folder_path, self.screen_size)
        return folder

    def get_current_folder(self):
        # Devuelve la carpeta actualmente seleccionada
        if self.image_folders:
            return self.image_folders[self.current_folder_index]
        return None

    def next_folder(self):
        # Cambia a la siguiente carpeta
        if self.image_folders:
            self.current_folder_index = (self.current_folder_index + 1) % len(self.image_folders)

    def set_folder(self, index):
        # Establece la carpeta actual por índice
        if self.image_folders and 0 <= index < len(self.image_folders):
            self.current_folder_index = index

class FolderLoaderThread(threading.Thread):
    def __init__(self, folder_path, screen_size, image_folders):
        super().__init__()
        self.folder_path = folder_path
        self.screen_size = screen_size
        self.image_folders = image_folders
        self.daemon = True

    def run(self):
        folder = ImageFolder(self.folder_path, self.screen_size)
        self.image_folders.append(folder)


class ParticleUpdateThread(threading.Thread):
    def __init__(self, particles):
        super().__init__()
        self.particles = particles
        self.running = True

    def run(self):
        while self.running:
            time.sleep(0.02)
            for particle in self.particles:
                particle.update()

    def stop(self):
        self.running = False


def log_message(message):
    console_tag = "\033[32m[@Console]\033[0m"
    formatted_message = f"{console_tag} {message}"
    print(formatted_message)


def get_max_workers():
    """Get the maximum number of threads that can be used for concurrent tasks."""
    return os.cpu_count() or 1


def main():
    log_message("Inicializando programa...")
    
    screen_width, screen_height = 800, 600
    folder_paths = get_folders_in_directory("images")
    
    if len(folder_paths) == 0:
        log_message("No se encontraron carpetas de imágenes.")
        return

    manager = FolderLoaderManager(folder_paths, (screen_width, screen_height))
    manager.load_folders()
    
    log_message("Pre-cargando los truenos...")
    lightning_manager = LightningManager(screen_width, screen_height, 7)
    lightning_manager.precalculate_lightnings()
    lightning = lightning_manager.get_random_lightning()

    image_folders = manager.image_folders

    log_message("Iniciando Pygame...")
    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.DOUBLEBUF | pygame.HWSURFACE)
    pygame.display.set_caption('Image Viewer')
    font = pygame.font.Font(None, 36)
    log_message("Pygame iniciado.")
    
    current_folder_index = 0
    folder = image_folders[current_folder_index]

    log_message("Iniciando bucle principal...")
    
    audio_processor = AudioProcessor(buffer_size=5)
    audio_processor.start()
    
    
    clock = pygame.time.Clock()
    showing_lightning = False
    lightning_count = 0
    time_since_last_change = 0
    transition_start = False
    transition_phase = 0
    transition_time = 5000  # 5 segundos
    while True:
        
        dt = clock.tick(30)  # 30 FPS, 'dt' es el tiempo transcurrido en milisegundos
        time_since_last_change += dt
        
        if time_since_last_change >= transition_time and not transition_start:
            transition_start = True
            transition_phase = 1
            lightning_count = 0

        if transition_start:
            if transition_phase == 1 and lightning_count < 3:
                lightning = lightning_manager.get_random_lightning()
                lightning.draw(screen)
                pygame.display.flip()
                pygame.time.wait(300)
                screen.fill((255, 255, 255))
                lightning_count += 1
                if lightning_count == 3:
                    transition_phase = 2

            elif transition_phase == 2:
                screen.fill((255, 255, 255))
                pygame.display.flip()
                pygame.time.wait(300)
                manager.next_folder()
                folder = manager.get_current_folder()
                transition_start = False
                time_since_last_change = 0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                folder.stop_particle_thread()
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_MINUS and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    audio_listener.adjust_threshold(-0.1)
                    log_message(f"Umbral de audio: {audio_listener.threshold}")
                elif event.key == pygame.K_EQUALS and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    audio_listener.adjust_threshold(0.1)
                    log_message(f"Umbral de audio: {audio_listener.threshold}")

                
        screen.fill((0, 0, 0))
        volume_level = audio_processor.get_volume()
        sensitivity = 1
        is_loud = volume_level > 0.9 * sensitivity
        folder.update_volume_level(is_loud)
        folder.update_particle_size(is_loud)
        folder.update_particle_visibility(is_loud)
        folder.start_particle_thread()
        folder.update_rotation_pause(is_loud)
        bg_img = folder.get_background_image()
        center_img = folder.get_center_image(pygame.time.get_ticks() / 1000.0)
        screen.blit(bg_img, bg_img.get_rect(center=(screen_width // 2, screen_height // 2)))
        screen.blit(center_img, center_img.get_rect(center=(screen_width // 2, screen_height // 2)))

        # Dibujar partículas
        for particle in folder.particles:
            particle.draw(screen)

        fps_text = font.render(f"FPS: {clock.get_fps():.2f}", True, pygame.Color('white'))
        screen.blit(fps_text, fps_text.get_rect(bottomright=(screen_width - 10, screen_height - 10)))

        pygame.display.flip()
        clock.tick(30)
if __name__ == "__main__":
    main()