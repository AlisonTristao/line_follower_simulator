import os
import math
import random
from collections import namedtuple

import numpy as np
import pygame

from graphics.graphics_elements import *
from graphics.track_generator import *
from car_modeling.car_dynamics import car_dynamics

"""
data returned by step_simulation:
    line            (np.ndarray) line sensor values in [0, 1]
    future_points   (np.ndarray) (N, 2) future track points in the car frame [m], columns (x lateral, y forward)
    speed           (float) linear speed [m/s]
    omega           (float) angular speed [rad/s], positive turns right
    wheels_speed    (tuple) (left, right) wheels speed [rad/s]
    lateral_error   (float) lateral distance from the car to the track [m]
"""
StepData = namedtuple("StepData", "line future_points speed omega wheels_speed lateral_error")

# elements drawn on the screen (they can be hidden)
DISPLAY_DEFAULTS = {
    "show_graphs": True,
    "show_fps": True,
    "show_info": True,
    "show_minimap": True,
    "show_compass": True,
    "show_coordinates": True,
    "show_score": True,
    "show_reference": True,
    "show_prediction": True,
    "show_sensor": True,
}

# shape of the generated track
TRACK_DEFAULTS = {
    "noise_level": 0.225,   # noise of the checkpoints (fraction of the radius)
    "checkpoints": 36,      # number of random checkpoints
    "resolution": 500,      # points of the spline between checkpoints
    "track_rad": 30,        # radius of the track [m]
}

