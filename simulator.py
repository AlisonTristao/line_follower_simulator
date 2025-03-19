import pygame
import random
import time
from graphics_elements import *
from track_generator import *
from car_dynamics import *

class SimulatorController:
    def __init__(self, fps, length, width, scale, render, sensor_distante):
        # controler parameters
        self.FPS = fps
        self.LENGTH = length
        self.WIDTH = width
        self.SCALE = scale
        self.RENDER = render
        self.sensor_distante = sensor_distante

        # simulator objects
        self.simulator = Simulator('FULL', self.FPS)
        self.track = None
        self.minimap = None
        self.display = None
        self.car = None
        self.fps_display = None
        self.coordinates_display = None
        self.compass = None
        self.line_sensor = None

        # model parameters
        self.car = None #car_dynamics(z=1/self.FPS)

        # setup the simulator
        self._setup_simulator()

    def setup_car_dynamics(self,  wheels_radius=0.04, wheels_distance=0.1, wheels_RPM=3000, ke=1, kq=1, accommodation_time=1.0):
        z = 1/self.FPS
        self.car = car_dynamics(z, wheels_radius, wheels_distance, wheels_RPM, ke, kq, accommodation_time)

    def _setup_simulator(self):
        # generate trajectory
        x_track, y_track = generate_track(CIRCLE, noise_level=0.5, checkpoints=36, resolution=1000, track_rad=30)

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
        self.car_draw = Car(self.simulator.get_center(), center=(1.36, 1.4))
        self.simulator.add(self.car_draw)

        # create line sensor
        self.line_sensor = LineSensor((self.car_draw.get_center()[0], self.car_draw.get_center()[1] - self.sensor_distante))
        self.simulator.add(self.line_sensor)

        # set track properties
        self.track.set_coordinates(((x_track[0] + self.LENGTH//2) * self.SCALE, (y_track[0] + self.WIDTH//2) * self.SCALE))
        self.track.set_center(self.car_draw.get_center())
        self.track.set_pivot(self.car_draw.get_center())

        # create display
        self.display = Display(self.simulator.get_center(), self.simulator.get_window_size())
        self.simulator.add(self.display)
        self._setup_display_graphs()

        # create statistics displays
        FPS_position = (1.99 * self.simulator.get_center()[0], 0.01 * self.simulator.get_center()[1])
        self.fps_display = Statistics(FPS_position)
        self.simulator.add(self.fps_display)

        # create coordinates display
        coordinates_position = (1.85 * self.simulator.get_center()[0], 1.95 * self.simulator.get_center()[1])
        self.coordinates_display = Statistics(coordinates_position)
        self.coordinates_display.set_offset(2)
        self.simulator.add(self.coordinates_display)

        # create compass
        self.compass = Compass((1.85 * self.simulator.get_center()[0], 1.75 * self.simulator.get_center()[1]))
        self.simulator.add(self.compass)

    def _setup_display_graphs(self):
        self.display.add_graph("wheels")
        self.display.add_line_to_graph("wheels", "left", color=(0, 200, 0))
        self.display.add_line_to_graph("wheels", "right", color=(200, 0, 0))

        self.display.add_graph("speed")
        self.display.add_line_to_graph("speed", "vm", color=(0, 0, 200))

        self.display.add_graph("omega")
        self.display.add_line_to_graph("omega", "ω", color=(200, 200, 0))

    def _update_graps(self):
        """
        update the graphs with the given values.
        """
        self.display.update_graph_data("wheels", "left", self.car.getWheels()[0])
        self.display.update_graph_data("wheels", "right", self.car.getWheels()[1])
        self.display.update_graph_data("speed", "vm", self.car.speed_norm())
        self.display.update_graph_data("omega", "ω", self.car.omega_norm())

    def update_FPS(self, fps):
        """
        update the FPS display with the given value.
        """
        self.fps_display.set_text(f"fps: {fps}")

    def step(self, v1, v2):
        """
        perform one simulation step with given movement and rotation inputs.
        """

        # calculates the car values normalized
        simulator._update_graps()

        # step the car dynamics
        self.car.step(v1, v2)

        # get the car values
        dx, dy, angle = self.car.get_space()

        dx *= -self.SCALE
        dy *= -self.SCALE
        self.track.step(dx, dy, angle)

        # update compass and coordinates
        self.compass.set_angle(-self.track.get_angle() - math.pi / 2)
        self.coordinates_display.set_text(
            f"x: {round(self.track.get_center()[0] / 200 + 1, 2):.2f} y: {round(self.track.get_center()[1] / 200 + 1, 2):.2f}"
        )

        # update minimap position
        self.minimap.set_player_position(
            (2 * self.track.get_center()[0] / (self.SCALE * self.LENGTH) - 1,
             -2 * self.track.get_center()[1] / (self.SCALE * self.WIDTH) + 1)
        )

        # render the simulator
        self.simulator.step()

        # return the sensor value
        linha = self.simulator.screen.subsurface((self.line_sensor.get_x() - self.line_sensor.get_size()/2, self.line_sensor.get_y() -1, self.line_sensor.get_size(), 1))
        linha_array = pygame.surfarray.pixels3d(linha)
        linha_pb = linha_array.mean(axis=2)  # Calcula a média no eixo das cores (R, G, B)
        linha_pb = np.array(linha_pb[:, 0], dtype=np.uint8)  # Remove dimensão extra do eixo Y
        return linha_pb

    def stop(self):
        """
        stop the simulator.
        """
        self.simulator.stop_running()


simulator = None #SimulatorController()

def start_simulation(fps=120, length=150, width=150, scale=600, render=3, sensor_distante=50):
    global simulator
    simulator = SimulatorController(fps, length, width, scale, render, sensor_distante)
    return simulator

def set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke, accommodation_time):
    # check if the simulator is initialized
    if simulator is None:
        print("Simulator not initialized")
        return

    simulator.setup_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke, 0, accommodation_time)

def step_simulation(v1, v2):
    # save the current time
    timer = time.time()

    # check if the simulator is initialized
    if simulator is None or simulator.car is None:
        print("Simulator not initialized")
        return

    # check for events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print("Simulation stopped using X button")
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                print("Simulation stopped using ESC")
                return None
            
    # render the simulator
    line = simulator.step(v1, v2)

    # fix the fps
    while (time.time() - timer) < 1/simulator.FPS:
        pass

    # update the fps count
    simulator.update_FPS("{:.1f}".format(1/(time.time() - timer)))

    return line
