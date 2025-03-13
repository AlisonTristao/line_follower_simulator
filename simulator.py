import pygame
import random
import time
from graphics_elements import *
from track_generator import *

class SimulatorController:
    def __init__(self, fps=120, length=100, width=100, scale=300, render=4):
        self.FPS = fps
        self.LENGTH = length
        self.WIDTH = width
        self.SCALE = scale
        self.RENDER = render
        
        self.simulator = Simulator('FULL', self.FPS)
        self.track = None
        self.minimap = None
        self.display = None
        self.car = None
        self.fps_display = None
        self.coordinates_display = None
        self.compass = None
        
        self._setup_simulator()

    def _setup_simulator(self):
        # generate trajectory
        x_track, y_track = generate_track(LEMNISCATE, noise_level=0.2, checkpoints=50, resolution=500, track_rad=40)

        # create the track
        self.track = Track((self.LENGTH, self.WIDTH), self.SCALE, self.RENDER)
        processed_points = set()
        for i in range(-self.LENGTH // 2, self.LENGTH // 2):
            for j in range(-self.WIDTH // 2, self.WIDTH // 2):
                index = points_in_square(i, j, (self.LENGTH + self.WIDTH) / self.SCALE, x_track, y_track)
                if len(index) > 0:
                    cluster = Cluster()
                    for k in index:
                        if (x_track[k], y_track[k]) not in processed_points:
                            x = (x_track[k] - i) * self.SCALE
                            y = (y_track[k] - j) * self.SCALE
                            cluster.add_point((x, y))
                            processed_points.add((x_track[k], y_track[k]))
                    self.track.set_obj(i + self.LENGTH // 2, j + self.WIDTH // 2, cluster)
        self.simulator.add(self.track)

        # create minimap
        minimap_position = (0.9 * self.simulator.get_center()[0], 1.75 * self.simulator.get_center()[1])
        self.minimap = MiniMap(minimap_position, (200, 150))
        for k in range(0, len(x_track), self.SCALE // 10):
            self.minimap.add_point((2 * x_track[k] / self.LENGTH, 2 * y_track[k] / self.WIDTH))
        self.simulator.add(self.minimap)

        # create car
        self.car = Car(self.simulator.get_center(), center=(1.36, 1.4))
        self.simulator.add(self.car)

        # set track properties
        self.track.set_coordinates(((x_track[0] + self.LENGTH//2) * self.SCALE, (y_track[0] + self.WIDTH//2) * self.SCALE))
        self.track.set_center(self.car.get_center())
        self.track.set_pivot(self.car.get_center())

        # create display
        self.display = Display(self.simulator.get_center(), self.simulator.get_window_size())
        self.simulator.add(self.display)
        self._setup_display_graphs()

        # create statistics displays
        FPS_position = (1.99 * self.simulator.get_center()[0], 0.01 * self.simulator.get_center()[1])
        self.fps_display = Statistics(FPS_position)
        self.simulator.add(self.fps_display)

        coordinates_position = (1.85 * self.simulator.get_center()[0], 1.95 * self.simulator.get_center()[1])
        self.coordinates_display = Statistics(coordinates_position)
        self.coordinates_display.set_offset(2)
        self.simulator.add(self.coordinates_display)

        # create compass
        self.compass = Compass((1.85 * self.simulator.get_center()[0], 1.8 * self.simulator.get_center()[1]))
        self.simulator.add(self.compass)

    def _setup_display_graphs(self):
        self.display.add_graph("wheels")
        self.display.add_line_to_graph("wheels", "left", color=(0, 200, 0))
        self.display.add_line_to_graph("wheels", "right", color=(200, 0, 0))

        self.display.add_graph("speed")
        self.display.add_line_to_graph("speed", "vm", color=(0, 0, 200))

        self.display.add_graph("omega")
        self.display.add_line_to_graph("omega", "ω", color=(200, 200, 0))

    def update_graps(self, wheels, speed, omega):
        """
        update the graphs with the given values.
        """
        self.display.update_graph_data("wheels", "left", wheels[0])
        self.display.update_graph_data("wheels", "right", wheels[1])
        self.display.update_graph_data("speed", "vm", speed)
        self.display.update_graph_data("omega", "ω", omega)

    def update_FPS(self, fps):
        """
        update the FPS display with the given value.
        """
        self.fps_display.set_text(f"fps: {fps}")

    def step(self, dx, dy, angle):
        """
        perform one simulation step with given movement and rotation inputs.
        """
        self.track.step(dx, dy, angle)

        # update compass and coordinates
        self.compass.set_angle(-self.track.get_angle() - math.pi / 2)
        self.coordinates_display.set_text(
            f"x: {round(self.track.get_center()[0], 1)} y: {round(self.track.get_center()[1], 1)}"
        )

        # update minimap position
        self.minimap.set_player_position(
            (2 * self.track.get_center()[0] / (self.SCALE * self.LENGTH) - 1,
             -2 * self.track.get_center()[1] / (self.SCALE * self.WIDTH) + 1)
        )

        # render the simulator
        self.simulator.step()

    def stop(self):
        """
        stop the simulator.
        """
        self.simulator.stop_running()

if __name__ == "__main__":
    simulator = SimulatorController()

    running = True
    timer = time.time()
    fps = 0
    while running:
        timer = time.time()
        dx, dy, angle = 0, 0, 0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            dx = -5
        if keys[pygame.K_RIGHT]:
            dx = 5
        if keys[pygame.K_UP]:
            dy = -5
        if keys[pygame.K_DOWN]:
            dy = 5
        if keys[pygame.K_a]:
            angle = 0.01
        if keys[pygame.K_d]:
            angle = -0.01

        # update graphs with random data
        random_left = random.randint(-50, 50)
        random_right = random.randint(-50, 50)
        random_vm = random.randint(-50, 50)
        random_ω = random.randint(-50, 50)
        simulator.update_graps((random_left, random_right), random_vm, random_ω)

        # render the simulator
        simulator.step(dx, dy, angle)

        # fix the fps
        while (time.time() - timer) < 1/simulator.FPS:
            pass

        # update the fps count
        simulator.update_FPS("{:.1f}".format(1/(time.time() - timer)))