class SimulatorController:
    def __init__(self, screen_size, fps, length, width, scale, render,
                 track_type=0, track_length=0.02, sensor_spacing=0.001, display=None, track=None):

        self._init_config(screen_size, fps, length, width, scale, render,
                          track_type, track_length, sensor_spacing)
        self.options = {**DISPLAY_DEFAULTS, **(display or {})}
        self.track_options = {**TRACK_DEFAULTS, **(track or {})}

        self._init_simulation_objects()
        self._setup_simulator()

    def _init_config(self, screen_size, fps, length, width, scale, render,
                     track_type, track_length, sensor_spacing):
        self.screen_size = screen_size
        self.FPS = fps
        self.LENGTH = length
        self.WIDTH = width
        self.SCALE = scale
        self.RENDER = render
        self.time_simulation = 0

        self.track_type = track_type
        self.track_length = track_length
        self.array_sensor_dist = sensor_spacing

    def _init_simulation_objects(self):
        self.simulator = Simulator(self.screen_size, self.FPS)
        self.car = None
        self.track = None
        self.display = None
        self.minimap = None
        self.fps_display = None
        self.coordinates_display = None
        self.info_display = None
        self.compass = None
        self.line_sensor = None
        self.future_points = None
        self.predicted_path = None
        self.track_percentage = None
        self.points = None
        self.win = None

        self.future_points_count = 10
        self.future_space = 30

    def setup_car_dynamics(self,  wheels_radius=0.04, wheels_distance=0.1, wheels_RPM=3000, ke_l=1, ke_r=1, kq=1, accommodation_time_l=1.0, accommodation_time_r=1.0, sensor_distance=0.1, sensor_count=8):
        z = 1/self.FPS
        self.car = car_dynamics(z, wheels_radius, wheels_distance, wheels_RPM, ke_l, ke_r, kq, accommodation_time_l, accommodation_time_r)
        self.car_draw.set_size(self.car.get_size()*self.SCALE)
        self.line_sensor.set_coordinates((self.car_draw.get_center()[0], self.car_draw.get_center()[1] - sensor_distance * self.SCALE))
        self.line_sensor.set_size(sensor_count * self.SCALE * self.array_sensor_dist)

    def set_future_points(self, count, space):
        self.future_points_count = count
        self.future_space = space
        Cluster.set_master(self.car_draw.get_center(), self.car_draw.get_size())    # set the master point
        Cluster.set_future_count(self.future_points_count, self.future_space)     # set the future points count

    # divide the track in clusters for rendering
    def configurate_cluster(self):
        cluster_matrix, position = generate_cluster(self.LENGTH, self.WIDTH, self.SCALE, self.x_track, self.y_track)
        for points, (row, col) in zip(cluster_matrix, position):
            cluster = Cluster(size=self.track_length*self.SCALE)
            cluster.set_points(points)
            self.track.set_obj(row, col, cluster)

    def _setup_simulator(self):
        print("Initializing simulator...")
        opt = self.options

        # generate trajectory
        self.x_track, self.y_track = generate_track(self.track_type, **self.track_options)
        self.win = len(self.x_track)

        # create car
        self.car_draw = Car(self.simulator.get_center(), center=(1.36, 1.8))

        # create the track
        self.track = Track((self.LENGTH, self.WIDTH), self.SCALE, self.RENDER)

        # create line sensor
        self.line_sensor = LineSensor((self.car_draw.get_center()[0], self.car_draw.get_center()[1]))

        # create future points (reference) and predicted path
        self.future_points = FuturePoints(self.car_draw.get_center(), size=self.track_length*0.5*self.SCALE)
        self.predicted_path = FuturePoints(self.car_draw.get_center(), color=(0, 120, 255), size=max(1, self.track_length*0.25*self.SCALE))

        # create minimap
        minimap_position = (0.9 * self.simulator.get_center()[0], 1.75 * self.simulator.get_center()[1])
        self.minimap = MiniMap(minimap_position, (200, 150))
        for k in range(0, len(self.x_track), max(1, self.SCALE // 10)):
            self.minimap.add_point((2 * self.x_track[k] / self.LENGTH, 2 * self.y_track[k] / self.WIDTH))

        # set track properties
        self.track.set_coordinates(((self.x_track[0] + self.LENGTH//2) * self.SCALE, (self.y_track[0] + self.WIDTH//2) * self.SCALE))
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
        font_size = {FULL: 25, MEDIUM: 18, SMALL: 12}
        self.coordinates_display.set_font_size(font_size[self.screen_size])

        # create statistics displays
        self.fps_display = Statistics((1.99 * self.simulator.get_center()[0], 0.01 * self.simulator.get_center()[1]))
        self.info_display = Statistics((0.70 * self.simulator.get_center()[0], 0.01 * self.simulator.get_center()[1]), color=(0, 0, 0))
        self.info_display.set_offset(2)
        self.info_display.set_text("")
        self.track_percentage = Statistics((1.0 * self.simulator.get_center()[0], 1.95 * self.simulator.get_center()[1]))
        self.points = Statistics((0.25 * self.simulator.get_center()[0], 1.95 * self.simulator.get_center()[1]))

        # create compass
        self.compass = Compass((1.85 * self.simulator.get_center()[0], 1.75 * self.simulator.get_center()[1]))

        # add objects to the simulator (the order of the objects is the layer order)
        layers = [
            (self.track, True),
            (self.car_draw, True),
            (self.line_sensor, opt["show_sensor"]),
            (self.minimap, opt["show_minimap"]),
            (self.fps_display, opt["show_fps"]),
            (self.info_display, opt["show_info"]),
            (self.coordinates_display, opt["show_coordinates"]),
            (self.compass, opt["show_compass"]),
            (self.future_points, opt["show_reference"]),
            (self.predicted_path, opt["show_prediction"]),
            (self.track_percentage, opt["show_score"]),
            (self.points, opt["show_score"]),
            (self.display, opt["show_graphs"]),
        ]
        for obj, visible in layers:
            if visible:
                self.simulator.add(obj)

        self.configurate_cluster()

        print("Simulator initialized")
        self.simulator.start()

    def _setup_display_graphs(self):
        # the graph colors are fixed so they do not touch the global random state
        rng = random.Random(0)
        self._color = lambda: tuple(rng.randint(0, 255) for _ in range(3))

        self.add_graph("wheels", ["left", "right"])
        self.add_graph("car", ["vm", "ω"], checked=False)
        self.add_graph("control", ["left", "right"])
        self.add_graph("perturbation", ["left", "right"], checked=False)

    def add_graph(self, name, lines, y_range=None, checked=None):
        self.display.add_graph(name, y_range, checked)
        for line in lines:
            self.display.add_line_to_graph(name, line, color=self._color())

    def _update_graphs(self):
        """
        update the time graphs with the car values.
        """
        wheels = self.car.get_wheels_norm()
        self.display.update_graph_data("wheels", "left", wheels[0])
        self.display.update_graph_data("wheels", "right", wheels[1])
        self.display.update_graph_data("car", "vm", self.car.speed_norm())
        self.display.update_graph_data("car", "ω", self.car.omega_norm())
        self.display.update_graph_data("control", "left", self.car.v1)
        self.display.update_graph_data("control", "right", self.car.v2)
        self.display.update_graph_data("perturbation", "left", self.car.q1)
        self.display.update_graph_data("perturbation", "right", self.car.q2)

    def to_screen(self, points):
        # car frame [m] (x lateral, y forward) -> screen [px]
        points = np.asarray(points, dtype=float).reshape(-1, 2)
        cx, cy = self.car_draw.get_center()
        return np.column_stack((cx + points[:, 0] * self.SCALE, cy - points[:, 1] * self.SCALE))

    def to_car_frame(self, points):
        # screen [px] -> car frame [m] (x lateral, y forward)
        points = np.asarray(points, dtype=float).reshape(-1, 2)
        cx, cy = self.car_draw.get_center()
        return np.column_stack(((points[:, 0] - cx) / self.SCALE, (cy - points[:, 1]) / self.SCALE))

    def car_pose(self):
        """
        pose of the car in the track coordinates (the same of x_track, y_track) [m, m, rad]
        heading is the angle of the forward direction of the car in this frame
        """
        x = self.track._x / self.SCALE - self.LENGTH // 2
        y = self.track._y / self.SCALE - self.WIDTH // 2
        a = self.track.get_angle()
        # screen forward (0, -1) rotated back to the track frame
        return x, y, math.atan2(-math.cos(a), -math.sin(a))

    def update_FPS(self, fps):
        self.fps_display.set_text(f"fps: {fps}")

    def update_coverage(self, coverage):
        self.track_percentage.set_text(f"covered: {coverage}")

    def update_points(self, points):
        self.points.set_text(f"score: {points}")

    def read_line_sensor(self):
        line = self.simulator.screen.subsurface((self.line_sensor.get_x() - self.line_sensor.get_size()/2, self.line_sensor.get_y() - 1, self.line_sensor.get_size(), 1))
        line_pb = pygame.surfarray.pixels3d(line)[:, 0, :].mean(axis=1)
        block_len = max(1, int(self.array_sensor_dist * self.SCALE))
        block_count = line_pb.shape[0] // block_len
        final_line = line_pb[:block_count * block_len].reshape(block_count, block_len).mean(axis=1)
        return 1 - final_line/255

    def step(self, v1, v2, q1=0, q2=0):
        """
        perform one simulation step with given movement and rotation inputs.
        """
        self.car.step(v1, v2, q1, q2)
        self._update_graphs()

        # move the track (the car is fixed on the screen)
        dx, dy, angle = self.car.get_space()
        self.track.step(-dx * self.SCALE, -dy * self.SCALE, -angle)

        # update compass and coordinates
        self.compass.set_angle(-self.track.get_angle() - math.pi / 2)
        x, y = self.track.get_center()
        self.coordinates_display.set_text(f"x: {x/self.SCALE:.2f} y: {y/self.SCALE:.2f}")

        # update minimap position
        self.minimap.set_player_position((2 * x/(self.SCALE * self.LENGTH) - 1, -2 * y/(self.SCALE * self.WIDTH) + 1))

        # render the simulator
        self.simulator.draw()

        # verify if win the game
        if Cluster._next_point >= self.win:
            print("Congratulations!")
            print("You win the game, you score is {:.2f}".format(100*100/self.time_simulation))
            return None

        # get the future points
        future_point = Cluster.get_next_point()
        self.future_points.set_points(future_point)
        lateral_error = self.to_car_frame(Cluster.get_current_point())[0, 0]

        return StepData(self.read_line_sensor(), self.to_car_frame(future_point), self.car.speed(), self.car.omega(),
                        self.car.get_wheels_speed(), lateral_error)

simulator = None
perturbation = 0.0
perturbation_step = 5.0
realtime = True

# why the last run stopped: "finished" (end of the track), "esc", "quit" (window closed) or None
stop_reason = None

def _check_simulator():
    if simulator is None:
        print("Simulator not initialized")
        return False
    return True

def reset_simulation():
    """
    clears the state of the previous run, so a new one can be started in the same process
    (the pygame window is kept open)
    """
    global simulator, perturbation, stop_reason
    simulator = None
    perturbation = 0.0
    stop_reason = None
    Cluster._next_point = 0
    Cluster._current_point = (0.0, 0.0)
    Cluster._arr_next_points = np.zeros_like(Cluster._arr_next_points)

def start_simulation(screen_size=MEDIUM, fps=120, length=100, width=100, scale=300, render=4, seed=None, track_type=0, track_length=0.02, sensor_spacing=0.001,
                     headless=False, real_time=True, display=None, track=None, perturbation_key_step=5.0):
    """
    headless:  runs without window (useful for experiments)
    real_time: limits the simulation to the fps (False runs as fast as possible)
    display:   elements shown on the screen (see DISPLAY_DEFAULTS)
    track:     shape of the generated track (see TRACK_DEFAULTS)
    """
    global simulator, realtime, perturbation_step

    if simulator is not None:
        print("Simulator already initialized")
        return simulator

    # define the seed
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    if headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        if screen_size == FULL:
            screen_size = MEDIUM

    realtime = real_time
    perturbation_step = perturbation_key_step
    simulator = SimulatorController(screen_size, fps, length, width, scale, render, track_type, track_length, sensor_spacing, display, track)
    return simulator

def set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke_l, ke_r, accommodation_time_l, accommodation_time_r, sensor_distance, sensor_count):
    if _check_simulator():
        simulator.setup_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke_l, ke_r, 1, accommodation_time_l, accommodation_time_r, sensor_distance, sensor_count)

def set_future_points(count, space):
    if _check_simulator():
        simulator.set_future_points(count, space)

def add_graph(name, lines, y_range=None, checked=None):
    """
    adds a graph to the display
        name    (str) title of the graph
        lines   (list of str) name of the lines
        y_range (tuple) (min, max) of the y axis
    """
    if _check_simulator():
        simulator.add_graph(name, lines, y_range, checked)

def set_graph_data(name, line, data):
    # replaces all the data of a line (e.g. a prediction along the horizon)
    if _check_simulator():
        simulator.display.set_graph_data(name, line, list(data))

def push_graph_data(name, line, value):
    # appends one value to a line (time graph)
    if _check_simulator():
        simulator.display.update_graph_data(name, line, value)

def set_predicted_path(points):
    # draws a path given in the car frame [m] (x lateral, y forward)
    if _check_simulator():
        simulator.predicted_path.set_points(simulator.to_screen(points))

def set_info(text):
    if _check_simulator():
        simulator.info_display.set_text(text)

def set_perturbation(value):
    global perturbation
    perturbation = value

def _handle_events():
    global perturbation, stop_reason
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print("Simulation stopped using X button")
            stop_reason = "quit"
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                print("Simulation stopped using ESC")
                stop_reason = "esc"
                return False
            # P/O increases/decreases the perturbation, R resets it
            if event.key in (pygame.K_p, pygame.K_o, pygame.K_r):
                if event.key == pygame.K_p:
                    perturbation += perturbation_step
                elif event.key == pygame.K_o:
                    perturbation -= perturbation_step
                else:
                    perturbation = 0.0
                print(f"Perturbation set to {perturbation}")

        simulator.display.verify_checkbox(event)
    return True

def step_simulation(v1, v2):
    """
    returns StepData or None when the run stops (see stop_reason); the window is kept open
    """
    global stop_reason

    # check if the simulator is initialized
    if simulator is None or simulator.car is None:
        print("Simulator not initialized")
        return None

    if not _handle_events():
        return None

    data = simulator.step(v1, v2, perturbation, -perturbation)
    if data is None:
        stop_reason = "finished"
        return None

    # integrate the time simulation
    simulator.time_simulation += 1/simulator.FPS

    # coverage and points of the track
    coverage = Cluster._next_point/simulator.win * 100
    simulator.update_coverage("{:.2f}%".format(coverage))
    simulator.update_points("{:.2f}".format(100*coverage/simulator.time_simulation))

    # fix the fps
    simulator.update_FPS("{:.1f}".format(simulator.simulator.tick(realtime)))

    return data

def get_car_pose():
    # (x, y, heading) of the car in the track coordinates (see get_track)
    return simulator.car_pose() if simulator else None

def get_track():
    # (x_track, y_track) points of the track [m]
    return (np.asarray(simulator.x_track), np.asarray(simulator.y_track)) if simulator else None

def get_time():
    return simulator.time_simulation if simulator else 0.0

def get_perturbation():
    return perturbation

def get_coverage():
    # percentage of the track already covered
    return Cluster._next_point/simulator.win * 100 if simulator else 0.0

def get_screen():
    # the pygame surface of the window (to draw the menus between the runs)
    return simulator.simulator.screen if simulator else pygame.display.get_surface()
