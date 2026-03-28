import pygame
import random
import time
import math
from dataclasses import dataclass

from graphics.graphics_elements import *
from graphics.track_generator import *
from car_modeling.car_dynamics import *
import numpy as np

@dataclass
class SimulationConfig:
    """Configuration values used to start a simulation."""

    screen_size: int
    fps: int
    length: int
    width: int
    scale: int
    render: int
    track_type: int = 0
    track_length: float = 0.02
    sensor_spacing: float = 0.001

class GameSimulation:
    """High level controller responsible for running the simulation."""

    def __init__(self, config: SimulationConfig):
        self.config = config

        # copy frequently used values for convenience
        self.screen_size = config.screen_size
        self.FPS = config.fps
        self.LENGTH = config.length
        self.WIDTH = config.width
        self.SCALE = config.scale
        self.RENDER = config.render
        self.track_type = config.track_type
        self.track_length = config.track_length
        self.array_sensor_dist = config.sensor_spacing

        self.time_simulation = 0
        self.timer = time.time()
        self.perturbation = 0.0

        self._init_simulation_objects()
        self._setup_simulator()

    def _init_simulation_objects(self):
        self.simulator = Simulator(self.screen_size, self.FPS)
        self.car = None
        self.track = None
        self.display = None
        self.minimap = None
        self.fps_display = None
        self.coordinates_display = None
        self.compass = None
        self.line_sensor = None
        self.future_points = None
        self.track_percentage = None
        self.points = None
        self.win = None

        self.future_points_count = 10
        #self.future_space = 30
        #self.future_omega = [0] * 10
        #self.future_v = [0] * 10
        #self.free_response_omega = [0] * 10
        #self.free_response_v = [0] * 10
        #self.future_control_left = [0] * 10
        #self.future_control_right = [0] * 10
        self.perturbation_left = [0] * 10
        self.perturbation_right = [0] * 10
        #self.error_omega = [0] * 10
        #self.error_v = [0] * 10

    def setup_car_dynamics(
        self,
        wheels_radius=0.04,
        wheels_distance=0.1,
        wheels_RPM=3000,
        ke_l=1,
        ke_r=1,
        kq=1,
        accommodation_time_l=1.0,
        accommodation_time_r=1.0,
        sensor_distance=0.1,
        sensor_count=8,
    ):
        z = 1 / self.FPS
        self.car = car_dynamics(
            z,
            wheels_radius,
            wheels_distance,
            wheels_RPM,
            ke_l,
            ke_r,
            kq,
            accommodation_time_l,
            accommodation_time_r,
        )
        self.car_draw.set_size(self.car.get_size() * self.SCALE)
        self.line_sensor.set_coordinates(
            (self.car_draw.get_center()[0], self.car_draw.get_center()[1] - sensor_distance * self.SCALE)
        )
        self.line_sensor.set_size(sensor_count * self.SCALE * self.array_sensor_dist)  # 0.05 meter between sensors

    def set_encoders_count(self, count):
        self.car.encoders.set_pulses(count)

    def set_optical_flow_distance(self, distance):
        self.car.optical_flow.set_distance(distance)

    def set_future_points(self, count, space):
        self.future_points_count = count
        self.future_space = space
        Cluster.set_master(self.car_draw.get_center(), self.car_draw.get_size())  # set the master point
        Cluster.set_future_count(self.future_points_count, self.future_space)     # set the future points count

    # divide the track in clusters for rendering
    def configurate_cluster(self):
        # create clusters of points in the track
        cluster_matrix, position = generate_cluster(self.LENGTH, self.WIDTH, self.SCALE, self.x_track, self.y_track)

        # create the cluster
        for i in range(len(cluster_matrix)):
            cluster = Cluster(size=self.track_length * self.SCALE)
            for k in cluster_matrix[i]:
                cluster.add_point(k)
            self.track.set_obj(position[i][0], position[i][1], cluster)

    def _setup_simulator(self):
        # print the initialization message
        print("Initializing simulator...")

        # generate trajectory
        self.x_track, self.y_track = generate_track(
            self.track_type, noise_level=0.225, checkpoints=36, resolution=500, track_rad=30
        )
        self.win = len(self.x_track - 1)

        # create car
        self.car_draw = Car(self.simulator.get_center(), center=(1.36, 1.8))

        # create the track
        self.track = Track((self.LENGTH, self.WIDTH), self.SCALE, self.RENDER)

        # create line sensor
        self.line_sensor = LineSensor((self.car_draw.get_center()[0], self.car_draw.get_center()[1]))

        # create future points
        self.future_points = FuturePoints(self.car_draw.get_center(), size=self.track_length * 0.5 * self.SCALE)

        # create minimap
        minimap_position = (0.9 * self.simulator.get_center()[0], 1.75 * self.simulator.get_center()[1])
        self.minimap = MiniMap(minimap_position, (200, 150))
        for k in range(0, len(self.x_track), self.SCALE // 10):
            self.minimap.add_point((2 * self.x_track[k] / self.LENGTH, 2 * self.y_track[k] / self.WIDTH))

        # set track properties
        self.track.set_coordinates(
            ((self.x_track[0] + self.LENGTH // 2) * self.SCALE, (self.y_track[0] + self.WIDTH // 2) * self.SCALE)
        )
        self.track.set_center(self.car_draw.get_center())
        self.track.set_pivot(self.car_draw.get_center())

        # create display
        self.display = Display(self.simulator.get_center(), self.simulator.get_window_size())
        self._setup_display_graphs()

        # create coordinates display
        coordinates_position = (1.85 * self.simulator.get_center()[0], 1.95 * self.simulator.get_center()[1])
        self.coordinates_display = Statistics(coordinates_position)
        self.coordinates_display.set_offset(2)

        # if the screen is big, raise the font size
        if self.screen_size == FULL:
            self.coordinates_display.set_font_size(25)
        if self.screen_size == MEDIUM:
            self.coordinates_display.set_font_size(18)
        if self.screen_size == SMALL:
            self.coordinates_display.set_font_size(12)

        # create statistics displays
        self.fps_display = Statistics((1.99 * self.simulator.get_center()[0], 0.01 * self.simulator.get_center()[1]))

        # create display points
        self.track_percentage = Statistics((1.0 * self.simulator.get_center()[0], 1.95 * self.simulator.get_center()[1]))

        # pontuation of the track
        self.points = Statistics((0.25 * self.simulator.get_center()[0], 1.95 * self.simulator.get_center()[1]))

        # create compass
        self.compass = Compass((1.85 * self.simulator.get_center()[0], 1.75 * self.simulator.get_center()[1]))

        # add objects to the simulator
        # the order of the objects is the layer order
        self.simulator.add(self.track)
        self.simulator.add(self.car_draw)
        self.simulator.add(self.line_sensor)
        self.simulator.add(self.minimap)
        self.simulator.add(self.fps_display)
        self.simulator.add(self.coordinates_display)
        self.simulator.add(self.compass)
        self.simulator.add(self.future_points)
        self.simulator.add(self.track_percentage)
        self.simulator.add(self.points)
        self.simulator.add(self.display)

        # configurate the cluster
        self.configurate_cluster()

        # print the initialization message
        print("Simulator initialized")

        self.simulator.start()

    def get_rand_color(self):
        random.seed(None)
        return tuple(random.randint(0, 255) for _ in range(3))

    def _setup_display_graphs(self):
        self.display.add_graph("wheels")
        self.display.add_line_to_graph("wheels", "left", color=self.get_rand_color())
        self.display.add_line_to_graph("wheels", "right", color=self.get_rand_color())

        self.display.add_graph("car")
        self.display.add_line_to_graph("car", "vm", color=self.get_rand_color())
        self.display.add_line_to_graph("car", "ω", color=self.get_rand_color())

        self.display.add_graph("control")
        self.display.add_line_to_graph("control", "left", color=self.get_rand_color())
        self.display.add_line_to_graph("control", "right", color=self.get_rand_color())

        self.display.add_graph("perturbation")
        self.display.add_line_to_graph("perturbation", "left", color=self.get_rand_color())
        self.display.add_line_to_graph("perturbation", "right", color=self.get_rand_color())

        '''self.display.add_graph("free_response")
        self.display.add_line_to_graph("free_response", "d", color=self.get_rand_color())
        self.display.add_line_to_graph("free_response", "θ", color=self.get_rand_color())

        self.display.add_graph("future_control")
        self.display.add_line_to_graph("future_control", "left", color=self.get_rand_color())
        self.display.add_line_to_graph("future_control", "right", color=self.get_rand_color())

        self.display.add_graph("reference")
        self.display.add_line_to_graph("reference", "d", color=self.get_rand_color())
        self.display.add_line_to_graph("reference", "θ", color=self.get_rand_color())

        self.display.add_graph("error")
        self.display.add_line_to_graph("error", "d", color=self.get_rand_color())
        self.display.add_line_to_graph("error", "θ", color=self.get_rand_color())'''

    def _update_graphs(self):
        """Update all graphs with the current simulation values."""
        self.display.update_graph_data("wheels", "left", self.car.get_wheels_norm()[0])
        self.display.update_graph_data("wheels", "right", self.car.get_wheels_norm()[1])
        self.display.update_graph_data("car", "vm", self.car.speed_norm())
        self.display.update_graph_data("car", "ω", self.car.omega_norm())
        self.display.update_graph_data("control", "left", self.car.v1)
        self.display.update_graph_data("control", "right", self.car.v2)
        self.display.update_graph_data("perturbation", "left", self.car.q1)
        self.display.update_graph_data("perturbation", "right", self.car.q2)
        '''self.display.set_graph_data("future_control", "left", self.future_control_left)
        self.display.set_graph_data("future_control", "right", self.future_control_right)
        self.display.set_graph_data("reference", "d", self.future_v)
        self.display.set_graph_data("reference", "θ", self.future_omega)
        self.display.set_graph_data("free_response", "d", self.free_response_v)
        self.display.set_graph_data("free_response", "θ", self.free_response_omega)
        self.display.set_graph_data("error", "d", self.error_v)
        self.display.set_graph_data("error", "θ", self.error_omega)'''

    def update_FPS(self, fps):
        """
        update the FPS display with the given value.
        """
        self.fps_display.set_text(f"fps: {fps}")

    def update_coverage(self, coverage):
        """
        update the coverage display with the given value.
        """
        self.track_percentage.set_text(f"covered: {coverage}")

    def update_points(self, points):
        """Update the points display with the given value."""
        self.points.set_text(f"score: {points}")

    # ------------------------------------------------------------------
    # Simulation main loop helpers
    # ------------------------------------------------------------------
    def _handle_events(self) -> bool:
        """Process pygame events. Returns False when simulation should stop."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                print("Simulation stopped using X button")
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    print("Simulation stopped using ESC")
                    return False
                if event.key == pygame.K_p:
                    result = input("Enter perturbation value (default is 0.0): ")
                    self.perturbation = float(result)
                    print(f"Perturbation set to {self.perturbation}")
            self.display.verify_checkbox(event)
        return True

    def _step_physics(self, v1, v2, q1=0, q2=0):
        """Simulate physics and render the scene."""
        self.car.step(v1, v2, q1, q2)
        self._update_graphs()

        self.car.calculate_out_data()
        dx, dy, angle = self.car.get_delta_space()
        dx *= -self.SCALE
        dy *= -self.SCALE
        angle *= -1
        self.track.step(dx, dy, angle)

        self.compass.set_angle(-self.track.get_angle() - math.pi / 2)
        self.coordinates_display.set_text(
            f"x: {round(self.track.get_center()[0]/self.SCALE, 2):.2f} y: {round(self.track.get_center()[1]/self.SCALE, 2):.2f}"
        )

        self.minimap.set_player_position(
            (2 * self.track.get_center()[0] / (self.SCALE * self.LENGTH) - 1,
             -2 * self.track.get_center()[1] / (self.SCALE * self.WIDTH) + 1)
        )

        self.simulator.draw()

        if Cluster._next_point == self.win:
            print("Congratulations!")
            print("You win the game, you score is {:.2f}".format(100 * 100 / self.time_simulation))
            return None

        future_point = Cluster.get_next_point()
        self.future_points.set_points(future_point)
        future_point = [
            ((x - self.car_draw.get_center()[0]) / self.SCALE,
             (-y + self.car_draw.get_center()[1]) / self.SCALE)
            for x, y in future_point
        ]

        line = self.simulator.screen.subsurface(
            (
                self.line_sensor.get_x() - self.line_sensor.get_size() / 2,
                self.line_sensor.get_y() - 1,
                self.line_sensor.get_size(),
                1,
            )
        )
        line_arr = pygame.surfarray.pixels3d(line)
        line_pb = line_arr.mean(axis=2)  # calculate the mediam
        line_pb = np.array(line_pb[:, 0], dtype=np.uint8)  # remove dimension
        block_len = int(self.array_sensor_dist * self.SCALE)
        block_count = line_pb.shape[0] // block_len
        final_line = line_pb[: block_count * block_len].reshape(block_count, block_len).mean(axis=1)

        return (
            1 - final_line / 255,
            future_point,
            self.car
        )

    def step(self, v1, v2):
        """Public method used by external modules to advance the simulation."""
        if not self._handle_events():
            return None

        data = self._step_physics(v1, v2, self.perturbation, -self.perturbation)
        if data is None:
            pygame.quit()
            return None

        self.time_simulation += 1 / self.FPS
        coverage = Cluster._next_point / self.win * 100
        self.update_coverage("{:.2f}%".format(coverage))
        self.update_points("{:.2f}".format(100 * coverage / self.time_simulation))

        while (time.time() - self.timer) < 1 / self.FPS:
            pass

        self.update_FPS("{:.1f}".format(1 / (time.time() - self.timer)))
        self.timer = time.time()

        return data

_simulation: GameSimulation | None = None

def start_simulation(
    screen_size=MEDIUM,
    fps=120,
    length=100,
    width=100,
    scale=300,
    render=4,
    seed=None,
    track_type=0,
    track_length=0.02,
    sensor_spacing=0.001,
):
    """Create and configure a :class:`GameSimulation` instance."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    global _simulation
    if _simulation is not None:
        print("Simulator already initialized")
        return _simulation

    config = SimulationConfig(
        screen_size,
        fps,
        length,
        width,
        scale,
        render,
        track_type,
        track_length,
        sensor_spacing,
    )
    _simulation = GameSimulation(config)
    return _simulation

def _require_simulation() -> GameSimulation | None:
    if _simulation is None:
        print("Simulator not initialized")
        return None
    return _simulation

def set_car_dynamics(
    wheels_radius,
    wheels_distance,
    wheels_RPM,
    ke_l,
    ke_r,
    accommodation_time_l,
    accommodation_time_r,
    sensor_distance,
    sensor_count,
):
    sim = _require_simulation()
    if sim is None:
        return
    sim.setup_car_dynamics(
        wheels_radius,
        wheels_distance,
        wheels_RPM,
        ke_l,
        ke_r,
        1,
        accommodation_time_l,
        accommodation_time_r,
        sensor_distance,
        sensor_count,
    )

def set_future_points(count, space):
    sim = _require_simulation()
    if sim is None:
        return
    sim.set_future_points(count, space)

'''def set_graph_future_control(left, right):
    sim = _require_simulation()
    if sim is None:
        return
    sim.future_control_left = left
    sim.future_control_right = right

def set_graph_reference(omega, v):
    sim = _require_simulation()
    if sim is None:
        return
    sim.future_v = v
    sim.future_omega = omega

def set_graph_free_response(omega, v):
    sim = _require_simulation()
    if sim is None:
        return
    sim.free_response_omega = omega
    sim.free_response_v = v

def set_graph_forced_response(omega, v):
    sim = _require_simulation()
    if sim is None:
        return
    sim.forced_response_omega = omega
    sim.forced_response_v = v

def set_graph_error(omega, v):
    sim = _require_simulation()
    if sim is None:
        return
    sim.error_omega = omega
    sim.error_v = v'''

def step_simulation(v1, v2):
    sim = _require_simulation()
    if sim is None or sim.car is None:
        return None
    return sim.step(v1, v2)